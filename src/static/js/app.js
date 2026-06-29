const elements = {
  projectName: document.querySelector("#project-name"),
  clock: document.querySelector("#clock"),
  systemStatus: document.querySelector("#system-status"),
  radioName: document.querySelector("#radio-name"),
  radioStatus: document.querySelector("#radio-status"),
  stationList: document.querySelector("#station-list"),
  radioToggle: document.querySelector("#radio-toggle"),
  networkState: document.querySelector("#network-state"),
  volumeControl: document.querySelector("#volume-control"),
  volumeState: document.querySelector("#volume-state"),
};

let radioState = "standby";
let selectedStationId = "";
let volumeDebounceId = null;
let isVolumeDragging = false;

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

  if (!isVolumeDragging) {
    elements.volumeControl.value = system.volume;
  }
}

function updateRadio(radio) {
  radioState = radio.state;
  selectedStationId = radio.station?.id || selectedStationId;
  elements.radioName.textContent = radio.station?.name || getSelectedStationName() || "Select station";
  elements.radioStatus.textContent = radio.error || radio.label;
  elements.radioToggle.textContent = radio.state === "playing" ? "Stop" : "Play";
  elements.radioToggle.classList.toggle("playing", radio.state === "playing");

  if (radio.station?.id) {
    setSelectedStation(radio.station.id);
  }
}

function loadStations(stations) {
  elements.stationList.replaceChildren();

  for (const station of stations) {
    const button = document.createElement("button");
    button.className = "station-button";
    button.type = "button";
    button.dataset.stationId = station.id;
    button.textContent = station.name;
    button.addEventListener("click", () => {
      setSelectedStation(station.id);
      elements.radioName.textContent = station.name;
    });
    elements.stationList.append(button);
  }

  if (stations.length > 0) {
    setSelectedStation(stations[0].id);
    elements.radioName.textContent = stations[0].name;
  }
}

function setSelectedStation(stationId) {
  selectedStationId = stationId;

  for (const button of elements.stationList.querySelectorAll(".station-button")) {
    button.classList.toggle("selected", button.dataset.stationId === stationId);
  }
}

function getSelectedStationName() {
  const selected = elements.stationList.querySelector(".station-button.selected");
  return selected?.textContent || "";
}

async function toggleRadio() {
  elements.radioToggle.disabled = true;

  try {
    const radio = radioState === "playing"
      ? await postJson("/api/radio/stop")
      : await postJson("/api/radio/play", { station_id: selectedStationId });

    updateRadio(radio);
  } catch (error) {
    elements.radioStatus.textContent = "Radio error";
    console.error(error);
  } finally {
    elements.radioToggle.disabled = false;
  }
}

function updateVolumeLabel(volume) {
  elements.volumeState.textContent = `Vol ${volume}%`;
}

async function setVolume(volume) {
  try {
    const system = await postJson("/api/system/volume", { volume });
    updateSystem(system);
  } catch (error) {
    elements.systemStatus.textContent = "Volume error";
    console.error(error);
  }
}

function queueVolumeUpdate() {
  const volume = Number(elements.volumeControl.value);
  updateVolumeLabel(volume);
  window.clearTimeout(volumeDebounceId);
  volumeDebounceId = window.setTimeout(() => setVolume(volume), 180);
}

async function refresh() {
  try {
    const [system, radio] = await Promise.all([
      getJson("/api/system/status"),
      getJson("/api/radio/status"),
    ]);

    updateSystem(system);
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
  elements.volumeControl.addEventListener("pointerdown", () => {
    isVolumeDragging = true;
  });
  elements.volumeControl.addEventListener("pointerup", () => {
    isVolumeDragging = false;
    queueVolumeUpdate();
  });
  elements.volumeControl.addEventListener("input", queueVolumeUpdate);
  elements.volumeControl.addEventListener("change", () => {
    isVolumeDragging = false;
    queueVolumeUpdate();
  });
  refresh();
  setInterval(refresh, 5000);
}

init();
