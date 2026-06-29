const elements = {
  projectName: document.querySelector("#project-name"),
  clock: document.querySelector("#clock"),
  systemStatus: document.querySelector("#system-status"),
  spotifyStatus: document.querySelector("#spotify-status"),
  spotifySource: document.querySelector("#spotify-source"),
  radioName: document.querySelector("#radio-name"),
  radioFrequency: document.querySelector("#radio-frequency"),
  radioStatus: document.querySelector("#radio-status"),
  radioToggle: document.querySelector("#radio-toggle"),
  radioAction: document.querySelector("#radio-action"),
  radioPrev: document.querySelector("#radio-prev"),
  radioNext: document.querySelector("#radio-next"),
  networkState: document.querySelector("#network-state"),
  audioOutputSelect: document.querySelector("#audio-output-select"),
  audioState: document.querySelector("#audio-state"),
  volumeControl: document.querySelector("#volume-control"),
  volumeState: document.querySelector("#volume-state"),
};

let radioState = "standby";
let selectedStationId = "";
let stations = [];
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
  updateAudioOutput(system.audio);

  if (!isVolumeDragging) {
    elements.volumeControl.value = system.volume;
  }
}

function updateAudioOutput(audio) {
  if (!audio) {
    return;
  }

  const currentOptions = Array.from(elements.audioOutputSelect.options).map((option) => option.value);
  const nextOptions = audio.outputs.map((output) => output.id);

  if (currentOptions.join("|") !== nextOptions.join("|")) {
    elements.audioOutputSelect.replaceChildren();

    for (const output of audio.outputs) {
      const option = document.createElement("option");
      option.value = output.id;
      option.textContent = output.label;
      elements.audioOutputSelect.append(option);
    }
  }

  elements.audioOutputSelect.value = audio.output;
  elements.audioState.textContent = elements.audioOutputSelect.selectedOptions[0]?.textContent || audio.output;
}

function updateRadio(radio) {
  radioState = radio.state;
  selectedStationId = radio.station?.id || selectedStationId;
  const station = radio.station || getSelectedStation();
  elements.radioName.textContent = station?.name || "Select station";
  elements.radioFrequency.textContent = station?.frequency || "--.-";
  elements.radioStatus.textContent = radio.error || radio.label;
  elements.radioAction.textContent = radio.state === "playing" ? "Stop" : "Play";
  elements.radioToggle.classList.toggle("playing", radio.state === "playing");

  if (radio.station?.id) {
    setSelectedStation(radio.station.id);
  }
}

function updateSpotify(spotify) {
  elements.spotifyStatus.textContent = spotify.available ? spotify.label : "Not set";
  elements.spotifySource.classList.toggle("disabled", !spotify.available);
}

function loadStations(nextStations) {
  stations = nextStations;

  if (stations.length > 0 && !selectedStationId) {
    setSelectedStation(stations[0].id);
  }
}

function setSelectedStation(stationId) {
  selectedStationId = stationId;
  const station = getSelectedStation();

  if (station) {
    elements.radioName.textContent = station.name;
    elements.radioFrequency.textContent = station.frequency;
  }
}

function getSelectedStation() {
  return stations.find((station) => station.id === selectedStationId) || stations[0] || null;
}

async function selectStationOffset(offset) {
  if (stations.length === 0) {
    return;
  }

  const currentIndex = Math.max(0, stations.findIndex((station) => station.id === selectedStationId));
  const nextIndex = (currentIndex + offset + stations.length) % stations.length;
  setSelectedStation(stations[nextIndex].id);

  if (radioState === "playing") {
    try {
      const radio = await playSelectedStation();
      updateRadio(radio);
    } catch (error) {
      elements.radioStatus.textContent = "Radio error";
      console.error(error);
    }
  }
}

async function toggleRadio() {
  elements.radioToggle.disabled = true;

  try {
    const radio = radioState === "playing"
      ? await postJson("/api/radio/stop")
      : await playSelectedStation();

    updateRadio(radio);
  } catch (error) {
    elements.radioStatus.textContent = "Radio error";
    console.error(error);
  } finally {
    elements.radioToggle.disabled = false;
  }
}

async function playSelectedStation() {
  return postJson("/api/radio/play", { station_id: selectedStationId });
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

async function setAudioOutput(output) {
  elements.audioOutputSelect.disabled = true;

  try {
    const system = await postJson("/api/system/audio-output", { output });
    updateSystem(system);

    if (radioState === "playing") {
      const radio = await postJson("/api/radio/play", { station_id: selectedStationId });
      updateRadio(radio);
    }
  } catch (error) {
    elements.systemStatus.textContent = "Audio error";
    console.error(error);
  } finally {
    elements.audioOutputSelect.disabled = false;
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
    const [system, radio, spotify] = await Promise.all([
      getJson("/api/system/status"),
      getJson("/api/radio/status"),
      getJson("/api/spotify/status"),
    ]);

    updateSystem(system);
    updateRadio(radio);
    updateSpotify(spotify);
  } catch (error) {
    elements.systemStatus.textContent = "API unavailable";
    console.error(error);
  }
}

async function init() {
  try {
    const [radioData, spotify] = await Promise.all([
      getJson("/api/radio/stations"),
      getJson("/api/spotify/status"),
    ]);
    loadStations(radioData.stations);
    updateSpotify(spotify);
  } catch (error) {
    elements.radioStatus.textContent = "Source error";
    console.error(error);
  }

  elements.radioToggle.addEventListener("click", toggleRadio);
  elements.radioPrev.addEventListener("click", () => selectStationOffset(-1));
  elements.radioNext.addEventListener("click", () => selectStationOffset(1));
  elements.audioOutputSelect.addEventListener("change", () => {
    setAudioOutput(elements.audioOutputSelect.value);
  });
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
