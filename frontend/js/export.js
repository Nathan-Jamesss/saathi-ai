/* export.js · jsPDF session export */

export function exportSessionPDF(session) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });

  const margin = 18;
  const pageW  = 210;
  const usableW = pageW - margin * 2;
  let y = margin;

  function checkPage(needed = 12) {
    if (y + needed > 280) { doc.addPage(); y = margin; }
  }

  function line(text, size = 11, color = [50, 50, 70], bold = false) {
    doc.setFontSize(size);
    doc.setTextColor(...color);
    doc.setFont('helvetica', bold ? 'bold' : 'normal');
    const lines = doc.splitTextToSize(String(text), usableW);
    checkPage(lines.length * (size * 0.4 + 1));
    doc.text(lines, margin, y);
    y += lines.length * (size * 0.4 + 1) + 2;
  }

  function divider() {
    checkPage(6);
    doc.setDrawColor(200, 200, 220);
    doc.line(margin, y, pageW - margin, y);
    y += 5;
  }

  // Header
  doc.setFillColor(79, 70, 229);
  doc.rect(0, 0, pageW, 22, 'F');
  doc.setFontSize(16);
  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.text('Saathi.AI · Session Export', margin, 14);
  y = 30;

  line(`Session: ${new Date(session.startedAt).toLocaleString()}`, 10, [120, 120, 140]);
  line(`Grade: Class ${session.grade}  |  Subject: ${session.subject}`, 10, [120, 120, 140]);
  line(`Total interactions: ${session.history.length}`, 10, [120, 120, 140]);
  y += 4;
  divider();

  if (session.history.length === 0) {
    line('No session history to export.', 11, [120, 120, 140]);
  }

  session.history.forEach((item, idx) => {
    checkPage(20);
    const intentLabels = {
      concept_simplification: 'Concept Simplification',
      quiz_generation: 'Quiz Generation',
      bilingual_translation: 'Translation',
      activity_guide: 'Activity Guide',
    };

    line(`${idx + 1}. ${intentLabels[item.intent] || item.intent}`, 12, [30, 30, 80], true);
    if (item.topic) line(`Topic: ${item.topic}`, 10, [100, 100, 140]);
    line(`Time: ${new Date(item.timestamp).toLocaleTimeString()}`, 9, [150, 150, 170]);
    y += 2;

    const c = item.response?.content || item.response || {};

    if (item.intent === 'concept_simplification') {
      if (c.explanation) { line('Explanation:', 10, [60, 60, 100], true); line(c.explanation, 10); }
      if (c.key_points?.length) {
        line('Key Points:', 10, [60, 60, 100], true);
        c.key_points.forEach(pt => line(`• ${pt}`, 10, [80, 80, 110]));
      }
      if (c.analogy) { line(`Analogy: ${c.analogy}`, 10, [100, 80, 180]); }
    }

    if (item.intent === 'quiz_generation' && c.questions) {
      line(`Quiz (${c.questions.length} questions):`, 10, [60, 60, 100], true);
      c.questions.forEach((q, qi) => {
        checkPage(18);
        line(`Q${qi+1}: ${q.question}`, 10, [50, 50, 80], true);
        if (q.options) q.options.forEach(opt => line(`  ${opt}`, 9, [100, 100, 130]));
        if (q.correct_answer) line(`Answer: ${q.correct_answer}`, 9, [34, 139, 34]);
        if (q.explanation) line(`Explanation: ${q.explanation}`, 9, [100, 120, 100]);
        y += 2;
      });
    }

    if (item.intent === 'bilingual_translation') {
      if (c.original_text)    line(`Original: ${c.original_text}`, 10, [50, 50, 80], true);
      if (c.translated_text)  line(`Translated: ${c.translated_text}`, 10);
      if (c.transliteration)  line(`Transliteration: ${c.transliteration}`, 9, [120, 120, 150]);
      if (c.notes)            line(`Notes: ${c.notes}`, 9, [150, 150, 170]);
    }

    if (item.intent === 'activity_guide') {
      if (c.activity_title) line(c.activity_title, 11, [50, 50, 100], true);
      if (c.steps) {
        c.steps.forEach(s => {
          checkPage(14);
          line(`Step ${s.step_number}: ${s.title}`, 10, [60, 60, 100], true);
          line(s.instruction, 10, [80, 80, 110]);
          if (s.teacher_note) line(`Teacher note: ${s.teacher_note}`, 9, [140, 120, 100]);
          y += 1;
        });
      }
    }

    if (item.rating !== 0) {
      line(item.rating === 1 ? 'Rated helpful' : 'Rated unhelpful', 9, [150, 150, 170]);
    }

    divider();
  });

  // Footer
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(180, 180, 200);
    doc.setFont('helvetica', 'normal');
    doc.text(`Saathi.AI · Page ${i} of ${pageCount}`, pageW / 2, 291, { align: 'center' });
  }

  doc.save(`saathi-session-${session.id}.pdf`);
}
