const elements = {
  status: document.querySelector("#admin-status"),
  linkState: document.querySelector("#spotify-link-state"),
  form: document.querySelector("#spotify-settings-form"),
  enabled: document.querySelector("#spotify-enabled"),
  deviceName: document.querySelector("#spotify-device-name"),
  bitrate: document.querySelector("#spotify-bitrate"),
  cacheDir: document.querySelector("#spotify-cache-dir"),
  clientId: document.querySelector("#spotify-client-id"),
  clientSecret: document.querySelector("#spotify-client-secret"),
  redirectUri: document.querySelector("#spotify-redirect-uri"),
  save: document.querySelector("#spotify-save"),
  link: document.querySelector("#spotify-link"),
};

let currentSettings = {
  enabled: false,
  client_id: "",
  client_secret_set: false,
};

async function getJson(url) {
  const response = await fetch(url, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}`);
  }

  return response.json();
}

async function postJson(url, payload = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${url} returned ${response.status}`);
  }

  return response.json();
}

function renderStatus(settings, spotify) {
  const labels = [];

  if (settings.enabled) {
    labels.push("Enabled");
  } else {
    labels.push("Disabled");
  }

  labels.push(settings.linked ? "Linked" : "Not linked");
  labels.push(settings.client_secret_set ? "Secret saved" : "Secret missing");
  labels.push(spotify.available ? "librespot ready" : spotify.state);

  elements.linkState.textContent = labels.join("  ");
}

function fillForm(settings) {
  currentSettings = settings;
  elements.enabled.checked = Boolean(settings.enabled);
  elements.deviceName.value = settings.device_name || "";
  elements.bitrate.value = settings.bitrate || "320";
  elements.cacheDir.value = settings.cache_dir || "";
  elements.clientId.value = settings.client_id || "";
  elements.clientSecret.value = "";
  elements.redirectUri.value = settings.redirect_uri || "";
  updateLinkButtonState();
}

function updateLinkButtonState() {
  elements.link.disabled = !elements.enabled.checked || !currentSettings.client_id || !currentSettings.client_secret_set;
}

function setMessage(message, isError = false) {
  elements.status.textContent = message;
  elements.status.classList.toggle("error", isError);
}

async function load() {
  try {
    const [settings, spotify] = await Promise.all([
      getJson("/api/spotify/settings"),
      getJson("/api/spotify/status"),
    ]);

    fillForm(settings);
    renderStatus(settings, spotify);
    setMessage("Ready");
  } catch (error) {
    setMessage("Unable to load settings", true);
    console.error(error);
  }
}

async function save(event) {
  event.preventDefault();
  elements.save.disabled = true;

  try {
    const settings = await postJson("/api/spotify/settings", {
      enabled: elements.enabled.checked,
      device_name: elements.deviceName.value.trim(),
      bitrate: elements.bitrate.value.trim(),
      cache_dir: elements.cacheDir.value.trim(),
      client_id: elements.clientId.value.trim(),
      client_secret: elements.clientSecret.value.trim(),
      redirect_uri: elements.redirectUri.value.trim(),
    });

    const spotify = await getJson("/api/spotify/status");
    currentSettings = settings;
    fillForm(settings);
    renderStatus(settings, spotify);
    setMessage("Settings saved");
  } catch (error) {
    setMessage("Save failed", true);
    console.error(error);
  } finally {
    elements.save.disabled = false;
  }
}

function linkAccount() {
  window.location.href = "/api/spotify/login";
}

elements.form.addEventListener("submit", save);
elements.link.addEventListener("click", linkAccount);
elements.enabled.addEventListener("change", () => {
  updateLinkButtonState();
});

load();
