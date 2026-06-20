/* broadcast.js · BroadcastChannel for teacher-control ↔ projector-display sync */

const CHANNEL_NAME = 'saathi-display';

export class DisplaySender {
  constructor() {
    this._ch = new BroadcastChannel(CHANNEL_NAME);
  }

  showContent(intent, grade, subject, data) {
    this._ch.postMessage({ type: 'SHOW_CONTENT', intent, grade, subject, data });
  }

  quizNext()   { this._ch.postMessage({ type: 'QUIZ_NEXT' }); }
  quizReveal() { this._ch.postMessage({ type: 'QUIZ_REVEAL' }); }
  quizReset()  { this._ch.postMessage({ type: 'QUIZ_RESET' }); }

  timerStart() { this._ch.postMessage({ type: 'TIMER_START' }); }
  timerNext()  { this._ch.postMessage({ type: 'TIMER_NEXT' }); }

  close() { this._ch.close(); }
}

export class DisplayReceiver {
  constructor() {
    this._ch = new BroadcastChannel(CHANNEL_NAME);
    this._handler = null;
    this._ch.onmessage = (e) => { if (this._handler) this._handler(e.data); };
  }

  onMessage(fn) {
    this._handler = fn;
  }

  close() { this._ch.close(); }
}
