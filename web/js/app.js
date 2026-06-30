const elements = {
  systemStatus: document.querySelector("#system-status"),
  source: document.querySelector("#source"),
  state: document.querySelector("#state"),
  title: document.querySelector("#title"),
  artist: document.querySelector("#artist"),
  volume: document.querySelector("#volume"),
  album: document.querySelector("#album"),
};

let pollTimer = null;

async function getJson(url) {
  const response = await fetch(url, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}`);
  }

  return response.json();
}

function renderPlayer(player) {
  elements.source.textContent = player.source || "spotify";
  elements.state.textContent = player.state || "idle";
  elements.title.textContent = player.title || "Spotify Ready";
  elements.artist.textContent = player.artist || "Waiting for playback";
  elements.volume.textContent = `${Number(player.volume ?? 50)}%`;
  elements.album.textContent = player.album || "--";
  document.title = `${player.title || "MusicStreamer"} - MusicStreamer`;
}

function renderSystem(system) {
  elements.systemStatus.textContent = `${system.service || "musicstreamer"} ${system.status || "running"}`;
}

async function refresh() {
  const [playerResult, systemResult] = await Promise.allSettled([
    getJson("/api/player"),
    getJson("/api/system"),
  ]);

  if (playerResult.status === "fulfilled") {
    renderPlayer(playerResult.value);
  }

  if (systemResult.status === "fulfilled") {
    renderSystem(systemResult.value);
  }

  if (playerResult.status === "rejected" && systemResult.status === "rejected") {
    elements.systemStatus.textContent = "api unavailable";
  }
}

function startPolling() {
  refresh();
  pollTimer = window.setInterval(refresh, 1000);
}

window.addEventListener("beforeunload", () => {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer);
  }
});

startPolling();
