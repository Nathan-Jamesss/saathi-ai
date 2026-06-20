/* stt.js · Web Speech API wrapper */

const LANG_LABELS = { 'en-IN': 'English', 'hi-IN': 'Hindi (हिंदी)', 'ml-IN': 'Malayalam (മലയാളം)' };

export class STTController {
  constructor({ onTranscript, onInterim, onStart, onEnd, onError }) {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      throw new Error('Web Speech API not supported in this browser. Please use Chrome.');
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    this._rec = new SR();
    this._rec.continuous = false;
    this._rec.interimResults = true;
    this._lang = 'en-IN';
    this._recording = false;

    this._rec.onstart = () => { this._recording = true; onStart?.(); };
    this._rec.onend   = () => { this._recording = false; onEnd?.(); };
    this._rec.onerror = (e) => { this._recording = false; onError?.(e.error); };

    this._rec.onresult = (e) => {
      let interim = '', final = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) final += t;
        else interim += t;
      }
      if (interim) onInterim?.(interim);
      if (final)   onTranscript?.(final.trim());
    };
  }

  setLang(lang) {
    this._lang = lang;
    this._rec.lang = lang;
  }

  getLangLabel() {
    return LANG_LABELS[this._lang] || this._lang;
  }

  start() {
    if (this._recording) return;
    this._rec.lang = this._lang;
    try { this._rec.start(); } catch {}
  }

  stop() {
    if (!this._recording) return;
    try { this._rec.stop(); } catch {}
  }

  isRecording() { return this._recording; }
}

export function detectLanguageFromText(text) {
  const malayalamPattern = /[ഀ-ൿ]/;
  const hindiPattern     = /[ऀ-ॿ]/;
  if (malayalamPattern.test(text)) return 'ml-IN';
  if (hindiPattern.test(text))     return 'hi-IN';
  return 'en-IN';
}

export function langCodeToShort(bcp47) {
  const map = { 'en-IN': 'en', 'hi-IN': 'hi', 'ml-IN': 'ml' };
  return map[bcp47] || 'en';
}
