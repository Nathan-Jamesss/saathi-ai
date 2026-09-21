/* admin.js · Admin dashboard: teacher management */

import { requireAuth, authFetch, logout } from './auth.js';

if (requireAuth('admin')) {
  init();
}

async function init() {
  document.getElementById('logout-btn').addEventListener('click', logout);
  document.getElementById('add-teacher-form').addEventListener('submit', onAddTeacher);
  await loadTeachers();
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
    const item = document.createElement('div');
    item.className = 'history-item card';
    item.innerHTML = `
      <div>
        <div>${t.name} — ${t.email}</div>
        <div class="meta">${t.session_count} sessions · ${t.is_active ? 'active' : 'deactivated'}</div>
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
  await loadTeachers();
}
