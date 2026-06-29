const elements = {
  projectName: document.querySelector("#project-name"),
  clock: document.querySelector("#clock"),
  systemStatus: document.querySelector("#system-status"),
  spotifyStatus: document.querySelector("#spotify-status"),
  radioCard: document.querySelector("#radio-card"),
  radioName: document.querySelector("#radio-name"),
  radioStatus: document.querySelector("#radio-status"),
  stationSelect: document.querySelector("#station-select"),
  radioToggle: document.querySelector("#radio-toggle"),
  networkState: document.querySelector("#network-state"),
  volumeState: document.querySelector("#volume-state"),
};

let radioState = "standby";

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

function updateRadio(radio) {
  radioState = radio.state;
  elements.radioName.textContent = radio.station?.name || "Radio";
  elements.radioStatus.textContent = radio.error || radio.label;
  elements.radioToggle.textContent = radio.state === "playing" ? "Stop" : "Play";
  elements.radioCard.classList.toggle("playing", radio.state === "playing");

  if (radio.station?.id) {
    elements.stationSelect.value = radio.station.id;
  }
}

function loadStations(stations) {
  elements.stationSelect.replaceChildren();

  for (const station of stations) {
    const option = document.createElement("option");
    option.value = station.id;
    option.textContent = station.name;
    elements.stationSelect.append(option);
  }
}

async function toggleRadio() {
  elements.radioToggle.disabled = true;

  try {
    const radio = radioState === "playing"
      ? await postJson("/api/radio/stop")
      : await postJson("/api/radio/play", { station_id: elements.stationSelect.value });

    updateRadio(radio);
  } catch (error) {
    elements.radioStatus.textContent = "Radio error";
    console.error(error);
  } finally {
    elements.radioToggle.disabled = false;
  }
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
    updateRadio(radio);
  } catch (error) {
    elements.systemStatus.textContent = "API unavailable";
    console.error(error);
  }
}

async function init() {
  try {
    const data = await getJson("/api/radio/stations");
    loadStations(data.stations);
  } catch (error) {
    elements.radioStatus.textContent = "No stations";
    console.error(error);
  }

  elements.radioToggle.addEventListener("click", toggleRadio);
  refresh();
  setInterval(refresh, 5000);
}

init();
