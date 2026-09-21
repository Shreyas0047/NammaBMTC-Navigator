/**
 * NammaBMTC Navigator - 3D Exploded Transit Scrollytelling Engine
 * Powered by Three.js (Procedural PBR Model, zero external assets, ultra-fast load).
 * Visualizes the complete anatomy of a Bengaluru commute:
 * - Orbital VTMS Satellite Telemetry Layer
 * - AC Vajra & Climate-Comfort Roof Core
 * - Shakti Smart Ticket Deck & Chassis
 * - Subterranean Namma Metro & Arterial Highway Layer
 */

(function () {
  'use strict';

  // DOM Elements
  const container = document.getElementById('scrolly-canvas-container');
  if (!container) return;

  const canvas = document.getElementById('scrolly-3d-canvas');
  const scrubSlider = document.getElementById('explode-scrub-slider');
  const scrubValueText = document.getElementById('explode-scrub-val');
  const stepPills = document.querySelectorAll('.scrolly-step-pill');
  const showcaseSection = document.getElementById('showcase-section');
  const jumpToAppBtn = document.getElementById('jump-to-app-btn');
  const navJumpBtn = document.getElementById('nav-jump-app-btn');
  const navShowcaseBtn = document.getElementById('nav-showcase-btn');

  // Three.js Core Variables
  let scene, camera, renderer;
  let busRoot, layerSatellite, layerRoof, layerBody, layerInterior, layerChassis, layerMetro;
  let radarCone, solarPanelsLeft, solarPanelsRight;
  let leaderLines = [];
  let isUserInteracting = false;
  let targetRotationY = -0.45;
  let targetRotationX = 0.22;
  let currentRotationY = -0.45;
  let currentRotationX = 0.22;
  let lastMouseX = 0, lastMouseY = 0;
  let explodeTarget = 0.0;
  let explodeCurrent = 0.0;
  let isVisible = true;
  let animFrameId = null;

  // Materials & Colors
  const COLORS = {
    bmtcBlue: 0x0284C7,
    bmtcDeepBlue: 0x0369A1,
    bmtcTeal: 0x06B6D4,
    bmtcCyanGlow: 0x00D2FF,
    nammaGreen: 0x10B981,
    metroPurple: 0x8B5CF6,
    metalDark: 0x1E293B,
    metalLight: 0xCBD5E1,
    glassTint: 0x0F172A,
    roadDark: 0x0B0F19,
    solarGold: 0xF59E0B,
    ledAmber: 0xFBBF24,
  };

  function initThree() {
    // 1. Scene Setup
    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x080D1A, 0.022);

    // 2. Camera Setup
    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;
    camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 100);
    camera.position.set(13, 8, 14);
    camera.lookAt(0, 1.2, 0);

    // 3. Renderer Setup
    renderer = new THREE.WebGLRenderer({
      canvas: canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;

    // 4. Studio Lighting
    const ambientLight = new THREE.AmbientLight(0x94A3B8, 0.9);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xFFFFFF, 1.8);
    dirLight.position.set(15, 25, 12);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 50;
    dirLight.shadow.camera.left = -10;
    dirLight.shadow.camera.right = 10;
    dirLight.shadow.camera.top = 10;
    dirLight.shadow.camera.bottom = -10;
    dirLight.shadow.bias = -0.0005;
    scene.add(dirLight);

    // Cyan rim accent light
    const cyanRimLight = new THREE.DirectionalLight(0x00D2FF, 2.2);
    cyanRimLight.position.set(-12, 10, -10);
    scene.add(cyanRimLight);

    // Purple ground bounce light (representing Namma Metro underneath)
    const purpleBounceLight = new THREE.PointLight(0x8B5CF6, 1.6, 25);
    purpleBounceLight.position.set(0, -3, 0);
    scene.add(purpleBounceLight);

    // 5. Build Procedural 3D Bus & Transit Strata
    buildTransitScene();

    // 6. Event Listeners
    setupInteractions();

    // 7. Start Render Loop
    animate();
  }

  function buildTransitScene() {
    busRoot = new THREE.Group();
    scene.add(busRoot);

    // Layer 1: Subterranean Metro & Highway Ground
    layerMetro = createSubterraneanMetroLayer();
    busRoot.add(layerMetro);

    // Layer 2: Chassis & Wheels
    layerChassis = createChassisLayer();
    busRoot.add(layerChassis);

    // Layer 3: Passenger Deck & Shakti Ticketing
    layerInterior = createInteriorDeckLayer();
    busRoot.add(layerInterior);

    // Layer 4: Bus Aerodynamic Body & Glazing
    layerBody = createBodyShellLayer();
    busRoot.add(layerBody);

    // Layer 5: Roof Canopy & AC Vajra Climate Unit
    layerRoof = createRoofCanopyLayer();
    busRoot.add(layerRoof);

    // Layer 6: Orbital VTMS Satellite
    layerSatellite = createSatelliteTelemetryLayer();
    busRoot.add(layerSatellite);

    // Ground High-Tech Perspective Grid
    const gridHelper = new THREE.GridHelper(36, 36, 0x0284C7, 0x1E293B);
    gridHelper.position.y = -2.8;
    scene.add(gridHelper);
  }

  // ==================== LAYER CREATION FUNCTIONS ====================

  /** Layer 1: Subterranean Namma Metro Rails & Ground Highway */
  function createSubterraneanMetroLayer() {
    const group = new THREE.Group();

    // Road Surface
    const roadGeo = new THREE.BoxGeometry(16, 0.3, 7.5);
    const roadMat = new THREE.MeshStandardMaterial({
      color: COLORS.roadDark,
      roughness: 0.9,
      metalness: 0.1,
    });
    const road = new THREE.Mesh(roadGeo, roadMat);
    road.position.y = -0.15;
    road.receiveShadow = true;
    group.add(road);

    // White Lane Markings
    const laneGeo = new THREE.PlaneGeometry(1.6, 0.15);
    const laneMat = new THREE.MeshBasicMaterial({ color: 0xFFFFFF });
    for (let x = -6; x <= 6; x += 3.2) {
      const line = new THREE.Mesh(laneGeo, laneMat);
      line.rotation.x = -Math.PI / 2;
      line.position.set(x, 0.01, -0.6);
      group.add(line);
    }

    // Bus Lane Green / Cyan Tactile Strip
    const stripGeo = new THREE.BoxGeometry(16, 0.02, 0.25);
    const stripMat = new THREE.MeshBasicMaterial({ color: COLORS.bmtcCyanGlow });
    const strip = new THREE.Mesh(stripGeo, stripMat);
    strip.position.set(0, 0.02, 2.5);
    group.add(strip);

    // Boarding Platform Curb
    const curbGeo = new THREE.BoxGeometry(16, 0.35, 1.8);
    const curbMat = new THREE.MeshStandardMaterial({
      color: 0x334155,
      roughness: 0.8,
    });
    const curb = new THREE.Mesh(curbGeo, curbMat);
    curb.position.set(0, 0.15, 3.8);
    curb.receiveShadow = true;
    group.add(curb);

    // Subterranean Metro Cutaway Tunnel Bed
    const tunnelGeo = new THREE.BoxGeometry(18, 0.8, 4);
    const tunnelMat = new THREE.MeshStandardMaterial({
      color: 0x05070D,
      roughness: 0.95,
      metalness: 0.2,
    });
    const tunnel = new THREE.Mesh(tunnelGeo, tunnelMat);
    tunnel.position.set(0, -1.8, 0);
    group.add(tunnel);

    // Dual Metro Tracks (Purple Line & Green Line)
    const railMatPurple = new THREE.MeshStandardMaterial({ color: COLORS.metroPurple, roughness: 0.3, metalness: 0.8 });
    const railMatGreen = new THREE.MeshStandardMaterial({ color: COLORS.nammaGreen, roughness: 0.3, metalness: 0.8 });

    const railGeo = new THREE.CylinderGeometry(0.04, 0.04, 18, 8);
    // Purple Line Rails
    [-0.8, -0.3].forEach((z) => {
      const rail = new THREE.Mesh(railGeo, railMatPurple);
      rail.rotation.z = Math.PI / 2;
      rail.position.set(0, -1.35, z);
      group.add(rail);
    });
    // Green Line Rails
    [0.3, 0.8].forEach((z) => {
      const rail = new THREE.Mesh(railGeo, railMatGreen);
      rail.rotation.z = Math.PI / 2;
      rail.position.set(0, -1.35, z);
      group.add(rail);
    });

    // Metro Sleepers (Ties)
    const tieGeo = new THREE.BoxGeometry(0.12, 0.08, 2.2);
    const tieMat = new THREE.MeshStandardMaterial({ color: 0x1E293B, roughness: 0.9 });
    for (let x = -8; x <= 8; x += 0.9) {
      const tie = new THREE.Mesh(tieGeo, tieMat);
      tie.position.set(x, -1.42, 0);
      group.add(tie);
    }

    return group;
  }

  /** Layer 2: Chassis Frame & 6 Alloy Wheels */
  function createChassisLayer() {
    const group = new THREE.Group();

    // Steel Ladder Frame Beams
    const beamGeo = new THREE.BoxGeometry(8.2, 0.22, 0.2);
    const beamMat = new THREE.MeshStandardMaterial({ color: COLORS.metalDark, roughness: 0.5, metalness: 0.8 });

    [-0.9, 0.9].forEach((z) => {
      const beam = new THREE.Mesh(beamGeo, beamMat);
      beam.position.set(0, 0.45, z);
      beam.castShadow = true;
      group.add(beam);
    });

    // Cross members
    const crossGeo = new THREE.BoxGeometry(0.2, 0.18, 1.9);
    for (let x = -3.5; x <= 3.5; x += 1.4) {
      const cross = new THREE.Mesh(crossGeo, beamMat);
      cross.position.set(x, 0.45, 0);
      group.add(cross);
    }

    // Battery Pack / Engine Module
    const batGeo = new THREE.BoxGeometry(3.2, 0.35, 1.6);
    const batMat = new THREE.MeshStandardMaterial({ color: 0x0284C7, roughness: 0.4, metalness: 0.6 });
    const bat = new THREE.Mesh(batGeo, batMat);
    bat.position.set(0, 0.45, 0);
    group.add(bat);

    // 6 Wheels with Rims (2 Front, 4 Rear Dual)
    const wheelPositions = [
      [2.7, 0.42, 1.25],   // Front Right
      [2.7, 0.42, -1.25],  // Front Left
      [-2.4, 0.42, 1.28],  // Rear Right Outer
      [-2.4, 0.42, -1.28], // Rear Left Outer
      [-2.4, 0.42, 1.12],  // Rear Right Inner
      [-2.4, 0.42, -1.12], // Rear Left Inner
    ];

    const tireGeo = new THREE.CylinderGeometry(0.42, 0.42, 0.25, 20);
    const tireMat = new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.9, metalness: 0.1 });
    const rimGeo = new THREE.CylinderGeometry(0.24, 0.24, 0.26, 16);
    const rimMat = new THREE.MeshStandardMaterial({ color: COLORS.metalLight, roughness: 0.2, metalness: 0.9 });
    const capGeo = new THREE.CylinderGeometry(0.08, 0.08, 0.28, 12);
    const capMat = new THREE.MeshBasicMaterial({ color: COLORS.bmtcCyanGlow });

    wheelPositions.forEach(([wx, wy, wz]) => {
      const tire = new THREE.Mesh(tireGeo, tireMat);
      tire.rotation.x = Math.PI / 2;
      tire.position.set(wx, wy, wz);
      tire.castShadow = true;

      const rim = new THREE.Mesh(rimGeo, rimMat);
      tire.add(rim);

      const cap = new THREE.Mesh(capGeo, capMat);
      tire.add(cap);

      group.add(tire);
    });

    return group;
  }

  /** Layer 3: Passenger Deck, Seating & Shakti Concession Validator */
  function createInteriorDeckLayer() {
    const group = new THREE.Group();

    // Floor Plate
    const floorGeo = new THREE.BoxGeometry(8.6, 0.1, 2.4);
    const floorMat = new THREE.MeshStandardMaterial({ color: 0x1F2937, roughness: 0.8, metalness: 0.2 });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.position.set(0, 0.62, 0);
    floor.receiveShadow = true;
    group.add(floor);

    // Passenger Seats Rows (Blue & Green BMTC Seats)
    const seatGeo = new THREE.BoxGeometry(0.45, 0.45, 0.45);
    const seatMatGreen = new THREE.MeshStandardMaterial({ color: COLORS.nammaGreen, roughness: 0.7 });
    const seatMatBlue = new THREE.MeshStandardMaterial({ color: COLORS.bmtcBlue, roughness: 0.7 });

    for (let x = -3.2; x <= 2.2; x += 0.85) {
      // Left side seat
      const sLeft = new THREE.Mesh(seatGeo, (Math.abs(x) < 1) ? seatMatGreen : seatMatBlue);
      sLeft.position.set(x, 0.9, -0.85);
      sLeft.castShadow = true;
      group.add(sLeft);

      // Right side seat
      const sRight = new THREE.Mesh(seatGeo, seatMatBlue);
      sRight.position.set(x, 0.9, 0.85);
      sRight.castShadow = true;
      group.add(sRight);
    }

    // Driver Cab & Steering Console
    const consoleGeo = new THREE.BoxGeometry(0.6, 0.7, 0.8);
    const consoleMat = new THREE.MeshStandardMaterial({ color: 0x0F172A, roughness: 0.5 });
    const consoleMesh = new THREE.Mesh(consoleGeo, consoleMat);
    consoleMesh.position.set(3.8, 0.98, -0.6);
    group.add(consoleMesh);

    // Shakti Scheme Smart Validator Stand near Entrance Door
    const validatorStandGeo = new THREE.CylinderGeometry(0.04, 0.04, 1.1, 8);
    const standMat = new THREE.MeshStandardMaterial({ color: COLORS.metalLight, metalness: 0.9 });
    const stand = new THREE.Mesh(validatorStandGeo, standMat);
    stand.position.set(2.4, 1.18, 1.05);
    group.add(stand);

    const validatorHeadGeo = new THREE.BoxGeometry(0.18, 0.26, 0.12);
    const validatorMat = new THREE.MeshBasicMaterial({ color: COLORS.nammaGreen });
    const valHead = new THREE.Mesh(validatorHeadGeo, validatorMat);
    valHead.position.set(2.4, 1.7, 1.05);
    group.add(valHead);

    // Stainless Steel Stanchion Handrails
    const railMat = new THREE.MeshStandardMaterial({ color: 0xE2E8F0, metalness: 0.95, roughness: 0.1 });
    const vertRailGeo = new THREE.CylinderGeometry(0.025, 0.025, 1.8, 8);
    [-2, 0, 1.8].forEach((rx) => {
      const r = new THREE.Mesh(vertRailGeo, railMat);
      r.position.set(rx, 1.55, 0.35);
      group.add(r);
    });

    return group;
  }

  /** Layer 4: Bus Outer Body Shell, Livery & Panoramic Tinted Glazing */
  function createBodyShellLayer() {
    const group = new THREE.Group();

    // Lower Body Skirts (Bangalore Deep Blue & White Stripe)
    const lowerBodyGeo = new THREE.BoxGeometry(8.9, 0.8, 2.5);
    const bodyMat = new THREE.MeshStandardMaterial({
      color: COLORS.bmtcBlue,
      roughness: 0.25,
      metalness: 0.3,
    });
    const lowerBody = new THREE.Mesh(lowerBodyGeo, bodyMat);
    lowerBody.position.set(0, 1.05, 0);
    lowerBody.castShadow = true;
    group.add(lowerBody);

    // Teal Livery Accent Stripe
    const stripeGeo = new THREE.BoxGeometry(8.92, 0.12, 2.52);
    const stripeMat = new THREE.MeshBasicMaterial({ color: COLORS.bmtcCyanGlow });
    const stripe = new THREE.Mesh(stripeGeo, stripeMat);
    stripe.position.set(0, 1.35, 0);
    group.add(stripe);

    // Upper Window Pillars
    const pillarMat = new THREE.MeshStandardMaterial({ color: 0x0F172A, roughness: 0.4 });
    [-4.35, -2.6, -0.8, 1.0, 2.8, 4.35].forEach((px) => {
      const pGeo = new THREE.BoxGeometry(0.18, 1.1, 2.5);
      const p = new THREE.Mesh(pGeo, pillarMat);
      p.position.set(px, 1.95, 0);
      group.add(p);
    });

    // Panoramic Window Glazing (Tinted Glass)
    const glassMat = new THREE.MeshPhysicalMaterial({
      color: 0x0F2942,
      transparent: true,
      opacity: 0.48,
      roughness: 0.05,
      metalness: 0.1,
      transmission: 0.8,
      ior: 1.5,
    });

    // Side Windows Left & Right
    const sideGlassGeo = new THREE.BoxGeometry(8.5, 0.95, 0.05);
    [-1.24, 1.24].forEach((gz) => {
      const glass = new THREE.Mesh(sideGlassGeo, glassMat);
      glass.position.set(0, 1.95, gz);
      group.add(glass);
    });

    // Front Windshield
    const frontGlassGeo = new THREE.BoxGeometry(0.05, 1.1, 2.35);
    const frontGlass = new THREE.Mesh(frontGlassGeo, glassMat);
    frontGlass.position.set(4.42, 1.95, 0);
    frontGlass.rotation.z = -0.08;
    group.add(frontGlass);

    // Front Destination LED Route Display Board
    const ledBoardGeo = new THREE.BoxGeometry(0.08, 0.28, 1.6);
    const ledBoardMat = new THREE.MeshBasicMaterial({ color: COLORS.ledAmber });
    const ledBoard = new THREE.Mesh(ledBoardGeo, ledBoardMat);
    ledBoard.position.set(4.44, 2.45, 0);
    group.add(ledBoard);

    // Dual High-Intensity LED Headlights
    const lightMat = new THREE.MeshBasicMaterial({ color: 0xFFFFFF });
    const lightGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.05, 12);
    [-0.85, 0.85].forEach((lz) => {
      const hlight = new THREE.Mesh(lightGeo, lightMat);
      hlight.rotation.z = Math.PI / 2;
      hlight.position.set(4.46, 0.88, lz);
      group.add(hlight);
    });

    return group;
  }

  /** Layer 5: Roof Canopy & AC Vajra Climate Unit */
  function createRoofCanopyLayer() {
    const group = new THREE.Group();

    // Fiberglass Roof Panel
    const roofGeo = new THREE.BoxGeometry(9.0, 0.22, 2.52);
    const roofMat = new THREE.MeshStandardMaterial({
      color: 0xFFFFFF,
      roughness: 0.3,
      metalness: 0.1,
    });
    const roof = new THREE.Mesh(roofGeo, roofMat);
    roof.position.set(0, 2.6, 0);
    roof.castShadow = true;
    group.add(roof);

    // AC Vajra Climate Core Housing
    const acGeo = new THREE.BoxGeometry(2.4, 0.42, 1.7);
    const acMat = new THREE.MeshStandardMaterial({
      color: 0xE2E8F0,
      roughness: 0.4,
      metalness: 0.5,
    });
    const ac = new THREE.Mesh(acGeo, acMat);
    ac.position.set(-0.5, 2.88, 0);
    ac.castShadow = true;
    group.add(ac);

    // AC Dual Vents
    const ventMat = new THREE.MeshBasicMaterial({ color: 0x1E293B });
    const ventGeo = new THREE.CylinderGeometry(0.35, 0.35, 0.05, 16);
    [-0.5, 0.5].forEach((vx) => {
      const vent = new THREE.Mesh(ventGeo, ventMat);
      vent.position.set(-0.5 + vx, 3.1, 0);
      group.add(vent);
    });

    // Roof GPS Dome Transceiver
    const domeGeo = new THREE.SphereGeometry(0.14, 12, 12);
    const domeMat = new THREE.MeshStandardMaterial({ color: COLORS.bmtcCyanGlow, roughness: 0.2, metalness: 0.8 });
    const dome = new THREE.Mesh(domeGeo, domeMat);
    dome.position.set(2.8, 2.76, 0);
    group.add(dome);

    return group;
  }

  /** Layer 6: Orbital VTMS Satellite & Telemetry Radar Beam */
  function createSatelliteTelemetryLayer() {
    const group = new THREE.Group();

    // Satellite Core Chassis
    const satBodyGeo = new THREE.BoxGeometry(0.85, 0.85, 0.85);
    const satBodyMat = new THREE.MeshStandardMaterial({
      color: COLORS.solarGold,
      roughness: 0.25,
      metalness: 0.9,
    });
    const satBody = new THREE.Mesh(satBodyGeo, satBodyMat);
    satBody.position.set(2.8, 5.8, 0);
    satBody.castShadow = true;
    group.add(satBody);

    // Rotating Antenna Dish
    const dishGeo = new THREE.CylinderGeometry(0.45, 0.05, 0.15, 16);
    const dishMat = new THREE.MeshStandardMaterial({ color: COLORS.metalLight, metalness: 0.95 });
    const dish = new THREE.Mesh(dishGeo, dishMat);
    dish.position.set(2.8, 5.25, 0);
    dish.rotation.x = Math.PI;
    group.add(dish);

    // Solar Panel Arrays Left & Right
    const panelGeo = new THREE.BoxGeometry(1.6, 0.04, 0.85);
    const panelMat = new THREE.MeshStandardMaterial({
      color: 0x1E3A8A,
      roughness: 0.2,
      metalness: 0.8,
    });

    solarPanelsLeft = new THREE.Mesh(panelGeo, panelMat);
    solarPanelsLeft.position.set(2.8, 5.8, -1.45);
    group.add(solarPanelsLeft);

    solarPanelsRight = new THREE.Mesh(panelGeo, panelMat);
    solarPanelsRight.position.set(2.8, 5.8, 1.45);
    group.add(solarPanelsRight);

    // Telemetry Radar Pulse Cone
    const coneGeo = new THREE.ConeGeometry(1.9, 3.2, 24, 1, true);
    const coneMat = new THREE.MeshBasicMaterial({
      color: COLORS.bmtcCyanGlow,
      transparent: true,
      opacity: 0.28,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    radarCone = new THREE.Mesh(coneGeo, coneMat);
    radarCone.position.set(2.8, 3.8, 0);
    group.add(radarCone);

    return group;
  }

  // ==================== INTERACTION & SCROLLYTELLING ====================

  function setupInteractions() {
    // 1. Mouse / Touch Drag to Orbit Model
    container.addEventListener('mousedown', (e) => {
      isUserInteracting = true;
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;
    });

    window.addEventListener('mousemove', (e) => {
      if (!isUserInteracting) return;
      const deltaX = e.clientX - lastMouseX;
      const deltaY = e.clientY - lastMouseY;
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;

      targetRotationY += deltaX * 0.007;
      targetRotationX += deltaY * 0.005;
      targetRotationX = Math.max(-0.2, Math.min(0.85, targetRotationX));
    });

    window.addEventListener('mouseup', () => {
      isUserInteracting = false;
    });

    // Touch support for mobile devices
    container.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        isUserInteracting = true;
        lastMouseX = e.touches[0].clientX;
        lastMouseY = e.touches[0].clientY;
      }
    }, { passive: true });

    window.addEventListener('touchmove', (e) => {
      if (!isUserInteracting || e.touches.length !== 1) return;
      const deltaX = e.touches[0].clientX - lastMouseX;
      const deltaY = e.touches[0].clientY - lastMouseY;
      lastMouseX = e.touches[0].clientX;
      lastMouseY = e.touches[0].clientY;

      targetRotationY += deltaX * 0.007;
      targetRotationX += deltaY * 0.005;
      targetRotationX = Math.max(-0.2, Math.min(0.85, targetRotationX));
    }, { passive: true });

    window.addEventListener('touchend', () => {
      isUserInteracting = false;
    });

    // 2. Manual Scrub Slider
    if (scrubSlider) {
      scrubSlider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        explodeTarget = val / 100.0;
        updateScrubLabel(val);
      });
    }

    // 3. Step Pills Buttons
    stepPills.forEach((btn) => {
      btn.addEventListener('click', () => {
        const stepVal = parseFloat(btn.dataset.explode || '0');
        explodeTarget = stepVal;
        if (scrubSlider) scrubSlider.value = (stepVal * 100).toFixed(0);
        updateScrubLabel(stepVal * 100);
        stepPills.forEach((p) => p.classList.remove('active'));
        btn.classList.add('active');

        // Scroll to corresponding narrative card
        const targetCard = document.querySelector(`.story-card[data-step="${btn.dataset.step}"]`);
        if (targetCard) {
          targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      });
    });

    // 4. Scroll-Triggered Explosion Driver
    window.addEventListener('scroll', handleScroll, { passive: true });

    // 5. Window Resize Handler
    window.addEventListener('resize', handleResize);

    // 6. Navigation Buttons
    const scrollToApp = () => {
      const appTarget = document.getElementById('navigator-app') || document.getElementById('search-card');
      if (appTarget) {
        appTarget.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    };

    if (jumpToAppBtn) jumpToAppBtn.addEventListener('click', scrollToApp);
    if (navJumpBtn) navJumpBtn.addEventListener('click', scrollToApp);
    if (navShowcaseBtn) {
      navShowcaseBtn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }
  }

  function handleScroll() {
    if (!showcaseSection) return;

    const rect = showcaseSection.getBoundingClientRect();
    const sectionHeight = showcaseSection.offsetHeight;
    const windowHeight = window.innerHeight;

    // Determine visibility for render loop throttling
    isVisible = (rect.bottom > 0 && rect.top < windowHeight);

    // Calculate normalized scroll progress within showcase
    const scrollStart = 0;
    const scrollEnd = sectionHeight - windowHeight;
    const currentScroll = -rect.top;

    if (currentScroll >= scrollStart && currentScroll <= scrollEnd) {
      const progress = Math.max(0, Math.min(1, currentScroll / (scrollEnd - scrollStart)));
      explodeTarget = progress;
      if (scrubSlider) scrubSlider.value = (progress * 100).toFixed(0);
      updateScrubLabel(progress * 100);
      syncStepPills(progress);
    }
  }

  function syncStepPills(progress) {
    stepPills.forEach((pill) => {
      const val = parseFloat(pill.dataset.explode || '0');
      pill.classList.toggle('active', Math.abs(progress - val) < 0.18);
    });
  }

  function updateScrubLabel(percentage) {
    if (scrubValueText) {
      scrubValueText.textContent = `${Math.round(percentage)}%`;
    }
  }

  function handleResize() {
    if (!container || !camera || !renderer) return;
    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }

  // ==================== ANIMATION & RENDER LOOP ====================

  function applyExplosion(factor) {
    // Smooth lerp easing
    const t = factor;

    // Layer 1 (Subterranean Metro & Road): Pulls downward into strata
    if (layerMetro) {
      layerMetro.position.y = -t * 2.8;
    }

    // Layer 2 (Chassis & Wheels): Anchored base
    if (layerChassis) {
      layerChassis.position.y = 0;
    }

    // Layer 3 (Passenger Deck & Shakti Validator): Floats upward slightly
    if (layerInterior) {
      layerInterior.position.y = t * 1.8;
    }

    // Layer 4 (Aerodynamic Body Shell & Glazing): Lifts high
    if (layerBody) {
      layerBody.position.y = t * 3.8;
    }

    // Layer 5 (Roof Canopy & Climate Core): Floats into stratosphere
    if (layerRoof) {
      layerRoof.position.y = t * 6.2;
    }

    // Layer 6 (Orbital Satellite Telemetry): Deploys high into orbit
    if (layerSatellite) {
      layerSatellite.position.y = t * 7.5;

      // Expand & pulse radar cone
      if (radarCone) {
        radarCone.scale.set(1 + t * 0.8, 1 + t * 1.2, 1 + t * 0.8);
        radarCone.material.opacity = 0.15 + Math.sin(Date.now() * 0.005) * 0.12;
      }

      // Rotate satellite solar wings slowly
      if (solarPanelsLeft && solarPanelsRight) {
        solarPanelsLeft.rotation.z = Math.sin(Date.now() * 0.001) * 0.1;
        solarPanelsRight.rotation.z = -Math.sin(Date.now() * 0.001) * 0.1;
      }
    }

    // Dynamic Camera Orbit adjustments based on explode factor
    camera.position.y = 8 + t * 4.5;
    camera.position.z = 14 + t * 3.0;
  }

  function animate() {
    animFrameId = requestAnimationFrame(animate);

    if (!isVisible) return; // Save GPU cycles when scrolled away

    // Smooth lerp rotation towards target
    currentRotationY += (targetRotationY - currentRotationY) * 0.08;
    currentRotationX += (targetRotationX - currentRotationX) * 0.08;

    if (busRoot) {
      busRoot.rotation.y = currentRotationY;
      busRoot.rotation.x = currentRotationX;
    }

    // Smooth lerp explosion factor
    explodeCurrent += (explodeTarget - explodeCurrent) * 0.09;
    applyExplosion(explodeCurrent);

    renderer.render(scene, camera);
  }

  // Initialize once DOM is loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initThree);
  } else {
    initThree();
  }

})();
