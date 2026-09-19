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
  serviceFilter: "ALL",
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

// Return Journey Swap & Metro Intermodal Elements
const swapJourneyBtn = document.getElementById("swap-journey-btn");
const metroIntermodalCard = document.getElementById("metro-intermodal-card");
const metroSpeedBadge = document.getElementById("metro-speed-badge");
const metroLinePill = document.getElementById("metro-line-pill");
const metroRouteTitle = document.getElementById("metro-route-title");
const metroSavingsMins = document.getElementById("metro-savings-mins");
const metroRideTime = document.getElementById("metro-ride-time");
const metroStationsCount = document.getElementById("metro-stations-count");
const metroFareVal = document.getElementById("metro-fare-val");
const metroTotalTime = document.getElementById("metro-total-time");
const metroStepsList = document.getElementById("metro-steps-list");
const toggleMetroMapBtn = document.getElementById("toggle-metro-map-btn");

// AC vs Non-AC Service Filter & Fare Elements
const filterTabBtns = document.querySelectorAll(".filter-tab-btn");
const serviceFareBadge = document.getElementById("service-fare-badge");

let currentMetroOption = null;
let metroPolyline = null;
let metroMarkers = [];

// Live Bus Telemetry State & DOM Elements
let telemetryIntervalId = null;
let liveBusMarkers = [];
let showLiveBusesOnMap = false;
let currentTelemetryParams = null;
let latestTelemetryData = null;

const liveTelemetryBox = document.getElementById("live-bus-telemetry-box");
const telemetryStatusTitle = document.getElementById("telemetry-status-title");
const telemetryLastSync = document.getElementById("telemetry-last-sync");
const telemetryRefreshBtn = document.getElementById("telemetry-refresh-btn");
const nearestBusBanner = document.getElementById("nearest-bus-banner");
const approachingBusesList = document.getElementById("approaching-buses-list");
const toggleBusMapBtn = document.getElementById("toggle-bus-map-btn");

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

// ================= Enhanced Autocomplete & Recent Searches =================
const RECENT_SEARCHES_KEY = "bmtc_recent_destinations";
const recentTray = document.getElementById("recent-searches-tray");
const recentChipsList = document.getElementById("recent-chips-list");
const clearRecentBtn = document.getElementById("clear-recent-btn");

function getRecentSearches() {
  try {
    const raw = localStorage.getItem(RECENT_SEARCHES_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function saveRecentSearch(item) {
  if (!item || !item.name) return;
  try {
    let recents = getRecentSearches();
    recents = recents.filter((r) => r.name.toLowerCase() !== item.name.toLowerCase());
    recents.unshift({
      name: item.name,
      lat: item.lat,
      lon: item.lon,
      desc: item.desc || "",
    });
    recents = recents.slice(0, 5);
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(recents));
    renderRecentSearches();
  } catch (e) {
    console.warn("Failed to persist recent search:", e);
  }
}

function renderRecentSearches() {
  if (!recentTray || !recentChipsList) return;
  const recents = getRecentSearches();
  if (recents.length === 0) {
    recentTray.classList.add("hidden");
    recentChipsList.innerHTML = "";
    return;
  }

  recentTray.classList.remove("hidden");
  recentChipsList.innerHTML = recents
    .map(
      (r) => `
      <button class="recent-chip" type="button" data-name="${r.name}" data-lat="${r.lat}" data-lon="${r.lon}">
        <span class="chip-icon">🕒</span>
        <span class="chip-name">${r.name}</span>
      </button>
    `
    )
    .join("");

  recentChipsList.querySelectorAll(".recent-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const name = chip.dataset.name;
      const lat = parseFloat(chip.dataset.lat);
      const lon = parseFloat(chip.dataset.lon);
      setDestination(name, lat, lon);
      triggerRecommendation();
    });
  });
}

if (clearRecentBtn) {
  clearRecentBtn.addEventListener("click", () => {
    try {
      localStorage.removeItem(RECENT_SEARCHES_KEY);
    } catch (e) {}
    renderRecentSearches();
  });
}

// Global Keyboard Shortcut: Press '/' or 'Ctrl+K' to focus search
document.addEventListener("keydown", (e) => {
  if (
    (e.key === "/" && document.activeElement !== destSearchInput && document.activeElement !== originSearchInput) ||
    ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k")
  ) {
    e.preventDefault();
    destSearchInput.focus();
    destSearchInput.select();
  }
});

let debounceTimer = null;
function setupAutocomplete(inputEl, dropdownEl, onSelect) {
  let activeIndex = -1;

  function closeDropdown() {
    dropdownEl.innerHTML = "";
    dropdownEl.classList.add("hidden");
    activeIndex = -1;
    if (dropdownEl === destSuggestions) {
      document.querySelector(".search-section")?.classList.remove("is-searching");
    }
  }

  // Keyboard navigation inside input (ArrowDown, ArrowUp, Enter, Escape)
  inputEl.addEventListener("keydown", (e) => {
    const items = dropdownEl.querySelectorAll(".suggestion-item");
    if (!items || items.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % items.length;
      updateActiveItem(items, activeIndex);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex = (activeIndex - 1 + items.length) % items.length;
      updateActiveItem(items, activeIndex);
    } else if (e.key === "Enter" && activeIndex >= 0 && items[activeIndex]) {
      e.preventDefault();
      items[activeIndex].click();
    } else if (e.key === "Escape") {
      closeDropdown();
    }
  });

  inputEl.addEventListener("input", () => {
    const q = inputEl.value.trim();
    if (q.length < 2) {
      closeDropdown();
      return;
    }

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      try {
        const uLat = state.origin.lat || "";
        const uLon = state.origin.lon || "";
        const url = `/api/stops/search?q=${encodeURIComponent(q)}&user_lat=${uLat}&user_lon=${uLon}`;
        const res = await fetch(url);
        const stops = await res.json();
        activeIndex = -1;
        renderDropdown(stops, dropdownEl, (item) => {
          onSelect(item);
          closeDropdown();
        });
      } catch (e) {
        console.error("Search failed:", e);
      }
    }, 120);
  });

  // Close on outside click
  document.addEventListener("click", (e) => {
    if (!inputEl.contains(e.target) && !dropdownEl.contains(e.target)) {
      closeDropdown();
    }
  });
}

