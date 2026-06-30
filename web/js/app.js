const elements = {
  systemStatus: document.querySelector("#system-status"),
  source: document.querySelector("#source"),
  state: document.querySelector("#state"),
  title: document.querySelector("#title"),
  artist: document.querySelector("#artist"),
  context: document.querySelector("#context"),
  volume: document.querySelector("#volume"),
  radioStation: document.querySelector("#radio-station"),
  audioOutput: document.querySelector("#audio-output"),
  sourceSpotify: document.querySelector("#source-spotify"),
  sourceRadio: document.querySelector("#source-radio"),
};

let pollTimer = null;
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

  if (isSpotify) {
    title = spotifyTrack.track || player?.title || "Spotify Ready";
    artist = spotifyTrack.artist || "Waiting for playback";
    context = spotifyTrack.album || player?.album || "--";
    state = spotify?.label || spotify?.state || player?.state || "idle";
    sourceLabel = spotify?.service || "spotify";
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
    context = radio?.state === "playing" ? "Playing radio" : "Radio ready";
    state = radio?.state || player?.state || "idle";
    sourceLabel = "radio";
  }

  elements.source.textContent = sourceLabel;
  elements.state.textContent = state;
  elements.title.textContent = title;
  elements.artist.textContent = artist;
  elements.context.textContent = context;
  elements.volume.textContent = `${Number(player?.volume ?? 50)}%`;
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

elements.audioOutput.addEventListener("change", () => {
  postJson("/api/system/audio-output", { output: elements.audioOutput.value })
    .then(() => refresh())
    .catch((error) => {
      elements.systemStatus.textContent = error.message;
    });
});

function startPolling() {
  refresh();
  pollTimer = window.setInterval(refresh, 1000);
}

window.addEventListener("beforeunload", () => {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer);
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
