/* motion.js · cinematic interactions for the landing page
   Vanilla, GPU-friendly (transform/opacity), respects reduced-motion. */
(() => {
  'use strict';
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  /* ── preloader ── */
  const pre = $('#preloader'), preCount = $('#pre-count');
  let n = 0;
  const finish = () => {
    document.body.classList.add('ready');
    pre && pre.classList.add('done');
  };
  if (reduce) {
    if (preCount) preCount.textContent = '100';
    finish();
  } else {
    const t = setInterval(() => {
      n = Math.min(n + Math.ceil(Math.random() * 9 + 3), 100);
      if (preCount) preCount.textContent = n;
      if (n >= 100) { clearInterval(t); setTimeout(finish, 280); }
    }, 95);
  }

  /* custom cursor removed for accessibility · real pointer kept */

  /* ── scroll progress + nav ── */
  const bar = $('#scroll-progress'), nav = $('#nav');
  const onScroll = () => {
    const h = document.documentElement;
    const p = h.scrollTop / (h.scrollHeight - h.clientHeight || 1);
    if (bar) bar.style.width = (p * 100) + '%';
    if (nav) nav.classList.toggle('scrolled', h.scrollTop > 40);
  };
  addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ── reveals ── */
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
  }, { threshold: 0.16, rootMargin: '0px 0px -8% 0px' });
  $$('[data-reveal], [data-reveal-lines]').forEach(el => io.observe(el));

  /* ── marquee loop (seamless) ── */
  const track = $('#marquee-track');
  if (track && !reduce) {
    let off = 0;
    const third = () => track.scrollWidth / 3;
    const loop = () => {
      off -= 0.5;
      if (-off >= third()) off = 0;
      track.style.transform = `translateX(${off}px)`;
      requestAnimationFrame(loop);
    };
    loop();
  }

  /* ── aurora parallax (pointer, subtle) ── */
  const blobs = $$('.blob');
  if (blobs.length && !reduce) {
    addEventListener('mousemove', e => {
      const cx = (e.clientX / innerWidth - 0.5);
      const cy = (e.clientY / innerHeight - 0.5);
      blobs.forEach((b, i) => {
        const d = (i + 1) * 14;
        b.style.translate = `${cx * d}px ${cy * d}px`;
      });
    }, { passive: true });
  }
})();