function updateActiveItem(items, index) {
  items.forEach((item, idx) => {
    if (idx === index) {
      item.classList.add("active");
      item.scrollIntoView({ block: "nearest" });
    } else {
      item.classList.remove("active");
    }
  });
}

function renderDropdown(items, dropdownEl, onSelect) {
  if (dropdownEl === destSuggestions) {
    document.querySelector(".search-section")?.classList.add("is-searching");
  }

  if (!items || items.length === 0) {
    dropdownEl.innerHTML = `
      <div class="suggestion-empty">
        <span class="empty-icon">🔍</span>
        <span>No matching BMTC stops found. Try typing a landmark or area (e.g. Majestic, Silk Board, ITPL).</span>
      </div>
    `;
    dropdownEl.classList.remove("hidden");
    return;
  }

  dropdownEl.innerHTML = items
    .map(
      (s) => `
      <div class="suggestion-item" data-id="${s.stop_id}" data-name="${s.stop_name}" data-desc="${s.stop_desc}" data-lat="${s.lat}" data-lon="${s.lon}">
        <div class="sugg-left">
          <span class="sugg-pin-icon">🚏</span>
          <div class="sugg-meta">
            <div class="sugg-name">${s.stop_name}</div>
            <div class="sugg-desc">${s.stop_desc || "BMTC Boarding Node"}</div>
          </div>
        </div>
        ${s.dist_km != null ? `<span class="sugg-dist-tag">${s.dist_km} km</span>` : ""}
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
  saveRecentSearch(stop);
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
  destSuggestions.classList.add("hidden");
  document.querySelector(".search-section")?.classList.remove("is-searching");
  resultView.classList.remove("is-visible");
  resultView.classList.add("hidden");
  if (liveWatchId !== null && navigator.geolocation) {
    navigator.geolocation.clearWatch(liveWatchId);
    liveWatchId = null;
  }
  stopLiveBusTelemetry();
  destSearchInput.focus();
});

// Render recent searches on startup
renderRecentSearches();

// Close dropdowns on outside click
document.addEventListener("click", (e) => {
  if (!e.target.closest(".destination-search-card")) {
    destSuggestions.classList.add("hidden");
    document.querySelector(".search-section")?.classList.remove("is-searching");
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

// Commute Breakdown & En-Route Milestones DOM Elements
const commuteBreakdownCard = document.getElementById("commute-breakdown-card");
const commuteTotalMins = document.getElementById("commute-total-mins");
const breakdownWalkChip = document.getElementById("breakdown-walk-chip");
const breakdownWaitChip = document.getElementById("breakdown-wait-chip");
const breakdownRideChip = document.getElementById("breakdown-ride-chip");
const breakdownShaktiPill = document.getElementById("breakdown-shakti-pill");
const breakdownPassPill = document.getElementById("breakdown-pass-pill");
const enrouteMilestonesBox = document.getElementById("enroute-milestones-box");
const milestonesPillsList = document.getElementById("milestones-pills-list");

// Handle Enter key in destination input
destSearchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    destSuggestions.classList.add("hidden");
    triggerRecommendation();
  }
});

// ================= Return Journey Swap Handler =================
if (swapJourneyBtn) {
  swapJourneyBtn.addEventListener("click", async () => {
    if (!state.origin.lat) {
      showStatus("Acquiring your location first...", "info");
      return;
    }
    
    // Resolve destination if user typed it
    let targetDestName = state.destination.name;
    let targetDestLat = state.destination.lat;
    let targetDestLon = state.destination.lon;

    if (!targetDestLat || !targetDestLon) {
      const typed = destSearchInput.value.trim();
      if (typed.length >= 2) {
        try {
          const res = await fetch(`/api/stops/search?q=${encodeURIComponent(typed)}`);
          const items = await res.json();
          if (items && items.length > 0) {
            targetDestName = items[0].stop_name;
            targetDestLat = items[0].lat;
            targetDestLon = items[0].lon;
          }
        } catch (e) {}
      }
    }

    if (!targetDestLat || !targetDestLon) {
      showStatus("Please pick or type a valid destination to swap.", "info");
      destSearchInput.focus();
      return;
    }

    // Perform the swap
    const oldOrigName = state.origin.name;
    const oldOrigLat = state.origin.lat;
    const oldOrigLon = state.origin.lon;

    state.origin.name = targetDestName;
    state.origin.lat = targetDestLat;
    state.origin.lon = targetDestLon;
    state.origin.isLive = false;

    state.destination.name = oldOrigName;
    state.destination.lat = oldOrigLat;
    state.destination.lon = oldOrigLon;

    currentLocDisplay.textContent = state.origin.name;
    destSearchInput.value = state.destination.name;
    clearDestBtn.classList.remove("hidden");
    gpsStatusPill.classList.remove("active");
    gpsStatusText.textContent = "Custom Origin";

    showStatus(`Swapped: ${state.origin.name} ➔ ${state.destination.name}`, "info");
    triggerRecommendation();
  });
}

// ================= AC vs Non-AC Bus Service Filter =================
filterTabBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    filterTabBtns.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.serviceFilter = btn.dataset.filter || "ALL";

    // Auto-refresh recommendation if user has a destination set
    if (state.destination.lat && state.destination.lon) {
      triggerRecommendation();
    }
  });
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
        showStatus("Please enter your destination bus stop or area.", "error");
        destSearchInput.focus();
        return;
      }
    } else {
      showStatus("Please enter your destination bus stop or area.", "error");
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
      service_filter: state.serviceFilter || "ALL",
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

// Helper to format consistent route rows with AC status, fare tags, Shakti scheme, and milestones
function formatRouteRow(r, customBg = null) {
  const isAc = r.is_ac || (r.service_type && r.service_type !== "ORDINARY");
  const prefix = isAc ? (r.route.startsWith("KIA") ? "✈️ " : "❄️ ") : "";
  const bgStyle = customBg ? `style="background-color: ${customBg};"` : (isAc ? 'style="background: linear-gradient(180deg, #0284C7 0%, #0369A1 100%);"' : '');
  const fareTag = r.fare_text ? `<span class="route-fare-tag ${isAc ? 'is-ac' : ''}">${r.fare_text}</span>` : '';
  const shaktiTag = r.shakti_eligible ? `<span class="route-shakti-tag" title="Shakti Scheme: Free travel for Karnataka women">🌸 Shakti</span>` : '';
  const milestonesHtml = (r.enroute_milestones && r.enroute_milestones.length > 0)
    ? `<div class="route-enroute-milestones"><span class="milestone-pin">🚏</span> Passes: ${r.enroute_milestones.join(" ➔ ")}</div>`
    : '';

  return `
    <div class="route-row">
      <div class="route-row-main">
        <div class="route-ident">
          <span class="route-pill ${isAc ? 'is-ac' : ''}" ${bgStyle}>${prefix}${r.route}</span>
          <span class="route-headsign">Towards ${r.towards}</span>
        </div>
        <div class="route-meta-group" style="display:flex; align-items:center; gap:6px;">
          ${shaktiTag}
          ${fareTag}
          <span class="route-frequency">${r.trips_per_day} buses/day</span>
        </div>
      </div>
      ${milestonesHtml}
    </div>
  `;
}

// ================= Render Journey Stepper & Map =================
function renderJourney(data) {
  skeletonView.classList.add("hidden");
  const p = data.primary;
  currentPrimaryStop = p;

  // Clear any existing metro map overlay
  if (mapInstance && metroPolyline) {
    mapInstance.removeLayer(metroPolyline);
    metroMarkers.forEach((m) => mapInstance.removeLayer(m));
    metroPolyline = null;
    metroMarkers = [];
    if (toggleMetroMapBtn) toggleMetroMapBtn.innerHTML = "<span>🗺️ Highlight Metro Track on Map</span>";
  }

  // Render Namma Metro Intermodal Option
  renderMetroIntermodalCard(data.metro_option);

  // Origin step
  journeyOriginTitle.textContent = state.origin.name || "Your Current Location";

  // Walk Directive
  const walkStr = `Walk ${p.walk_distance_m} m (~${p.walk_duration_min} min)`;
  timelineWalkText.textContent = walkStr;
  liveDistanceCountdown.textContent = walkStr;
  arrivalStatusPill.classList.add("hidden");

  // Update Interactive 3D Directional Compass
  update3DCompass(state.origin.lat, state.origin.lon, p.lat, p.lon);

  // Boarding Stop
  recStopName.textContent = p.stop_name;
  if (p.stop_desc) {
    recStopDesc.innerHTML = `<span class="dir-icon">📍</span> <span class="dir-text">${p.stop_desc}</span>`;
    recStopDesc.classList.remove("hidden");
  } else {
    recStopDesc.classList.add("hidden");
  }

  // Service Category & Fare Indicator Badge
  if (serviceFareBadge) {
    if (p.has_ac && !p.has_non_ac) {
      serviceFareBadge.className = "service-fare-badge ac";
      serviceFareBadge.innerHTML = `❄️ Est. ${p.fare_range_str} • AC Vajra`;
    } else if (p.has_ac && p.has_non_ac) {
      serviceFareBadge.className = "service-fare-badge";
      serviceFareBadge.innerHTML = `🪙 Est. ${p.fare_range_str} • Mixed`;
    } else {
      serviceFareBadge.className = "service-fare-badge";
      serviceFareBadge.innerHTML = `🪙 Est. ${p.fare_range_str || "₹15 - ₹25"} • Non-AC`;
    }
  }

  // Render Commute Duration & Travel Breakdown Strip
  const jb = p.journey_breakdown;
  if (jb && commuteTotalMins) {
    commuteTotalMins.textContent = `~${jb.total_journey_min} min`;
    if (breakdownWalkChip) breakdownWalkChip.textContent = `🚶 ${jb.walk_time_min}m walk`;
    if (breakdownWaitChip) breakdownWaitChip.textContent = `⏳ ~${jb.wait_headway_min}m wait`;
    if (breakdownRideChip) breakdownRideChip.textContent = `🚍 ~${jb.ride_time_min}m ride`;

    if (breakdownShaktiPill) {
      if (jb.shakti_scheme_eligible) {
        breakdownShaktiPill.classList.remove("hidden");
        breakdownShaktiPill.innerHTML = `🌸 Shakti Scheme: Free for Women`;
      } else {
        breakdownShaktiPill.classList.add("hidden");
      }
    }
    if (breakdownPassPill) {
      breakdownPassPill.innerHTML = `🎫 ${jb.pass_info || "BMTC Daily Pass Valid"}`;
    }
  }

  // Render Key En-Route Waypoints / Milestones
  if (jb && jb.key_milestones && jb.key_milestones.length > 0 && milestonesPillsList && enrouteMilestonesBox) {
    enrouteMilestonesBox.classList.remove("hidden");
    milestonesPillsList.innerHTML = jb.key_milestones
      .map(
        (m, idx) => `
        <span class="milestone-chip">${m}</span>
        ${idx < jb.key_milestones.length - 1 ? '<span class="milestone-sep">➔</span>' : ''}
      `
      )
      .join("");
  } else if (enrouteMilestonesBox) {
    enrouteMilestonesBox.classList.add("hidden");
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
      .map((r) => formatRouteRow(r, "#B45309"))
      .join("");

    // 2nd Transfer Step
    transfer2StepBox.classList.remove("hidden");
    transfer2HubName.textContent = p.transfer2_stop_name;
    transfer2HubDesc.textContent = p.transfer2_stop_desc || "Change to Bus 3 towards destination";
    const leg3Routes = p.leg3_routes || [];
    recLeg3RoutesList.innerHTML = leg3Routes
      .slice(0, 4)
      .map((r) => formatRouteRow(r, "#C2410C"))
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
      .map((r) => formatRouteRow(r, "#B45309"))
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
    .map((r) => formatRouteRow(r))
    .join("");

  // Destination
  const destName = p.routes.length > 0 ? p.routes[0].destination_stop : state.destination.name;
  recDestStop.textContent = destName;

  // Trigger Real-Time Live Bus VTMS Telemetry Tracking with Multi-Route aggregation
  if (routesToDisplay && routesToDisplay.length > 0) {
    const candidateRoutes = [...new Set(routesToDisplay.map((r) => (r.route || "").trim()).filter(Boolean))].slice(0, 4);
    const routesParam = candidateRoutes.length > 0 ? candidateRoutes.join(",") : routesToDisplay[0].route;
    startLiveBusTelemetry(routesParam, p.lat, p.lon, state.destination.lat, state.destination.lon);
  } else {
    stopLiveBusTelemetry();
  }

  // Alternatives Accordion
  const alts = data.alternatives || [];
  if (alts.length > 0) {
    toggleAltsBtn.classList.remove("hidden");
    altsCountLabel.textContent = `Other Nearby Boarding Stops (${alts.length})`;

    alternativesContainer.innerHTML = alts
      .map((alt, i) => {
        const leg1Routes = (alt.leg1_routes && alt.leg1_routes.length > 0) ? alt.leg1_routes : (alt.routes || []);
        const tagClass = alt.transfers_count === 2 ? 'tag-two-transfer' : (alt.transfers_count === 1 ? 'tag-one-transfer' : 'tag-direct');
        let tagText = 'DIRECT BMTC BUS ROUTE';
        if (alt.transfers_count === 2) {
          tagText = `2 TRANSFERS • VIA ${(alt.transfer_stop_name || 'HUB 1').toUpperCase()} & ${(alt.transfer2_stop_name || 'HUB 2').toUpperCase()}`;
        } else if (alt.transfers_count === 1) {
          tagText = `1 TRANSFER • VIA ${(alt.transfer_stop_name || 'HUB').toUpperCase()}`;
        }

        const altMapsUrl = `https://www.google.com/maps/dir/?api=1&origin=${state.origin.lat},${state.origin.lon}&destination=${alt.lat},${alt.lon}&travelmode=walking`;

        return `
        <div class="alt-journey-card" data-idx="${i}">
          <div class="alt-card-header">
            <span class="alt-rank-tag">OPTION #${i + 2}</span>
            <div class="alt-walk-badge">
              <span>🚶</span>
              <span>Walk ${alt.walk_distance_m} m (~${alt.walk_duration_min} min)</span>
            </div>
          </div>

          <h4 class="alt-stop-name">${alt.stop_name}</h4>
          ${alt.stop_desc ? `
            <div class="alt-dir-callout">
              <span class="dir-icon">📍</span>
              <span class="dir-text">${alt.stop_desc}</span>
            </div>
          ` : ''}

          <div class="alt-service-tag ${tagClass}">${tagText} • ${alt.fare_range_str || "₹15 - ₹25"}</div>

          <!-- Leg 1 Routes -->
          <div class="alt-buses-section">
            <span class="box-caption">${alt.transfers_count > 0 ? 'LEG 1: CATCH ANY TO INTERCHANGE' : 'CATCH ANY OF THESE SERVICES'}</span>
            <div class="buses-list">
              ${leg1Routes.slice(0, 3).map(r => formatRouteRow(r)).join('')}
            </div>
          </div>

          <!-- Transfer Interchange Details (If Applicable) -->
          ${alt.transfers_count >= 1 ? `
            <div class="alt-transfer-summary">
              <div class="alt-transfer-step">
                <span class="hub-pill">⇄ Interchange 1</span>
                <span class="hub-title">${alt.transfer_stop_name}</span>
                ${(alt.leg2_routes && alt.leg2_routes.length > 0) ? `
                  <div class="alt-sub-routes">Connecting buses: ${alt.leg2_routes.slice(0, 3).map(r => `<b>${r.route}</b> (${r.trips_per_day}/day)`).join(', ')}</div>
                ` : ''}
              </div>
              ${alt.transfers_count === 2 ? `
                <div class="alt-transfer-step" style="margin-top: 8px; border-top: 1px dashed #FDE68A; padding-top: 6px;">
                  <span class="hub-pill" style="background-color: #FFEDD5; color: #C2410C;">⇄ Interchange 2</span>
                  <span class="hub-title" style="color: #9A3412;">${alt.transfer2_stop_name}</span>
                  ${(alt.leg3_routes && alt.leg3_routes.length > 0) ? `
                    <div class="alt-sub-routes" style="color: #7C2D12;">Final connecting buses: ${alt.leg3_routes.slice(0, 3).map(r => `<b>${r.route}</b> (${r.trips_per_day}/day)`).join(', ')}</div>
                  ` : ''}
                </div>
              ` : ''}
            </div>
          ` : ''}

          <!-- Action Buttons -->
          <div class="alt-action-row">
            <button class="select-alt-btn" type="button" data-idx="${i}">
              <span>🎯 Make This My Boarding Stop</span>
            </button>
            <a class="alt-maps-btn" href="${altMapsUrl}" target="_blank" rel="noopener" title="Open Google Maps Walking Navigation">
              <span>🧭 Walk GPS</span>
            </a>
          </div>
        </div>
      `;
      }).join("");

    // Wire switcher buttons
    alternativesContainer.querySelectorAll(".select-alt-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.dataset.idx, 10);
        if (!isNaN(idx) && data.alternatives && data.alternatives[idx]) {
          const selectedAlt = data.alternatives[idx];
          const oldPrimary = data.primary;
          data.primary = selectedAlt;
          data.alternatives[idx] = oldPrimary;
          renderJourney(data);
          resultView.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    });
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

