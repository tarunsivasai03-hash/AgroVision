/*
 * Gemini page translator for AgroVision.
 * Captures the original English DOM and translates visible UI strings on demand.
 */
(function () {
  'use strict';

  const LANGUAGE_OPTIONS = [
    ['en', 'English'],
    ['hi', 'Hindi'],
    ['te', 'Telugu'],
    ['ta', 'Tamil'],
    ['kn', 'Kannada'],
    ['mr', 'Marathi'],
  ];

  const SKIP_SELECTOR = [
    'script',
    'style',
    'noscript',
    'svg',
    'canvas',
    'code',
    'pre',
    '[data-no-translate]',
    '.message.user',
    '.chatbot-message.user',
    'input[type="file"]',
  ].join(',');

  let textItems = [];
  let attributeItems = [];
  let originalTitle = '';
  let translating = false;
  let translationDisabled = false;
  let debounceTimer = null;
  let mutationObserver = null;

  function languageName(codeOrName) {
    const found = LANGUAGE_OPTIONS.find(([code]) => code === codeOrName);
    return found ? found[1] : codeOrName;
  }

  function isWorthTranslating(text) {
    const value = (text || '').replace(/\s+/g, ' ').trim();
    if (!value) return false;
    if (/^[\d\s.,:%₹$€£+\-*/()[\]#|]+$/.test(value)) return false;
    return /[A-Za-z]/.test(value);
  }

  function shouldSkip(node) {
    const element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
    return !element || !!element.closest(SKIP_SELECTOR);
  }

  function collectTextNodes() {
    textItems = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (shouldSkip(node)) return NodeFilter.FILTER_REJECT;
        return isWorthTranslating(node.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      },
    });

    let node;
    while ((node = walker.nextNode())) {
      if (!node.__agroOriginalText) {
        node.__agroOriginalText = node.nodeValue;
      }
      textItems.push({ node, original: node.__agroOriginalText });
    }
  }

  function collectAttributes() {
    attributeItems = [];
    const elements = document.querySelectorAll('input, textarea, button, [title], [aria-label]');
    elements.forEach((el) => {
      if (shouldSkip(el)) return;
      ['placeholder', 'title', 'aria-label'].forEach((attr) => {
        const value = el.getAttribute(attr);
        if (!isWorthTranslating(value)) return;
        const key = `__agroOriginal_${attr}`;
        if (!el[key]) el[key] = value;
        attributeItems.push({ element: el, attr, original: el[key] });
      });
    });
  }

  function collectOriginals() {
    if (!originalTitle) originalTitle = document.title;
    collectTextNodes();
    collectAttributes();
  }

  function restoreEnglish() {
    textItems.forEach((item) => {
      item.node.nodeValue = item.original;
    });
    attributeItems.forEach((item) => {
      item.element.setAttribute(item.attr, item.original);
    });
    if (originalTitle) document.title = originalTitle;
    document.documentElement.lang = 'en';
  }

  function getStoredGeminiApiKey() {
    return localStorage.getItem('agrovision_gemini_api_key') || '';
  }

  function getCacheKey(targetLanguage, texts) {
    return `agrovision-translation:${location.pathname}:${targetLanguage}:${btoa(unescape(encodeURIComponent(texts.join('\\u0001')))).slice(0, 80)}`;
  }

  async function translateBatch(texts, targetLanguage) {
    const cacheKey = getCacheKey(targetLanguage, texts);
    const cached = sessionStorage.getItem(cacheKey);
    if (cached) return JSON.parse(cached);

    const response = await fetch('/api/translate-page', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_language: languageName(targetLanguage),
        texts,
        gemini_api_key: getStoredGeminiApiKey(),
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      const err = new Error(data.response || data.error || 'Translation failed');
      err.httpStatus = response.status;
      throw err;
    }
    sessionStorage.setItem(cacheKey, JSON.stringify(data.translations));
    return data.translations;
  }

  function disableTranslation() {
    translationDisabled = true;
    if (mutationObserver) {
      mutationObserver.disconnect();
      mutationObserver = null;
    }
  }

  async function applyGeminiTranslation(targetLanguage) {
    if (!targetLanguage || targetLanguage === 'en') {
      restoreEnglish();
      return;
    }

    if (translationDisabled) {
      return;
    }

    collectTextNodes();
    collectAttributes();

    const items = [
      ...(isWorthTranslating(originalTitle) ? [{ type: 'title', original: originalTitle }] : []),
      ...textItems.map((item) => ({ type: 'text', target: item.node, original: item.original })),
      ...attributeItems.map((item) => ({ type: 'attr', target: item.element, attr: item.attr, original: item.original })),
    ];

    const texts = items.map((item) => item.original.replace(/\s+/g, ' ').trim());
    if (!texts.length) return;

    translating = true;
    document.documentElement.classList.add('is-translating');
    try {
      const batchSize = 80;
      for (let start = 0; start < texts.length; start += batchSize) {
        const batchTexts = texts.slice(start, start + batchSize);
        const translated = await translateBatch(batchTexts, targetLanguage);
        translated.forEach((value, index) => {
          const item = items[start + index];
          if (!item) return;
          if (item.type === 'text') {
            item.target.nodeValue = value;
          } else if (item.type === 'title') {
            document.title = value;
          } else {
            item.target.setAttribute(item.attr, value);
          }
        });
      }
      document.documentElement.lang = targetLanguage;
    } catch (error) {
      console.error('Translation error:', error);
      const status = error.httpStatus || 0;
      const isPermanent = status === 503 || status === 401;
      if (isPermanent) {
        showTranslationError('Translation is unavailable. Check your Gemini API key and try again.');
        disableTranslation();
      } else {
        showTranslationError(error.message);
      }
      setSelectedLanguage('en');
      restoreEnglish();
    } finally {
      translating = false;
      document.documentElement.classList.remove('is-translating');
    }
  }

  function showTranslationError(message) {
    let toast = document.getElementById('translationToast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'translationToast';
      toast.style.cssText = 'position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:9999;background:#0f172a;color:#fff;padding:10px 14px;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.2);font:500 14px Inter,system-ui;max-width:min(92vw,560px);';
      document.body.appendChild(toast);
    }
    toast.textContent = message || 'Could not translate this page. Check your Gemini API key and try again.';
    clearTimeout(toast.__timer);
    toast.__timer = setTimeout(() => toast.remove(), 5000);
  }

  function ensureLanguageOptions(select) {
    const current = select.value || localStorage.getItem('selectedLanguage') || 'en';
    const seen = new Set([...select.options].map((option) => option.value));
    LANGUAGE_OPTIONS.forEach(([value, label]) => {
      if (seen.has(value)) return;
      const option = document.createElement('option');
      option.value = value;
      option.textContent = label;
      select.appendChild(option);
    });

    if ([...select.options].some((option) => option.value === current)) {
      select.value = current;
    }
  }

  function bindLanguageSelect(select) {
    ensureLanguageOptions(select);
    select.addEventListener('change', () => {
      const value = select.value;
      localStorage.setItem('selectedLanguage', value);
      window.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: value } }));
    });
  }

  function setSelectedLanguage(lang) {
    localStorage.setItem('selectedLanguage', lang);
    document.querySelectorAll('#languageSelect, #languageSelectMobile').forEach((select) => {
      if (select) select.value = lang;
    });
  }

  function selectedLanguage() {
    const stored = localStorage.getItem('selectedLanguage');
    const supported = LANGUAGE_OPTIONS.map(([value]) => value);
    if (stored && supported.includes(stored)) {
      return stored;
    }
    const elementValue = document.getElementById('languageSelect')?.value;
    return supported.includes(elementValue) ? elementValue : 'en';
  }

  function scheduleTranslation(language) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => applyGeminiTranslation(language), 120);
  }

  function init() {
    collectOriginals();
    document.querySelectorAll('#languageSelect, #languageSelectMobile').forEach(bindLanguageSelect);
    const initialLanguage = selectedLanguage();
    if (initialLanguage !== 'en') {
      scheduleTranslation(initialLanguage);
    }

    window.addEventListener('languageChanged', (event) => {
      const lang = event.detail?.language || selectedLanguage();
      if (translationDisabled && lang !== 'en') return;
      scheduleTranslation(lang);
    });

    mutationObserver = new MutationObserver(() => {
      if (translating || translationDisabled || selectedLanguage() === 'en') return;
      scheduleTranslation(selectedLanguage());
    });
    mutationObserver.observe(document.body, { childList: true, subtree: true });
  }

  window.AgroVisionTranslate = {
    translate: applyGeminiTranslation,
    languageName,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
