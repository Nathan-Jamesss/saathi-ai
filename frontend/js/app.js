/* app.js · Main app controller */

import { createSession, loadSession, saveSession, clearSession, addToHistory, rateEntry, updateSessionLanguage, getSessionContext } from './session.js';
import { STTController, detectLanguageFromText, langCodeToShort } from './stt.js';
import { processTranscript, fetchTTS } from './api.js';
import { renderPreview } from './renderer.js';
import { DisplaySender } from './broadcast.js';
import { exportSessionPDF } from './export.js';

// ── State ──
let session = null;
let stt = null;
let currentResponse = null;
let currentHistoryIndex = -1;
const sender = new DisplaySender();

// ── DOM refs ──
const sessionModal   = document.getElementById('session-modal');
const appContainer   = document.getElementById('app-container');
const beginBtn       = document.getElementById('begin-session-btn');
const gradeSelect    = document.getElementById('grade-select');
const subjectSelect  = document.getElementById('subject-select');
const topbarGrade    = document.getElementById('topbar-grade');
const topbarSubject  = document.getElementById('topbar-subject');
const transcriptText = document.getElementById('transcript-text');
const previewEmpty   = document.getElementById('preview-empty');
const previewContent = document.getElementById('preview-content');
const processingOvr  = document.getElementById('processing-overlay');
const micBtn         = document.getElementById('mic-btn');
const voiceStatus    = document.getElementById('voice-status');
const voiceHint      = document.getElementById('voice-hint');
const voiceWaveform  = document.getElementById('voice-waveform');
const langIndicator  = document.getElementById('lang-indicator');
const langLabel      = document.getElementById('lang-label');
const historyList    = document.getElementById('history-list');
const exportBtn      = document.getElementById('export-pdf-btn');
const clearBtn       = document.getElementById('clear-session-btn');
const projectBtn     = document.getElementById('project-btn');
const themeBtn       = document.getElementById('theme-btn');
const settingsBtn    = document.getElementById('settings-btn');
const settingsDrawer = document.getElementById('settings-drawer');
const settingsClear  = document.getElementById('settings-clear-btn');
const langOverride   = document.getElementById('lang-override');
const ttsToggle      = document.getElementById('tts-toggle');
const toast          = document.getElementById('toast');
const toastTitle     = document.getElementById('toast-title');
const toastMsg       = document.getElementById('toast-msg');

// ── Init theme ──
const savedTheme = localStorage.getItem('saathi-theme') || 'dark';
document.documentElement.setAttribute('data-theme', savedTheme);

// ── Session Start ──
beginBtn.addEventListener('click', () => {
  session = createSession(gradeSelect.value, subjectSelect.value);
  sessionModal.style.display = 'none';
  appContainer.style.display = 'flex';
  topbarGrade.textContent   = `Class ${session.grade}`;
  topbarSubject.textContent = session.subject.charAt(0).toUpperCase() + session.subject.slice(1);
  initSTT();
  renderHistoryList();
});

// ── STT setup ──
function initSTT() {
  try {
    stt = new STTController({
      onInterim: (text) => {
        transcriptText.textContent = text;
        transcriptText.classList.remove('placeholder');
      },
      onTranscript: (text) => {
        transcriptText.textContent = text;
        transcriptText.classList.remove('placeholder');
        const detected = detectLanguageFromText(text);
        stt.setLang(detected);
        langLabel.textContent = stt.getLangLabel();
        updateSessionLanguage(session, langCodeToShort(detected));
        handleTranscript(text);
      },
      onStart: () => {
        micBtn.classList.add('recording', 'pulse');
        voiceStatus.textContent = 'Recording…';
        voiceWaveform.classList.remove('hidden');
      },
      onEnd: () => {
        micBtn.classList.remove('recording', 'pulse');
        voiceStatus.textContent = 'Hold SPACE or click mic to speak';
        voiceWaveform.classList.add('hidden');
      },
      onError: (err) => {
        micBtn.classList.remove('recording', 'pulse');
        voiceWaveform.classList.add('hidden');
        if (err === 'network') showToast('Mic needs internet + Chrome', 'Web Speech uses Google servers. Use Chrome (not Brave), check connection, or just type the command below.');
        else if (err === 'not-allowed') showToast('Mic blocked', 'Allow microphone access in the browser, or type the command below.');
        else if (err !== 'no-speech') showToast('Mic error', `${err}. You can type the command below instead.`);
      },
    });
  } catch (e) {
    showToast('Browser not supported', e.message);
  }
}

// ── Mic button ──
micBtn.addEventListener('mousedown', () => stt?.start());
micBtn.addEventListener('mouseup',   () => stt?.stop());
micBtn.addEventListener('touchstart', (e) => { e.preventDefault(); stt?.start(); });
micBtn.addEventListener('touchend',   (e) => { e.preventDefault(); stt?.stop(); });