// ================= Namma Metro (BMRCL) Intermodal Rendering =================
function renderMetroIntermodalCard(metro) {
  if (!metroIntermodalCard) return;

  if (!metro || !metro.available) {
    metroIntermodalCard.classList.add("hidden");
    currentMetroOption = null;
    return;
  }

  currentMetroOption = metro;
  metroIntermodalCard.classList.remove("hidden");

  // Speed Badge & Savings
  const savingsPill = document.getElementById("metro-time-savings-pill");
  if (metro.is_substantially_faster) {
    metroSpeedBadge.textContent = "⚡ FASTEST: NAMMA METRO HYBRID";
    metroSpeedBadge.className = "metro-speed-badge";
    if (metroSavingsMins) metroSavingsMins.textContent = `~${metro.time_saved_mins} min`;
    if (savingsPill) savingsPill.style.display = "flex";
  } else if (metro.is_faster) {
    metroSpeedBadge.textContent = "🚇 TRAFFIC-IMMUNE METRO ROUTE";
    metroSpeedBadge.className = "metro-speed-badge normal";
    if (metroSavingsMins) metroSavingsMins.textContent = `~${metro.time_saved_mins} min`;
    if (savingsPill) savingsPill.style.display = "flex";
  } else {
    metroSpeedBadge.textContent = "🚇 METRO TRANSIT ALTERNATIVE";
    metroSpeedBadge.className = "metro-speed-badge normal";
    if (savingsPill) savingsPill.style.display = "none";
  }

  // Line pill
  const lineName = metro.primary_line || "PURPLE";
  if (metroLinePill) {
    metroLinePill.textContent = `${lineName} LINE`;
    metroLinePill.style.backgroundColor = metro.primary_color || "#7C3AED";
  }
  metroIntermodalCard.style.borderColor = metro.primary_color || "#7C3AED";

  // Route Title
  if (metroRouteTitle) {
    if (metro.has_interchange) {
      const lines = (metro.lines_used || []).join(" + ");
      metroRouteTitle.textContent = `${metro.origin_station.name} ➔ ${metro.dest_station.name} (${lines} Line)`;
    } else {
      metroRouteTitle.textContent = `${metro.primary_line} Line: ${metro.origin_station.name} ➔ ${metro.dest_station.name}`;
    }
  }

  // Metrics
  if (metroRideTime) metroRideTime.textContent = `${metro.metro_ride_time_mins} min`;
  if (metroStationsCount) metroStationsCount.textContent = `${metro.total_stations} stops`;
  if (metroFareVal) metroFareVal.textContent = `₹${metro.fare}`;
  if (metroTotalTime) metroTotalTime.textContent = `${metro.total_travel_time_mins} min`;

  // Step-by-step itinerary list
  if (metroStepsList) {
    metroStepsList.innerHTML = (metro.steps || []).map((s) => {
      const isMetro = s.type === "metro";
      const isInterchange = s.type === "interchange";
      const itemClass = isMetro
        ? "metro-step-item is-metro-leg"
        : isInterchange
        ? "metro-step-item is-interchange"
        : "metro-step-item";

      return `
        <div class="${itemClass}">
          <span class="metro-step-icon">${s.icon || "📍"}</span>
          <div class="metro-step-body">
            <div class="metro-step-title">${s.title}</div>
            <div class="metro-step-desc">${s.subtitle || ""}</div>
          </div>
        </div>
      `;
    }).join("");
  }
}

