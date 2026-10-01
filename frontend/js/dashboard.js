/* dashboard.js · Teacher dashboard: history list, resume, and syllabus editor */

import { requireAuth, authFetch, getName, logout } from './auth.js';

if (requireAuth('teacher')) {
  init();
}

async function init() {
  document.getElementById('teacher-name').textContent = getName() || 'Teacher';
  document.getElementById('logout-btn').addEventListener('click', logout);

  await loadHistory();
  initSyllabus();
  initSchedule();
  initNotes();
}

// ── Class notes as Google Docs ──
function initNotes() {
  document.getElementById('notes-connect-btn').addEventListener('click', connectGoogle);
  document.getElementById('notes-disconnect-btn').addEventListener('click', disconnectGoogle);
  document.getElementById('notes-create-btn').addEventListener('click', createNotesDoc);
  document.getElementById('notes-append-btn').addEventListener('click', appendNote);

  // Google sends the teacher back here after they approve.
  const googleResult = new URLSearchParams(location.search).get('google');
  if (googleResult) {
    const statusEl = document.getElementById('notes-status');
    statusEl.textContent = googleResult === 'connected'
      ? 'Google account connected.'
      : 'Could not connect that Google account. Try again.';
    history.replaceState({}, '', location.pathname);
  }

  loadGoogleStatus();
}

async function loadGoogleStatus() {
  const disconnected = document.getElementById('notes-disconnected');
  const connected = document.getElementById('notes-connected');
  const unavailable = document.getElementById('notes-unavailable');

  try {
    const res = await authFetch('/api/auth/me/google');
    if (!res.ok) return;
    const data = await res.json();

    if (!data.configured) {
      disconnected.style.display = 'none';
      connected.style.display = 'none';
      unavailable.style.display = 'block';
      return;
    }

    unavailable.style.display = 'none';
    disconnected.style.display = data.connected ? 'none' : 'block';
    connected.style.display = data.connected ? 'block' : 'none';

    if (data.connected) {
      document.getElementById('notes-account').textContent = data.google_email
        ? `Connected as ${data.google_email}`
        : 'Google account connected';
      const grade = document.getElementById('syllabus-grade').value;
      const subject = document.getElementById('syllabus-subject').value;
      loadNotesDoc(grade, subject);
    }
  } catch {
    // notes are optional — the rest of the dashboard works regardless
  }
}

async function connectGoogle() {
  const statusEl = document.getElementById('notes-status');
  const res = await authFetch('/api/auth/google/authorize');
  if (!res.ok) {
    statusEl.textContent = 'Google notes are not switched on yet.';
    return;
  }
  location.href = (await res.json()).url;
}

async function disconnectGoogle() {
  await authFetch('/api/auth/me/google', { method: 'DELETE' });
  await loadGoogleStatus();
}

async function loadNotesDoc(grade, subject) {
  const link = document.getElementById('notes-open-link');
  const createBtn = document.getElementById('notes-create-btn');
  const appendArea = document.getElementById('notes-append-area');

  const res = await authFetch(`/api/auth/me/notes?grade=${grade}&subject=${encodeURIComponent(subject)}`);
  if (!res.ok) return;
  const data = await res.json();

  if (data.doc_url) {
    link.href = data.doc_url;
    link.style.display = 'inline-flex';
    createBtn.style.display = 'none';
    appendArea.style.display = 'block';
  } else {
    link.style.display = 'none';
    createBtn.style.display = 'inline-flex';
    appendArea.style.display = 'none';
  }
}

async function createNotesDoc() {
  const grade = document.getElementById('syllabus-grade').value;
  const subject = document.getElementById('syllabus-subject').value;
  const statusEl = document.getElementById('notes-status');

  statusEl.textContent = 'Creating the doc…';
  const res = await authFetch('/api/auth/me/notes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ grade: Number(grade), subject }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    statusEl.textContent = data.detail || 'Could not create the notes doc';
    return;
  }
  statusEl.textContent = 'Notes doc ready.';
  await loadNotesDoc(grade, subject);
}

async function appendNote() {
  const grade = document.getElementById('syllabus-grade').value;
  const subject = document.getElementById('syllabus-subject').value;
  const textarea = document.getElementById('notes-append-text');
  const statusEl = document.getElementById('notes-status');
  const text = textarea.value.trim();
  if (!text) return;

  statusEl.textContent = 'Saving to Google Docs…';
  const res = await authFetch('/api/auth/me/notes/append', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ grade: Number(grade), subject, text }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    statusEl.textContent = data.detail || 'Could not save the note';
    return;
  }
  textarea.value = '';
  statusEl.textContent = 'Added to your Google Doc.';
  setTimeout(() => {
    if (statusEl.textContent === 'Added to your Google Doc.') statusEl.textContent = '';
  }, 2500);
}

