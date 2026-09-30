/* admin.js · Admin dashboard: teacher management */

import { requireAuth, authFetch, logout } from './auth.js';

if (requireAuth('admin')) {
  init();
}

async function init() {
  document.getElementById('logout-btn').addEventListener('click', logout);
  document.getElementById('add-teacher-form').addEventListener('submit', onAddTeacher);
  document.getElementById('admin-sched-days').addEventListener('change', loadAdminSchedule);
  document.getElementById('admin-add-class-form').addEventListener('submit', onAddClass);
  await loadOverview();
  await loadTeachers();
  await loadAdminSchedule();
}

// ── Upcoming classes across all teachers ──
function formatDate(iso) {
  return new Date(iso + 'T00:00:00').toLocaleDateString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric',
  });
}

async function loadAdminSchedule() {
  const days = document.getElementById('admin-sched-days').value;
  const table = document.getElementById('admin-schedule-table');
  const empty = document.getElementById('admin-schedule-empty');

  const res = await authFetch(`/api/auth/admin/schedule?days=${days}`);
  if (!res.ok) {
    table.innerHTML = '';
    empty.textContent = 'Could not load the schedule.';
    empty.style.display = 'block';
    return;
  }

  const rows = await res.json();
  if (rows.length === 0) {
    table.innerHTML = '';
    empty.textContent = 'No classes scheduled in this window.';
    empty.style.display = 'block';
    return;
  }

  empty.style.display = 'none';
  table.innerHTML = `
    <thead><tr>
      <th>Date</th><th>Teacher</th><th>Class</th><th>Chapter</th><th>Focus</th><th></th>
    </tr></thead>
    <tbody></tbody>
  `;
  const body = table.querySelector('tbody');
  for (const row of rows) {
    body.appendChild(buildScheduleRow(row));
  }
}

function buildScheduleRow(row) {
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td>${formatDate(row.scheduled_date)}</td>
    <td>${row.teacher_name}</td>
    <td>Class ${row.grade} · ${row.subject}</td>
    <td>${row.chapter}</td>
    <td>${row.focus}</td>
    <td style="white-space:nowrap;">
      <button class="btn btn-secondary btn-sm edit-btn">Edit</button>
      <button class="btn btn-ghost btn-sm del-btn">Remove</button>
    </td>
  `;
  tr.querySelector('.edit-btn').addEventListener('click', () => startEditRow(tr, row));
  tr.querySelector('.del-btn').addEventListener('click', () => deleteClass(row.id));
  return tr;
}

function startEditRow(tr, row) {
  tr.innerHTML = `
    <td><input type="date" class="edit-date" value="${row.scheduled_date}" /></td>
    <td>${row.teacher_name}</td>
    <td>Class ${row.grade} · ${row.subject}</td>
    <td><input type="text" class="edit-chapter" value="${row.chapter.replace(/"/g, '&quot;')}" /></td>
    <td><input type="text" class="edit-focus" value="${row.focus.replace(/"/g, '&quot;')}" /></td>
    <td style="white-space:nowrap;">
      <button class="btn btn-primary btn-sm save-btn">Save</button>
      <button class="btn btn-ghost btn-sm cancel-btn">Cancel</button>
    </td>
  `;
  tr.querySelector('.cancel-btn').addEventListener('click', () => {
    tr.replaceWith(buildScheduleRow(row));
  });
  tr.querySelector('.save-btn').addEventListener('click', async () => {
    const updated = {
      chapter: tr.querySelector('.edit-chapter').value.trim(),
      focus: tr.querySelector('.edit-focus').value.trim(),
      scheduled_date: tr.querySelector('.edit-date').value,
    };
    const res = await authFetch(`/api/auth/admin/schedule/${row.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updated),
    });
    if (res.ok) {
      await loadAdminSchedule();
    }
  });
}

async function deleteClass(id) {
  await authFetch(`/api/auth/admin/schedule/${id}`, { method: 'DELETE' });
  await loadAdminSchedule();
}

async function onAddClass(e) {
  e.preventDefault();
  const statusEl = document.getElementById('admin-add-class-status');
  statusEl.textContent = 'Adding…';

  const res = await authFetch('/api/auth/admin/schedule', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      teacher_id: Number(document.getElementById('ac-teacher').value),
      grade: Number(document.getElementById('ac-grade').value),
      subject: document.getElementById('ac-subject').value,
      chapter: document.getElementById('ac-chapter').value.trim(),
      focus: document.getElementById('ac-focus').value.trim(),
      scheduled_date: document.getElementById('ac-date').value,
    }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    statusEl.textContent = data.detail || 'Could not add the class';
    return;
  }
  e.target.reset();
  statusEl.textContent = 'Added.';
  setTimeout(() => { if (statusEl.textContent === 'Added.') statusEl.textContent = ''; }, 2000);
  await loadAdminSchedule();
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
  const teacherSelect = document.getElementById('ac-teacher');
  teacherSelect.innerHTML = teachers
    .map((t) => `<option value="${t.id}">${t.name} (${t.email})</option>`)
    .join('');

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
