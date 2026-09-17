/**
 * NammaBMTC Navigator - Modern Windows XP / Luna Frutiger Aero Controller
 * Integrates Destination-Aware Transit Engine with Real-Time BMTC VTMS Telemetry
 */

// Application State
const appState = {
  origin: {
    name: "Detecting GPS location...",
    lat: 12.9774,
    lon: 77.5708,
    isLive: false,
  },
  destination: {
    name: null,
    lat: null,
    lon: null,
  },
  primaryCandidate: null,
  alternatives: [],
  activeBusMarker: null,
  telemetryTimer: null,
};

// Map instances
let map = null;
let userMarker = null;
let stopMarker = null;
let walkLine = null;
let busMarker = null;

// DOM Cache
const gpsStatusText = document.getElementById("gps-status-text");
const currentOriginText = document.getElementById("current-origin-text");
const changeOriginBtn = document.getElementById("change-origin-btn");
const originModal = document.getElementById("origin-modal");
const modalCloseBtn = document.getElementById("modal-close-btn");
const modalCancelBtn = document.getElementById("modal-cancel-btn");
const modalSaveBtn = document.getElementById("modal-save-btn");
const modalOriginInput = document.getElementById("modal-origin-input");
const modalOriginSuggestions = document.getElementById("modal-origin-suggestions");

const destinationInput = document.getElementById("destination-input");
const clearSearchBtn = document.getElementById("clear-search-btn");
const suggestionsDropdown = document.getElementById("suggestions-dropdown");
const recentChipsContainer = document.getElementById("recent-chips-container");
const clearRecentBtn = document.getElementById("clear-recent-btn");
const loadingIndicator = document.getElementById("loading-indicator");

const journeyResults = document.getElementById("journey-results");
const primaryCard = document.getElementById("primary-card");
const step1OriginName = document.getElementById("step1-origin-name");
const walkInfoChip = document.getElementById("walk-info-chip");
const step2StopName = document.getElementById("step2-stop-name");
const step2PlatformDesc = document.getElementById("step2-platform-desc");
const vtmsStatusTitle = document.getElementById("vtms-status-title");
const radarEtaPill = document.getElementById("radar-eta-pill");
const fleetPillsRow = document.getElementById("fleet-pills-row");
const walkingNavBtn = document.getElementById("walking-nav-btn");
const step3DestName = document.getElementById("step3-dest-name");
const step3Subtext = document.getElementById("step3-subtext");
const fareSummaryBadge = document.getElementById("fare-summary-badge");

const transferBox = document.getElementById("transfer-box");
const transferRow = document.getElementById("transfer-row");
const alternativesDrawer = document.getElementById("alternatives-drawer");
const altDrawerTrigger = document.getElementById("alt-drawer-trigger");
const altDrawerContent = document.getElementById("alt-drawer-content");
const altChevron = document.getElementById("alt-chevron");
const altHeading = document.getElementById("alt-heading");

const navToast = document.getElementById("nav-toast");
const navToastMsg = document.getElementById("nav-toast-msg");

// ==========================================
// 1. Geolocation Setup
// ==========================================
function initGeolocation() {
  if (!navigator.geolocation) {
    setFallbackOrigin("Majestic (Kempegowda Bus Station)", 12.9774, 77.5708);
    return;
  }

  currentOriginText.textContent = "Acquiring satellite lock...";
  gpsStatusText.textContent = "Acquiring GPS...";

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      appState.origin.lat = pos.coords.latitude;
      appState.origin.lon = pos.coords.longitude;
      appState.origin.isLive = true;
      appState.origin.name = "Your Live Location (GPS)";

      gpsStatusText.textContent = "● Live GPS Active";
      currentOriginText.textContent = "Live GPS Location";
      step1OriginName.textContent = "Your Location";

      // If destination already selected, refresh recommendation
      if (appState.destination.lat && appState.destination.lon) {
        fetchRecommendation();
      }
    },
    (err) => {
      console.warn("GPS access denied or unavailable:", err.message);
      setFallbackOrigin("Majestic (KBS)", 12.9774, 77.5708);
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
  );
}

function setFallbackOrigin(name, lat, lon) {
  appState.origin.lat = lat;
  appState.origin.lon = lon;
  appState.origin.isLive = false;
  appState.origin.name = name;

  gpsStatusText.textContent = "● Preset Origin";
  currentOriginText.textContent = name;
  step1OriginName.textContent = name;
}

