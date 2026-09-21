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

// ── Class timetable ──
function initSchedule() {
  const generateBtn = document.getElementById('schedule-generate-btn');
  generateBtn.addEventListener('click', onGenerateSchedule);
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
  const table = document.getElementById('schedule-table');
  const body  = document.getElementById('schedule-table-body');
  if (rows.length === 0) {
    table.style.display = 'none';
    return;
  }
  table.style.display = 'table';
  body.innerHTML = '';
  for (const row of rows) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.class_number}</td>
      <td>${new Date(row.scheduled_date + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</td>
      <td>${row.chapter}</td>
      <td>${row.focus}</td>
      <td><button class="btn btn-ghost btn-sm delete-class-btn">Remove</button></td>
    `;
    tr.querySelector('.delete-class-btn').addEventListener('click', () => deleteScheduleEntry(row.id, tr));
    body.appendChild(tr);
  }
}

async function deleteScheduleEntry(id, tr) {
  await authFetch(`/api/auth/me/schedule/${id}`, { method: 'DELETE' });
  tr.remove();
  const body = document.getElementById('schedule-table-body');
  if (body.children.length === 0) {
    document.getElementById('schedule-table').style.display = 'none';
  }
}