async function loadHistory() {
  const listEl = document.getElementById('history-list');
  try {
    const res = await authFetch('/api/auth/me/history');
    if (!res.ok) throw new Error('Failed to load history');
    const rows = await res.json();
    renderHistory(listEl, rows);
  } catch (err) {
    listEl.innerHTML = `<div class="history-empty">Couldn't load history: ${err.message}</div>`;
  }
}

function renderHistory(listEl, rows) {
  if (rows.length === 0) {
    listEl.innerHTML = '<div class="history-empty">No sessions yet — launch the classroom to get started.</div>';
    return;
  }
  listEl.innerHTML = '';
  for (const row of rows) {
    const item = document.createElement('div');
    item.className = 'history-item card';
    item.innerHTML = `
      <div>
        <div>${row.topic || row.intent}</div>
        <div class="meta">${row.intent} · Grade ${row.grade} · ${row.subject} · ${new Date(row.created_at).toLocaleString()}</div>
      </div>
      <button class="btn btn-secondary btn-sm resume-btn">Resume</button>
    `;
    item.querySelector('.resume-btn').addEventListener('click', () => resume(row));
    listEl.appendChild(item);
  }
}

function resume(row) {
  sessionStorage.setItem('saathi-resume', JSON.stringify(row));
  location.href = 'app.html';
}

// ── Syllabus editor ──
function initSyllabus() {
  const gradeSelect   = document.getElementById('syllabus-grade');
  const subjectSelect = document.getElementById('syllabus-subject');
  const textarea      = document.getElementById('syllabus-content');
  const saveBtn       = document.getElementById('syllabus-save-btn');
  const statusEl      = document.getElementById('syllabus-status');
  const pdfInput      = document.getElementById('syllabus-pdf-input');

  const loadForSelection = () => {
    loadSyllabus(gradeSelect.value, subjectSelect.value, textarea, statusEl);
    loadSchedule(gradeSelect.value, subjectSelect.value);
    loadSchoolTimetable(gradeSelect.value, subjectSelect.value);
    if (document.getElementById('notes-connected').style.display === 'block') {
      loadNotesDoc(gradeSelect.value, subjectSelect.value);
    }
  };

  gradeSelect.addEventListener('change', loadForSelection);
  subjectSelect.addEventListener('change', loadForSelection);
  saveBtn.addEventListener('click', () =>
    saveSyllabus(gradeSelect.value, subjectSelect.value, textarea.value, statusEl)
  );
  pdfInput.addEventListener('change', () => {
    if (pdfInput.files[0]) {
      uploadSyllabusPdf(gradeSelect.value, subjectSelect.value, pdfInput.files[0], textarea, statusEl);
      pdfInput.value = '';
    }
  });

  loadForSelection();
}

async function loadSyllabus(grade, subject, textarea, statusEl) {
  statusEl.textContent = 'Loading…';
  try {
    const res = await authFetch(`/api/auth/me/syllabus?grade=${grade}&subject=${encodeURIComponent(subject)}`);
    if (!res.ok) throw new Error('Failed to load syllabus');
    const data = await res.json();
    textarea.value = data.content || '';
    statusEl.textContent = '';
  } catch (err) {
    statusEl.textContent = err.message;
  }
}

async function saveSyllabus(grade, subject, content, statusEl) {
  statusEl.textContent = 'Saving…';
  try {
    const res = await authFetch('/api/auth/me/syllabus', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ grade: Number(grade), subject, content }),
    });
    if (!res.ok) throw new Error('Failed to save syllabus');
    statusEl.textContent = 'Saved.';
    setTimeout(() => { if (statusEl.textContent === 'Saved.') statusEl.textContent = ''; }, 2000);
  } catch (err) {
    statusEl.textContent = err.message;
  }
}

async function uploadSyllabusPdf(grade, subject, file, textarea, statusEl) {
  statusEl.textContent = 'Reading PDF…';
  try {
    const formData = new FormData();
    formData.append('grade', grade);
    formData.append('subject', subject);
    formData.append('file', file);
    const res = await authFetch('/api/auth/me/syllabus/upload', { method: 'POST', body: formData });
    if (!res.ok) throw new Error('Failed to extract syllabus from PDF');
    const data = await res.json();
    textarea.value = data.content || '';
    statusEl.textContent = 'Extracted and saved.';
    setTimeout(() => { if (statusEl.textContent === 'Extracted and saved.') statusEl.textContent = ''; }, 2500);
  } catch (err) {
    statusEl.textContent = err.message;
  }
}

