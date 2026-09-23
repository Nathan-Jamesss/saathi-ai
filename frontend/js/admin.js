/* admin.js · Admin dashboard: teacher management */

import { requireAuth, authFetch, logout } from './auth.js';

if (requireAuth('admin')) {
  init();
}

async function init() {
  document.getElementById('logout-btn').addEventListener('click', logout);
  document.getElementById('add-teacher-form').addEventListener('submit', onAddTeacher);
  await loadOverview();
  await loadTeachers();
}

async function loadOverview() {
  const res = await authFetch('/api/auth/admin/overview');
  if (!res.ok) return;
  const data = await res.json();

  document.getElementById('stat-total-teachers').textContent = data.total_teachers;
  document.getElementById('stat-active-teachers').textContent = data.active_teachers;
  document.getElementById('stat-total-sessions').textContent = data.total_sessions;
  document.getElementById('stat-total-scheduled').textContent = data.total_scheduled_classes;

  renderCoverageTable(data.coverage);
}

function renderCoverageTable(coverage) {
  const grades = [...new Set(coverage.map((c) => c.grade))];
  const subjects = [...new Set(coverage.map((c) => c.subject))];
  const bySubjectGrade = {};
  for (const cell of coverage) {
    bySubjectGrade[`${cell.grade}|${cell.subject}`] = cell.teachers;
  }

  const table = document.getElementById('coverage-table');
  let html = '<thead><tr><th></th>';
  for (const subject of subjects) {
    html += `<th>${subject.charAt(0).toUpperCase() + subject.slice(1)}</th>`;
  }
  html += '</tr></thead><tbody>';
  for (const grade of grades) {
    html += `<tr><th class="coverage-row-label">Class ${grade}</th>`;
    for (const subject of subjects) {
      const teachers = bySubjectGrade[`${grade}|${subject}`] || [];
      const covered = teachers.length > 0;
      html += `<td class="${covered ? 'coverage-cell covered' : 'coverage-cell gap'}">${covered ? teachers.join(', ') : '—'}</td>`;
    }
    html += '</tr>';
  }
  html += '</tbody>';
  table.innerHTML = html;
}

async function loadTeachers() {
  const listEl = document.getElementById('teacher-list');
  const res = await authFetch('/api/auth/admin/teachers');
  if (!res.ok) {
    listEl.innerHTML = '<div class="history-empty">Failed to load teachers.</div>';
    return;
  }
  const teachers = await res.json();
  if (teachers.length === 0) {
    listEl.innerHTML = '<div class="history-empty">No teachers yet.</div>';
    return;
  }
  listEl.innerHTML = '';
  for (const t of teachers) {
    const lastActive = t.last_active
      ? new Date(t.last_active).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
      : 'never used';
    const item = document.createElement('div');
    item.className = 'history-item card';
    item.innerHTML = `
      <div>
        <div>${t.name} — ${t.email}</div>
        <div class="meta">${t.session_count} sessions · last active ${lastActive} · ${t.is_active ? 'active' : 'deactivated'}</div>
      </div>
      <button class="btn btn-secondary btn-sm toggle-btn">${t.is_active ? 'Deactivate' : 'Activate'}</button>
    `;
    item.querySelector('.toggle-btn').addEventListener('click', () => toggleTeacher(t.id, !t.is_active));
    listEl.appendChild(item);
  }
}

async function toggleTeacher(id, isActive) {
  await authFetch(`/api/auth/admin/teachers/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_active: isActive }),
  });
  await loadOverview();
  await loadTeachers();
}

async function onAddTeacher(e) {
  e.preventDefault();
  const errorEl = document.getElementById('add-error');
  errorEl.textContent = '';
  const name = document.getElementById('new-name').value.trim();
  const email = document.getElementById('new-email').value.trim();
  const password = document.getElementById('new-password').value;
  const res = await authFetch('/api/auth/admin/teachers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    errorEl.textContent = data.detail || 'Failed to add teacher';
    return;
  }
  e.target.reset();
  await loadOverview();
  await loadTeachers();
}