function toggleMetroOnMap() {
  if (!mapInstance || !currentMetroOption || !currentMetroOption.polyline) return;

  if (metroPolyline) {
    // Hide Metro Track
    mapInstance.removeLayer(metroPolyline);
    metroMarkers.forEach((m) => mapInstance.removeLayer(m));
    metroPolyline = null;
    metroMarkers = [];
    if (toggleMetroMapBtn) {
      toggleMetroMapBtn.innerHTML = "<span>🗺️ Highlight Metro Track on Map</span>";
    }

    // Re-center on bus/walking route
    if (currentPrimaryStop && state.origin.lat) {
      mapInstance.fitBounds(
        [
          [state.origin.lat, state.origin.lon],
          [currentPrimaryStop.lat, currentPrimaryStop.lon],
        ],
        { padding: [35, 35], maxZoom: 17 }
      );
    }
  } else {
    // Show Metro Track
    metroPolyline = L.polyline(currentMetroOption.polyline, {
      color: currentMetroOption.primary_color || "#7C3AED",
      weight: 5,
      opacity: 0.95,
    }).addTo(mapInstance);

    const origStn = currentMetroOption.origin_station;
    const destStn = currentMetroOption.dest_station;

    const metroIconOrig = L.divIcon({
      className: "custom-metro-icon",
      html: `<div class="metro-marker-pin" style="background:${currentMetroOption.primary_color || "#7C3AED"}">🚇 ${origStn.name}</div>`,
      iconSize: [120, 24],
      iconAnchor: [60, 12],
    });
    const m1 = L.marker([origStn.lat, origStn.lon], { icon: metroIconOrig }).addTo(mapInstance);
    metroMarkers.push(m1);

    const metroIconDest = L.divIcon({
      className: "custom-metro-icon",
      html: `<div class="metro-marker-pin" style="background:${currentMetroOption.primary_color || "#7C3AED"}">🚇 ${destStn.name}</div>`,
      iconSize: [120, 24],
      iconAnchor: [60, 12],
    });
    const m2 = L.marker([destStn.lat, destStn.lon], { icon: metroIconDest }).addTo(mapInstance);
    metroMarkers.push(m2);

    mapInstance.fitBounds(currentMetroOption.polyline, { padding: [40, 40], maxZoom: 15 });
    if (toggleMetroMapBtn) {
      toggleMetroMapBtn.innerHTML = "<span>🗺️ Hide Metro Track</span>";
    }
  }
}