// ── Class timetable (calendar) ──
let scheduleRows = [];
let calendarViewDate = new Date();

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function initSchedule() {
  document.getElementById('schedule-generate-btn').addEventListener('click', onGenerateSchedule);

  const ttInput = document.getElementById('school-timetable-input');
  ttInput.addEventListener('change', () => {
    if (ttInput.files[0]) {
      uploadSchoolTimetable(ttInput.files[0]);
      ttInput.value = '';
    }
  });
  document.getElementById('tt-cal-prev').addEventListener('click', () => shiftCalendarMonth(-1));
  document.getElementById('tt-cal-next').addEventListener('click', () => shiftCalendarMonth(1));
  document.getElementById('tt-detail-close').addEventListener('click', closeDetail);
}

function shiftCalendarMonth(delta) {
  calendarViewDate = new Date(calendarViewDate.getFullYear(), calendarViewDate.getMonth() + delta, 1);
  renderCalendar();
}

async function onGenerateSchedule() {
  const grade      = document.getElementById('syllabus-grade').value;
  const subject    = document.getElementById('syllabus-subject').value;
  const startDate  = document.getElementById('schedule-start').value;
  const endDate    = document.getElementById('schedule-end').value;
  const perWeek    = document.getElementById('schedule-per-week').value;
  const statusEl   = document.getElementById('schedule-status');

  if (!startDate || !endDate) {
    statusEl.textContent = 'Pick a term start and end date.';
    return;
  }

  statusEl.textContent = 'Generating with AI… this can take a moment.';
  try {
    const res = await authFetch('/api/auth/me/schedule/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        grade: Number(grade), subject,
        start_date: startDate, end_date: endDate,
        classes_per_week: Number(perWeek),
      }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || 'Failed to generate timetable');
    }
    const rows = await res.json();
    renderSchedule(rows);
    statusEl.textContent = `Generated ${rows.length} classes.`;
  } catch (err) {
    statusEl.textContent = err.message;
  }
}

async function uploadSchoolTimetable(file) {
  const grade    = document.getElementById('syllabus-grade').value;
  const subject  = document.getElementById('syllabus-subject').value;
  const statusEl = document.getElementById('school-timetable-status');

  statusEl.textContent = 'Reading timetable…';
  try {
    const formData = new FormData();
    formData.append('grade', grade);
    formData.append('subject', subject);
    formData.append('file', file);
    const res = await authFetch('/api/auth/me/timetable/upload', { method: 'POST', body: formData });
    if (!res.ok) throw new Error('Could not read that timetable');
    renderTimetableStatus(await res.json());
  } catch (err) {
    statusEl.textContent = err.message;
  }
}

async function loadSchoolTimetable(grade, subject) {
  try {
    const res = await authFetch(`/api/auth/me/timetable?grade=${grade}&subject=${encodeURIComponent(subject)}`);
    if (!res.ok) return;
    renderTimetableStatus(await res.json());
  } catch {
    // optional feature — schedule generation still works without it
  }
}

function renderTimetableStatus(data) {
  const statusEl = document.getElementById('school-timetable-status');
  if (!data.weekdays || data.weekdays.length === 0) {
    statusEl.textContent = '';
    return;
  }
  const days = data.weekdays.map((d) => DAY_NAMES[d]).join(', ');
  statusEl.textContent = `Classes on ${days} — schedules will use these days.`;
}

async function loadSchedule(grade, subject) {
  try {
    const res = await authFetch(`/api/auth/me/schedule?grade=${grade}&subject=${encodeURIComponent(subject)}`);
    if (!res.ok) return;
    renderSchedule(await res.json());
  } catch {
    // silent — timetable is optional, syllabus load already reports errors
  }
}

function renderSchedule(rows) {
  scheduleRows = rows;
  const calendar = document.getElementById('schedule-calendar');
  const progress = document.getElementById('schedule-progress');
  const bento = document.getElementById('bento-overview');
  const bentoEmpty = document.getElementById('bento-empty');
  closeDetail();

  if (rows.length === 0) {
    calendar.style.display = 'none';
    progress.style.display = 'none';
    bento.style.display = 'none';
    bentoEmpty.style.display = 'block';
    return;
  }

  const todayStr = new Date().toISOString().slice(0, 10);
  const doneCount = rows.filter((r) => r.scheduled_date < todayStr).length;
  const pct = Math.round((doneCount / rows.length) * 100);

  progress.style.display = 'block';
  document.getElementById('schedule-progress-fill').style.width = `${pct}%`;
  document.getElementById('schedule-progress-text').textContent =
    `${doneCount} of ${rows.length} classes done · ${rows.length - doneCount} remaining · ${pct}% of syllabus covered`;

  bentoEmpty.style.display = 'none';
  bento.style.display = 'grid';
  renderBentoOverview(rows, todayStr, doneCount, pct);

  calendar.style.display = 'block';

  // Jump the calendar to the first upcoming class (or first class overall) on a fresh load.
  const upcoming = rows.find((r) => r.scheduled_date >= todayStr) || rows[0];
  const [y, m] = upcoming.scheduled_date.split('-').map(Number);
  calendarViewDate = new Date(y, m - 1, 1);

  renderCalendar();
}

