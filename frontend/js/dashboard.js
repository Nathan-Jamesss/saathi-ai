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

  const loadForSelection = () => loadSyllabus(gradeSelect.value, subjectSelect.value, textarea, statusEl);

  gradeSelect.addEventListener('change', loadForSelection);
  subjectSelect.addEventListener('change', loadForSelection);
  saveBtn.addEventListener('click', () =>
    saveSyllabus(gradeSelect.value, subjectSelect.value, textarea.value, statusEl)
  );

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
