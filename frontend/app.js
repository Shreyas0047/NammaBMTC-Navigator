/**
 * BMTC Boarding Point Recommender - Destination-First Client
 * With Live Walking Radar, Interactive Map, and Native Turn-by-Turn Deep-Link
 */

const state = {
  origin: {
    name: "Detecting GPS location...",
    lat: null,
    lon: null,
    isLive: false,
  },
  destination: {
    name: null,
    lat: null,
    lon: null,
  },
};

// Map & Navigation State
let mapInstance = null;
let userMarker = null;
let stopMarker = null;
let walkPolyline = null;
let liveWatchId = null;
let currentPrimaryStop = null;

// DOM Elements
const gpsStatusPill = document.getElementById("gps-status-pill");
const gpsStatusText = document.getElementById("gps-status-text");
const currentLocDisplay = document.getElementById("current-loc-display");
const editOriginBtn = document.getElementById("edit-origin-btn");
const originDrawer = document.getElementById("origin-edit-drawer");
const closeDrawerBtn = document.getElementById("close-drawer-btn");
const originSearchInput = document.getElementById("origin-search-input");
const originSuggestions = document.getElementById("origin-suggestions");
const useGpsTrigger = document.getElementById("use-gps-trigger");

const destSearchInput = document.getElementById("dest-search-input");
const destSuggestions = document.getElementById("dest-suggestions");
const clearDestBtn = document.getElementById("clear-dest-btn");
const findActionBtn = document.getElementById("find-action-btn");
const statusCard = document.getElementById("status-card");

const resultView = document.getElementById("result-view");
const journeyOriginTitle = document.getElementById("journey-origin-title");
const timelineWalkText = document.getElementById("timeline-walk-text");
const recStopName = document.getElementById("rec-stop-name");
const recStopDesc = document.getElementById("rec-stop-desc");
const recRoutesList = document.getElementById("rec-routes-list");
const recDestStop = document.getElementById("rec-dest-stop");

const liveDistanceCountdown = document.getElementById("live-distance-countdown");
const arrivalStatusPill = document.getElementById("arrival-status-pill");
const nativeNavBtn = document.getElementById("native-nav-btn");
const recenterMapBtn = document.getElementById("recenter-map-btn");

const toggleAltsBtn = document.getElementById("toggle-alts-btn");
const altsCountLabel = document.getElementById("alts-count-label");
const alternativesContainer = document.getElementById("alternatives-container");

// ================= Geolocation Helpers =================
function haversineMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const toRad = (x) => (x * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function requestLiveLocation(silent = false) {
  if (!navigator.geolocation) {
    fallbackLocation("GPS not supported by your browser");
    return;
  }

  currentLocDisplay.textContent = "Acquiring live GPS satellite lock...";
  gpsStatusText.textContent = "Acquiring...";

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      state.origin.lat = pos.coords.latitude;
      state.origin.lon = pos.coords.longitude;
      state.origin.name = "My Live Street Location";
      state.origin.isLive = true;

      currentLocDisplay.textContent = "📍 Live GPS Location";
      gpsStatusText.textContent = "Live GPS Active";
      gpsStatusPill.classList.add("active");
      hideStatus();
    },
    (err) => {
      console.warn("GPS Error / Denied:", err);
      fallbackLocation("Location denied. Defaulted to Corporation Circle.");
    },
    { enableHighAccuracy: true, timeout: 9000 }
  );
}

function fallbackLocation(msg) {
  // Default: Corporation Circle
  state.origin.lat = 12.9680;
  state.origin.lon = 77.5880;
  state.origin.name = "Corporation Circle (Default)";
  state.origin.isLive = false;

  currentLocDisplay.textContent = "Corporation Circle (Tap 'Change' to pick)";
  gpsStatusText.textContent = "Set Location";
  gpsStatusPill.classList.remove("active");
  if (msg) showStatus(msg, "info");
}

gpsStatusPill.addEventListener("click", () => requestLiveLocation(false));
useGpsTrigger.addEventListener("click", () => {
  requestLiveLocation(false);
  originDrawer.classList.add("hidden");
});

