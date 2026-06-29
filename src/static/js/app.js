const elements = {
  projectName: document.querySelector("#project-name"),
  clock: document.querySelector("#clock"),
  systemStatus: document.querySelector("#system-status"),
  spotifyStatus: document.querySelector("#spotify-status"),
  radioStatus: document.querySelector("#radio-status"),
  networkState: document.querySelector("#network-state"),
  volumeState: document.querySelector("#volume-state"),
};

async function getJson(url) {
  const response = await fetch(url, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}`);
  }

  return response.json();
}

function updateSystem(system) {
  elements.projectName.textContent = system.project;
  elements.clock.textContent = system.time;
  elements.clock.dateTime = `${system.date}T${system.time}`;
  elements.systemStatus.textContent = system.status;
  elements.networkState.textContent = system.network;
  elements.volumeState.textContent = `Vol ${system.volume}%`;
}

function updateSource(element, source) {
  element.textContent = source.label;
}

async function refresh() {
  try {
    const [system, spotify, radio] = await Promise.all([
      getJson("/api/system/status"),
      getJson("/api/spotify/status"),
      getJson("/api/radio/status"),
    ]);

    updateSystem(system);
    updateSource(elements.spotifyStatus, spotify);
    updateSource(elements.radioStatus, radio);
  } catch (error) {
    elements.systemStatus.textContent = "API unavailable";
    console.error(error);
  }
}

refresh();
setInterval(refresh, 5000);