// ==========================================
// 2. Leaflet Mini-Map
// ==========================================
function initOrUpdateMap(originLat, originLon, stopLat, stopLon, stopName, approachingBus = null) {
  const mapContainer = document.getElementById("mini-map");
  if (!mapContainer) return;

  if (!map) {
    map = L.map("mini-map", {
      zoomControl: false,
      attributionControl: false,
    }).setView([originLat, originLon], 14);

    L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
    }).addTo(map);

    L.control.zoom({ position: "topleft" }).addTo(map);
  }

  // Clear previous markers & lines
  if (userMarker) map.removeLayer(userMarker);
  if (stopMarker) map.removeLayer(stopMarker);
  if (walkLine) map.removeLayer(walkLine);
  if (busMarker) map.removeLayer(busMarker);

  // User Marker
  const userIcon = L.divIcon({
    className: "user-pin-marker",
    html: `<div style="width:14px;height:14px;border-radius:50%;background:#0a246a;border:2px solid #fff;box-shadow:0 0 6px #0a246a;"></div>`,
    iconSize: [14, 14],
  });
  userMarker = L.marker([originLat, originLon], { icon: userIcon })
    .addTo(map)
    .bindPopup(`<b>Your Location</b><br>${appState.origin.name}`);

  // Stop Marker
  const stopIcon = L.divIcon({
    className: "stop-pin-marker",
    html: `<div id="map-stop-pill" style="background:#127533;color:#fff;padding:3px 8px;font-size:11px;font-weight:bold;border:1px solid #fff;border-radius:3px;box-shadow:1px 1px 4px rgba(0,0,0,0.4);white-space:nowrap;">🚏 ${stopName}</div>`,
    iconSize: [120, 24],
  });
  stopMarker = L.marker([stopLat, stopLon], { icon: stopIcon })
    .addTo(map)
    .bindPopup(`<b>Boarding Point</b><br>${stopName}`);

  // Walking Dotted Line
  walkLine = L.polyline([[originLat, originLon], [stopLat, stopLon]], {
    color: "#0a246a",
    weight: 3,
    dashArray: "5, 6",
    opacity: 0.85,
  }).addTo(map);

  const bounds = [[originLat, originLon], [stopLat, stopLon]];

  // If live approaching bus available, plot it
  if (approachingBus && approachingBus.lat && approachingBus.lon) {
    const busIcon = L.divIcon({
      className: "bus-pin-marker",
      html: `<div style="background:#0a246a;color:#fff;padding:3px 8px;font-size:11px;font-weight:bold;border:1px solid #fff;border-radius:3px;box-shadow:1px 1px 5px rgba(0,0,0,0.5);white-space:nowrap;">🚌 ${approachingBus.route || 'BMTC'} (${approachingBus.eta_mins || '?'}m)</div>`,
      iconSize: [100, 24],
    });
    busMarker = L.marker([approachingBus.lat, approachingBus.lon], { icon: busIcon })
      .addTo(map)
      .bindPopup(`<b>Live BMTC Bus (${approachingBus.route || 'BMTC'})</b><br>Vehicle: ${approachingBus.vehicle_no || 'In Service'}<br>ETA: ~${approachingBus.eta_mins || 2} min`);
    bounds.push([approachingBus.lat, approachingBus.lon]);
  }

  map.fitBounds(bounds, { padding: [35, 35] });
  setTimeout(() => map.invalidateSize(), 200);
}

// ==========================================
// 3. Stop Autocomplete & Search Engine
// ==========================================
let searchDebounceTimer = null;

destinationInput.addEventListener("input", (e) => {
  const query = e.target.value.trim();
  clearSearchBtn.style.display = query.length > 0 ? "flex" : "none";

  clearTimeout(searchDebounceTimer);
  if (query.length < 2) {
    suggestionsDropdown.style.display = "none";
    return;
  }

  searchDebounceTimer = setTimeout(() => {
    fetchStopSuggestions(query);
  }, 220);
});

clearSearchBtn.addEventListener("click", () => {
  destinationInput.value = "";
  clearSearchBtn.style.display = "none";
  suggestionsDropdown.style.display = "none";
  destinationInput.focus();
});