// Origin Edit Drawer
editOriginBtn.addEventListener("click", () => {
  originDrawer.classList.toggle("hidden");
  if (!originDrawer.classList.contains("hidden")) {
    originSearchInput.focus();
  }
});

closeDrawerBtn.addEventListener("click", () => {
  originDrawer.classList.add("hidden");
});

// ================= Autocomplete Search =================
let debounceTimer = null;
function setupAutocomplete(inputEl, dropdownEl, onSelect) {
  inputEl.addEventListener("input", () => {
    const q = inputEl.value.trim();
    if (q.length < 2) {
      dropdownEl.innerHTML = "";
      dropdownEl.classList.add("hidden");
      return;
    }

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/stops/search?q=${encodeURIComponent(q)}`);
        const stops = await res.json();
        renderDropdown(stops, dropdownEl, onSelect);
      } catch (e) {
        console.error("Search failed:", e);
      }
    }, 220);
  });
}

function renderDropdown(items, dropdownEl, onSelect) {
  if (!items || items.length === 0) {
    dropdownEl.innerHTML = `<div class="suggestion-item"><span class="sugg-name">No stops found</span></div>`;
    dropdownEl.classList.remove("hidden");
    return;
  }

  dropdownEl.innerHTML = items
    .map(
      (s) => `
      <div class="suggestion-item" data-id="${s.stop_id}" data-name="${s.stop_name}" data-desc="${s.stop_desc}" data-lat="${s.lat}" data-lon="${s.lon}">
        <div class="sugg-name">${s.stop_name}</div>
        <div class="sugg-desc">${s.stop_desc || "BMTC Stop"}</div>
      </div>
    `
    )
    .join("");

  dropdownEl.classList.remove("hidden");

  dropdownEl.querySelectorAll(".suggestion-item").forEach((el) => {
    el.addEventListener("click", () => {
      const data = {
        id: el.dataset.id,
        name: el.dataset.name,
        desc: el.dataset.desc,
        lat: parseFloat(el.dataset.lat),
        lon: parseFloat(el.dataset.lon),
      };
      onSelect(data);
      dropdownEl.classList.add("hidden");
    });
  });
}

// Wire Origin Autocomplete
setupAutocomplete(originSearchInput, originSuggestions, (stop) => {
  state.origin.name = stop.name;
  state.origin.lat = stop.lat;
  state.origin.lon = stop.lon;
  state.origin.isLive = false;

  currentLocDisplay.textContent = stop.name;
  gpsStatusText.textContent = "Custom Origin";
  gpsStatusPill.classList.remove("active");
  originDrawer.classList.add("hidden");
});

// Wire Destination Autocomplete
setupAutocomplete(destSearchInput, destSuggestions, (stop) => {
  setDestination(stop.name, stop.lat, stop.lon);
  document.querySelectorAll(".hub-card").forEach((c) => c.classList.remove("active"));
  triggerRecommendation();
});

function setDestination(name, lat, lon) {
  state.destination.name = name;
  state.destination.lat = lat;
  state.destination.lon = lon;
  destSearchInput.value = name;
  clearDestBtn.classList.remove("hidden");
  hideStatus();
}

clearDestBtn.addEventListener("click", () => {
  state.destination.name = null;
  state.destination.lat = null;
  state.destination.lon = null;
  destSearchInput.value = "";
  clearDestBtn.classList.add("hidden");
  document.querySelectorAll(".hub-card").forEach((c) => c.classList.remove("active"));
  resultView.classList.remove("is-visible");
  resultView.classList.add("hidden");
  if (liveWatchId !== null && navigator.geolocation) {
    navigator.geolocation.clearWatch(liveWatchId);
    liveWatchId = null;
  }
});

// Hub Cards
document.querySelectorAll(".hub-card").forEach((card) => {
  card.addEventListener("click", () => {
    document.querySelectorAll(".hub-card").forEach((c) => c.classList.remove("active"));
    card.classList.add("active");

    const lat = parseFloat(card.dataset.lat);
    const lon = parseFloat(card.dataset.lon);
    const name = card.dataset.name;

    setDestination(name, lat, lon);
    triggerRecommendation();
  });
});

// Close dropdowns on outside click
document.addEventListener("click", (e) => {
  if (!e.target.closest(".destination-search-card")) {
    destSuggestions.classList.add("hidden");
  }
  if (!e.target.closest(".search-box")) {
    originSuggestions.classList.add("hidden");
  }
});

// Status Card Helper
function showStatus(msg, type = "info") {
  statusCard.textContent = msg;
  statusCard.className = `status-card ${type}`;
  statusCard.classList.remove("hidden");
}

function hideStatus() {
  statusCard.classList.add("hidden");
}

const skeletonView = document.getElementById("skeleton-view");
const resultBadgeText = document.getElementById("result-badge-text");
const boardingTagLabel = document.getElementById("boarding-tag-label");
const leg1BoxCaption = document.getElementById("leg1-box-caption");
const transferStepBox = document.getElementById("transfer-step-box");
const transferHubName = document.getElementById("transfer-hub-name");
const transferHubDesc = document.getElementById("transfer-hub-desc");
const recLeg2RoutesList = document.getElementById("rec-leg2-routes-list");
const transfer2StepBox = document.getElementById("transfer2-step-box");
const transfer2HubName = document.getElementById("transfer2-hub-name");
const transfer2HubDesc = document.getElementById("transfer2-hub-desc");
const recLeg3RoutesList = document.getElementById("rec-leg3-routes-list");
const timelineTransitText = document.getElementById("timeline-transit-text");

// Handle Enter key in destination input
destSearchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    destSuggestions.classList.add("hidden");
    triggerRecommendation();
  }
});

// ================= Find Action Handler =================
findActionBtn.addEventListener("click", () => {
  triggerRecommendation();
});

async function triggerRecommendation() {
  if (!state.origin.lat || !state.origin.lon) {
    showStatus("Please allow GPS location or pick a starting stop.", "error");
    return;
  }

  // Smart resolution: if user typed destination but didn't click dropdown item
  if (!state.destination.lat || !state.destination.lon) {
    const typed = destSearchInput.value.trim();
    if (typed.length >= 2) {
      try {
        const searchRes = await fetch(`/api/stops/search?q=${encodeURIComponent(typed)}`);
        const items = await searchRes.json();
        if (items && items.length > 0) {
          setDestination(items[0].stop_name, items[0].lat, items[0].lon);
        } else {
          showStatus(`No BMTC stops found matching "${typed}". Please check spelling.`, "error");
          destSearchInput.focus();
          return;
        }
      } catch (e) {
        showStatus("Please enter your destination or choose one of the popular hubs.", "error");
        destSearchInput.focus();
        return;
      }
    } else {
      showStatus("Please enter your destination or choose one of the popular hubs.", "error");
      destSearchInput.focus();
      return;
    }
  }

  hideStatus();
  resultView.classList.remove("is-visible");
  resultView.classList.add("hidden");
  skeletonView.classList.remove("hidden");
  skeletonView.scrollIntoView({ behavior: "smooth", block: "nearest" });

  findActionBtn.disabled = true;
  findActionBtn.innerHTML = `<span>Finding Best Boarding Stop...</span>`;

  const startTime = Date.now();
  const MIN_SKELETON_MS = 550; // Smooth skeleton shimmer duration

  try {
    const payload = {
      origin_lat: state.origin.lat,
      origin_lon: state.origin.lon,
      dest_lat: state.destination.lat,
      dest_lon: state.destination.lon,
      origin_name: state.origin.name,
      dest_name: state.destination.name,
    };

    const fetchPromise = fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const [res] = await Promise.all([
      fetchPromise,
      new Promise((resolve) => {
        const elapsed = Date.now() - startTime;
        const remaining = Math.max(0, MIN_SKELETON_MS - elapsed);
        setTimeout(resolve, remaining);
      }),
    ]);

    const data = await res.json();

    if (!res.ok || data.status !== "OK" || !data.primary) {
      skeletonView.classList.add("hidden");
      showStatus(data.message || "No viable BMTC bus route found between these points.", "error");
      resultView.classList.add("hidden");
      return;
    }

    renderJourney(data);
  } catch (err) {
    console.error("API Error:", err);
    skeletonView.classList.add("hidden");
    showStatus("Failed to connect to local recommender server.", "error");
  } finally {
    findActionBtn.disabled = false;
    findActionBtn.innerHTML = `
      <span>Recommend My Boarding Point</span>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="5" y1="12" x2="19" y2="12"></line>
        <polyline points="12 5 19 12 12 19"></polyline>
      </svg>
    `;
  }
}

// ================= Render Journey Stepper & Map =================
function renderJourney(data) {
  skeletonView.classList.add("hidden");
  const p = data.primary;
  currentPrimaryStop = p;

  // Origin step
  journeyOriginTitle.textContent = state.origin.name || "Your Current Location";

  // Walk Directive
  const walkStr = `Walk ${p.walk_distance_m} m (~${p.walk_duration_min} min)`;
  timelineWalkText.textContent = walkStr;
  liveDistanceCountdown.textContent = walkStr;
  arrivalStatusPill.classList.add("hidden");

  // Boarding Stop
  recStopName.textContent = p.stop_name;
  if (p.stop_desc) {
    recStopDesc.innerHTML = `<span class="dir-icon">📍</span> <span class="dir-text">${p.stop_desc}</span>`;
    recStopDesc.classList.remove("hidden");
  } else {
    recStopDesc.classList.add("hidden");
  }

  // Handle Direct vs 1-Transfer vs 2-Transfer Journey
  if (p.transfers_count === 2) {
    resultBadgeText.textContent = "2 BUS CHANGES • 3-LEG JOURNEY";
    resultBadgeText.style.backgroundColor = "#C2410C";
    boardingTagLabel.textContent = "BOARD BUS 1 HERE";
    leg1BoxCaption.textContent = "LEG 1: CATCH ANY TO 1ST INTERCHANGE";

    // 1st Transfer Step
    transferStepBox.classList.remove("hidden");
    transferHubName.textContent = p.transfer_stop_name;
    transferHubDesc.textContent = p.transfer_stop_desc || "Change to Bus 2";
    const leg2Routes = p.leg2_routes || [];
    recLeg2RoutesList.innerHTML = leg2Routes
      .slice(0, 4)
      .map(
        (r) => `
        <div class="route-row">
          <div class="route-ident">
            <span class="route-pill" style="background-color: #B45309;">${r.route}</span>
            <span class="route-headsign">Towards ${r.towards}</span>
          </div>
          <span class="route-frequency">${r.trips_per_day} buses/day</span>
        </div>
      `
      )
      .join("");

    // 2nd Transfer Step
    transfer2StepBox.classList.remove("hidden");
    transfer2HubName.textContent = p.transfer2_stop_name;
    transfer2HubDesc.textContent = p.transfer2_stop_desc || "Change to Bus 3 towards destination";
    const leg3Routes = p.leg3_routes || [];
    recLeg3RoutesList.innerHTML = leg3Routes
      .slice(0, 4)
      .map(
        (r) => `
        <div class="route-row">
          <div class="route-ident">
            <span class="route-pill" style="background-color: #C2410C;">${r.route}</span>
            <span class="route-headsign">Towards ${r.towards}</span>
          </div>
          <span class="route-frequency">${r.trips_per_day} buses/day</span>
        </div>
      `
      )
      .join("");

    timelineTransitText.textContent = `Via ${p.transfer_stop_name} & ${p.transfer2_stop_name}`;
  } else if (p.is_direct === false || p.transfers_count === 1) {
    resultBadgeText.textContent = "TRANSFER ROUTE • 1 BUS CHANGE";
    resultBadgeText.style.backgroundColor = "#D97706";
    boardingTagLabel.textContent = "BOARD BUS 1 HERE";
    leg1BoxCaption.textContent = "LEG 1: CATCH ANY TO INTERCHANGE";

    transferStepBox.classList.remove("hidden");
    transfer2StepBox.classList.add("hidden");
    transferHubName.textContent = p.transfer_stop_name;
    transferHubDesc.textContent = p.transfer_stop_desc || "Change to connecting bus";

    // Leg 2 routes
    const leg2Routes = p.leg2_routes || [];
    recLeg2RoutesList.innerHTML = leg2Routes
      .slice(0, 4)
      .map(
        (r) => `
        <div class="route-row">
          <div class="route-ident">
            <span class="route-pill" style="background-color: #B45309;">${r.route}</span>
            <span class="route-headsign">Towards ${r.towards}</span>
          </div>
          <span class="route-frequency">${r.trips_per_day} buses/day</span>
        </div>
      `
      )
      .join("");

    timelineTransitText.textContent = `Change at ${p.transfer_stop_name}`;
  } else {
    resultBadgeText.textContent = "PRIMARY RECOMMENDATION (DIRECT)";
    resultBadgeText.style.backgroundColor = "var(--bmtc-navy)";
    boardingTagLabel.textContent = "BOARD YOUR BUS HERE";
    leg1BoxCaption.textContent = "CATCH ANY OF THESE SERVICES";
    transferStepBox.classList.add("hidden");
    transfer2StepBox.classList.add("hidden");
    timelineTransitText.textContent = "Direct BMTC Bus Route";
  }

  // Setup Native Walking Navigation Deep-Link (Google Maps Walking Mode)
  const mapsUrl = `https://www.google.com/maps/dir/?api=1&origin=${state.origin.lat},${state.origin.lon}&destination=${p.lat},${p.lon}&travelmode=walking`;
  nativeNavBtn.href = mapsUrl;

  // Initialize or update the interactive walking map
  initOrUpdateWalkingMap(state.origin.lat, state.origin.lon, p.lat, p.lon, p.stop_name, p.stop_desc);

  // Start live walking radar tracker
  startWalkingTracker(p.lat, p.lon);

  // Routes (Leg 1 or Direct)
  const routesToDisplay = p.leg1_routes && p.leg1_routes.length > 0 ? p.leg1_routes : p.routes;
  recRoutesList.innerHTML = routesToDisplay
    .slice(0, 4)
    .map(
      (r) => `
      <div class="route-row">
        <div class="route-ident">
          <span class="route-pill">${r.route}</span>
          <span class="route-headsign">Towards ${r.towards}</span>
        </div>
        <span class="route-frequency">${r.trips_per_day} buses/day</span>
      </div>
    `
    )
    .join("");

  // Destination
  const destName = p.routes.length > 0 ? p.routes[0].destination_stop : state.destination.name;
  recDestStop.textContent = destName;

  // Alternatives Accordion
  const alts = data.alternatives || [];
  if (alts.length > 0) {
    toggleAltsBtn.classList.remove("hidden");
    altsCountLabel.textContent = `Other Nearby Boarding Stops (${alts.length})`;

    alternativesContainer.innerHTML = alts
      .map(
        (alt, i) => `
        <div class="alt-card">
          <div class="alt-top">
            <span class="alt-title">#${i + 2}. ${alt.stop_name}</span>
            <span class="alt-dist">${alt.walk_distance_m}m walk</span>
          </div>
          <div class="alt-desc">${alt.stop_desc || ""}</div>
          <div class="alt-buses">
            Available: ${(alt.routes || alt.leg1_routes || []).slice(0, 3).map((r) => `<b>${r.route}</b>`).join(", ")}
          </div>
        </div>
      `
      )
      .join("");
  } else {
    toggleAltsBtn.classList.add("hidden");
    alternativesContainer.classList.add("hidden");
  }

  resultView.classList.remove("hidden");
  // Force reflow to replay spring animations fresh
  void resultView.offsetWidth;
  resultView.classList.add("is-visible");
  resultView.scrollIntoView({ behavior: "smooth", block: "start" });

  setTimeout(() => {
    if (mapInstance) {
      mapInstance.invalidateSize();
    }
  }, 350);
}

// ================= Interactive Walking Map =================
function initOrUpdateWalkingMap(userLat, userLon, stopLat, stopLon, stopName, stopDesc) {
  if (typeof L === "undefined") {
    console.warn("Leaflet not loaded");
    return;
  }

  const mapEl = document.getElementById("walking-map");
  if (!mapEl) return;

  if (!mapInstance) {
    mapInstance = L.map("walking-map", {
      zoomControl: false,
      attributionControl: false,
    });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
    }).addTo(mapInstance);
  }

  const userIcon = L.divIcon({
    className: "custom-user-icon",
    html: '<div class="user-marker-pulse"></div>',
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });

  const stopIcon = L.divIcon({
    className: "custom-stop-icon",
    html: `<div class="stop-marker-pin">🚏 ${stopName}</div>`,
    iconSize: [120, 24],
    iconAnchor: [60, 12],
  });

  if (!userMarker) {
    userMarker = L.marker([userLat, userLon], { icon: userIcon }).addTo(mapInstance);
  } else {
    userMarker.setLatLng([userLat, userLon]);
  }

  if (!stopMarker) {
    stopMarker = L.marker([stopLat, stopLon], { icon: stopIcon }).addTo(mapInstance);
  } else {
    stopMarker.setLatLng([stopLat, stopLon]);
  }

  const polylineCoords = [
    [userLat, userLon],
    [stopLat, stopLon],
  ];

  if (!walkPolyline) {
    walkPolyline = L.polyline(polylineCoords, {
      color: "#0284C7",
      weight: 3,
      dashArray: "6, 6",
      opacity: 0.9,
    }).addTo(mapInstance);
  } else {
    walkPolyline.setLatLngs(polylineCoords);
  }

  mapInstance.fitBounds(polylineCoords, { padding: [35, 35], maxZoom: 17 });
  setTimeout(() => mapInstance && mapInstance.invalidateSize(), 250);
}

