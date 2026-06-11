/**
 * Government Schemes page — loads schemes from API + Gemini advisor
 */
(function () {
  const grid = document.getElementById('schemesGrid');
  const searchInput = document.getElementById('searchInput');
  const stateFilter = document.getElementById('stateFilter');
  const typeFilter = document.getElementById('typeFilter');
  const advisorForm = document.getElementById('schemeAdvisorForm');
  const advisorBtn = document.getElementById('advisorBtn');
  const advisorResult = document.getElementById('advisorResult');
  const advisorLoading = document.getElementById('advisorLoading');
  const modal = document.getElementById('infoModal');
  const modalTitle = document.getElementById('modalTitle');
  const modalBody = document.getElementById('modalBody');
  const modalActions = document.getElementById('modalActions');

  let schemes = [];
  let activeScheme = null;
  const weatherForm = document.getElementById('weatherForm');
  const weatherLocationInput = document.getElementById('weatherLocation');
  const weatherResult = document.getElementById('weatherResult');

  function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
  }

  function formatAiResponse(text) {
    if (!text) return '';
    const lines = escapeHtml(text).split('\n');
    let html = '';
    let inList = false;

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line) {
        if (inList) {
          html += '</ul>';
          inList = false;
        }
        continue;
      }

      const heading = line.match(/^##+\s*(.+)$/);
      const bullet = line.match(/^[\-\*\•]\s+(.+)$/);
      if (heading) {
        if (inList) {
          html += '</ul>';
          inList = false;
        }
        html += `<h3>${heading[1]}</h3>`;
        continue;
      }
      if (bullet) {
        if (!inList) {
          inList = true;
          html += '<ul class="ai-list">';
        }
        html += `<li>${bullet[1]}</li>`;
        continue;
      }

      if (inList) {
        html += '</ul>';
        inList = false;
      }
      html += `<p>${line}</p>`;
    }

    if (inList) html += '</ul>';
    return html;
  }

  function renderWeatherResult(weather) {
    if (!weather || weather.error) {
      return `<p class="load-error">${escapeHtml(weather?.error || 'Unable to load weather data.')}</p>`;
    }

    let alertsHtml = '';
    if (weather.alerts && weather.alerts.length) {
      alertsHtml = weather.alerts.map((alert) => `
        <div class="weather-alert">
          <strong>${escapeHtml(alert.event || 'Weather Alert')}</strong>
          <p>${escapeHtml(alert.description || alert.sender_name || '')}</p>
        </div>
      `).join('');
    }

    const forecastHtml = weather.forecast.map((day) => `
      <div class="weather-day">
        <strong>${escapeHtml(day.date)}</strong>
        <p>${escapeHtml(day.condition)}</p>
        <p>${day.temp_max}° / ${day.temp_min}°  ·  ${day.precipitation}% rain
        </p>
      </div>
    `).join('');

    return `
      <div class="weather-summary">
        <div>
          <p class="weather-temp">${weather.current.temperature}°C</p>
          <p class="weather-meta">${escapeHtml(weather.current.condition)} · Feels like ${weather.current.feels_like}°C</p>
          <p class="weather-meta">Humidity ${weather.current.humidity}% · Wind ${weather.current.wind_speed} m/s</p>
        </div>
        <p class="weather-meta"><strong>${escapeHtml(weather.location)}</strong></p>
      </div>
      ${alertsHtml}
      <div class="weather-forecast">${forecastHtml}</div>
    `;
  }

  async function fetchWeather(location) {
    if (!weatherResult) return;
    if (!location) {
      weatherResult.innerHTML = '<p class="load-error">Please enter a location to fetch weather.</p>';
      return;
    }

    weatherResult.innerHTML = '<p>Loading weather information…</p>';
    try {
      const res = await fetch(`/api/weather?location=${encodeURIComponent(location)}`);
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Unable to fetch weather.');
      }
      weatherResult.innerHTML = renderWeatherResult(data.weather);
    } catch (err) {
      weatherResult.innerHTML = `<p class="load-error">${escapeHtml(err.message)}</p>`;
    }
  }

  function onWeatherSubmit(event) {
    event.preventDefault();
    const query = weatherLocationInput.value.trim();
    fetchWeather(query);
  }

  function badgeClass(badge) {
    return badge === 'state' ? 'badge-state' : 'badge-central';
  }

  function badgeLabel(badge) {
    return badge === 'state' ? 'State Govt' : 'Central Govt';
  }

  function formatInline(text) {
    return escapeHtml(text || '')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>');
  }

  function renderAiResponse(text) {
    const cleaned = (text || '').trim();
    if (!cleaned) return '<div class="ai-response"><p>No response received.</p></div>';

    const lines = cleaned.split(/\r?\n/);
    const sections = [];
    let current = { title: '', items: [], paragraphs: [] };

    function pushCurrent() {
      if (current.title || current.items.length || current.paragraphs.length) {
        sections.push(current);
      }
    }

    lines.forEach((rawLine) => {
      const line = rawLine.trim();
      if (!line) return;

      const heading = line.match(/^#{1,3}\s+(.+)$/);
      if (heading) {
        pushCurrent();
        current = { title: heading[1].trim(), items: [], paragraphs: [] };
        return;
      }

      const bullet = line.match(/^[-*]\s+(.+)$/);
      if (bullet) {
        current.items.push(bullet[1].trim());
        return;
      }

      current.paragraphs.push(line);
    });
    pushCurrent();

    if (!sections.length) {
      return `<div class="ai-response"><p>${formatInline(cleaned).replace(/\n/g, '<br>')}</p></div>`;
    }

    const html = sections.map((section) => {
      const title = section.title ? `<h3>${formatInline(section.title)}</h3>` : '';
      const paragraphs = section.paragraphs.map((p) => `<p>${formatInline(p)}</p>`).join('');
      const items = section.items.length
        ? `<ul>${section.items.map((item) => `<li>${formatInline(item)}</li>`).join('')}</ul>`
        : '';
      const sectionClass = section.title ? 'ai-section' : 'response-note';
      return `<section class="${sectionClass}">${title}${paragraphs}${items}</section>`;
    }).join('');

    return `<div class="ai-response">${html}</div>`;
  }

  function renderCard(s) {
    const card = document.createElement('article');
    card.className = 'scheme-card';
    card.dataset.location = s.location;
    card.dataset.type = s.type;
    card.dataset.id = s.id;
    card.innerHTML = `
      <div class="card-header">
        <div class="scheme-icon">${escapeHtml(s.icon)}</div>
        <span class="badge ${badgeClass(s.badge)}">${badgeLabel(s.badge)}</span>
      </div>
      <div class="card-body">
        <h3>${escapeHtml(s.name)}</h3>
        <p>${escapeHtml(s.description)}</p>
        <div class="benefit-box">
          <span class="benefit-icon">✓</span>
          <strong>${escapeHtml(s.benefit)}</strong>
        </div>
        <p class="eligibility-snippet"><strong>Eligibility:</strong> ${escapeHtml(s.eligibility)}</p>
      </div>
      <div class="card-footer">
        <button type="button" class="btn btn-outline btn-full btn-ai-details" data-id="${escapeHtml(s.id)}">✨ AI Guide</button>
        <a class="btn btn-primary btn-full" href="${escapeHtml(s.url)}" target="_blank" rel="noopener">Apply / Portal</a>
      </div>
    `;
    card.querySelector('.btn-ai-details').addEventListener('click', () => openSchemeAI(s));
    return card;
  }

  function populateStateFilter() {
    const options = [
      { value: 'all', label: 'All Locations' },
      { value: 'national', label: 'National (Central)' },
    ];
    const seen = new Set(['all', 'national']);
    schemes.forEach((s) => {
      if (s.location !== 'national' && !seen.has(s.location)) {
        seen.add(s.location);
        const label = s.location.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
        options.push({ value: s.location, label });
      }
    });
    stateFilter.innerHTML = '';
    options.forEach((st) => {
      const opt = document.createElement('option');
      opt.value = st.value;
      opt.textContent = st.label;
      stateFilter.appendChild(opt);
    });
  }

  function filterSchemes() {
    const searchTerm = searchInput.value.toLowerCase();
    const stateValue = stateFilter.value;
    const typeValue = typeFilter.value;
    let visibleCount = 0;

    grid.querySelectorAll('.empty-state').forEach((el) => el.remove());
    document.querySelectorAll('.scheme-card').forEach((card) => {
      const title = card.querySelector('h3').textContent.toLowerCase();
      const desc = card.querySelector('p').textContent.toLowerCase();
      const location = card.getAttribute('data-location');
      const type = card.getAttribute('data-type');
      const matchesSearch = title.includes(searchTerm) || desc.includes(searchTerm);
      const matchesState = stateValue === 'all' || location === stateValue;
      const matchesType = typeValue === 'all' || type === typeValue;
      const isVisible = matchesSearch && matchesState && matchesType;
      card.style.display = isVisible ? 'flex' : 'none';
      if (isVisible) visibleCount += 1;
    });

    if (!visibleCount && schemes.length) {
      const empty = document.createElement('p');
      empty.className = 'empty-state';
      empty.textContent = 'No schemes match these filters. Try another state, type, or search term.';
      grid.appendChild(empty);
    }
  }

  async function loadSchemes() {
    try {
      const res = await fetch('/api/schemes');
      const data = await res.json();
      schemes = data.schemes || [];
      grid.innerHTML = '';
      if (!schemes.length) {
        grid.innerHTML = '<p class="empty-state">No schemes are available right now.</p>';
        return;
      }
      schemes.forEach((s) => grid.appendChild(renderCard(s)));
      populateStateFilter();
      filterSchemes();
    } catch (e) {
      grid.innerHTML = '<p class="load-error">Could not load schemes. Refresh the page.</p>';
      console.error(e);
    }
  }

  async function openSchemeAI(scheme) {
    activeScheme = scheme;
    modalTitle.textContent = scheme.name;
    modalBody.innerHTML = '<p class="modal-loading">Generating personalized guide with Gemini...</p>';
    modalActions.innerHTML = '';
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';

    const state = document.getElementById('advisorState')?.value || 'India';
    try {
      const res = await fetch(`/api/schemes/${scheme.id}/explain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state,
          question: 'Explain eligibility, required documents, step-by-step application, and benefits for a small farmer.',
        }),
      });
      const data = await res.json();
      const text = data.response || data.error || 'Unable to load AI guide.';
      modalBody.innerHTML = renderAiResponse(text);
      modalActions.innerHTML = `
        <a class="btn btn-primary" href="${escapeHtml(scheme.url)}" target="_blank" rel="noopener">Official Portal</a>
        <button type="button" class="btn btn-outline" id="modalCloseBtn">Close</button>
      `;
      document.getElementById('modalCloseBtn').onclick = () => {
        modal.classList.remove('show');
        document.body.style.overflow = 'auto';
      };
    } catch (e) {
      const fallbackResponse = `
## Eligibility & Quick Guide for ${escapeHtml(scheme.name)}

This is a general farming support program. Here are typical requirements:

### Basic Eligibility
- Indian farmer with valid land records
- Farming as primary occupation
- Adheres to scheme-specific conditions

### Required Documents
- Land records (Patta/Khata/Record of Rights)
- Aadhar Card
- Bank Account (IFSC code needed)
- Farmer ID or proof of occupation

### How To Apply
- Visit the official scheme portal
- Register with your state agriculture office
- Submit required documents
- Wait for verification and approval

### Next Steps
1. Visit the official portal (link below)
2. Check state-specific guidelines
3. Contact your local agriculture officer for detailed eligibility
4. Prepare documents in advance

For detailed information and to apply, please visit the official portal.`;
      
      modalBody.innerHTML = renderAiResponse(fallbackResponse);
      modalActions.innerHTML = `
        <a class="btn btn-primary" href="${escapeHtml(scheme.url)}" target="_blank" rel="noopener">Official Portal</a>
        <button type="button" class="btn btn-outline" id="modalCloseBtn">Close</button>
      `;
      document.getElementById('modalCloseBtn').onclick = () => {
        modal.classList.remove('show');
        document.body.style.overflow = 'auto';
      };
    }
  }

  function closeModal(e) {
    if (e.target.id === 'infoModal') {
      modal.classList.remove('show');
      document.body.style.overflow = 'auto';
    }
  }

  async function submitAdvisor(e) {
    e.preventDefault();
    const message = document.getElementById('advisorMessage').value.trim();
    if (!message) return;

    if (advisorBtn) advisorBtn.disabled = true;
    advisorLoading.style.display = 'flex';
    advisorResult.style.display = 'none';

    const payload = {
      message,
      state: document.getElementById('advisorState').value,
      crop: document.getElementById('advisorCrop').value.trim() || 'not specified',
      land_acres: document.getElementById('advisorLand').value.trim() || 'not specified',
    };

    try {
      const res = await fetch('/api/schemes/advise', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      advisorResult.innerHTML = renderAiResponse(data.response || data.error || 'No response');
      advisorResult.style.display = 'block';
    } catch (err) {
      const fallbackResponse = `
## Scheme Recommendations Based on Your Profile

Based on your farming profile, here are some general government schemes that may be useful:

### Popular Schemes for Farmers
- **PM-KISAN**: Direct income support program (₹6,000/year in installments)
- **Pradhan Mantri Fasal Bima Yojana (PMFBY)**: Crop insurance for weather risks and crop failure
- **Pradhan Mantri Kisan Samman Nidhi**: Agricultural income support scheme
- **State-specific subsidies**: Check with your state agriculture office for crop-specific support

### Next Steps
1. **Verify your eligibility** with your state agriculture office
2. **Gather required documents**: Land records, ID proof, bank account details
3. **Visit official portals** to check latest scheme details
4. **Contact local CSC or agriculture officer** for personalized guidance
5. **Apply online or through authorized centers**

### Important Notes
- Schemes vary by state and can change annually
- Some schemes have specific eligibility criteria (land size, crop type, income limit)
- Proper documentation is essential for approval
- Contact your local agriculture department for the most current information

For personalized recommendations, please contact your local agriculture office or visit state government websites.`;
      
      advisorResult.innerHTML = renderAiResponse(fallbackResponse);
      advisorResult.style.display = 'block';
    } finally {
      advisorLoading.style.display = 'none';
      if (advisorBtn) advisorBtn.disabled = false;
    }
  }

  function attachSuggestionButtons() {
    document.querySelectorAll('.suggestion-btn').forEach((button) => {
      button.addEventListener('click', () => {
        const prompt = button.dataset.prompt || '';
        const messageField = document.getElementById('advisorMessage');
        if (messageField) {
          messageField.value = prompt;
          messageField.focus();
        }
      });
    });
  }

  if (searchInput) searchInput.addEventListener('input', filterSchemes);
  if (stateFilter) stateFilter.addEventListener('change', filterSchemes);
  if (typeFilter) typeFilter.addEventListener('change', filterSchemes);
  if (advisorForm) advisorForm.addEventListener('submit', submitAdvisor);
  if (weatherForm) weatherForm.addEventListener('submit', onWeatherSubmit);
  if (modal) modal.addEventListener('click', closeModal);
  attachSuggestionButtons();

  loadSchemes();
})();
