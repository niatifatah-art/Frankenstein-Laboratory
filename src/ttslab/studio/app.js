const $ = (id) => document.getElementById(id);

const state = { style: "natural", busy: false };

function setError(message) {
  const box = $("error");
  if (!message) {
    box.classList.add("hidden");
    box.textContent = "";
    return;
  }
  box.textContent = message;
  box.classList.remove("hidden");
}

async function json(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail || `${response.status} ${response.statusText}`;
    throw new Error(detail);
  }
  return payload;
}

function updateCount() {
  $("count").textContent = $("text").value.length.toLocaleString();
}

function updateSpeed() {
  $("speedValue").textContent = `${Number($("speed").value).toFixed(2)}×`;
}

function selectStyle(value) {
  state.style = value;
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.classList.toggle("active", chip.dataset.style === value);
  });
}

async function loadHealth() {
  const health = $("health");
  try {
    const payload = await json("/api/health");
    health.textContent = `${payload.product} ${payload.version}`;
    health.classList.add("online");
    health.classList.remove("offline");
  } catch (_) {
    health.textContent = "offline";
    health.classList.add("offline");
    health.classList.remove("online");
  }
}

async function loadVoices() {
  const select = $("voice");
  try {
    const voices = await json("/api/voices");
    for (const voice of voices) {
      const option = document.createElement("option");
      option.value = voice.voice_id;
      option.textContent = voice.errors?.length
        ? `${voice.display_name} — needs attention`
        : voice.display_name;
      select.appendChild(option);
    }
  } catch (error) {
    console.warn("Could not load VoicePacks", error);
  }
}

async function loadEngines() {
  const select = $("engine");
  try {
    const engines = await json("/api/engines");
    for (const engine of engines) {
      const option = document.createElement("option");
      option.value = engine.key;
      option.textContent = engine.name || engine.key;
      select.appendChild(option);
    }
  } catch (error) {
    console.warn("Could not load engines", error);
  }
}

function requestPayload() {
  const speed = Number($("speed").value);
  return {
    text: $("text").value,
    language: $("language").value.trim() || null,
    profile: $("profile").value,
    voice_id: $("voice").value || null,
    style: state.style,
    speed: speed === 1 ? null : speed,
    engine: $("engine").value || null,
    device: null,
  };
}

function showResult(payload) {
  const result = $("result");
  $("audio").src = `${payload.audio_url}?t=${Date.now()}`;
  $("resultTitle").textContent = "Generated successfully";
  $("engineBadge").textContent = `engine: ${payload.engine}`;
  $("cacheBadge").textContent = payload.cached ? "from cache" : "fresh render";
  $("details").textContent = JSON.stringify({
    profile: payload.profile,
    device: payload.device,
    engine: payload.engine,
    segments: payload.segments,
    exact_pause_ms: payload.exact_pause_ms,
    native_controls: payload.native_controls,
    degraded_controls: payload.degraded_controls,
    reference_provenance: payload.reference_provenance,
  }, null, 2);
  result.classList.remove("hidden");
  result.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function generate() {
  if (state.busy) return;
  setError("");
  const text = $("text").value.trim();
  if (!text) {
    setError("Add something for ourTTS to say first.");
    return;
  }
  state.busy = true;
  const button = $("generate");
  button.disabled = true;
  button.querySelector("span:last-child").textContent = "Generating…";
  try {
    const payload = await json("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestPayload()),
    });
    showResult(payload);
  } catch (error) {
    setError(error.message || String(error));
  } finally {
    state.busy = false;
    button.disabled = false;
    button.querySelector("span:last-child").textContent = "Generate";
  }
}

$("text").addEventListener("input", updateCount);
$("speed").addEventListener("input", updateSpeed);
$("generate").addEventListener("click", generate);
$("regenerate").addEventListener("click", generate);
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => selectStyle(chip.dataset.style));
});

updateCount();
updateSpeed();
loadHealth();
loadVoices();
loadEngines();