async function fetchStopSuggestions(query) {
  try {
    const params = new URLSearchParams({
      q: query,
      user_lat: appState.origin.lat,
      user_lon: appState.origin.lon,
    });
    const res = await fetch(`/api/stops/search?${params.toString()}`);
    if (!res.ok) return;
    const stops = await res.json();

    if (stops.length === 0) {
      suggestionsDropdown.innerHTML = `<div style="padding:10px;font-size:12px;color:#666;">No BMTC stops found matching "${query}"</div>`;
      suggestionsDropdown.style.display = "block";
      return;
    }

    suggestionsDropdown.innerHTML = stops
      .slice(0, 8)
      .map(
        (s) => `
      <div class="suggestion-item" data-id="${s.stop_id}" data-name="${s.stop_name}" data-lat="${s.lat}" data-lon="${s.lon}">
        <div>
          <div class="sugg-name">${s.stop_name}</div>
          <div class="sugg-sub">${s.stop_desc ? s.stop_desc : 'Bengaluru BMTC Transit Stop'}</div>
        </div>
        ${s.dist_km !== undefined && s.dist_km !== null ? `<span class="sugg-dist-chip">${s.dist_km} km</span>` : ''}
      </div>
    `
      )
      .join("");

    suggestionsDropdown.style.display = "block";

    // Attach click handlers
    suggestionsDropdown.querySelectorAll(".suggestion-item").forEach((item) => {
      item.addEventListener("click", () => {
        const name = item.getAttribute("data-name");
        const lat = parseFloat(item.getAttribute("data-lat"));
        const lon = parseFloat(item.getAttribute("data-lon"));

        selectDestination(name, lat, lon);
      });
    });
  } catch (e) {
    console.error("Autocomplete fetch error:", e);
  }
}

function selectDestination(name, lat, lon) {
  appState.destination.name = name;
  appState.destination.lat = lat;
  appState.destination.lon = lon;

  destinationInput.value = name;
  clearSearchBtn.style.display = "flex";
  suggestionsDropdown.style.display = "none";

  saveRecentSearch(name, lat, lon);
  fetchRecommendation();
}

// Document click to close suggestions
document.addEventListener("click", (e) => {
  if (!destinationInput.contains(e.target) && !suggestionsDropdown.contains(e.target)) {
    suggestionsDropdown.style.display = "none";
  }
});

// Keyboard Shortcut Ctrl+K / /
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    destinationInput.focus();
    destinationInput.select();
  }
  if (e.key === "Escape") {
    suggestionsDropdown.style.display = "none";
    originModal.style.display = "none";
  }
});

// ==========================================
// 4. Recent Searches Tray (localStorage)
// ==========================================
const RECENT_STORAGE_KEY = "nammabmtc_recent_commutes";

function loadRecentSearches() {
  try {
    const raw = localStorage.getItem(RECENT_STORAGE_KEY);
    const recents = raw ? JSON.parse(raw) : [];
    renderRecentChips(recents);
  } catch (e) {
    renderRecentChips([]);
  }
}

function saveRecentSearch(name, lat, lon) {
  try {
    let recents = [];
    const raw = localStorage.getItem(RECENT_STORAGE_KEY);
    if (raw) recents = JSON.parse(raw);

    recents = recents.filter((r) => r.name !== name);
    recents.unshift({ name, lat, lon });
    if (recents.length > 5) recents.pop();

    localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(recents));
    renderRecentChips(recents);
  } catch (e) {
    console.warn("localStorage save failed:", e);
  }
}

function renderRecentChips(recents) {
  if (!recents || recents.length === 0) {
    // Default preset hubs for immediate first-time discovery
    const defaults = [
      { name: "Silk Board", lat: 12.9176, lon: 77.6238, color: "#2ecc71" },
      { name: "Electronic City", lat: 12.8452, lon: 77.6602, color: "#3b82f6" },
      { name: "ITPL Tech Park", lat: 12.9863, lon: 77.7378, color: "#f59e0b" },
      { name: "Majestic", lat: 12.9774, lon: 77.5708, color: "#8b5cf6" },
    ];
    recentChipsContainer.innerHTML = defaults
      .map(
        (d) => `
      <button class="luna-chip" data-name="${d.name}" data-lat="${d.lat}" data-lon="${d.lon}">
        <span style="color:${d.color};">●</span> ${d.name}
      </button>
    `
      )
      .join("");
  } else {
    const colors = ["#2ecc71", "#3b82f6", "#f59e0b", "#8b5cf6", "#ec4899"];
    recentChipsContainer.innerHTML = recents
      .map(
        (r, idx) => `
      <button class="luna-chip" data-name="${r.name}" data-lat="${r.lat}" data-lon="${r.lon}">
        <span style="color:${colors[idx % colors.length]};">●</span> ${r.name}
      </button>
    `
      )
      .join("");
  }

  recentChipsContainer.querySelectorAll(".luna-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const name = chip.getAttribute("data-name");
      const lat = parseFloat(chip.getAttribute("data-lat"));
      const lon = parseFloat(chip.getAttribute("data-lon"));
      selectDestination(name, lat, lon);
    });
  });
}

