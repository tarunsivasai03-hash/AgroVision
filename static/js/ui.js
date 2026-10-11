/*
 * Shared page shell behaviour: theme toggle, back-to-top button, offline banner.
 * The initial theme is applied by an inline script in base.html to avoid a flash.
 */
(function () {
  'use strict';

  const THEME_KEY = 'agrovision-theme';
  const root = document.documentElement;

  function storeTheme(theme) {
    try { localStorage.setItem(THEME_KEY, theme); } catch (e) { /* storage unavailable */ }
  }

  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    const toggle = document.getElementById('themeToggle');
    if (toggle) {
      const label = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
      toggle.setAttribute('aria-label', label);
      toggle.title = label;
    }
  }

  function init() {
    applyTheme(root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light');

    const toggle = document.getElementById('themeToggle');
    if (toggle) {
      toggle.addEventListener('click', () => {
        const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        storeTheme(next);
      });
    }

    const backToTop = document.getElementById('backToTop');
    if (backToTop) {
      const update = () => { backToTop.hidden = window.scrollY < 400; };
      window.addEventListener('scroll', update, { passive: true });
      update();
      backToTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
    }

    const offline = document.getElementById('offlineIndicator');
    if (offline) {
      const sync = () => offline.classList.toggle('show', !navigator.onLine);
      window.addEventListener('offline', sync);
      window.addEventListener('online', sync);
      sync();
    }

    const year = document.getElementById('year');
    if (year) year.textContent = new Date().getFullYear();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
