"use strict";

const $ = id => document.getElementById(id);
const layers = {paths: new Map(), markers: new Map(), cameraMarkers: new Map(), cameraWedges: new Map()};
const toggles = ["show-tracks", "camera-only", "show-cameras"];
let dataset, map, selectedKey = null, selectedGroupKey = null, now = 0, playing = false, lastTick = 0, lastDraw = 0;
const idColors = new Map();

function fmtElapsed(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

function fmtCount(count, noun) { return `${count} ${noun}${count === 1 ? "" : "s"}`; }

function fmtUtc(seconds) {
  if (!dataset.start_utc) return "UTC start unavailable";
  return new Date(Date.parse(dataset.start_utc) + seconds * 1000).toISOString().replace("T", " ").replace("Z", " UTC");
}

function lowerBound(samples, value) {
  let lo = 0, hi = samples.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (samples[mid][0] < value) lo = mid + 1; else hi = mid; }
  return lo;
}

function closest(samples, value, limit) {
  if (!samples.length) return null;
  const i = lowerBound(samples, value);
  const a = samples[Math.max(0, i - 1)], b = samples[Math.min(i, samples.length - 1)];
  const chosen = Math.abs(a[0] - value) <= Math.abs(b[0] - value) ? a : b;
  return Math.abs(chosen[0] - value) <= limit ? chosen : null;
}

function destination(lat, lon, bearing, distance) {
  const radius = 6371000, a = distance / radius, p = lat * Math.PI / 180, h = bearing * Math.PI / 180;
  const p2 = Math.asin(Math.sin(p) * Math.cos(a) + Math.cos(p) * Math.sin(a) * Math.cos(h));
  const l2 = lon * Math.PI / 180 + Math.atan2(Math.sin(h) * Math.sin(a) * Math.cos(p), Math.cos(a) - Math.sin(p) * Math.sin(p2));
  return [p2 * 180 / Math.PI, l2 * 180 / Math.PI];
}

function cameraWedge(sample, fov) {
  const result = [[sample[1], sample[2]]];
  for (let i = 0; i <= 14; i++) result.push(destination(sample[1], sample[2], sample[4] - fov / 2 + fov * i / 14, 1000));
  return result;
}

function groupKey(track) { return track.object_id && track.object_id !== "unknown" ? `object:${track.object_id}` : track.key; }
function selected(track) { return selectedGroupKey !== null && groupKey(track) === selectedGroupKey; }
function color(track) { return idColors.get(groupKey(track)); }

function assignColors() {
  const keys = [...new Set(dataset.tracks.map(groupKey))].sort();
  keys.forEach((key, index) => idColors.set(key, `hsl(${Math.round((index * 137.508 + 200) % 360)} 70% 38%)`));
}

function bearing(a, b) {
  const lat1 = a[1] * Math.PI / 180, lat2 = b[1] * Math.PI / 180;
  const deltaLon = (b[2] - a[2]) * Math.PI / 180;
  return (Math.atan2(Math.sin(deltaLon) * Math.cos(lat2),
    Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(deltaLon)) * 180 / Math.PI + 360) % 360;
}

function headingAt(track, sample) {
  if (Number.isFinite(sample[5])) return sample[5];
  const i = lowerBound(track.samples, sample[0]);
  for (let j = i + 1; j < track.samples.length; j++) {
    if (Math.abs(track.samples[j][1] - sample[1]) + Math.abs(track.samples[j][2] - sample[2]) > 1e-7)
      return bearing(sample, track.samples[j]);
  }
  for (let j = i - 1; j >= 0; j--) {
    if (Math.abs(track.samples[j][1] - sample[1]) + Math.abs(track.samples[j][2] - sample[2]) > 1e-7)
      return bearing(track.samples[j], sample);
  }
  return 0;
}

function pathSegments(samples, cutoff) {
  const segments = []; let segment = [], previous = null;
  for (const sample of samples) {
    if (sample[0] > cutoff) break;
    if (previous && sample[0] - previous[0] > 2) { if (segment.length > 1) segments.push(segment); segment = []; }
    segment.push([sample[1], sample[2]]);
    previous = sample;
  }
  if (segment.length > 1) segments.push(segment);
  return segments;
}

function makeIcon(className, text = "") {
  const size = className === "camera-pin" ? 27 : 14;
  return L.divIcon({className: "", html: `<div class="${className}">${text}</div>`, iconSize: [size, size], iconAnchor: [size / 2, size / 2]});
}

function flightIcon(track, heading) {
  const aircraft = '<path d="M16 1c-1.7 0-2.6 1.9-2.6 4.2v8.2L2 20.4V24l11.4-3v5.4l-3.5 2.5V31l6.1-1.7 6.1 1.7v-2.1l-3.5-2.5V21L30 24v-3.6l-11.4-7V5.2C18.6 2.9 17.7 1 16 1Z"/>';
  const drone = '<path d="M14 5h4l1 5 4 4 5-1 2 2-2 3-5-1-4 4-1 6h-4l-1-6-4-4-5 1-2-3 2-2 5 1 4-4z"/><circle cx="16" cy="16" r="3" fill="white"/><path d="M16 2l3 6h-6z"/>';
  const shape = String(track.vehicle_type).toLowerCase() === "drone" ? drone : aircraft;
  const html = `<div class="flight-pin" style="color:${color(track)};--heading:${Math.round(heading)}deg"><svg viewBox="0 0 32 32" aria-hidden="true">${shape}</svg></div>`;
  return L.divIcon({className: "", html, iconSize: [30, 30], iconAnchor: [15, 15]});
}

