/* auth.js · Login/signup/session-token management */

const TOKEN_KEY = 'saathi-token';
const ROLE_KEY  = 'saathi-role';
const NAME_KEY  = 'saathi-name';

const BACKEND_URL = ['localhost', '127.0.0.1'].includes(location.hostname)
  ? 'http://localhost:8000'
  : 'https://saathi-ai-hfqi.onrender.com';

function storeSession({ token, role, name }) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(ROLE_KEY, role);
  localStorage.setItem(NAME_KEY, name);
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRole() {
  return localStorage.getItem(ROLE_KEY);
}

export function getName() {
  return localStorage.getItem(NAME_KEY);
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(NAME_KEY);
  location.href = 'login.html';
}

async function _authRequest(path, body) {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  storeSession(data);
  return data;
}

export function signup({ email, password, name, school }) {
  return _authRequest('/api/auth/signup', { email, password, name, school });
}

export function login({ email, password }) {
  return _authRequest('/api/auth/login', { email, password });
}

export async function authFetch(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(`${BACKEND_URL}${path}`, { ...options, headers });
}

export function requireAuth(expectedRole) {
  const token = getToken();
  if (!token) {
    location.href = 'login.html';
    return false;
  }
  if (expectedRole && getRole() !== expectedRole) {
    location.href = getRole() === 'admin' ? 'admin.html' : 'dashboard.html';
    return false;
  }
  return true;
}
