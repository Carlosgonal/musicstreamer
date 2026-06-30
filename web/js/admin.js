const elements = {
  spotifyStatus: document.querySelector("#spotify-status"),
  spotifyEnabled: document.querySelector("#spotify-enabled"),
  spotifyDeviceName: document.querySelector("#spotify-device-name"),
  spotifyBitrate: document.querySelector("#spotify-bitrate"),
  spotifyCacheDir: document.querySelector("#spotify-cache-dir"),
  spotifyClientId: document.querySelector("#spotify-client-id"),
  spotifyClientSecret: document.querySelector("#spotify-client-secret"),
  spotifyRedirectUri: document.querySelector("#spotify-redirect-uri"),
  spotifyForm: document.querySelector("#spotify-form"),
  spotifyLogin: document.querySelector("#spotify-login"),
  audioStatus: document.querySelector("#audio-status"),
  audioForm: document.querySelector("#audio-form"),
  audioOutput: document.querySelector("#audio-output"),
  radioCount: document.querySelector("#radio-count"),
  radioForm: document.querySelector("#radio-form"),
  stationName: document.querySelector("#station-name"),
  stationUrl: document.querySelector("#station-url"),
  stationFrequency: document.querySelector("#station-frequency"),
  stationImageUrl: document.querySelector("#station-image-url"),
  stationsList: document.querySelector("#stations-list"),
  logsCount: document.querySelector("#logs-count"),
  logsQuery: document.querySelector("#logs-query"),
  logsRefresh: document.querySelector("#logs-refresh"),
  logsOutput: document.querySelector("#logs-output"),
  adminMessage: document.querySelector("#admin-message"),
};

let stations = [];
let logTimer = null;
let logRefreshTimer = null;

