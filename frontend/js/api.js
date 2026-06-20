/* api.js · Backend API calls */

// Local dev uses localhost; deployed frontend uses the Render backend.
// After deploy, replace the production URL with your actual Render service URL.
const BACKEND_URL = ['localhost', '127.0.0.1'].includes(location.hostname)
  ? 'http://localhost:8000'
  : 'https://saathi-ai-hfqi.onrender.com';

export async function processTranscript(transcript, sessionContext, regenerate = false) {
  const res = await fetch(`${BACKEND_URL}/api/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transcript, session: sessionContext, regenerate }),
    signal: AbortSignal.timeout(90000),  // cold-started server can take ~30-50s
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Server error ${res.status}`);
  }
  return res.json();
}

export async function fetchTTS(text, language) {
  const res = await fetch(`${BACKEND_URL}/api/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language }),
  });
  if (!res.ok) throw new Error('TTS request failed');
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export async function checkHealth() {
  const res = await fetch(`${BACKEND_URL}/api/health`, {
    signal: AbortSignal.timeout(10000),
  });
  return res.ok ? res.json() : null;
}

export async function exportSession(session) {
  const res = await fetch(`${BACKEND_URL}/api/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session }),
  });
  if (!res.ok) throw new Error('Export request failed');
  return res.json();
}