clearRecentBtn.addEventListener("click", () => {
  localStorage.removeItem(RECENT_STORAGE_KEY);
  renderRecentChips([]);
});

// ==========================================
// 5. Recommendation Fetch & Render Engine
// ==========================================
async function fetchRecommendation() {
  if (!appState.destination.lat || !appState.destination.lon) return;

  loadingIndicator.style.display = "block";
  journeyResults.style.display = "none";

  try {
    const payload = {
      origin_lat: appState.origin.lat,
      origin_lon: appState.origin.lon,
      dest_lat: appState.destination.lat,
      dest_lon: appState.destination.lon,
      origin_name: appState.origin.name,
      dest_name: appState.destination.name,
    };

    const res = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    loadingIndicator.style.display = "none";

    if (!res.ok) {
      alert("Unable to find transit options for this corridor. Please select another stop.");
      return;
    }

    const data = await res.json();
    if (!data.primary) {
      alert("No direct or connecting BMTC routes found between these locations.");
      return;
    }

    appState.primaryCandidate = data.primary;
    appState.alternatives = data.alternatives || [];

    renderRecommendation(data.primary, data.alternatives);
    journeyResults.style.display = "block";

    // Scroll to results smoothly
    journeyResults.scrollIntoView({ behavior: "smooth", block: "start" });

    // Start Live VTMS Polling
    startLiveTelemetryPolling(data.primary);
  } catch (e) {
    loadingIndicator.style.display = "none";
    console.error("Failed to compute recommendation:", e);
  }
}