async function getJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}`);
  }
  return response.json();
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const body = await response.text();
  if (!response.ok) {
    throw new Error(body || `${url} returned ${response.status}`);
  }
  return body ? JSON.parse(body) : {};
}

async function deleteJson(url) {
  const response = await fetch(url, { method: "DELETE" });
  const body = await response.text();
  if (!response.ok) {
    throw new Error(body || `${url} returned ${response.status}`);
  }
  return body ? JSON.parse(body) : {};
}

async function refreshLogs() {
  const query = elements.logsQuery.value.trim();
  const url = query
    ? `/api/logs/recent?limit=200&query=${encodeURIComponent(query)}`
    : "/api/logs/recent?limit=200";

  try {
    const payload = await getJson(url);
    const lines = Array.isArray(payload.lines) ? payload.lines : [];
    elements.logsCount.textContent = `${payload.count ?? lines.length}`;
    elements.logsOutput.textContent = lines.length ? lines.join("\n") : "No logs yet.";
  } catch (error) {
    elements.logsCount.textContent = "0";
    elements.logsOutput.textContent = `Unable to load logs: ${error.message}`;
  }
}

function setMessage(text, isError = false) {
  elements.adminMessage.textContent = text;
  elements.adminMessage.style.color = isError ? "var(--danger)" : "var(--muted)";
}

function renderSpotify(settings) {
  elements.spotifyStatus.textContent = settings.linked ? "linked" : "not linked";
  elements.spotifyEnabled.checked = Boolean(settings.enabled);
  elements.spotifyDeviceName.value = settings.device_name || "";
  elements.spotifyBitrate.value = String(settings.bitrate || "320");
  elements.spotifyCacheDir.value = settings.cache_dir || "";
  elements.spotifyClientId.value = settings.client_id || "";
  elements.spotifyClientSecret.value = "";
  elements.spotifyRedirectUri.value = settings.redirect_uri || "";
}

function renderAudio(audio) {
  const outputs = Array.isArray(audio.outputs) ? audio.outputs : [];
  elements.audioStatus.textContent = audio.output || "unknown";
  elements.audioOutput.innerHTML = outputs
    .map((entry) => `<option value="${escapeHtml(entry.id)}">${escapeHtml(entry.label)}</option>`)
    .join("");
  elements.audioOutput.value = audio.output || "jack";
}

function renderStationsList() {
  elements.radioCount.textContent = `${stations.length}`;

  if (!stations.length) {
    elements.stationsList.innerHTML = '<div class="message">No stations configured.</div>';
    return;
  }

  elements.stationsList.innerHTML = stations
    .map((station) => {
      return `
        <div class="station-row">
          <div class="station-meta">
            <strong>${escapeHtml(station.name)}</strong>
            <span>${escapeHtml(station.url)}${station.frequency ? ` · ${escapeHtml(station.frequency)}` : ""}${station.image_url ? " · image" : ""}</span>
          </div>
          <div class="station-actions">
            <button class="button" type="button" data-play="${escapeHtml(station.id)}">Play</button>
            <button class="button" type="button" data-delete="${escapeHtml(station.id)}">Delete</button>
          </div>
        </div>
      `;
    })
    .join("");

  elements.stationsList.querySelectorAll("[data-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      const stationId = button.getAttribute("data-delete");
      if (!stationId) {
        return;
      }
      try {
        await deleteJson(`/api/radio/stations/${encodeURIComponent(stationId)}`);
        setMessage("Station removed.");
        await refreshStations();
      } catch (error) {
        setMessage(`Could not delete station: ${error.message}`, true);
      }
    });
  });

  elements.stationsList.querySelectorAll("[data-play]").forEach((button) => {
    button.addEventListener("click", async () => {
      const stationId = button.getAttribute("data-play");
      if (!stationId) {
        return;
      }
      try {
        await postJson("/api/radio/play", { station_id: stationId });
        setMessage("Station started.");
      } catch (error) {
        setMessage(`Could not play station: ${error.message}`, true);
      }
    });
  });
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function refreshSpotify() {
  const settings = await getJson("/api/spotify/settings");
  renderSpotify(settings);
}

async function refreshAudio() {
  const audio = await getJson("/api/system/audio-output");
  renderAudio(audio);
}

async function refreshStations() {
  const payload = await getJson("/api/radio/stations");
  stations = Array.isArray(payload.stations) ? payload.stations : [];
  renderStationsList();
}

async function refreshAll() {
  try {
    await Promise.all([refreshSpotify(), refreshAudio(), refreshStations()]);
    setMessage("Configuration loaded.");
  } catch (error) {
    setMessage(`Unable to load admin data: ${error.message}`, true);
  }

  await refreshLogs();
}

elements.spotifyForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    const settings = await postJson("/api/spotify/settings", {
      enabled: elements.spotifyEnabled.checked,
      device_name: elements.spotifyDeviceName.value.trim(),
      bitrate: elements.spotifyBitrate.value,
      cache_dir: elements.spotifyCacheDir.value.trim(),
      client_id: elements.spotifyClientId.value.trim(),
      client_secret: elements.spotifyClientSecret.value,
      redirect_uri: elements.spotifyRedirectUri.value.trim(),
    });
    renderSpotify(settings);
    setMessage("Spotify settings saved.");
  } catch (error) {
    setMessage(`Could not save Spotify: ${error.message}`, true);
  }
});

elements.spotifyLogin.addEventListener("click", () => {
  window.location.href = "/api/spotify/login";
});

elements.audioForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    const audio = await postJson("/api/system/audio-output", {
      output: elements.audioOutput.value,
    });
    renderAudio(audio);
    setMessage("Audio settings saved.");
  } catch (error) {
    setMessage(`Could not save audio: ${error.message}`, true);
  }
});

elements.radioForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    await postJson("/api/radio/stations", {
      name: elements.stationName.value.trim(),
      url: elements.stationUrl.value.trim(),
      frequency: elements.stationFrequency.value.trim(),
      image_url: elements.stationImageUrl.value.trim(),
    });
    elements.stationName.value = "";
    elements.stationUrl.value = "";
    elements.stationFrequency.value = "";
    elements.stationImageUrl.value = "";
    setMessage("Station added.");
    await refreshStations();
  } catch (error) {
    setMessage(`Could not add station: ${error.message}`, true);
  }
});

elements.logsRefresh.addEventListener("click", () => {
  refreshLogs();
});

elements.logsQuery.addEventListener("input", () => {
  window.clearTimeout(logTimer);
  logTimer = window.setTimeout(() => {
    refreshLogs();
  }, 250);
});

refreshAll();
logRefreshTimer = window.setInterval(refreshLogs, 5000);

window.addEventListener("beforeunload", () => {
  if (logRefreshTimer !== null) {
    window.clearInterval(logRefreshTimer);
  }
  if (logTimer !== null) {
    window.clearTimeout(logTimer);
  }
});
