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

function initSchedule() {
  document.getElementById('schedule-generate-btn').addEventListener('click', onGenerateSchedule);
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
  closeDetail();

  if (rows.length === 0) {
    calendar.style.display = 'none';
    progress.style.display = 'none';
    return;
  }

  const todayStr = new Date().toISOString().slice(0, 10);
  const doneCount = rows.filter((r) => r.scheduled_date < todayStr).length;
  const pct = Math.round((doneCount / rows.length) * 100);

  progress.style.display = 'block';
  document.getElementById('schedule-progress-fill').style.width = `${pct}%`;
  document.getElementById('schedule-progress-text').textContent =
    `${doneCount} of ${rows.length} classes done · ${rows.length - doneCount} remaining · ${pct}% of syllabus covered`;

  calendar.style.display = 'block';

  // Jump the calendar to the first upcoming class (or first class overall) on a fresh load.
  const upcoming = rows.find((r) => r.scheduled_date >= todayStr) || rows[0];
  const [y, m] = upcoming.scheduled_date.split('-').map(Number);
  calendarViewDate = new Date(y, m - 1, 1);

  renderCalendar();
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
