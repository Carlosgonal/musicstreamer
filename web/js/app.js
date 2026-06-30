const elements = {
  systemStatus: document.querySelector("#system-status"),
  source: document.querySelector("#source"),
  state: document.querySelector("#state"),
  title: document.querySelector("#title"),
  artist: document.querySelector("#artist"),
  context: document.querySelector("#context"),
  artwork: document.querySelector("#artwork"),
  artworkFallback: document.querySelector("#artwork-fallback"),
  playPause: document.querySelector("#play-pause"),
  elapsed: document.querySelector("#elapsed"),
  remaining: document.querySelector("#remaining"),
  progressFill: document.querySelector("#progress-fill"),
  volume: document.querySelector("#volume"),
  volumeSlider: document.querySelector("#volume-slider"),
  radioStation: document.querySelector("#radio-station"),
  audioOutput: document.querySelector("#audio-output"),
  sourceSpotify: document.querySelector("#source-spotify"),
  sourceRadio: document.querySelector("#source-radio"),
};

let pollTimer = null;
let volumeTimer = null;
let appState = {
  player: null,
  spotify: null,
  radio: null,
  audio: null,
};

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
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const body = await response.text();

  if (!response.ok) {
    throw new Error(body || `${url} returned ${response.status}`);
  }

  return body ? JSON.parse(body) : {};
}

function setButtonState(source) {
  const isSpotify = source === "spotify";
  elements.sourceSpotify.classList.toggle("is-active", isSpotify);
  elements.sourceRadio.classList.toggle("is-active", !isSpotify);
}

function setArtwork(imageUrl, fallbackText) {
  const label = (fallbackText || "MS").trim().slice(0, 2).toUpperCase();
  elements.artworkFallback.textContent = label || "MS";

  if (!imageUrl) {
    elements.artwork.hidden = true;
    elements.artwork.removeAttribute("src");
    elements.artwork.dataset.src = "";
    elements.artworkFallback.hidden = false;
    return;
  }

  if (elements.artwork.dataset.src === imageUrl) {
    return;
  }

  elements.artwork.onload = () => {
    elements.artwork.hidden = false;
    elements.artworkFallback.hidden = true;
  };
  elements.artwork.onerror = () => {
    elements.artwork.hidden = true;
    elements.artworkFallback.hidden = false;
  };
  elements.artwork.dataset.src = imageUrl;
  elements.artwork.src = imageUrl;
}

