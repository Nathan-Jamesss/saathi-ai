/* renderer.js · Component rendering for Teacher View and Projector Display */

// ──────────────────────────────────────────────
// TEACHER CONTROL VIEW RENDERING
// ──────────────────────────────────────────────

export function renderPreview(intent, data, container, callbacks = {}) {
  container.innerHTML = '';

  if (intent === 'concept_simplification') renderConceptPreview(data, container, callbacks);
  else if (intent === 'quiz_generation')    renderQuizPreview(data, container, callbacks);
  else if (intent === 'bilingual_translation') renderTranslationPreview(data, container, callbacks);
  else if (intent === 'activity_guide')     renderActivityPreview(data, container, callbacks);
}

function makePreviewCard(title, metaText, bodyHTML, footerHTML) {
  return `
    <div class="preview-card">
      <div class="preview-card-header">
        <div>${title}</div>
        <div class="preview-card-meta">${metaText}</div>
      </div>
      <div class="preview-card-body">${bodyHTML}</div>
      <div class="preview-actions">${footerHTML}</div>
    </div>
  `;
}

function feedbackBar(callbacks) {
  const svgUp   = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M7 10v11M2 13v6a2 2 0 0 0 2 2h13.5a2 2 0 0 0 2-1.7l1.3-8A2 2 0 0 0 18 9h-5l1-4a2 2 0 0 0-2-2.5L7 10"/></svg>`;
  const svgDown = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M17 14V3M22 11V5a2 2 0 0 0-2-2H6.5a2 2 0 0 0-2 1.7l-1.3 8A2 2 0 0 0 6 15h5l-1 4a2 2 0 0 0 2 2.5L17 14"/></svg>`;
  const svgSpk  = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M11 5 6 9H2v6h4l5 4V5zM16 9a3 3 0 0 1 0 6M19 6a7 7 0 0 1 0 12"/></svg>`;
  return `
    <div class="feedback-btns">
      <button class="feedback-btn" id="thumb-up" title="Helpful" aria-label="Helpful">${svgUp}</button>
      <button class="feedback-btn" id="thumb-down" title="Not helpful, regenerate" aria-label="Not helpful">${svgDown}</button>
      <button class="feedback-btn" id="speak-btn" title="Read aloud" aria-label="Read aloud">${svgSpk}</button>
    </div>
    <button class="btn btn-primary btn-sm" id="project-content-btn">Project to class</button>
  `;
}

function renderConceptPreview(data, container, callbacks) {
  const c = data.content || data;
  let diagramHTML = '';
  if (c.mermaid_diagram) {
    diagramHTML += `<div class="mermaid-container"><div class="mermaid">${c.mermaid_diagram}</div></div>`;
  }
  if (c.wikipedia_image_url) {
    diagramHTML += `<div class="wiki-image-container">
      <img src="${c.wikipedia_image_url}" alt="${c.wikipedia_image_caption || 'Image'}" onerror="this.parentElement.style.display='none'" />
      <div class="wiki-caption">${c.wikipedia_image_caption || ''}</div>
    </div>`;
  }

  const kpHTML = (c.key_points || []).map(p => `<li>${p}</li>`).join('');
  const analogyHTML = c.analogy ? `<div class="analogy-box">${c.analogy}</div>` : '';

  const badge = `<span class="badge badge-concept">CONCEPT</span>`;
  const meta  = `${data.topic || ''} · Grade ${data.grade || ''}`;

  const body = `
    ${diagramHTML}
    <p class="concept-explanation">${c.explanation || ''}</p>
    ${kpHTML ? `<ul class="key-points-list">${kpHTML}</ul>` : ''}
    ${analogyHTML}
  `;

  container.innerHTML = makePreviewCard(badge, meta, body, feedbackBar(callbacks));

  // Render Mermaid after DOM insert
  if (c.mermaid_diagram && typeof mermaid !== 'undefined') {
    mermaid.run({ querySelector: '.preview-card .mermaid' }).catch(() => {
      const el = container.querySelector('.mermaid-container');
      if (el) el.style.display = 'none';
    });
  }

  attachFeedbackListeners(container, callbacks);
}

