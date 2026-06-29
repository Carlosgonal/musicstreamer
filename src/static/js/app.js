const elements = {
  clock: document.querySelector("#clock"),
  date: document.querySelector("#date"),
  systemStatus: document.querySelector("#system-status"),
  spotifyStatus: document.querySelector("#spotify-status"),
  spotifySource: document.querySelector("#spotify-source"),
  spotifyView: document.querySelector("#spotify-view"),
  spotifyCover: document.querySelector("#spotify-cover"),
  spotifyTrack: document.querySelector("#spotify-track"),
  spotifyArtist: document.querySelector("#spotify-artist"),
  spotifyProgress: document.querySelector("#spotify-progress"),
  spotifyTime: document.querySelector("#spotify-time"),
  spotifyPrev: document.querySelector("#spotify-prev"),
  spotifyPlayPause: document.querySelector("#spotify-playpause"),
  spotifyNext: document.querySelector("#spotify-next"),
  radioView: document.querySelector("#radio-view"),
  radioName: document.querySelector("#radio-name"),
  radioFrequency: document.querySelector("#radio-frequency"),
  radioStatus: document.querySelector("#radio-status"),
  radioToggle: document.querySelector("#radio-toggle"),
  radioAction: document.querySelector("#radio-action"),
  radioPrev: document.querySelector("#radio-prev"),
  radioNext: document.querySelector("#radio-next"),
  manualFrequency: document.querySelector("#manual-frequency"),
  manualTune: document.querySelector("#manual-tune"),
  manualSave: document.querySelector("#manual-save"),
  stationDialog: document.querySelector("#station-dialog"),
  stationForm: document.querySelector("#station-form"),
  stationNameInput: document.querySelector("#station-name-input"),
  stationUrlInput: document.querySelector("#station-url-input"),
  stationCancel: document.querySelector("#station-cancel"),
  audioOutputSelect: document.querySelector("#audio-output-select"),
  volumeControl: document.querySelector("#volume-control"),
  volumeState: document.querySelector("#volume-state"),
};

let radioState = "standby";
let spotifyState = "standby";
let activeSource = "radio";
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
  elements.clock.textContent = system.time;
  elements.clock.dateTime = `${system.date}T${system.time}`;
  elements.date.textContent = formatDate(system.date);
  elements.date.dateTime = system.date;
  elements.systemStatus.textContent = system.status;
  elements.volumeState.textContent = `Vol ${system.volume}%`;
  updateAudioOutput(system.audio);

  if (!isVolumeDragging) {
    elements.volumeControl.value = system.volume;
  }
}

function formatDate(date) {
  const [year, month, day] = String(date).split("-");

  if (!year || !month || !day) {
    return "--/--/----";
  }

  return `${day}/${month}/${year}`;
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
  elements.radioToggle.classList.toggle("active", activeSource === "radio");

  if (radio.station?.id) {
    setSelectedStation(radio.station.id);
  }

  if (radio.state === "playing") {
    setActiveSource("radio");
  }
}

function updateSpotify(spotify) {
  spotifyState = spotify.state;
  elements.spotifyStatus.textContent = spotify.available ? spotify.label : spotify.label;
  elements.spotifySource.classList.toggle("disabled", !spotify.available);
  elements.spotifySource.classList.toggle("playing", spotify.state === "playing");
  elements.spotifySource.classList.toggle("active", activeSource === "spotify");
  elements.radioToggle.classList.toggle("active", activeSource === "radio");
  elements.spotifySource.disabled = spotify.state === "disabled" || spotify.state === "setup";
  updateSpotifyPlayer(spotify);

  if (spotify.state === "playing") {
    setActiveSource("spotify");
  }
}

function setActiveSource(source) {
  activeSource = source;
  elements.spotifyView.classList.toggle("hidden", source !== "spotify");
  elements.radioView.classList.toggle("hidden", source !== "radio");
  elements.spotifySource.classList.toggle("active", source === "spotify");
  elements.radioToggle.classList.toggle("active", source === "radio");
}

