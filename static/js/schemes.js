/**
 * Government schemes page: scheme list with filters, the scheme advisor,
 * and the plain-language guide for a single scheme.
 */
(function () {
  'use strict';

  const grid = document.getElementById('schemesGrid');
  const countLabel = document.getElementById('schemeCount');
  const searchInput = document.getElementById('searchInput');
  const stateFilter = document.getElementById('stateFilter');
  const typeFilter = document.getElementById('typeFilter');
  const advisorForm = document.getElementById('schemeAdvisorForm');
  const advisorBtn = document.getElementById('advisorBtn');
  const advisorResult = document.getElementById('advisorResult');
  const advisorLoading = document.getElementById('advisorLoading');
  const dialog = document.getElementById('infoModal');
  const dialogTitle = document.getElementById('modalTitle');
  const dialogBody = document.getElementById('modalBody');
  const dialogActions = document.getElementById('modalActions');

  const DEFAULT_QUESTION = 'Which schemes can I apply for, and what documents do I need?';
  const TYPE_LABELS = {
    financial: 'Income and credit',
    insurance: 'Crop insurance',
    infrastructure: 'Farm infrastructure',
  };
  const TYPE_ICONS = {
    financial: '<path d="M12 2v20"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    insurance: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    infrastructure: '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5S5 13 5 15a7 7 0 0 0 7 7z"/>',
  };
  const EXTERNAL_ICON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>';

  let schemes = [];

  // --- Formatting helpers ---------------------------------------------------

  function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text == null ? '' : String(text);
    return d.innerHTML;
  }

  function titleCase(slug) {
    return String(slug || '').replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function formatInline(text) {
    return escapeHtml(text)
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>');
  }

  /** Render Gemini's markdown-ish answer (headings, bullets, numbered steps) safely. */
  function renderAiResponse(text) {
    const cleaned = (text || '').trim();
    if (!cleaned) return '<p>No answer was returned. Try again.</p>';

    const sections = [];
    let current = { title: '', blocks: [] };
    const pushList = (type, item) => {
      const last = current.blocks[current.blocks.length - 1];
      if (last && last.type === type) last.items.push(item);
      else current.blocks.push({ type, items: [item] });
    };

    cleaned.split(/\r?\n/).forEach((raw) => {
      const line = raw.trim();
      if (!line) return;
      const heading = line.match(/^#{1,4}\s+(.+)$/);
      const bullet = line.match(/^[-*•]\s+(.+)$/);
      const numbered = line.match(/^\d+[.)]\s+(.+)$/);
      if (heading) {
        if (current.title || current.blocks.length) sections.push(current);
        current = { title: heading[1], blocks: [] };
      } else if (bullet) {
        pushList('ul', bullet[1]);
      } else if (numbered) {
        pushList('ol', numbered[1]);
      } else {
        current.blocks.push({ type: 'p', text: line });
      }
    });
    if (current.title || current.blocks.length) sections.push(current);

    const html = sections.map((section) => {
      const title = section.title ? `<h3>${formatInline(section.title)}</h3>` : '';
      const body = section.blocks.map((b) => (b.type === 'p'
        ? `<p>${formatInline(b.text)}</p>`
        : `<${b.type}>${b.items.map((i) => `<li>${formatInline(i)}</li>`).join('')}</${b.type}>`)).join('');
      return `<section>${title}${body}</section>`;
    }).join('');
    return `<div class="ai-response">${html}</div>`;
  }

  function notice(kind, text) {
    return `<p class="notice ${kind}" role="note"><span>${escapeHtml(text)}</span></p>`;
  }

  function fallbackNotice(data) {
    return data && data.ai_powered === false
      ? notice('notice-warn', 'The AI advisor is not available right now, so this is general information rather than advice for your farm.')
      : '';
  }

  async function postJson(url, payload) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `The server returned an error (${res.status}).`);
    return data;
  }

  function errorMessage(err) {
    return !navigator.onLine || err instanceof TypeError
      ? 'Could not reach AgroVision. Check your internet connection and try again.'
      : err.message;
  }

  // --- Scheme list ------------------------------------------------------------

  function governmentLabel(s) {
    return s.location === 'national' ? 'Central government' : `${titleCase(s.location)} government`;
  }

  function renderCard(s) {
    const card = document.createElement('article');
    card.className = 'scheme-card';
    card.dataset.location = s.location;
    card.dataset.type = s.type;
    card.dataset.search = [s.name, s.description, s.benefit, s.eligibility].join(' ').toLowerCase();
    const typeIcon = TYPE_ICONS[s.type] || TYPE_ICONS.financial;
    card.innerHTML = `
      <div class="scheme-meta">
        <span class="scheme-type"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${typeIcon}</svg>${escapeHtml(TYPE_LABELS[s.type] || titleCase(s.type))}</span>
        <span class="scheme-gov ${s.location === 'national' ? '' : 'state'}">${escapeHtml(governmentLabel(s))}</span>
      </div>
      <h3>${escapeHtml(s.name)}</h3>
      <p class="desc">${escapeHtml(s.description)}</p>
      <p class="benefit">${escapeHtml(s.benefit)}</p>
      <p class="eligibility"><strong>Who can apply:</strong> ${escapeHtml(s.eligibility)}</p>
      <div class="scheme-actions">
        <button type="button" class="btn btn-secondary">Explain in simple words</button>
        <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">Official website ${EXTERNAL_ICON}<span class="visually-hidden"> (opens in a new tab)</span></a>
      </div>
    `;
    card.querySelector('button').addEventListener('click', () => openGuide(s));
    return card;
  }

  function populateStateFilter() {
    const locations = [...new Set(schemes.map((s) => s.location))]
      .sort((a, b) => (a === 'national' ? -1 : b === 'national' ? 1 : a.localeCompare(b)));
    stateFilter.innerHTML = '<option value="all">All governments</option>';
    locations.forEach((loc) => {
      const opt = document.createElement('option');
      opt.value = loc;
      opt.textContent = loc === 'national' ? 'Central government' : `${titleCase(loc)} government`;
      stateFilter.appendChild(opt);
    });
  }

  function filterSchemes() {
    const term = searchInput.value.trim().toLowerCase();
    const state = stateFilter.value;
    const type = typeFilter.value;
    let visible = 0;

    grid.querySelectorAll('.list-message').forEach((el) => el.remove());
    grid.querySelectorAll('.scheme-card').forEach((card) => {
      const show = (!term || card.dataset.search.includes(term))
        && (state === 'all' || card.dataset.location === state)
        && (type === 'all' || card.dataset.type === type);
      card.hidden = !show;
      if (show) visible += 1;
    });

    countLabel.textContent = `Showing ${visible} of ${schemes.length}`;
    if (!visible && schemes.length) {
      const empty = document.createElement('p');
      empty.className = 'list-message';
      empty.textContent = 'No schemes match. Clear the search or choose "All governments" and "All types".';
      grid.appendChild(empty);
    }
  }

  async function loadSchemes() {
    try {
      const res = await fetch('/api/schemes');
      if (!res.ok) throw new Error(`The server returned an error (${res.status}).`);
      schemes = (await res.json()).schemes || [];
      grid.replaceChildren(...schemes.map(renderCard));
      if (!schemes.length) {
        grid.innerHTML = '<p class="list-message">No schemes are listed yet.</p>';
        return;
      }
      populateStateFilter();
      filterSchemes();
    } catch (err) {
      grid.innerHTML = `<p class="list-message">Could not load schemes. ${escapeHtml(errorMessage(err))}</p>`;
    }
  }

  // --- Scheme guide dialog ----------------------------------------------------

  function setGuideActions(scheme) {
    dialogActions.innerHTML = `
      <a class="btn btn-primary" href="${escapeHtml(scheme.url)}" target="_blank" rel="noopener">Open official website<span class="visually-hidden"> (opens in a new tab)</span></a>
      <button type="button" class="btn btn-secondary" data-close>Close</button>
    `;
    dialogActions.querySelector('[data-close]').addEventListener('click', () => dialog.close());
  }

  async function openGuide(scheme) {
    dialogTitle.textContent = scheme.name;
    dialogBody.innerHTML = '<p class="guide-loading"><span class="spinner" aria-hidden="true"></span>Writing a simple guide to this scheme…</p>';
    setGuideActions(scheme);
    dialog.showModal();

    const state = document.getElementById('advisorState').value || 'India';
    try {
      const data = await postJson(`/api/schemes/${encodeURIComponent(scheme.id)}/explain`, {
        state,
        question: 'Explain who can apply, the documents needed, the steps to apply, and the benefit, for a small farmer.',
      });
      dialogBody.innerHTML = fallbackNotice(data) + renderAiResponse(data.response);
    } catch (err) {
      const docs = (scheme.documents || []).map((d) => `<li>${escapeHtml(d)}</li>`).join('');
      dialogBody.innerHTML = notice('notice-warn', `Could not write a guide: ${errorMessage(err)} Here are the basic details.`)
        + `<div class="ai-response">
             <section><h3>Benefit</h3><p>${escapeHtml(scheme.benefit)}</p></section>
             <section><h3>Who can apply</h3><p>${escapeHtml(scheme.eligibility)}</p></section>
             ${docs ? `<section><h3>Documents</h3><ul>${docs}</ul></section>` : ''}
           </div>`;
    }
  }

  document.getElementById('closeModalBtn').addEventListener('click', () => dialog.close());
  // Close when the backdrop (outside the dialog box) is clicked.
  dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.close(); });

  // --- Advisor ----------------------------------------------------------------

  async function submitAdvisor(e) {
    e.preventDefault();
    const message = document.getElementById('advisorMessage').value.trim() || DEFAULT_QUESTION;
    advisorBtn.disabled = true;
    advisorLoading.classList.add('show');
    advisorResult.innerHTML = '';

    try {
      const data = await postJson('/api/schemes/advise', {
        message,
        state: document.getElementById('advisorState').value,
        crop: document.getElementById('advisorCrop').value.trim(),
        land_acres: document.getElementById('advisorLand').value.trim(),
      });
      advisorResult.innerHTML = fallbackNotice(data) + renderAiResponse(data.response);
    } catch (err) {
      advisorResult.innerHTML = notice('notice-danger', errorMessage(err));
    } finally {
      advisorLoading.classList.remove('show');
      advisorBtn.disabled = false;
    }
  }

  document.querySelectorAll('.suggestion-btn').forEach((button) => {
    button.addEventListener('click', () => {
      const field = document.getElementById('advisorMessage');
      field.value = button.dataset.prompt || '';
      field.focus();
    });
  });

  searchInput.addEventListener('input', filterSchemes);
  stateFilter.addEventListener('change', filterSchemes);
  typeFilter.addEventListener('change', filterSchemes);
  advisorForm.addEventListener('submit', submitAdvisor);

  loadSchemes();
})();