function renderQuizPreview(data, container, callbacks) {
  const c = data.content || data;
  const questions = c.questions || [];

  const cardsHTML = questions.map((q, i) => `
    <div class="quiz-card">
      <div class="quiz-card-header">
        <span class="quiz-q-num">Q${q.number || i+1}</span>
        <button class="btn btn-ghost btn-sm show-answers-toggle" data-qi="${i}">Show Answer</button>
      </div>
      <div class="quiz-question">${q.question}</div>
      ${q.options ? `<div class="quiz-options">${q.options.map(opt => `<div class="quiz-option">${opt}</div>`).join('')}</div>` : ''}
      <div class="quiz-answer" id="quiz-ans-${i}">
        Answer: <strong>${q.correct_answer}</strong>${q.explanation ? `. ${q.explanation}` : ''}
      </div>
    </div>
  `).join('');

  const badge = `<span class="badge badge-quiz">QUIZ</span>`;
  const meta  = `${questions.length} ${c.quiz_type || 'MCQ'} · Grade ${data.grade || ''}`;
  container.innerHTML = makePreviewCard(badge, meta, `<div class="quiz-cards">${cardsHTML}</div>`, feedbackBar(callbacks));

  // Show/hide answer toggles
  container.querySelectorAll('.show-answers-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const qi = btn.dataset.qi;
      const ans = document.getElementById(`quiz-ans-${qi}`);
      const visible = ans.style.display === 'block';
      ans.style.display = visible ? 'none' : 'block';
      btn.textContent = visible ? 'Show Answer' : 'Hide Answer';
    });
  });

  attachFeedbackListeners(container, callbacks);
}

function renderTranslationPreview(data, container, callbacks) {
  const c = data.content || data;
  const langLabels = { en: 'English', hi: 'Hindi (हिंदी)', ml: 'Malayalam (മലയാളം)' };

  const body = `
    <div class="translation-grid">
      <div class="translation-panel">
        <div class="translation-lang-label">${langLabels[c.original_language] || 'Original'}</div>
        <div class="translation-text">${c.original_text || ''}</div>
      </div>
      <div class="translation-panel">
        <div class="translation-lang-label">${langLabels[c.target_language] || 'Translation'}</div>
        <div class="translation-text">${c.translated_text || ''}</div>
        ${c.transliteration ? `<div class="transliteration">${c.transliteration}</div>` : ''}
      </div>
    </div>
    ${c.notes ? `<div class="translation-notes">Note: ${c.notes}</div>` : ''}
  `;

  const badge = `<span class="badge badge-translate">TRANSLATE</span>`;
  const srcLang = langLabels[c.original_language] || '';
  const tgtLang = langLabels[c.target_language] || '';
  const meta = `${srcLang} → ${tgtLang}`;

  container.innerHTML = makePreviewCard(badge, meta, body, feedbackBar(callbacks));
  attachFeedbackListeners(container, callbacks);
}

function renderActivityPreview(data, container, callbacks) {
  const c = data.content || data;
  const steps = c.steps || [];

  const stepsHTML = steps.map(s => `
    <div class="activity-step">
      <div class="step-badge">${s.step_number}</div>
      <div class="step-content">
        <div class="step-title">${s.title}</div>
        <div class="step-dur">${Math.round(s.duration_seconds / 60)} min</div>
      </div>
    </div>
  `).join('');

  const body = `
    <div class="activity-header">
      <h3>${c.activity_title || 'Activity Guide'}</h3>
      <div class="activity-meta">${c.activity_type || 'group'} · ${c.duration_minutes} min · ${steps.length} steps</div>
    </div>
    <div class="activity-steps">${stepsHTML}</div>
    ${c.materials_needed?.length ? `<div class="translation-notes">Materials: ${c.materials_needed.join(', ')}</div>` : ''}
  `;

  const badge = `<span class="badge badge-activity">ACTIVITY</span>`;
  const meta  = `${c.duration_minutes} min · ${c.activity_type} · Grade ${data.grade || ''}`;

  container.innerHTML = makePreviewCard(badge, meta, body, feedbackBar(callbacks));
  attachFeedbackListeners(container, callbacks);
}

function attachFeedbackListeners(container, callbacks) {
  container.querySelector('#thumb-up')?.addEventListener('click', (e) => {
    e.currentTarget.classList.add('active-up');
    container.querySelector('#thumb-down')?.classList.remove('active-down');
    callbacks.onThumbUp?.();
  });
  container.querySelector('#thumb-down')?.addEventListener('click', (e) => {
    e.currentTarget.classList.add('active-down');
    container.querySelector('#thumb-up')?.classList.remove('active-up');
    callbacks.onThumbDown?.();
  });
  container.querySelector('#project-content-btn')?.addEventListener('click', () => {
    callbacks.onProject?.();
  });
  container.querySelector('#speak-btn')?.addEventListener('click', (e) => {
    e.currentTarget.classList.add('active-up');
    callbacks.onSpeak?.();
  });
}