// ── Typed-command fallback (works when mic/Web Speech unavailable) ──
const typeForm  = document.getElementById('type-form');
const typeInput = document.getElementById('type-input');
typeForm?.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = typeInput.value.trim();
  if (!text) return;
  transcriptText.textContent = text;
  transcriptText.classList.remove('placeholder');
  const detected = detectLanguageFromText(text);
  stt?.setLang(detected);
  if (langLabel) langLabel.textContent = stt?.getLangLabel?.() || 'English';
  updateSessionLanguage(session, langCodeToShort(detected));
  handleTranscript(text);
  typeInput.value = '';
});

// ── Spacebar push-to-talk ──
document.addEventListener('keydown', (e) => {
  if (e.code === 'Space' && !e.repeat && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA' && e.target.tagName !== 'SELECT') {
    e.preventDefault();
    stt?.start();
  }
});
document.addEventListener('keyup', (e) => {
  if (e.code === 'Space') stt?.stop();
});

// ── Main transcript processing ──
async function handleTranscript(text, regenerate = false) {
  if (!text.trim()) return;
  setProcessing(true);

  try {
    const ctx = getSessionContext(session);
    const response = await processTranscript(text, ctx, regenerate);

    currentResponse = response;
    currentHistoryIndex = session.history.length;

    addToHistory(session, {
      intent: response.intent,
      topic: response.topic || '',
      transcript: text,
      response,
    });

    renderHistoryList();
    showPreview(response);

    // TTS if enabled
    if (document.getElementById('tts-toggle')?.checked && response.content) {
      const textForTTS = extractTTSText(response);
      if (textForTTS) {
        const audioUrl = await fetchTTS(textForTTS, response.detected_language || 'en').catch(() => null);
        if (audioUrl) new Audio(audioUrl).play().catch(() => {});
      }
    }
  } catch (err) {
    showToast('Error', err.message || 'Could not process request. Is the backend running?');
  } finally {
    setProcessing(false);
  }
}

function extractTTSText(response) {
  const c = response.content || {};
  if (response.intent === 'concept_simplification') return c.explanation?.slice(0, 500) || '';
  if (response.intent === 'quiz_generation')        return c.questions?.[0]?.question || '';
  if (response.intent === 'bilingual_translation')  return c.translated_text || '';
  if (response.intent === 'activity_guide')         return c.steps?.[0]?.instruction || '';
  return '';
}

function showPreview(response) {
  if (response.intent === 'unclear') {
    showToast("I didn't catch that", "Try: 'Explain [topic] to Class [grade]' or 'Give me 5 MCQ on [topic]'");
    return;
  }

  previewEmpty.style.display  = 'none';
  previewContent.style.display = 'block';

  const previewGate = document.getElementById('preview-gate-toggle')?.checked;

  renderPreview(response.intent, response, previewContent, {
    onThumbUp: () => {
      if (currentHistoryIndex >= 0) rateEntry(session, currentHistoryIndex, 1);
    },
    onThumbDown: () => {
      if (currentHistoryIndex >= 0) rateEntry(session, currentHistoryIndex, -1);
      handleTranscript(transcriptText.textContent, true);
    },
    onProject: () => {
      sender.showContent(response.intent, response.grade, response.subject || session.subject, response);
      showToast('Projected!', 'Content sent to display window.');
    },
    onSpeak: async () => {
      const text = extractTTSText(response);
      if (!text) { showToast('Nothing to read', 'No text in this response.'); return; }
      try {
        const url = await fetchTTS(text, response.detected_language || 'en');
        const audio = new Audio(url);
        await audio.play();
      } catch (err) {
        showToast('TTS failed', 'Could not play audio. Backend running + online?');
      }
    },
  });

  // Auto-project if preview gate is off
  if (!previewGate && response.intent !== 'unclear') {
    sender.showContent(response.intent, response.grade, response.subject || session.subject, response);
  }

  addProjectorControls(response);
}