const RING_CIRCUMFERENCE = 263.9;

function renderBentoOverview(rows, todayStr, doneCount, pct) {
  const grade   = document.getElementById('syllabus-grade').value;
  const subject = document.getElementById('syllabus-subject').value;

  const nextUp = rows.find((r) => r.scheduled_date >= todayStr);
  const nextBody = document.getElementById('bento-next-body');

  if (nextUp) {
    const dateLabel = new Date(nextUp.scheduled_date + 'T00:00:00')
      .toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });
    nextBody.innerHTML = `
      <div class="bento-next-topic">${nextUp.chapter}</div>
      <div class="bento-next-meta">Class ${nextUp.class_number} · ${dateLabel} · ${nextUp.focus}</div>
      <button class="btn btn-primary btn-sm" id="bento-launch-btn">Launch this lesson</button>
    `;
    document.getElementById('bento-launch-btn').addEventListener('click', () =>
      launchLesson(grade, subject, nextUp.chapter)
    );
  } else {
    nextBody.innerHTML = `<div class="bento-next-empty">All ${rows.length} classes covered. Generate a new term to keep going.</div>`;
  }

  document.getElementById('bento-ring-text').textContent = `${pct}%`;
  document.getElementById('bento-ring-fill').style.strokeDashoffset =
    String(RING_CIRCUMFERENCE * (1 - pct / 100));

  document.getElementById('bento-done-num').textContent = doneCount;
  document.getElementById('bento-remaining-num').textContent = rows.length - doneCount;
}

const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function renderCalendar() {
  const grid  = document.getElementById('tt-cal-grid');
  const title = document.getElementById('tt-cal-title');
  const year  = calendarViewDate.getFullYear();
  const month = calendarViewDate.getMonth();

  title.textContent = calendarViewDate.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });

  const byDate = {};
  for (const row of scheduleRows) {
    (byDate[row.scheduled_date] ||= []).push(row);
  }

  const todayStr = new Date().toISOString().slice(0, 10);
  const firstDow = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  grid.innerHTML = '';
  for (const label of DOW) {
    const el = document.createElement('div');
    el.className = 'tt-cal-dow';
    el.textContent = label;
    grid.appendChild(el);
  }
  for (let i = 0; i < firstDow; i++) {
    const el = document.createElement('div');
    el.className = 'tt-cal-day tt-empty';
    grid.appendChild(el);
  }
  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const dayRows = byDate[dateStr] || [];
    const cell = document.createElement('div');
    cell.className = 'tt-cal-day';
    if (dateStr === todayStr) cell.classList.add('tt-today');
    if (dayRows.length > 0) {
      cell.classList.add('tt-has-class');
      if (dateStr < todayStr) cell.classList.add('tt-done');
      cell.title = dayRows.map((r) => `${r.chapter} — ${r.focus}`).join('\n');
      cell.addEventListener('click', () => openDetail(dayRows[0]));
    }
    cell.innerHTML = `
      <div class="tt-cal-daynum">${day}</div>
      ${dayRows.slice(0, 1).map((r) => `<div class="tt-cal-chip">${r.chapter}</div>`).join('')}
    `;
    grid.appendChild(cell);
  }
}

function openDetail(row) {
  const grade   = document.getElementById('syllabus-grade').value;
  const subject = document.getElementById('syllabus-subject').value;
  const detail  = document.getElementById('tt-detail');

  document.getElementById('tt-detail-title').textContent =
    `Class ${row.class_number} · ${new Date(row.scheduled_date + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })} · ${row.chapter}`;
  document.getElementById('tt-detail-focus').textContent = row.focus;

  const launchBtn = document.getElementById('tt-detail-launch');
  launchBtn.onclick = () => launchLesson(grade, subject, row.chapter);

  const removeBtn = document.getElementById('tt-detail-remove');
  removeBtn.onclick = () => deleteScheduleEntry(row.id);

  detail.style.display = 'block';
}

function closeDetail() {
  document.getElementById('tt-detail').style.display = 'none';
}

function launchLesson(grade, subject, chapter) {
  sessionStorage.setItem('saathi-launch-topic', JSON.stringify({ grade: Number(grade), subject, chapter }));
  location.href = 'app.html';
}

async function deleteScheduleEntry(id) {
  await authFetch(`/api/auth/me/schedule/${id}`, { method: 'DELETE' });
  const grade   = document.getElementById('syllabus-grade').value;
  const subject = document.getElementById('syllabus-subject').value;
  await loadSchedule(grade, subject);
}