function formatDuration(milliseconds) {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function updateSpotifyPlayer(spotify) {
  const player = spotify.player;
  const controlsAvailable = spotify.controls_available && player;

  if (!spotify.credentials_configured) {
    elements.spotifyTrack.textContent = "Spotify";
    elements.spotifyArtist.textContent = "Configura API keys";
  } else if (!spotify.authenticated) {
    elements.spotifyTrack.textContent = "Spotify";
    elements.spotifyArtist.textContent = "Pulsa Spotify para vincular";
  } else if (!player) {
    elements.spotifyTrack.textContent = spotify.device_name;
    elements.spotifyArtist.textContent = "Abre Spotify y elige este dispositivo";
  } else {
    elements.spotifyTrack.textContent = player.track;
    elements.spotifyArtist.textContent = player.artist || player.album || "Spotify";
  }

  if (player?.image) {
    elements.spotifyCover.src = player.image;
  } else {
    elements.spotifyCover.removeAttribute("src");
  }
  elements.spotifyCover.classList.toggle("empty", !player?.image);
  elements.spotifyProgress.max = player?.duration_ms || 100;
  elements.spotifyProgress.value = player?.progress_ms || 0;
  elements.spotifyTime.textContent = `${formatDuration(player?.progress_ms || 0)} / ${formatDuration(player?.duration_ms || 0)}`;
  elements.spotifyPlayPause.textContent = player?.is_playing ? "Pause" : "Play";
  elements.spotifyPrev.disabled = !controlsAvailable;
  elements.spotifyPlayPause.disabled = !spotify.authenticated;
  elements.spotifyNext.disabled = !controlsAvailable;
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
    elements.manualFrequency.value = station.frequency;
  }
}

function getSelectedStation() {
  return stations.find((station) => station.id === selectedStationId) || stations[0] || null;
}

function findStationByFrequency(frequency) {
  if (!Number.isFinite(Number(frequency))) {
    return null;
  }

  const normalizedFrequency = Number(frequency).toFixed(1);
  return stations.find((station) => Number(station.frequency).toFixed(1) === normalizedFrequency) || null;
}