// ──────────────────────────────────────────────
// PROJECTOR DISPLAY VIEW RENDERING
// ──────────────────────────────────────────────

export function renderDisplay(intent, data, container, receiver) {
  container.innerHTML = '';
  const c = data.content || data;

  if (intent === 'concept_simplification') renderConceptDisplay(data, c, container);
  else if (intent === 'quiz_generation')   renderQuizDisplay(data, c, container);
  else if (intent === 'bilingual_translation') renderTranslationDisplay(data, c, container);
  else if (intent === 'activity_guide')    renderActivityDisplay(data, c, container);
}

function renderConceptDisplay(data, c, container) {
  const hasDiagram = !!c.mermaid_diagram;
  const hasImage   = !!c.wikipedia_image_url;
  const hasRight   = (c.key_points?.length || c.analogy || (hasDiagram && hasImage));

  // box shows diagram if present, else the photo
  const boxInner = hasDiagram
    ? `<div class="mermaid">${c.mermaid_diagram}</div>`
    : hasImage
      ? `<img class="concept-wiki-img" src="${c.wikipedia_image_url}" alt="${c.wikipedia_image_caption || ''}" onerror="this.src=''"/>`
      : `<span style="color:var(--text-muted);font-size:1rem;">No visual available</span>`;

  // when BOTH exist, photo goes top of the right column
  const photoInRight = (hasDiagram && hasImage)
    ? `<figure class="concept-photo">
         <img class="concept-wiki-img" src="${c.wikipedia_image_url}" alt="${c.wikipedia_image_caption || ''}" onerror="this.parentElement.style.display='none'"/>
         ${c.wikipedia_image_caption ? `<figcaption>${c.wikipedia_image_caption}</figcaption>` : ''}
       </figure>`
    : '';

  container.innerHTML = `
    <div class="display-topic">
      ${data.topic || ''}
      <div class="display-topic-meta">Class ${data.grade} · ${data.subject}</div>
    </div>
    <div class="concept-display-grid${!hasRight ? ' diagram-only' : ''}">
      <div class="concept-diagram-box" id="disp-diagram-box">${boxInner}</div>
      ${hasRight ? `
      <div class="concept-right">
        ${photoInRight}
        ${c.key_points?.length ? `<ul class="display-key-points">${c.key_points.map(p => `<li>${p}</li>`).join('')}</ul>` : ''}
        ${c.analogy ? `<div class="display-analogy">${c.analogy}</div>` : ''}
      </div>` : ''}
    </div>
  `;

  if (hasDiagram && typeof mermaid !== 'undefined') {
    mermaid.run({ querySelector: '#disp-diagram-box .mermaid' }).catch(() => {
      const box = document.getElementById('disp-diagram-box');
      if (box) box.querySelector('.mermaid').textContent = 'Diagram unavailable';
    });
  }
}

function renderQuizDisplay(data, c, container) {
  const questions = c.questions || [];
  let currentIndex = 0;
  let revealed = new Array(questions.length).fill(false);

  function buildQuestion(i) {
    const q = questions[i];
    const opts = q.options ? q.options.map((opt, oi) => {
      const letter = 'ABCD'[oi];
      let cls = 'quiz-opt';
      if (revealed[i]) {
        if (q.correct_answer === letter || opt.startsWith(`${q.correct_answer})`)) cls += ' revealed-correct';
        else cls += ' revealed-wrong';
      }
      return `<div class="${cls}">${opt}</div>`;
    }).join('') : '';

    const tfOpts = q.type === 'true_false' ? `
      <div class="quiz-tf-options">
        <div class="quiz-opt ${revealed[i] && q.correct_answer === 'True' ? 'revealed-correct' : ''}">True</div>
        <div class="quiz-opt ${revealed[i] && q.correct_answer === 'False' ? 'revealed-correct' : ''}">False</div>
      </div>` : '';

    const dots = questions.map((_, di) => {
      let cls = 'quiz-dot';
      if (di < i) cls += ' done';
      else if (di === i) cls += ' current';
      return `<div class="${cls}"></div>`;
    }).join('');

    return `
      <div class="quiz-display-container">
        <div class="quiz-question-card">
          <div class="quiz-q-num-display">Question ${i+1}</div>
          <div class="quiz-q-text">${q.question}</div>
          ${q.type !== 'true_false' ? `<div class="quiz-options-grid">${opts}</div>` : tfOpts}
          <div class="quiz-explanation ${revealed[i] ? 'visible' : ''}" id="disp-explanation">
            ${revealed[i] && q.explanation ? `${q.explanation}` : ''}
          </div>
        </div>
        <div class="quiz-progress-bar">
          <span class="quiz-progress-text">Question ${i+1} of ${questions.length}</span>
          <div class="quiz-dots">${dots}</div>
        </div>
      </div>
    `;
  }

  container.innerHTML = buildQuestion(currentIndex);

  window.quizDisplayNext = () => {
    if (currentIndex < questions.length - 1) {
      currentIndex++;
      container.innerHTML = buildQuestion(currentIndex);
    }
  };
  window.quizDisplayReveal = () => {
    revealed[currentIndex] = true;
    container.innerHTML = buildQuestion(currentIndex);
  };
  window.quizDisplayReset = () => {
    currentIndex = 0;
    revealed = new Array(questions.length).fill(false);
    container.innerHTML = buildQuestion(0);
  };
}

