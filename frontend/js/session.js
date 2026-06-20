/* session.js · Session state management (localStorage-backed) */

const SESSION_KEY = 'saathi-session';

function generateId() {
  return 'sess-' + Math.random().toString(36).slice(2, 10) + '-' + Date.now();
}

export function createSession(grade, subject) {
  const session = {
    id: generateId(),
    startedAt: new Date().toISOString(),
    grade: parseInt(grade),
    subject,
    language: 'en',
    history: [],
  };
  saveSession(session);
  return session;
}

export function saveSession(session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function loadSession() {
  const raw = localStorage.getItem(SESSION_KEY);
  return raw ? JSON.parse(raw) : null;
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

export function addToHistory(session, entry) {
  session.history.push({
    ...entry,
    timestamp: new Date().toISOString(),
    rating: 0,
  });
  saveSession(session);
}

export function rateEntry(session, index, rating) {
  if (session.history[index]) {
    session.history[index].rating = rating;
    saveSession(session);
  }
}

export function updateSessionLanguage(session, lang) {
  session.language = lang;
  saveSession(session);
}

export function getSessionContext(session) {
  const lastEntry = session.history[session.history.length - 1];
  return {
    grade: session.grade,
    subject: session.subject,
    language: session.language,
    previous_topic: lastEntry?.topic || null,
    history: session.history.slice(-5).map(h => h.topic).filter(Boolean),
  };
}