function sensorIcon(track) {
  return L.divIcon({className: "", html: `<div class="sensor-pin" style="background:${color(track)}"></div>`,
    iconSize: [14, 14], iconAnchor: [7, 7]});
}

function selectTrack(key, moveMap = true) {
  selectedKey = key;
  const track = dataset.tracks.find(item => item.key === key);
  selectedGroupKey = track ? groupKey(track) : null;
  if (!track) {
    $("selection-card").hidden = true;
  } else {
    $("show-tracks").checked = true;
    if (track.kind === "reference") $("camera-only").checked = false;
    $("selection-card").hidden = false;
    $("detail-title").textContent = track.label;
    const pieces = [track.kind === "reference" ? "Recorded Unreal actor pose" : "Camera-derived Kalman track",
      `${track.samples.length} position samples`,
      `Recorded from ${fmtElapsed(track.samples[0][0])} to ${fmtElapsed(track.samples.at(-1)[0])}`];
    if (track.object_id) pieces.push(`Object ID: ${track.object_id}`);
    if (track.vehicle_type) pieces.push(`Type: ${track.vehicle_type}`);
    if (track.kind === "sensor") pieces.push(track.camera_match ? `Segmentation match: ${track.camera_match}` : "No verified object match");
    if (track.object_id) {
      const related = dataset.tracks.filter(item => item.kind === "sensor" && item.object_id === track.object_id);
      if (related.length) pieces.push(`Camera track IDs for this object: ${related.map(item => item.label.replace("Camera track ", "")).join(", ")}`);
    }
    $("detail-body").replaceChildren(...pieces.flatMap((piece, i) => {
      const span = document.createElement("span"); span.textContent = piece;
      return i ? [document.createElement("br"), span] : [span];
    }));
    if (moveMap) {
      const sample = closest(track.samples, now, 1) || track.samples[Math.floor(track.samples.length / 2)];
      map.panTo([sample[1], sample[2]]);
    }
  }
  draw();
}

function draw() {
  if (!dataset || !map) return;
  $("time-slider").value = String(now);
  $("utc-time").textContent = fmtUtc(now);
  $("elapsed-time").textContent = `Elapsed ${fmtElapsed(now)} · ${now.toFixed(2)} s`;
  let activeReference = 0, activeSensor = 0;
  for (const track of dataset.tracks) {
    const visible = $("show-tracks").checked && (!$('camera-only').checked || track.kind === "sensor");
    let path = layers.paths.get(track.key);
    if (!path) {
      const line = {color: color(track), dashArray: track.kind === "sensor" ? "7 6" : null, interactive: true};
      const future = L.polyline([], {...line, weight: 1.5, opacity: .18});
      const past = L.polyline([], {...line, weight: 3, opacity: .85});
      future.bindTooltip(track.label, {sticky: true});
      past.bindTooltip(track.label, {sticky: true});
      future.on("click", () => selectTrack(track.key, false));
      past.on("click", () => selectTrack(track.key, false));
      path = {future, past}; layers.paths.set(track.key, path);
    }
    for (const part of [path.future, path.past]) {
      if (visible && !map.hasLayer(part)) part.addTo(map);
      if (!visible && map.hasLayer(part)) map.removeLayer(part);
    }
    if (visible) {
      path.past.setLatLngs(pathSegments(track.samples, now));
      path.future.setLatLngs(pathSegments(track.samples.slice(Math.max(0, lowerBound(track.samples, now) - 1)), Infinity));
      path.past.setStyle({weight: selected(track) ? 5 : 3, opacity: selectedKey && !selected(track) ? .26 : .85});
      path.future.setStyle({weight: selected(track) ? 2.5 : 1.5, opacity: selectedKey && !selected(track) ? .07 : .18});
    }
    let marker = layers.markers.get(track.key);
    const sample = visible ? closest(track.samples, now, .8) : null;
    if (sample) {
      if (track.kind === "reference") activeReference++; else activeSensor++;
      if (!marker) {
        const icon = track.kind === "reference" ? flightIcon(track, headingAt(track, sample)) :
          sensorIcon(track);
        marker = L.marker([sample[1], sample[2]], {icon, zIndexOffset: 300});
        if (track.kind === "reference") marker.heading = Math.round(headingAt(track, sample));
        marker.bindTooltip(track.label, {direction: "top"});
        marker.on("click", () => selectTrack(track.key, false));
        layers.markers.set(track.key, marker);
      }
      marker.setLatLng([sample[1], sample[2]]);
      if (track.kind === "reference") {
        const heading = Math.round(headingAt(track, sample));
        if (marker.heading !== heading) { marker.setIcon(flightIcon(track, heading)); marker.heading = heading; }
      }
      if (!map.hasLayer(marker)) marker.addTo(map);
    } else if (marker && map.hasLayer(marker)) map.removeLayer(marker);
  }
  for (const camera of dataset.cameras) {
    const sample = closest(camera.samples, now, 3) || camera.samples[0];
    if (!sample) continue;
    let marker = layers.cameraMarkers.get(camera.id), wedge = layers.cameraWedges.get(camera.id);
    if (!marker) {
      const index = dataset.cameras.indexOf(camera) + 1;
      marker = L.marker([sample[1], sample[2]], {icon: makeIcon("camera-pin", String(index)), zIndexOffset: 500});
      marker.bindTooltip(camera.name, {direction: "top"});
      layers.cameraMarkers.set(camera.id, marker);
      wedge = L.polygon([], {color: "#725bb6", weight: 1.5, fillColor: "#8b77c5", fillOpacity: .1, interactive: false});
      layers.cameraWedges.set(camera.id, wedge);
    }
    marker.setLatLng([sample[1], sample[2]]);
    wedge.setLatLngs(cameraWedge(sample, camera.fov_deg));
    for (const part of [wedge, marker]) {
      if ($("show-cameras").checked && !map.hasLayer(part)) part.addTo(map);
      if (!$("show-cameras").checked && map.hasLayer(part)) map.removeLayer(part);
    }
  }
  $("active-count").textContent = `${fmtCount(activeReference, "recorded object")} · ${fmtCount(activeSensor, "camera track")} at this time`;
}