function formatTime(ms) {
  if (!Number.isFinite(ms) || ms <= 0) {
    return "0:00";
  }

  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function renderProgress(progressMs, durationMs, isLive = false) {
  if (isLive) {
    elements.elapsed.textContent = "LIVE";
    elements.remaining.textContent = "";
    elements.progressFill.style.width = "100%";
    return;
  }

  const progress = Math.max(0, Number(progressMs || 0));
  const duration = Math.max(0, Number(durationMs || 0));
  const remaining = Math.max(0, duration - progress);
  const percent = duration > 0 ? Math.min(100, Math.max(0, (progress / duration) * 100)) : 0;

  elements.elapsed.textContent = formatTime(progress);
  elements.remaining.textContent = duration > 0 ? `-${formatTime(remaining)}` : "--:--";
  elements.progressFill.style.width = `${percent}%`;
}

function renderSystem(system, audio) {
  const service = system?.service || "musicstreamer";
  const status = system?.status || "running";
  elements.systemStatus.textContent = `${service} ${status}`;

  const outputs = audio?.outputs || system?.audio?.outputs || [];
  const currentOutput = audio?.output || system?.audio?.output || "jack";

  if (elements.audioOutput.options.length !== outputs.length) {
    elements.audioOutput.innerHTML = outputs
      .map((entry) => `<option value="${escapeHtml(entry.id)}">${escapeHtml(entry.label)}</option>`)
      .join("");
  }

  elements.audioOutput.value = currentOutput;

  const volume = Number(system?.volume ?? appState.player?.volume ?? 50);
  elements.volume.textContent = `${volume}%`;
  elements.volumeSlider.value = String(volume);
}

function renderStations(radio) {
  const stations = Array.isArray(radio?.stations) ? radio.stations : [];
  const selected = appState.player?.source === "radio" ? radio?.current_station?.id : null;

  elements.radioStation.innerHTML = stations
    .map((station) => {
      const label = station.frequency ? `${station.name} · ${station.frequency}` : station.name;
      return `<option value="${escapeHtml(station.id)}">${escapeHtml(label)}</option>`;
    })
    .join("");

  if (selected) {
    elements.radioStation.value = selected;
  } else if (stations.length && !elements.radioStation.value) {
    elements.radioStation.value = stations[0].id;
  }
}

function renderPlayer(player, spotify, radio) {
  appState.player = player;
  appState.spotify = spotify;
  appState.radio = radio;

  const source = (player?.source || "spotify").toLowerCase();
  setButtonState(source);

  const spotifyTrack = spotify?.player || {};
  const radioStation = radio?.current_station || null;
  const isSpotify = source === "spotify";
  const isRadio = source === "radio";

  let title = player?.title || "MusicStreamer";
  let artist = player?.artist || "Waiting for playback";
  let context = player?.album || "--";
  let state = player?.state || "idle";
  let sourceLabel = source;
  let artworkUrl = player?.artwork_url || "";
  let artworkLabel = title;
  let isPlaying = player?.state === "playing";

  if (isSpotify) {
    title = spotifyTrack.track || player?.title || "Spotify Ready";
    artist = spotifyTrack.artist || "Waiting for playback";
    context = spotifyTrack.album || player?.album || "--";
    state = spotify?.label || spotify?.state || player?.state || "idle";
    sourceLabel = spotify?.service || "spotify";
    artworkUrl = spotifyTrack.image || player?.artwork_url || "";
    artworkLabel = title;
    isPlaying = Boolean(spotifyTrack.is_playing);
    renderProgress(spotifyTrack.progress_ms, spotifyTrack.duration_ms, false);
  } else if (isRadio) {
    title = radioStation?.name || player?.title || "Radio Ready";
    const parts = [];
    if (radioStation?.frequency) {
      parts.push(radioStation.frequency);
    }
    if (radioStation?.url) {
      parts.push(radioStation.url);
    }
    artist = parts.join(" · ") || "No station selected";
    context = radio?.state === "playing" ? "Playing radio" : radio?.error || "Radio ready";
    state = radio?.state || player?.state || "idle";
    sourceLabel = "radio";
    artworkUrl = radioStation?.image_url || "";
    artworkLabel = radioStation?.name || "Radio";
    isPlaying = radio?.state === "playing";
    renderProgress(0, 0, radio?.state === "playing");
  } else {
    renderProgress(0, 0, false);
  }

  document.querySelector(".device").dataset.source = source;
  setArtwork(artworkUrl, artworkLabel);
  elements.source.textContent = sourceLabel;
  elements.state.textContent = state;
  elements.title.textContent = title;
  elements.artist.textContent = artist;
  elements.context.textContent = context;
  elements.playPause.textContent = isPlaying ? "Ⅱ" : "▶";
  elements.playPause.setAttribute("aria-label", isPlaying ? "Pause" : "Play");
  document.title = `${title} - MusicStreamer`;
}

async function refresh() {
  const [playerResult, systemResult, spotifyResult, radioResult, audioResult] = await Promise.allSettled([
    getJson("/api/player"),
    getJson("/api/system"),
    getJson("/api/spotify/status"),
    getJson("/api/radio"),
    getJson("/api/system/audio-output"),
  ]);

  const player = playerResult.status === "fulfilled" ? playerResult.value : null;
  const system = systemResult.status === "fulfilled" ? systemResult.value : null;
  const spotify = spotifyResult.status === "fulfilled" ? spotifyResult.value : null;
  const radio = radioResult.status === "fulfilled" ? radioResult.value : null;
  const audio = audioResult.status === "fulfilled" ? audioResult.value : null;

  if (system || audio) {
    renderSystem(system, audio);
  }

  if (radio) {
    renderStations(radio);
  }

  if (player) {
    renderPlayer(player, spotify, radio);
  }

  if (!player && !system) {
    elements.systemStatus.textContent = "api unavailable";
  }
}

async function switchSource(source) {
  const payload = { source };

  if (source === "radio" && elements.radioStation.value) {
    payload.station_id = elements.radioStation.value;
  }

  await postJson("/api/player/source", payload);
  await refresh();
}

async function togglePlayback() {
  const source = (appState.player?.source || "spotify").toLowerCase();
  const payload = { source };

  if (source === "radio" && elements.radioStation.value) {
    payload.station_id = elements.radioStation.value;
  }

  await postJson("/api/player/toggle", payload);
  await refresh();
}

function queueVolumeUpdate(volume) {
  if (volumeTimer !== null) {
    window.clearTimeout(volumeTimer);
  }

  volumeTimer = window.setTimeout(() => {
    postJson("/api/system/volume", { volume })
      .then(() => refresh())
      .catch((error) => {
        elements.systemStatus.textContent = error.message;
      });
  }, 150);
}

elements.sourceSpotify.addEventListener("click", () => {
  switchSource("spotify").catch((error) => {
    elements.systemStatus.textContent = error.message;
  });
});

elements.sourceRadio.addEventListener("click", () => {
  switchSource("radio").catch((error) => {
    elements.systemStatus.textContent = error.message;
  });
});

elements.radioStation.addEventListener("change", () => {
  if ((appState.player?.source || "spotify") === "radio") {
    switchSource("radio").catch((error) => {
      elements.systemStatus.textContent = error.message;
    });
  }
});

elements.playPause.addEventListener("click", () => {
  togglePlayback().catch((error) => {
    elements.systemStatus.textContent = error.message;
  });
});

elements.audioOutput.addEventListener("change", () => {
  postJson("/api/system/audio-output", { output: elements.audioOutput.value })
    .then(() => refresh())
    .catch((error) => {
      elements.systemStatus.textContent = error.message;
    });
});

elements.volumeSlider.addEventListener("input", () => {
  const volume = Number(elements.volumeSlider.value);
  elements.volume.textContent = `${volume}%`;
  queueVolumeUpdate(volume);
});

function startPolling() {
  refresh();
  pollTimer = window.setInterval(refresh, 1000);
}

window.addEventListener("beforeunload", () => {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer);
  }
  if (volumeTimer !== null) {
    window.clearTimeout(volumeTimer);
  }
});

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

startPolling();