if (toggleMetroMapBtn) {
  toggleMetroMapBtn.addEventListener("click", toggleMetroOnMap);
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

// ================= Walking Direction Compass =================
function calculateBearing(lat1, lon1, lat2, lon2) {
  const toRad = (d) => (d * Math.PI) / 180;
  const toDeg = (r) => (r * 180) / Math.PI;
  const φ1 = toRad(lat1), φ2 = toRad(lat2);
  const Δλ = toRad(lon2 - lon1);
  const y = Math.sin(Δλ) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
  let θ = toDeg(Math.atan2(y, x));
  return (θ + 360) % 360;
}

function getCompassCardinal(deg) {
  const cardinals = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  const idx = Math.round(deg / 45) % 8;
  return cardinals[idx];
}

function update3DCompass(oLat, oLon, dLat, dLon) {
  const needle = document.getElementById("compass-needle");
  const label = document.getElementById("compass-bearing-label");
  if (!needle || !label) return;

  if (oLat && oLon && dLat && dLon) {
    const bearing = Math.round(calculateBearing(oLat, oLon, dLat, dLon));
    needle.style.transform = `rotate(${bearing}deg)`;
    const cardinal = getCompassCardinal(bearing);
    label.textContent = `${cardinal} ${bearing}°`;
  }
}

// ================= Real-Time Live Bus VTMS Telemetry =================
function startLiveBusTelemetry(routeNo, origLat, origLon, destLat, destLon) {
  stopLiveBusTelemetry();
  currentTelemetryParams = { routeNo, origLat, origLon, destLat, destLon };

  if (liveTelemetryBox) {
    liveTelemetryBox.classList.remove("is-offline");
  }
  if (nearestBusBanner) {
    nearestBusBanner.innerHTML = `
      <div class="telemetry-skeleton">
        <span class="pulse-live-dot"></span>
        <span>Polling real-time GPS satellite feed for Route ${routeNo.replace(/,/g, " / ")}...</span>
      </div>
    `;
  }
  if (telemetryStatusTitle) {
    telemetryStatusTitle.textContent = `LIVE BUS TRACKER • ROUTE ${routeNo.replace(/,/g, " / ")}`;
  }
  if (telemetryLastSync) {
    telemetryLastSync.textContent = "Connecting to BMTC VTMS...";
  }

  pollLiveBusTelemetry();
  telemetryIntervalId = setInterval(pollLiveBusTelemetry, 18000);
}

function stopLiveBusTelemetry() {
  if (telemetryIntervalId) {
    clearInterval(telemetryIntervalId);
    telemetryIntervalId = null;
  }
  clearLiveBusMarkers();
}

async function pollLiveBusTelemetry() {
  if (!currentTelemetryParams) return;
  const { routeNo, origLat, origLon, destLat, destLon } = currentTelemetryParams;

  if (telemetryRefreshBtn) {
    telemetryRefreshBtn.classList.add("spinning");
  }

  try {
    const url = `/api/live-bus?route=${encodeURIComponent(routeNo)}&orig_lat=${origLat}&orig_lon=${origLon}` +
      (destLat != null ? `&dest_lat=${destLat}&dest_lon=${destLon}` : "");

    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    latestTelemetryData = data;

    renderLiveBusTelemetry(data);
  } catch (err) {
    console.warn("Live telemetry poll failed:", err);
    if (telemetryLastSync) {
      telemetryLastSync.textContent = "Feed slow · Retrying";
    }
  } finally {
    if (telemetryRefreshBtn) {
      telemetryRefreshBtn.classList.remove("spinning");
    }
  }
}

function renderLiveBusTelemetry(data) {
  if (!liveTelemetryBox) return;

  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

  if (data.live && (data.approaching_count > 0 || data.active_buses_total > 0)) {
    liveTelemetryBox.classList.remove("is-offline");

    const routesListStr = data.routes_queried && data.routes_queried.length > 0 ? data.routes_queried.join(", ") : (data.route || "");
    if (telemetryStatusTitle) {
      telemetryStatusTitle.textContent = data.approaching_count > 0
        ? `LIVE BUS GPS RADAR • ${data.approaching_count} APPROACHING (${routesListStr})`
        : `LIVE FLEET RADAR • ${data.active_buses_total} BUSES ACTIVE (${routesListStr})`;
    }
    if (telemetryLastSync) {
      telemetryLastSync.textContent = `Synced ${timeStr}`;
    }

    // Render nearest bus
    if (data.nearest_bus) {
      const b = data.nearest_bus;
      const isAtStop = b.is_at_stop || b.dist_km <= 0.25;
      const etaLabel = isAtStop
        ? `<span class="arrived-badge">🟢 AT PLATFORM NOW</span>`
        : `<span class="eta-highlight">~${b.eta_mins} min</span> (${(b.dist_km * 1000).toFixed(0)}m away)`;

      let stopsLabel = "";
      if (b.is_terminal_inbound) {
        stopsLabel = `<span class="stops-count-badge" style="background: #0284C7; color: #fff;">Arriving at Terminal</span>`;
      } else if (b.stops_away !== undefined && b.stops_away > 0) {
        stopsLabel = `<span class="stops-count-badge">${b.stops_away} stop${b.stops_away > 1 ? "s" : ""} away</span>`;
      }

      nearestBusBanner.innerHTML = `
        <div class="nearest-bus-card-inner">
          <div class="nearest-bus-meta">
            <div class="nearest-bus-title-row">
              <span class="route-pill" style="font-size: 11px; padding: 2px 7px; margin-right: 4px;">${b.route || data.route}</span>
              <span class="vehicle-reg-badge">${b.vehicle}</span>
              <span class="vehicle-type-tag">${b.type || "BMTC Bus"}</span>
              ${stopsLabel}
            </div>
            <div class="nearest-bus-eta-row">
              <span>Next Arrival:</span>
              ${etaLabel}
            </div>
          </div>
          <div class="nearest-bus-icon">
            <span style="font-size: 26px;">🚍</span>
          </div>
        </div>
      `;
    } else {
      const fallbackBus = data.nearest_active_bus;
      nearestBusBanner.innerHTML = `
        <div class="nearest-bus-card-inner" style="border-left: 4px solid #0284C7;">
          <div class="nearest-bus-meta">
            <div class="nearest-bus-title-row">
              <span class="route-pill" style="background:#0284C7; color:#fff; font-size:11px; padding:2px 7px; margin-right:4px;">${fallbackBus ? (fallbackBus.route || data.route) : data.route}</span>
              <span class="vehicle-reg-badge">${fallbackBus ? fallbackBus.vehicle : "Fleet Active"}</span>
              <span class="vehicle-type-tag">${fallbackBus ? (fallbackBus.type || "In Service") : "Active Fleet"}</span>
            </div>
            <div class="nearest-bus-eta-row">
              <span>Active Corridor Fleet:</span>
              <span class="eta-highlight" style="color:#0284C7;">${data.active_buses_total} Buses in Transit</span>
              ${fallbackBus ? `<span>(${fallbackBus.dist_km} km away)</span>` : ""}
            </div>
            <div style="margin-top: 6px;">
              <button onclick="toggleShowLiveBusesOnMap()" style="font-size: 11.5px; font-weight: 700; color: #0284C7; background: rgba(2,132,199,0.08); border: 1px solid rgba(2,132,199,0.25); border-radius: 4px; padding: 4px 10px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;">
                🗺️ Show All ${data.active_buses_total} Buses on Live Map
              </button>
            </div>
          </div>
          <div class="nearest-bus-icon">
            <span style="font-size: 26px;">🚍</span>
          </div>
        </div>
      `;
    }

    // Render other approaching buses
    if (data.approaching_buses && data.approaching_buses.length > 1) {
      approachingBusesList.classList.remove("hidden");
      approachingBusesList.innerHTML = data.approaching_buses
        .slice(1, 5)
        .map(
          (b) => `
          <div class="sub-bus-row">
            <div class="sub-bus-ident">
              <span style="color: #059669;">🚍</span>
              <span class="sub-route-tag" style="background: #ECFDF5; color: #065F46; font-size: 10px; font-weight: 800; padding: 1px 5px; border-radius: 3px; font-family: var(--font-mono);">${b.route || ""}</span>
              <span class="sub-reg">${b.vehicle}</span>
              <span class="vehicle-type-tag" style="font-size: 9.5px; padding: 1px 4px;">${b.type}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="sub-eta">~${b.eta_mins}m</span>
              <span class="sub-dist">${b.dist_km} km</span>
            </div>
          </div>
        `
        )
        .join("");
    } else {
      approachingBusesList.classList.add("hidden");
      approachingBusesList.innerHTML = "";
    }

    // Update markers on Leaflet map
    updateLiveBusMapMarkers(data.approaching_buses || [], data.all_active_buses || []);

  } else {
    // Graceful offline fallback
    liveTelemetryBox.classList.add("is-offline");
    if (telemetryStatusTitle) {
      telemetryStatusTitle.textContent = `SCHEDULED SERVICE ACTIVE • ROUTE ${data.route || ""}`;
    }
    if (telemetryLastSync) {
      telemetryLastSync.textContent = "GTFS Timetable";
    }
    nearestBusBanner.innerHTML = `
      <div class="telemetry-offline-card">
        <span>📡</span>
        <span><b>Official GTFS Frequency:</b> Regular high-frequency service. Live GPS satellite telemetry is currently quiet for this line. Next trip running per timetable.</span>
      </div>
    `;
    approachingBusesList.classList.add("hidden");
    clearLiveBusMarkers();
  }
}

function clearLiveBusMarkers() {
  if (mapInstance && liveBusMarkers.length > 0) {
    liveBusMarkers.forEach((m) => mapInstance.removeLayer(m));
    liveBusMarkers = [];
  }
}

function updateLiveBusMapMarkers(approachingBuses, allBuses) {
  if (!mapInstance || typeof L === "undefined") return;

  clearLiveBusMarkers();

  const hasApproaching = approachingBuses && approachingBuses.length > 0;
  const hasAll = allBuses && allBuses.length > 0;

  let busesToPlot = [];
  if (showLiveBusesOnMap) {
    busesToPlot = hasAll ? allBuses : (hasApproaching ? approachingBuses : []);
  } else {
    busesToPlot = hasApproaching ? approachingBuses : (hasAll ? allBuses : []);
  }

  const mapBusCountEl = document.getElementById("map-bus-count");
  if (mapBusCountEl) {
    const totalCount = hasAll ? allBuses.length : (hasApproaching ? approachingBuses.length : 0);
    mapBusCountEl.textContent = totalCount;
  }

  if (!busesToPlot || busesToPlot.length === 0) return;

  busesToPlot.forEach((b, idx) => {
    if (!b.lat || !b.lon) return;

    const isNearest = (hasApproaching && b.vehicle === approachingBuses[0].vehicle) || idx === 0;
    const etaText = b.eta_mins ? `~${b.eta_mins}m` : "";
    const routeTag = b.route ? `<span style="background: rgba(0,0,0,0.25); padding: 1px 4px; border-radius: 3px; margin-right: 3px; font-weight: 800;">${b.route}</span>` : "";

    const markerHtml = `
      <div class="bus-marker-pin ${isNearest ? 'is-nearest' : ''}">
        <span style="font-size: 12px;">🚍</span>
        ${routeTag}
        <span style="font-family: var(--font-mono); font-weight: 800;">${b.vehicle}</span>
        ${etaText ? `<span style="font-size: 10px; background: rgba(0,0,0,0.3); padding: 1px 4px; border-radius: 3px;">${etaText}</span>` : ""}
      </div>
    `;

    const icon = L.divIcon({
      className: "custom-bus-marker",
      html: markerHtml,
      iconSize: [120, 26],
      iconAnchor: [60, 13],
    });

    const marker = L.marker([b.lat, b.lon], { icon, zIndexOffset: isNearest ? 1000 : 500 }).addTo(mapInstance);
    marker.bindPopup(`
      <div style="font-family: var(--font-sans); font-size: 12px; line-height: 1.4; padding: 2px;">
        <div style="font-weight: 800; color: #065F46; font-size: 13px; font-family: var(--font-mono);">
          🚍 BMTC ${b.route ? `Route ${b.route} • ` : ""}${b.vehicle}
        </div>
        <div style="margin-top: 3px;"><b>Service:</b> ${b.type || "Ordinary"}</div>
        <div><b>Distance to stop:</b> ${b.dist_km} km</div>
        <div><b>Live Arrival:</b> <span style="font-weight: 800; color: #059669;">~${b.eta_mins} min</span></div>
        ${b.is_terminal_inbound ? '<div style="color: #0284C7; font-size: 11px; font-weight: 600; margin-top: 2px;">🔄 Inbound / Turnaround at terminal</div>' : ''}
        ${b.last_updated ? `<div style="color: #64748B; font-size: 10.5px; margin-top: 4px;">🛰️ Satellite Sync: ${b.last_updated}</div>` : ""}
      </div>
    `);

    liveBusMarkers.push(marker);
  });

  if (showLiveBusesOnMap && liveBusMarkers.length > 0 && userMarker && stopMarker) {
    const group = new L.featureGroup([userMarker, stopMarker, ...liveBusMarkers]);
    mapInstance.fitBounds(group.getBounds(), { padding: [45, 45], maxZoom: 15 });
  }
}

function toggleShowLiveBusesOnMap() {
  showLiveBusesOnMap = !showLiveBusesOnMap;

  if (toggleBusMapBtn) {
    toggleBusMapBtn.classList.toggle("active", showLiveBusesOnMap);
    toggleBusMapBtn.querySelector("span").textContent = showLiveBusesOnMap
      ? "🗺️ Focus on Walking Route"
      : "🚍 Show Live Buses on Map";
  }

  const mapBusQuickBtn = document.getElementById("map-live-buses-btn");
  if (mapBusQuickBtn) {
    mapBusQuickBtn.classList.toggle("active", showLiveBusesOnMap);
  }

  const mapContainer = document.getElementById("walking-map-container");
  if (mapContainer) {
    if (showLiveBusesOnMap) {
      mapContainer.classList.add("expanded");
    } else {
      mapContainer.classList.remove("expanded");
    }
  }

  setTimeout(() => {
    if (mapInstance) {
      mapInstance.invalidateSize();
    }
  }, 150);

  if (latestTelemetryData) {
    updateLiveBusMapMarkers(
      latestTelemetryData.approaching_buses || [],
      latestTelemetryData.all_active_buses || []
    );
  } else if (currentTelemetryParams) {
    pollLiveBusTelemetry();
  }

  if (showLiveBusesOnMap) {
    if (mapContainer) {
      mapContainer.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    setTimeout(() => {
      if (mapInstance && liveBusMarkers.length > 0 && userMarker && stopMarker) {
        const group = new L.featureGroup([userMarker, stopMarker, ...liveBusMarkers]);
        mapInstance.fitBounds(group.getBounds(), { padding: [45, 45], maxZoom: 15 });
        if (liveBusMarkers[0]) {
          liveBusMarkers[0].openPopup();
        }
      }
    }, 250);
  } else {
    if (mapInstance && userMarker && stopMarker) {
      const group = new L.featureGroup([userMarker, stopMarker]);
      mapInstance.fitBounds(group.getBounds(), { padding: [35, 35], maxZoom: 17 });
    }
  }
}

// Wire Telemetry Controls
if (telemetryRefreshBtn) {
  telemetryRefreshBtn.addEventListener("click", () => {
    pollLiveBusTelemetry();
  });
}

if (toggleBusMapBtn) {
  toggleBusMapBtn.addEventListener("click", toggleShowLiveBusesOnMap);
}

const mapLiveBusesBtn = document.getElementById("map-live-buses-btn");
if (mapLiveBusesBtn) {
  mapLiveBusesBtn.addEventListener("click", toggleShowLiveBusesOnMap);
}