function seek(value) {
  now = Math.min(dataset.time_max, Math.max(dataset.time_min, Number(value)));
  draw();
}

function setPlaying(value) {
  playing = value;
  $("play").textContent = playing ? "Ⅱ" : "▶";
  $("play").setAttribute("aria-label", playing ? "Pause" : "Play");
  lastTick = performance.now();
}

function animate(timestamp) {
  if (playing && dataset) {
    const delta = Math.min((timestamp - lastTick) / 1000, .25);
    now += delta * Number($("speed").value);
    if (now >= dataset.time_max) { now = dataset.time_max; setPlaying(false); }
    if (timestamp - lastDraw >= 80 || !playing) { draw(); lastDraw = timestamp; }
  }
  lastTick = timestamp;
  requestAnimationFrame(animate);
}

function fitBounds(cameraArea) {
  const positions = [];
  for (const camera of dataset.cameras) if (camera.samples.length) positions.push([camera.samples[0][1], camera.samples[0][2]]);
  if (!cameraArea || !positions.length) for (const track of dataset.tracks) if (track.kind === "reference")
    for (const sample of track.samples) positions.push([sample[1], sample[2]]);
  if (!positions.length) for (const track of dataset.tracks) for (const sample of track.samples) positions.push([sample[1], sample[2]]);
  if (positions.length) map.fitBounds(L.latLngBounds(positions).pad(cameraArea ? .9 : .15), {maxZoom: 14});
}

async function start() {
  if (typeof L === "undefined") {
    $("active-count").textContent = "The map library could not load. Check your internet connection.";
    return;
  }
  const response = await fetch("/api/data");
  if (!response.ok) throw new Error(`Dataset request failed: ${response.status}`);
  dataset = await response.json();
  assignColors();
  $("dataset-name").textContent = `${dataset.title} · ${fmtCount(dataset.tracks.filter(t => t.kind === "sensor").length, "camera track")} · ${fmtCount(dataset.tracks.filter(t => t.kind === "reference").length, "simulation object")} · ${fmtCount(dataset.cameras.length, "camera")}`;
  $("time-slider").min = dataset.time_min;
  $("time-slider").max = dataset.time_max;
  $("time-start").textContent = fmtElapsed(dataset.time_min);
  $("time-end").textContent = fmtElapsed(dataset.time_max);
  const center = [dataset.origin.latitude_deg, dataset.origin.longitude_deg];
  map = L.map("map", {zoomControl: true}).setView(center, 12);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
  }).addTo(map);
  $("active-count").textContent = "";
  fitBounds(true);
  now = dataset.time_min;
  draw();
  for (const id of toggles) $(id).addEventListener("change", () => {
    if (id === "camera-only" && $(id).checked && selectedKey?.startsWith("reference:")) {
      selectedKey = null;
      selectedGroupKey = null;
      $("selection-card").hidden = true;
    }
    draw();
  });
  $("close-selection").onclick = () => selectTrack(null, false);
  $("fit-airport").onclick = () => fitBounds(true);
  $("fit-all").onclick = () => fitBounds(false);
  $("time-slider").oninput = event => seek(event.target.value);
  $("play").onclick = () => setPlaying(!playing);
  $("restart").onclick = () => { seek(dataset.time_min); setPlaying(false); };
  document.addEventListener("keydown", event => {
    if (event.code === "Space" && !["INPUT", "BUTTON", "SELECT"].includes(document.activeElement.tagName)) {
      event.preventDefault(); setPlaying(!playing);
    }
  });
  requestAnimationFrame(animate);
}

start().catch(error => { $("active-count").textContent = error.message; console.error(error); });