function renderTranslationDisplay(data, c, container) {
  const langLabels = { en: 'English', hi: 'Hindi', ml: 'Malayalam' };
  container.innerHTML = `
    <div class="translation-display-grid">
      <div class="translation-panel-display">
        <div class="translation-lang-tag">${langLabels[c.original_language] || 'Original'}</div>
        <div class="translation-text-display">${c.original_text || ''}</div>
      </div>
      <div class="translation-panel-display">
        <div class="translation-lang-tag">${langLabels[c.target_language] || 'Translation'}</div>
        <div class="translation-text-display">${c.translated_text || ''}</div>
        ${c.transliteration ? `<div class="translation-translit-display">${c.transliteration}</div>` : ''}
      </div>
    </div>
  `;
}

function renderActivityDisplay(data, c, container) {
  const steps = c.steps || [];
  let currentStep = 0;
  let timeRemaining = steps[0]?.duration_seconds || 60;
  let timerInterval = null;

  function buildStep(si) {
    const s = steps[si];
    const mins = Math.floor(timeRemaining / 60);
    const secs = timeRemaining % 60;
    const timeStr = `${String(mins).padStart(2,'0')}:${String(secs).padStart(2,'0')}`;
    const timerCls = timeRemaining <= 10 ? 'danger' : timeRemaining <= 30 ? 'warning' : '';

    return `
      <div class="activity-display-header">
        <div style="font-family:var(--font-display);font-size:1.6rem;font-weight:400;letter-spacing:-0.02em;color:var(--text-primary);">${c.activity_title || 'Activity'}</div>
        <div class="activity-type-tag">${c.activity_type || 'Group'} Activity · ${c.duration_minutes} min</div>
      </div>
      <div class="activity-step-card">
        <div class="activity-step-num">Step ${s.step_number} of ${steps.length}</div>
        <div class="activity-step-title-display">${s.title}</div>
        <div class="activity-step-instruction">${s.instruction}</div>
        ${s.teacher_note ? `<div class="activity-teacher-note">Note: ${s.teacher_note}</div>` : ''}
      </div>
      <div class="activity-bottom">
        <div class="activity-step-progress">${si + 1} / ${steps.length}</div>
        <div class="activity-timer ${timerCls}" id="activity-timer-disp">${timeStr}</div>
      </div>
    `;
  }

  function buildComplete() {
    return `<div class="activity-complete">
      <div>Activity complete</div>
      <div style="font-size:1.2rem;color:var(--text-muted);font-weight:300;">Great work.</div>
    </div>`;
  }

  container.innerHTML = buildStep(currentStep);

  function updateTimer() {
    const el = document.getElementById('activity-timer-disp');
    if (!el) return;
    const mins = Math.floor(timeRemaining / 60);
    const secs = timeRemaining % 60;
    el.textContent = `${String(mins).padStart(2,'0')}:${String(secs).padStart(2,'0')}`;
    el.className = `activity-timer${timeRemaining <= 10 ? ' danger' : timeRemaining <= 30 ? ' warning' : ''}`;
  }

  window.activityTimerStart = () => {
    if (timerInterval) return;
    timerInterval = setInterval(() => {
      if (timeRemaining > 0) {
        timeRemaining--;
        updateTimer();
      } else {
        clearInterval(timerInterval);
        timerInterval = null;
      }
    }, 1000);
  };

  window.activityTimerNext = () => {
    clearInterval(timerInterval);
    timerInterval = null;
    currentStep++;
    if (currentStep >= steps.length) {
      container.innerHTML = buildComplete();
    } else {
      timeRemaining = steps[currentStep].duration_seconds || 60;
      container.innerHTML = buildStep(currentStep);
    }
  };
}