function renderRecommendation(primary, alternatives) {
  // Step 1: Origin
  step1OriginName.textContent = appState.origin.name;
  walkInfoChip.textContent = `🚶 Walk ${primary.walk_distance_m} m (~${primary.walk_duration_min} min)`;

  // Step 2: Optimal Boarding Stop
  step2StopName.textContent = primary.stop_name;
  step2PlatformDesc.textContent = primary.stop_desc
    ? `${primary.stop_desc}`
    : "Verified directional platform towards destination";

  // Step 3: Destination
  step3DestName.textContent = appState.destination.name;
  step3Subtext.textContent = primary.is_direct
    ? "Direct route reachability confirmed (Zero transfers)"
    : `Connecting route via ${primary.transfer_stop_name || 'Hub'}`;

  fareSummaryBadge.textContent = primary.is_direct
    ? "Direct Transit Route"
    : `1 Transfer via ${primary.transfer_stop_name || 'Transfer Hub'}`;

  // Route Fleet Pills
  const routesToRender = primary.is_direct
    ? primary.routes || []
    : primary.leg1_routes || primary.routes || [];

  if (routesToRender.length > 0) {
    fleetPillsRow.innerHTML = routesToRender
      .slice(0, 5)
      .map(
        (r, idx) => `
      <div class="route-pill-jelly ${idx % 2 === 0 ? 'blue' : 'dark'}" data-route="${r.route}">
        <span class="badge-code">${r.route}</span>
        <span class="route-freq-tag">${r.trips_per_day} trips/day</span>
      </div>
    `
      )
      .join("");
  } else {
    fleetPillsRow.innerHTML = `<div style="font-size:12px;color:#555;">Multiple connecting buses available</div>`;
  }

  // Google Maps 1-Tap Deep Link
  walkingNavBtn.onclick = () => {
    const navUrl = `https://www.google.com/maps/dir/?api=1&origin=${appState.origin.lat},${appState.origin.lon}&destination=${primary.lat},${primary.lon}&travelmode=walking`;
    window.open(navUrl, "_blank");

    navToastMsg.textContent = `Walking navigation active: Head towards ${primary.stop_name}`;
    navToast.classList.add("active");
    setTimeout(() => navToast.classList.remove("active"), 4000);
  };

  // Multi-Transfer Section
  if (!primary.is_direct && primary.transfer_stop_name) {
    transferBox.style.display = "block";
    const l1 = (primary.leg1_routes || []).map((r) => r.route).slice(0, 2).join(", ");
    const l2 = (primary.leg2_routes || []).map((r) => r.route).slice(0, 2).join(", ");

    transferRow.innerHTML = `
      <div class="transfer-leg">
        <span style="font-weight:700;color:#0a246a;">Leg 1: Bus ${l1 || 'Primary'}</span>
        <span class="leg-sub">Board at ${primary.stop_name}</span>
      </div>
      <span class="transfer-arrow">➔</span>
      <div class="transfer-leg">
        <span style="font-weight:700;color:#127533;">${primary.transfer_stop_name}</span>
        <span class="leg-sub">🚶 Transfer at platform</span>
      </div>
      <span class="transfer-arrow">➔</span>
      <div class="transfer-leg">
        <span style="font-weight:700;color:#8b5cf6;">Leg 2: Bus ${l2 || 'Connecting'}</span>
        <span class="leg-sub">Direct to ${appState.destination.name}</span>
      </div>
    `;
  } else {
    transferBox.style.display = "none";
  }

  // Alternatives Drawer
  if (alternatives && alternatives.length > 0) {
    alternativesDrawer.style.display = "block";
    altHeading.textContent = `Alternative Boarding Stops (${alternatives.length} other viable options)`;
    altDrawerContent.innerHTML = alternatives
      .map(
        (alt, idx) => `
      <div class="alt-stop-row" data-idx="${idx}">
        <div class="alt-stop-info">
          <span class="alt-stop-name">${alt.stop_name}</span>
          <span class="alt-stop-metrics">${alt.walk_distance_m} m walk (~${alt.walk_duration_min} min) • Score ${Math.round(alt.score)} pts</span>
        </div>
        <div class="alt-routes-badges">
          ${(alt.routes || alt.leg1_routes || [])
            .slice(0, 2)
            .map((r) => `<span class="alt-pill">${r.route}</span>`)
            .join("")}
        </div>
      </div>
    `
      )
      .join("");

    // Clicking an alternative swaps it
    altDrawerContent.querySelectorAll(".alt-stop-row").forEach((row) => {
      row.addEventListener("click", () => {
        const idx = parseInt(row.getAttribute("data-idx"));
        const chosenAlt = alternatives[idx];
        if (chosenAlt) {
          renderRecommendation(chosenAlt, []);
          initOrUpdateMap(appState.origin.lat, appState.origin.lon, chosenAlt.lat, chosenAlt.lon, chosenAlt.stop_name);
        }
      });
    });
  } else {
    alternativesDrawer.style.display = "none";
  }

  // Update Leaflet Map
  initOrUpdateMap(appState.origin.lat, appState.origin.lon, primary.lat, primary.lon, primary.stop_name);
}

// Alternatives Accordion Toggle
altDrawerTrigger.addEventListener("click", () => {
  const isHidden = altDrawerContent.style.display === "none";
  altDrawerContent.style.display = isHidden ? "flex" : "none";
  altChevron.classList.toggle("rotated", isHidden);
});

// ==========================================
// 6. Real-Time BMTC VTMS Satellite Telemetry
// ==========================================
function startLiveTelemetryPolling(candidate) {
  clearInterval(appState.telemetryTimer);

  const routes = (candidate.routes || candidate.leg1_routes || [])
    .map((r) => r.route)
    .filter(Boolean);

  if (routes.length === 0) return;

  fetchLiveTelemetry(routes.join(","), candidate);

  // Poll every 25 seconds
  appState.telemetryTimer = setInterval(() => {
    fetchLiveTelemetry(routes.join(","), candidate);
  }, 25000);
}