async function tuneManualFrequency() {
  if (!Number.isFinite(Number(elements.manualFrequency.value))) {
    elements.radioStatus.textContent = "Invalid frequency";
    return;
  }

  const station = findStationByFrequency(elements.manualFrequency.value);

  if (!station) {
    elements.radioStatus.textContent = "Frequency not saved";
    elements.radioFrequency.textContent = Number(elements.manualFrequency.value).toFixed(1);
    elements.radioName.textContent = "Manual";
    return;
  }

  setSelectedStation(station.id);

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

function openStationDialog() {
  const station = findStationByFrequency(elements.manualFrequency.value);
  elements.stationNameInput.value = station?.name || "";
  elements.stationUrlInput.value = station?.url || "";

  if (typeof elements.stationDialog.showModal === "function") {
    elements.stationDialog.showModal();
  } else {
    elements.stationDialog.setAttribute("open", "");
  }
}

function closeStationDialog() {
  if (typeof elements.stationDialog.close === "function") {
    elements.stationDialog.close();
  } else {
    elements.stationDialog.removeAttribute("open");
  }
}

async function saveManualStation() {
  if (!Number.isFinite(Number(elements.manualFrequency.value))) {
    elements.radioStatus.textContent = "Invalid frequency";
    return;
  }

  const payload = {
    frequency: Number(elements.manualFrequency.value).toFixed(1),
    name: elements.stationNameInput.value.trim(),
    url: elements.stationUrlInput.value.trim(),
  };

  try {
    const data = await postJson("/api/radio/stations", payload);
    loadStations(data.stations);
    setSelectedStation(data.station.id);
    elements.radioStatus.textContent = "Station saved";
    closeStationDialog();
  } catch (error) {
    elements.radioStatus.textContent = "Save error";
    console.error(error);
  }
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
    let radio;

    if (radioState === "playing") {
      radio = await postJson("/api/radio/stop");
    } else {
      if (spotifyState === "playing") {
        const spotify = await postJson("/api/spotify/stop");
        updateSpotify(spotify);
      }

      radio = await playSelectedStation();
    }

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

async function toggleSpotify() {
  elements.spotifySource.disabled = true;

  try {
    let spotify;
    setActiveSource("spotify");

    if (spotifyState === "auth") {
      window.location.href = "/api/spotify/login";
      return;
    }

    if (spotifyState === "playing") {
      spotify = await postJson("/api/spotify/stop");
    } else {
      if (radioState === "playing") {
        const radio = await postJson("/api/radio/stop");
        updateRadio(radio);
      }

      spotify = await postJson("/api/spotify/start");
    }

    updateSpotify(spotify);
  } catch (error) {
    elements.systemStatus.textContent = "Spotify error";
    console.error(error);
  } finally {
    if (spotifyState !== "missing" && spotifyState !== "disabled") {
      elements.spotifySource.disabled = false;
    }
  }
}

async function controlSpotify(action) {
  try {
    const spotify = await postJson(`/api/spotify/control/${action}`);
    updateSpotify(spotify);
  } catch (error) {
    elements.systemStatus.textContent = "Spotify error";
    console.error(error);
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

async function setAudioOutput(output) {
  elements.audioOutputSelect.disabled = true;

  try {
    const system = await postJson("/api/system/audio-output", { output });
    updateSystem(system);

    if (radioState === "playing") {
      const radio = await postJson("/api/radio/play", { station_id: selectedStationId });
      updateRadio(radio);
    }

    if (spotifyState === "playing") {
      const spotify = await postJson("/api/spotify/start");
      updateSpotify(spotify);
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
  const [systemResult, radioResult, spotifyResult] = await Promise.allSettled([
    getJson("/api/system/status"),
    getJson("/api/radio/status"),
    getJson("/api/spotify/status"),
  ]);

  if (systemResult.status === "fulfilled") {
    updateSystem(systemResult.value);
  }

  if (radioResult.status === "fulfilled") {
    updateRadio(radioResult.value);
  }

  if (spotifyResult.status === "fulfilled") {
    updateSpotify(spotifyResult.value);
  }

  if ([systemResult, radioResult, spotifyResult].every((result) => result.status === "rejected")) {
    elements.systemStatus.textContent = "API unavailable";
    console.error(systemResult.reason, radioResult.reason, spotifyResult.reason);
  } else if (systemResult.status === "rejected") {
    elements.systemStatus.textContent = "System unavailable";
    console.error(systemResult.reason);
  } else if (radioResult.status === "rejected") {
    elements.radioStatus.textContent = "Radio unavailable";
    console.error(radioResult.reason);
  } else if (spotifyResult.status === "rejected") {
    elements.spotifyStatus.textContent = "Spotify unavailable";
    console.error(spotifyResult.reason);
  }
}

async function init() {
  const [radioDataResult, spotifyResult] = await Promise.allSettled([
    getJson("/api/radio/stations"),
    getJson("/api/spotify/status"),
  ]);

  if (radioDataResult.status === "fulfilled") {
    loadStations(radioDataResult.value.stations);
  } else {
    elements.radioStatus.textContent = "Source error";
    console.error(radioDataResult.reason);
  }

  if (spotifyResult.status === "fulfilled") {
    updateSpotify(spotifyResult.value);
  } else {
    elements.spotifyStatus.textContent = "Spotify unavailable";
    console.error(spotifyResult.reason);
  }

  elements.radioToggle.addEventListener("click", toggleRadio);
  elements.spotifySource.addEventListener("click", toggleSpotify);
  elements.spotifyPrev.addEventListener("click", () => controlSpotify("previous"));
  elements.spotifyPlayPause.addEventListener("click", () => {
    controlSpotify(spotifyState === "playing" ? "pause" : "play");
  });
  elements.spotifyNext.addEventListener("click", () => controlSpotify("next"));
  elements.radioPrev.addEventListener("click", () => selectStationOffset(-1));
  elements.radioNext.addEventListener("click", () => selectStationOffset(1));
  elements.manualTune.addEventListener("click", tuneManualFrequency);
  elements.manualSave.addEventListener("click", openStationDialog);
  elements.stationCancel.addEventListener("click", closeStationDialog);
  elements.stationForm.addEventListener("submit", (event) => {
    event.preventDefault();
    saveManualStation();
  });
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