// Inject projector-advance controls into the preview footer for quiz + activity
function addProjectorControls(response) {
  const actions = previewContent.querySelector('.preview-actions');
  if (!actions) return;

  let html = '';
  if (response.intent === 'quiz_generation') {
    html = `
      <div class="proj-controls">
        <button class="btn btn-secondary btn-sm" id="pc-reveal">Reveal answer</button>
        <button class="btn btn-secondary btn-sm" id="pc-next">Next question →</button>
        <button class="btn btn-ghost btn-sm" id="pc-reset">Reset</button>
      </div>`;
  } else if (response.intent === 'activity_guide') {
    html = `
      <div class="proj-controls">
        <button class="btn btn-secondary btn-sm" id="pc-timer">Start timer</button>
        <button class="btn btn-secondary btn-sm" id="pc-step">Next step →</button>
      </div>`;
  }
  if (!html) return;

  actions.insertAdjacentHTML('beforeend', html);

  // Display already has content (auto-projected or via Project button).
  // These only send the advance command · they do NOT re-send content (which would reset state).
  document.getElementById('pc-reveal')?.addEventListener('click', () => sender.quizReveal());
  document.getElementById('pc-next')?.addEventListener('click',   () => sender.quizNext());
  document.getElementById('pc-reset')?.addEventListener('click',  () => sender.quizReset());
  document.getElementById('pc-timer')?.addEventListener('click',  () => sender.timerStart());
  document.getElementById('pc-step')?.addEventListener('click',   () => sender.timerNext());
}

function setProcessing(on) {
  processingOvr.classList.toggle('hidden', !on);
  micBtn.disabled = on;
  voiceStatus.textContent = on ? 'Processing…' : 'Hold SPACE or click mic to speak';
}

// ── History list ──
function renderHistoryList() {
  if (!session?.history?.length) {
    historyList.innerHTML = `<div style="padding:16px 10px;color:var(--text-muted);font-size:0.8rem;text-align:center;">Your session activity will appear here</div>`;
    return;
  }

  const icons = { concept_simplification: 'C', quiz_generation: 'Q', bilingual_translation: 'T', activity_guide: 'A' };

  historyList.innerHTML = session.history.map((h, i) => `
    <div class="history-item ${i === currentHistoryIndex ? 'active' : ''}" data-index="${i}">
      <div class="history-item-icon">${icons[h.intent] || '·'}</div>
      <div class="history-item-info">
        <div class="history-item-topic truncate">${h.topic || h.intent}</div>
        <div class="history-item-time">${new Date(h.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}</div>
      </div>
    </div>
  `).reverse().join('');

  historyList.querySelectorAll('.history-item').forEach(item => {
    item.addEventListener('click', () => {
      const idx = parseInt(item.dataset.index);
      const entry = session.history[idx];
      if (entry?.response) {
        currentHistoryIndex = idx;
        showPreview(entry.response);
        historyList.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
        item.classList.add('active');
      }
    });
  });
}

// ── Export PDF ──
exportBtn.addEventListener('click', () => {
  if (!session?.history?.length) { showToast('Nothing to export', 'Start a session first.'); return; }
  exportSessionPDF(session);
});

// ── Clear session ──
function doClear() {
  clearSession();
  session = null;
  sessionModal.style.display = 'flex';
  appContainer.style.display = 'none';
  previewEmpty.style.display = 'flex';
  previewContent.style.display = 'none';
  previewContent.innerHTML = '';
}
clearBtn.addEventListener('click', doClear);
settingsClear.addEventListener('click', doClear);

// ── Project button (open display window) ──
projectBtn.addEventListener('click', () => {
  window.open('display.html', 'saathi-display', 'width=1280,height=720');
});

// ── Theme toggle ──
themeBtn.addEventListener('click', () => {
  const curr = document.documentElement.getAttribute('data-theme');
  const next = curr === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('saathi-theme', next);
});

// ── Settings drawer ──
settingsBtn.addEventListener('click', () => settingsDrawer.classList.toggle('open'));
document.addEventListener('click', (e) => {
  if (!settingsDrawer.contains(e.target) && e.target !== settingsBtn) {
    settingsDrawer.classList.remove('open');
  }
});

// ── Language override ──
langOverride?.addEventListener('change', () => {
  const val = langOverride.value;
  if (val !== 'auto' && stt) {
    stt.setLang(val);
    langLabel.textContent = stt.getLangLabel();
  }
});

// ── Language indicator click (cycle) ──
langIndicator?.addEventListener('click', () => {
  const langs = ['en-IN', 'hi-IN', 'ml-IN'];
  const curr = stt?._lang || 'en-IN';
  const next = langs[(langs.indexOf(curr) + 1) % langs.length];
  stt?.setLang(next);
  langLabel.textContent = stt?.getLangLabel() || next;
});

// ── Toast helper ──
function showToast(title, msg) {
  toastTitle.textContent = title;
  toastMsg.textContent   = msg;
  toast.classList.add('show');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => toast.classList.remove('show'), 4000);
}

// Mermaid init (monochrome theme to match editorial style)
if (typeof mermaid !== 'undefined') {
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'loose',
    theme: 'base',
    themeVariables: {
      background: '#0a0a0a',
      primaryColor: '#151515',
      primaryBorderColor: '#3a3a38',
      primaryTextColor: '#f2f0eb',
      lineColor: '#56544f',
      fontFamily: "'Inter Tight', sans-serif",
      fontSize: '16px',
    },
  });
}