async function fetchLiveTelemetry(routesQuery, candidate) {
  try {
    const params = new URLSearchParams({
      route: routesQuery,
      orig_lat: candidate.lat,
      orig_lon: candidate.lon,
      dest_lat: appState.destination.lat,
      dest_lon: appState.destination.lon,
    });

    const res = await fetch(`/api/live-bus?${params.toString()}`);
    if (!res.ok) return;
    const data = await res.json();

    if (data.live && data.all_active_buses && data.all_active_buses.length > 0) {
      const activeCount = data.all_active_buses.length;
      const nearest = data.nearest_bus;

      vtmsStatusTitle.textContent = `LIVE VTMS: ${activeCount} BUSES ACTIVE ON CORRIDOR`;
      if (nearest) {
        radarEtaPill.innerHTML = `<span>⚡ ETA ${nearest.eta_mins} MINS</span>`;
        // Plot nearest moving bus on map
        initOrUpdateMap(
          appState.origin.lat,
          appState.origin.lon,
          candidate.lat,
          candidate.lon,
          candidate.stop_name,
          {
            lat: nearest.lat,
            lon: nearest.lon,
            route: nearest.route_no || candidate.routes?.[0]?.route,
            vehicle_no: nearest.vehicle_no,
            eta_mins: nearest.eta_mins,
          }
        );
      } else {
        radarEtaPill.innerHTML = `<span>⚡ ${activeCount} ACTIVE</span>`;
      }
    } else {
      vtmsStatusTitle.textContent = "BMTC FLEET: TIMETABLE SCHEDULE ACTIVE";
      radarEtaPill.innerHTML = `<span>⚡ HIGH FREQUENCY</span>`;
    }
  } catch (e) {
    console.warn("VTMS telemetry poll error:", e);
  }
}

// ==========================================
// 7. Origin Override Modal Handlers
// ==========================================
changeOriginBtn.addEventListener("click", () => {
  originModal.style.display = "flex";
  modalOriginInput.value = appState.origin.name === "Your Live Location (GPS)" ? "" : appState.origin.name;
  modalOriginInput.focus();
});

modalCloseBtn.addEventListener("click", () => (originModal.style.display = "none"));
modalCancelBtn.addEventListener("click", () => (originModal.style.display = "none"));

document.querySelectorAll(".preset-chip").forEach((btn) => {
  btn.addEventListener("click", () => {
    const name = btn.textContent.trim();
    const lat = parseFloat(btn.getAttribute("data-lat"));
    const lon = parseFloat(btn.getAttribute("data-lon"));

    setFallbackOrigin(name, lat, lon);
    originModal.style.display = "none";

    if (appState.destination.lat && appState.destination.lon) {
      fetchRecommendation();
    }
  });
});

let modalDebounceTimer = null;
modalOriginInput.addEventListener("input", (e) => {
  const query = e.target.value.trim();
  clearTimeout(modalDebounceTimer);
  if (query.length < 2) {
    modalOriginSuggestions.style.display = "none";
    return;
  }

  modalDebounceTimer = setTimeout(async () => {
    try {
      const res = await fetch(`/api/stops/search?q=${encodeURIComponent(query)}`);
      if (!res.ok) return;
      const stops = await res.json();
      if (stops.length === 0) {
        modalOriginSuggestions.style.display = "none";
        return;
      }

      modalOriginSuggestions.innerHTML = stops
        .slice(0, 5)
        .map(
          (s) => `
        <div style="padding:6px 8px;border-bottom:1px solid #eee;cursor:pointer;font-size:12px;" data-name="${s.stop_name}" data-lat="${s.lat}" data-lon="${s.lon}">
          <b>${s.stop_name}</b> <span style="color:#666;font-size:11px;">(${s.stop_desc || 'BMTC Stop'})</span>
        </div>
      `
        )
        .join("");
      modalOriginSuggestions.style.display = "block";

      modalOriginSuggestions.querySelectorAll("div").forEach((item) => {
        item.addEventListener("click", () => {
          const name = item.getAttribute("data-name");
          const lat = parseFloat(item.getAttribute("data-lat"));
          const lon = parseFloat(item.getAttribute("data-lon"));

          setFallbackOrigin(name, lat, lon);
          originModal.style.display = "none";

          if (appState.destination.lat && appState.destination.lon) {
            fetchRecommendation();
          }
        });
      });
    } catch (err) {
      console.warn("Modal origin search error:", err);
    }
  }, 220);
});

modalSaveBtn.addEventListener("click", () => {
  const val = modalOriginInput.value.trim();
  if (val) {
    setFallbackOrigin(val, appState.origin.lat, appState.origin.lon);
  }
  originModal.style.display = "none";
  if (appState.destination.lat && appState.destination.lon) {
    fetchRecommendation();
  }
});

// Window Minimise / Close buttons (aesthetic micro-interactions)
document.querySelectorAll(".win-btn-close, .win-btn-min").forEach((btn) => {
  btn.addEventListener("click", () => {
    navToastMsg.textContent = "NammaBMTC Navigator is running in your browser.";
    navToast.classList.add("active");
    setTimeout(() => navToast.classList.remove("active"), 2500);
  });
});

// ==========================================
// 8. Initialization on Page Load
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
  loadRecentSearches();
  initGeolocation();
});
