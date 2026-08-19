(() => {
  const views = {
    create: ['CREATE', 'Make speech'],
    projects: ['PROJECTS', 'Build longer work'],
    voices: ['VOICES', 'Your voice identities'],
    history: ['HISTORY', 'Nothing good gets lost'],
    models: ['MODELS', 'What runs underneath'],
    settings: ['SETTINGS', 'This machine & storage']
  };

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];

  const text = $('#text');
  const voice = $('#voice');
  const language = $('#language');
  const quality = $('#quality');
  const speed = $('#speed');
  const speedValue = $('#speed-value');
  const characterCount = $('#character-count');
  const generateButton = $('#generate');
  const cancelButton = $('#cancel-job');
  const statusDot = $('#status-dot');
  const jobStatus = $('#job-status');
  const jobSubtitle = $('#job-subtitle');
  const jobProgress = $('#job-progress');
  const progressBar = $('#progress-bar');
  const routeSummary = $('#route-summary');
  const engine = $('#engine');
  const reason = $('#reason');
  const technicalDetails = $('#technical-details');
  const jobJson = $('#job-json');
  const audio = $('#audio');
  const playerToggle = $('#player-toggle');
  const playerTitle = $('#player-title');
  const playerSubtitle = $('#player-subtitle');
  const seek = $('#seek');
  const timeReadout = $('#time-readout');
  const downloadAudio = $('#download-audio');
  const toastRegion = $('#toast-region');

  let selectedStyle = 'natural';
  let currentView = 'create';
  let currentJobId = null;
  let pollTimer = null;
  let developerMode = false;
  let latestSystem = null;

  function toast(message, kind = 'normal') {
    const node = document.createElement('div');
    node.className = `toast ${kind === 'error' ? 'error' : ''}`;
    node.textContent = message;
    toastRegion.appendChild(node);
    window.setTimeout(() => node.remove(), 4200);
  }

  async function getJson(url) {
    const response = await fetch(url, {headers: {'Accept': 'application/json'}});
    let body;
    try {
      body = await response.json();
    } catch {
      throw new Error(`Request failed (${response.status})`);
    }
    if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
    return body;
  }

  async function postJson(url, payload) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
      body: JSON.stringify(payload)
    });
    let body;
    try {
      body = await response.json();
    } catch {
      throw new Error(`Request failed (${response.status})`);
    }
    if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
    return body;
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function formatBytes(bytes) {
    if (!Number.isFinite(bytes) || bytes < 0) return 'Unknown';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let value = bytes;
    let unit = 0;
    while (value >= 1024 && unit < units.length - 1) {
      value /= 1024;
      unit += 1;
    }
    return `${value.toFixed(unit >= 3 ? 1 : 0)} ${units[unit]}`;
  }

  function formatTime(seconds) {
    const safe = Number.isFinite(seconds) && seconds >= 0 ? seconds : 0;
    const minutes = Math.floor(safe / 60);
    const remaining = Math.floor(safe % 60);
    return `${String(minutes).padStart(2, '0')}:${String(remaining).padStart(2, '0')}`;
  }

  function emptyCard(message) {
    return `<div class="empty-card">${escapeHtml(message)}</div>`;
  }

  function requestPayload() {
    const controls = {};
    const selectedSpeed = Number(speed.value);
    if (Math.abs(selectedSpeed - 1) > 0.001) controls.speed = selectedSpeed;
    return {
      text: text.value.trim(),
      voice: voice.value || null,
      language: language.value || null,
      style: selectedStyle,
      quality: quality.value,
      offline: quality.value === 'local',
      controls
    };
  }

  function setJobVisual(job) {
    const status = job?.status || 'queued';
    const phase = job?.phase || status;
    const progress = Math.max(0, Math.min(1, Number(job?.progress || 0)));
    const labels = {
      queued: 'Queued',
      planning: 'Choosing a route',
      loading_model: 'Loading model',
      generating: 'Generating',
      rendering: 'Rendering',
      quality_check: 'Checking quality',
      cancel_requested: 'Cancelling',
      cancelled: 'Cancelled',
      interrupted: 'Interrupted',
      completed: 'Ready',
      failed: 'Generation failed'
    };
    jobStatus.textContent = labels[phase] || labels[status] || phase.replaceAll('_', ' ');
    jobProgress.textContent = `${Math.round(progress * 100)}%`;
    progressBar.style.width = `${Math.round(progress * 100)}%`;
    statusDot.className = `status-dot ${status === 'completed' ? 'done' : status === 'failed' || status === 'interrupted' ? 'error' : status === 'cancelled' ? 'idle' : 'working'}`;
    jobJson.textContent = JSON.stringify(job, null, 2);

    const result = job?.result || {};
    if (result.engine) {
      routeSummary.classList.remove('hidden');
      engine.textContent = result.engine;
      const reasons = result.routing_reasons || [];
      reason.textContent = Array.isArray(reasons) ? reasons.join('; ') : String(reasons || 'Verified product route');
    }

    if (status === 'queued') jobSubtitle.textContent = 'Waiting for a local generation slot.';
    else if (status === 'planning') jobSubtitle.textContent = 'Matching language, controls, hardware and evidence.';
    else if (status === 'loading_model') jobSubtitle.textContent = `Preparing ${result.engine || 'the selected engine'} locally.`;
    else if (status === 'generating') jobSubtitle.textContent = 'The selected backend is producing this take.';
    else if (status === 'completed') jobSubtitle.textContent = result.voice_id ? `Voice: ${result.voice_id}` : 'The take was generated and added to local history.';
    else if (status === 'failed') jobSubtitle.textContent = job.error || 'The job failed. Technical details preserve the exact reason.';
    else if (status === 'interrupted') jobSubtitle.textContent = job.error || 'ourTTS recovered this unfinished job after restart.';
    else if (status === 'cancelled') jobSubtitle.textContent = 'This generation was cancelled.';

    const active = !['completed', 'failed', 'cancelled', 'interrupted'].includes(status);
    generateButton.disabled = active;
    generateButton.innerHTML = active ? '<span>◌</span> Working…' : '<span>▶</span> Generate';
    cancelButton.classList.toggle('hidden', !active);
  }

  function stopPolling() {
    if (pollTimer !== null) window.clearTimeout(pollTimer);
    pollTimer = null;
  }

  async function pollJob(jobId) {
    try {
      const job = await getJson(`/v1/jobs/${jobId}`);
      if (jobId !== currentJobId) return;
      setJobVisual(job);
      if (job.status === 'completed') {
        stopPolling();
        const result = job.result || {};
        if (result.audio_url) {
          audio.src = `${result.audio_url}?t=${Date.now()}`;
          audio.load();
          downloadAudio.href = result.audio_url;
          downloadAudio.classList.add('ready');
          playerTitle.textContent = text.value.trim().slice(0, 64) || 'Generated take';
          playerSubtitle.textContent = result.engine ? `${result.engine} · local history saved` : 'Local history saved';
          audio.play().catch(() => {});
        }
        await loadHistory();
        return;
      }
      if (['failed', 'cancelled', 'interrupted'].includes(job.status)) {
        stopPolling();
        if (job.status === 'failed') toast(job.error || 'Generation failed', 'error');
        return;
      }
      pollTimer = window.setTimeout(() => pollJob(jobId), 650);
    } catch (error) {
      stopPolling();
      generateButton.disabled = false;
      cancelButton.classList.add('hidden');
      statusDot.className = 'status-dot error';
      jobStatus.textContent = 'Connection problem';
      jobSubtitle.textContent = error instanceof Error ? error.message : String(error);
    }
  }

  async function generate() {
    const payload = requestPayload();
    if (!payload.text) {
      text.focus();
      toast('Type something first.');
      return;
    }

    try {
      stopPolling();
      routeSummary.classList.add('hidden');
      downloadAudio.classList.remove('ready');
      setJobVisual({status: 'queued', phase: 'queued', progress: 0});
      const job = await postJson('/v1/jobs', payload);
      currentJobId = job.id;
      setJobVisual(job);
      pollJob(job.id);
    } catch (error) {
      setJobVisual({
        status: 'failed',
        phase: 'failed',
        progress: 1,
        error: error instanceof Error ? error.message : String(error)
      });
      toast(error instanceof Error ? error.message : String(error), 'error');
    }
  }

  async function cancelCurrentJob() {
    if (!currentJobId) return;
    try {
      const job = await postJson(`/v1/jobs/${currentJobId}/cancel`, {});
      setJobVisual(job);
    } catch (error) {
      toast(error instanceof Error ? error.message : String(error), 'error');
    }
  }

  async function loadVoices() {
    try {
      const library = await getJson('/v1/voices');
      const voices = library.voices || [];
      const previous = voice.value;
      voice.innerHTML = '<option value="">Built-in / Auto voice</option>';
      voices.filter((item) => item.ready).forEach((item) => {
        const option = document.createElement('option');
        option.value = item.voice_id;
        option.textContent = item.display_name;
        voice.appendChild(option);
      });
      if ([...voice.options].some((option) => option.value === previous)) voice.value = previous;

      $('#voices-list').innerHTML = voices.length ? voices.map((item) => `
        <article class="voice-card">
          <div>
            <h3>${escapeHtml(item.display_name)}</h3>
            <p>${escapeHtml(item.voice_id)} · ${(item.languages || []).map(escapeHtml).join(', ') || 'language not specified'}</p>
          </div>
          <div class="card-meta">
            <span class="badge ${item.ready ? 'good' : 'warn'}">${item.ready ? 'Ready' : 'Needs attention'}</span>
            <span class="badge">${escapeHtml(item.references ?? 0)} reference${item.references === 1 ? '' : 's'}</span>
          </div>
        </article>`).join('') : emptyCard('No VoicePacks yet. The built-in voice path still works.');
    } catch (error) {
      $('#voices-list').innerHTML = emptyCard('The Voice Library could not be read.');
    }
  }

  async function loadProjects() {
    const list = $('#projects-list');
    try {
      const payload = await getJson('/v1/projects');
      const projects = payload.projects || [];
      list.innerHTML = projects.length ? projects.map((item) => `
        <article class="entity-card" data-project-id="${escapeHtml(item.id)}">
          <div>
            <h3>${escapeHtml(item.name)}</h3>
            <p>Updated ${escapeHtml(new Date(item.updated_at).toLocaleString())}</p>
          </div>
          <div class="card-meta"><span class="badge">Local project</span></div>
        </article>`).join('') : emptyCard('No projects yet. Create one for scripts that need segments and multiple takes.');
    } catch (error) {
      list.innerHTML = emptyCard(error instanceof Error ? error.message : 'Projects could not be loaded.');
    }
  }

  async function createProject(event) {
    event.preventDefault();
    const input = $('#project-name');
    const name = input.value.trim();
    if (!name) return;
    try {
      await postJson('/v1/projects', {name, metadata: {created_from: 'studio'}});
      input.value = '';
      await loadProjects();
      toast('Project created and saved locally.');
    } catch (error) {
      toast(error instanceof Error ? error.message : String(error), 'error');
    }
  }

  async function loadHistory() {
    const list = $('#history-list');
    try {
      const payload = await getJson('/v1/history?limit=100');
      const history = payload.history || [];
      list.innerHTML = history.length ? history.map((item) => `
        <article class="history-card">
          <div>
            <strong>${escapeHtml(item.text_preview)}</strong>
            <p>${escapeHtml(item.engine || 'engine not recorded')} · ${escapeHtml(item.language || 'language auto')} · ${escapeHtml(new Date(item.created_at).toLocaleString())}</p>
          </div>
          <div class="card-meta">${item.voice_id ? `<span class="badge">${escapeHtml(item.voice_id)}</span>` : ''}</div>
        </article>`).join('') : emptyCard('No generations yet. Your completed takes will appear here automatically.');
    } catch (error) {
      list.innerHTML = emptyCard('History could not be loaded.');
    }
  }

  function modelBadges(item) {
    const badges = [];
    if (item.status === 'ready') badges.push('<span class="badge good">Qualified</span>');
    else badges.push(`<span class="badge">${escapeHtml(item.status)}</span>`);
    if (item.access_gated) badges.push('<span class="badge warn">Access gated</span>');
    if (item.hardware?.includes('cpu')) badges.push('<span class="badge">CPU</span>');
    if (item.hardware?.includes('cuda')) badges.push('<span class="badge">CUDA</span>');
    return badges.join('');
  }

  async function loadModels() {
    try {
      const payload = await getJson('/v1/models');
      const models = payload.models || [];
      const recommended = payload.recommended || [];
      $('#recommended-models').innerHTML = recommended.length ? recommended.map((entry) => `
        <article class="recommended-card">
          <div>
            <h3>${escapeHtml(entry.model.name)}</h3>
            <p>${(entry.reasons || []).map(escapeHtml).join(' · ')}</p>
          </div>
          <div class="card-meta"><span class="badge good">Score ${escapeHtml(entry.score)}</span></div>
        </article>`).join('') : emptyCard('No runtime currently meets the recommendation gate for this machine.');

      $('#models-list').innerHTML = models.map((item) => `
        <article class="model-card">
          <div class="model-card-head">
            <div>
              <h3>${escapeHtml(item.name)}</h3>
              <div class="model-family">${escapeHtml(item.family)}</div>
            </div>
            <div class="card-meta">${modelBadges(item)}</div>
          </div>
          <div class="model-detail">
            <span>Runtime</span><strong>${escapeHtml(item.runtime_state)}</strong>
            <span>Weights</span><strong>${escapeHtml(item.weights_state)}</strong>
            <span>Code license</span><strong>${escapeHtml(item.code_license)}</strong>
            <span>Weights license</span><strong>${escapeHtml(item.weights_license)}</strong>
            <span>CPU RTF</span><strong>${item.cpu_generation_rtf == null ? 'Not measured' : escapeHtml(item.cpu_generation_rtf)}</strong>
          </div>
        </article>`).join('');
    } catch (error) {
      $('#models-list').innerHTML = emptyCard(error instanceof Error ? error.message : 'Models could not be loaded.');
    }
  }

  function settingsCard(title, rows) {
    return `<section class="settings-card"><h3>${escapeHtml(title)}</h3>${rows.map(([label, value]) => `
      <div class="settings-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join('')}</section>`;
  }

  async function loadSystem() {
    try {
      latestSystem = await getJson('/v1/system');
      $('#system-pill').textContent = `${latestSystem.os} · ${latestSystem.accelerator}`;
      const paths = latestSystem.paths || {};
      $('#settings-grid').innerHTML = [
        settingsCard('Machine', [
          ['OS', `${latestSystem.os} ${latestSystem.release}`],
          ['Architecture', latestSystem.machine],
          ['CPU', latestSystem.cpu],
          ['RAM', formatBytes(latestSystem.ram_bytes)],
          ['Accelerator', latestSystem.accelerator],
          ['Free disk', formatBytes(latestSystem.free_disk_bytes)]
        ]),
        settingsCard('Runtime', [
          ['Python', latestSystem.python],
          ['uv', latestSystem.uv || 'Not found'],
          ['FFmpeg', latestSystem.ffmpeg || 'Not found'],
          ['eSpeak', latestSystem.espeak || 'Not found']
        ]),
        settingsCard('Local data', [
          ['Root', paths.root || 'Unknown'],
          ['Database', paths.database || 'Unknown'],
          ['Projects', paths.projects || 'Unknown'],
          ['Voices', paths.voices || 'Unknown']
        ]),
        settingsCard('Large storage', [
          ['Models', paths.models || 'Unknown'],
          ['Cache', paths.cache || 'Unknown'],
          ['Artifacts', paths.artifacts || 'Unknown'],
          ['Logs', paths.logs || 'Unknown']
        ])
      ].join('');
    } catch (error) {
      $('#system-pill').textContent = 'System check unavailable';
      $('#settings-grid').innerHTML = emptyCard('System information could not be read.');
    }
  }

  async function loadView(view) {
    if (view === 'projects') await loadProjects();
    if (view === 'voices') await loadVoices();
    if (view === 'history') await loadHistory();
    if (view === 'models') await loadModels();
    if (view === 'settings') await loadSystem();
  }

  function switchView(view) {
    if (!views[view]) return;
    currentView = view;
    $$('.nav-item').forEach((item) => item.classList.toggle('active', item.dataset.view === view));
    $$('.view').forEach((panel) => panel.classList.toggle('active', panel.dataset.panel === view));
    $('#view-eyebrow').textContent = views[view][0];
    $('#view-title').textContent = views[view][1];
    loadView(view);
  }

  function updateCharacterCount() {
    characterCount.textContent = `${text.value.length.toLocaleString()} character${text.value.length === 1 ? '' : 's'}`;
  }

  function insertPause() {
    const token = '[[pause:320ms]]';
    const start = text.selectionStart;
    const end = text.selectionEnd;
    const before = text.value.slice(0, start);
    const after = text.value.slice(end);
    const leading = before && !before.endsWith(' ') ? ' ' : '';
    const trailing = after && !after.startsWith(' ') ? ' ' : '';
    text.value = `${before}${leading}${token}${trailing}${after}`;
    const cursor = before.length + leading.length + token.length + trailing.length;
    text.setSelectionRange(cursor, cursor);
    text.focus();
    updateCharacterCount();
  }

  function syncPlayer() {
    const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
    const current = Number.isFinite(audio.currentTime) ? audio.currentTime : 0;
    seek.value = duration > 0 ? String(Math.round((current / duration) * 1000)) : '0';
    timeReadout.textContent = `${formatTime(current)} / ${formatTime(duration)}`;
    playerToggle.textContent = audio.paused ? '▶' : '❚❚';
  }

  $$('.nav-item').forEach((button) => button.addEventListener('click', () => switchView(button.dataset.view)));
  $$('.chip[data-style]').forEach((button) => button.addEventListener('click', () => {
    selectedStyle = button.dataset.style;
    $$('.chip[data-style]').forEach((item) => item.classList.toggle('active', item === button));
  }));

  text.addEventListener('input', updateCharacterCount);
  speed.addEventListener('input', () => { speedValue.textContent = `${Number(speed.value).toFixed(2)}×`; });
  $('#insert-pause').addEventListener('click', insertPause);
  generateButton.addEventListener('click', generate);
  cancelButton.addEventListener('click', cancelCurrentJob);
  $('#project-form').addEventListener('submit', createProject);
  $('#refresh-view').addEventListener('click', () => loadView(currentView));
  $('#developer-toggle').addEventListener('click', () => {
    developerMode = !developerMode;
    technicalDetails.classList.toggle('hidden', !developerMode);
    $('#developer-toggle').textContent = developerMode ? 'Hide developer details' : 'Developer details';
  });

  playerToggle.addEventListener('click', () => {
    if (!audio.src) return;
    if (audio.paused) audio.play().catch(() => {});
    else audio.pause();
  });
  audio.addEventListener('timeupdate', syncPlayer);
  audio.addEventListener('loadedmetadata', syncPlayer);
  audio.addEventListener('play', syncPlayer);
  audio.addEventListener('pause', syncPlayer);
  seek.addEventListener('input', () => {
    if (!Number.isFinite(audio.duration) || audio.duration <= 0) return;
    audio.currentTime = (Number(seek.value) / 1000) * audio.duration;
  });

  document.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      switchView('create');
      generate();
    }
    if (event.key === ' ' && event.target === document.body && audio.src) {
      event.preventDefault();
      playerToggle.click();
    }
  });

  updateCharacterCount();
  loadSystem();
  loadVoices();
  loadHistory();
})();