// Re-center Map
recenterMapBtn.addEventListener("click", () => {
  if (mapInstance && currentPrimaryStop && state.origin.lat) {
    mapInstance.fitBounds(
      [
        [state.origin.lat, state.origin.lon],
        [currentPrimaryStop.lat, currentPrimaryStop.lon],
      ],
      { padding: [35, 35], maxZoom: 17 }
    );
  }
});

// ================= Live Walking Tracker =================
function startWalkingTracker(stopLat, stopLon) {
  if (liveWatchId !== null && navigator.geolocation) {
    navigator.geolocation.clearWatch(liveWatchId);
    liveWatchId = null;
  }

  if (!navigator.geolocation) return;

  liveWatchId = navigator.geolocation.watchPosition(
    (pos) => {
      const curLat = pos.coords.latitude;
      const curLon = pos.coords.longitude;
      state.origin.lat = curLat;
      state.origin.lon = curLon;

      const rawDist = haversineMeters(curLat, curLon, stopLat, stopLon);
      const estWalkM = Math.round(rawDist * 1.35);
      const estWalkMin = Math.max(1, Math.ceil(estWalkM / 72));

      if (rawDist <= 30) {
        liveDistanceCountdown.textContent = "You have arrived at the stop!";
        arrivalStatusPill.classList.remove("hidden");
      } else {
        const liveStr = `Walk ${estWalkM} m (~${estWalkMin} min)`;
        liveDistanceCountdown.textContent = liveStr;
        timelineWalkText.textContent = liveStr;
        arrivalStatusPill.classList.add("hidden");
      }

      if (userMarker) userMarker.setLatLng([curLat, curLon]);
      if (walkPolyline) walkPolyline.setLatLngs([[curLat, curLon], [stopLat, stopLon]]);
    },
    (err) => console.warn("Live watch error:", err),
    { enableHighAccuracy: true, maximumAge: 3000, timeout: 10000 }
  );
}

// Alternatives Toggle
toggleAltsBtn.addEventListener("click", () => {
  const isHidden = alternativesContainer.classList.contains("hidden");
  if (isHidden) {
    alternativesContainer.classList.remove("hidden");
    toggleAltsBtn.classList.add("expanded");
  } else {
    alternativesContainer.classList.add("hidden");
    toggleAltsBtn.classList.remove("expanded");
  }
});

// Auto-run GPS detection on initial load
requestLiveLocation(true);
