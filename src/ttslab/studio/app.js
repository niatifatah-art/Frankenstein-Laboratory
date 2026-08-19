(() => {
  const text = document.querySelector('#text');
  const language = document.querySelector('#language');
  const quality = document.querySelector('#quality');
  const generateButton = document.querySelector('#generate');
  const result = document.querySelector('#result');
  const status = document.querySelector('#status');
  const statusSub = document.querySelector('#status-sub');
  const statusDot = document.querySelector('.status-dot');
  const routeBadge = document.querySelector('#route-badge');
  const audio = document.querySelector('#audio');
  const engine = document.querySelector('#engine');
  const reason = document.querySelector('#reason');
  const styleButtons = [...document.querySelectorAll('[data-style]')];
  const sampleButtons = [...document.querySelectorAll('[data-sample]')];
  const surprise = document.querySelector('#surprise');

  const surprises = [
    'The tiny model looked at the giant model and said: skill issue.',
    'One interface. Too many models underneath. Somehow this was the simple option.',
    'Hello human. I was routed here because a benchmark said I should be.',
    'Frankenstein Laboratory is the basement. ourTTS is the clean living room upstairs.'
  ];

  let selectedStyle = 'natural';

  function setWorking(title, subtitle) {
    result.classList.remove('hidden');
    status.textContent = title;
    statusSub.textContent = subtitle;
    statusDot.className = 'status-dot working';
    generateButton.disabled = true;
    generateButton.querySelector('span:last-child').textContent = 'Working…';
  }

  function setDone(title, subtitle) {
    status.textContent = title;
    statusSub.textContent = subtitle;
    statusDot.className = 'status-dot done';
    generateButton.disabled = false;
    generateButton.querySelector('span:last-child').textContent = 'Generate';
  }

  function setError(message) {
    result.classList.remove('hidden');
    status.textContent = 'Could not generate';
    statusSub.textContent = message;
    statusDot.className = 'status-dot error';
    generateButton.disabled = false;
    generateButton.querySelector('span:last-child').textContent = 'Generate';
    audio.removeAttribute('src');
  }

  async function postJson(url, payload) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.detail || `Request failed (${response.status})`);
    }
    return body;
  }

  function requestPayload() {
    return {
      text: text.value.trim(),
      language: language.value || null,
      style: selectedStyle,
      quality: quality.value,
      offline: quality.value === 'local'
    };
  }

  async function generate() {
    const payload = requestPayload();
    if (!payload.text) {
      text.focus();
      return;
    }

    try {
      routeBadge.textContent = payload.quality === 'auto' ? 'Auto' : payload.quality;
      setWorking('Finding the right route…', 'ourTTS is checking capability and measured performance.');
      const plan = await postJson('/v1/plan', payload);
      engine.textContent = plan.engine;
      reason.textContent = (plan.routing_reasons || []).join('; ') || 'Qualified product route';

      if (selectedStyle !== 'natural') {
        setWorking('Generating the expressive take…', `Verified route: ${plan.engine}. Expressive models can take longer on CPU.`);
      } else {
        setWorking('Generating your voice…', `Verified route selected. The backend stays out of your way.`);
      }

      const generated = await postJson('/v1/generate', payload);
      engine.textContent = generated.engine;
      reason.textContent = (generated.routing_reasons || []).join('; ') || reason.textContent;
      audio.src = `${generated.audio_url}?t=${Date.now()}`;
      audio.load();
      setDone('Ready to play', 'Generated through the verified ourTTS product path.');
      audio.play().catch(() => {});
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    }
  }

  styleButtons.forEach((button) => {
    button.addEventListener('click', () => {
      selectedStyle = button.dataset.style;
      styleButtons.forEach((item) => item.classList.toggle('active', item === button));
    });
  });

  sampleButtons.forEach((button) => {
    button.addEventListener('click', () => {
      text.value = button.dataset.sample;
      text.focus();
    });
  });

  surprise.addEventListener('click', () => {
    text.value = surprises[Math.floor(Math.random() * surprises.length)];
    text.focus();
  });

  generateButton.addEventListener('click', generate);
  document.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      generate();
    }
  });
})();
