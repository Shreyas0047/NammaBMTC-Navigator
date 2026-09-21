/**
 * NammaBMTC Navigator - 3D Exploded Transit Scrollytelling Engine
 * Ultra-Modern BMTC Electric Bus (Tata Starbus EV / Volvo EV styling)
 * Powered by Three.js (Procedural PBR Model, zero external assets, ultra-fast load).
 * Visualizes the complete anatomy of a Bengaluru commute:
 * - Orbital VTMS Satellite Telemetry Layer
 * - Aerodynamic Roof-Mounted EV Battery & Dual Climate Core
 * - Modern Low-Floor Interior & Shakti Smart Ticket Validator
 * - Electric Powertrain Chassis & Aero-Alloy Wheels
 * - Subterranean Namma Metro & Arterial Highway Layer
 */

(function () {
  'use strict';

  // DOM Elements
  const container = document.getElementById('scrolly-canvas-container');
  if (!container) return;

  const canvas = document.getElementById('scrolly-3d-canvas');
  const showcaseSection = document.getElementById('showcase-section');
  const storyCards = document.querySelectorAll('.story-card');

  // Three.js Core Variables
  let scene, camera, renderer;
  let busRoot, layerSatellite, layerRoof, layerBody, layerInterior, layerChassis, layerMetro;
  let radarCone, solarPanelsLeft, solarPanelsRight;
  let isUserInteracting = false;
  let targetRotationY = -0.42;
  let targetRotationX = 0.20;
  let currentRotationY = -0.42;
  let currentRotationX = 0.20;
  let lastMouseX = 0, lastMouseY = 0;
  let explodeTarget = 0.0;
  let explodeCurrent = 0.0;
  let isVisible = false;
  let animFrameId = null;

  // Modern EV Color Palette
  const COLORS = {
    evWhite: 0xF8FAFC,
    evBlue: 0x0284C7,
    evCyan: 0x00D2FF,
    evGreen: 0x10B981,
    metroPurple: 0x8B5CF6,
    metalDark: 0x0F172A,
    metalMid: 0x1E293B,
    metalLight: 0xE2E8F0,
    glassTint: 0x081326,
    roadDark: 0x0B0F19,
    solarGold: 0xF59E0B,
    ledAmber: 0xFBBF24,
    hvOrange: 0xF97316,
  };

  function initThree() {
    // 1. Scene Setup
    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x070B12, 0.02);

    // 2. Camera Setup
    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;
    camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    camera.position.set(13, 7.5, 14);
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
    const ambientLight = new THREE.AmbientLight(0x94A3B8, 1.0);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xFFFFFF, 1.9);
    dirLight.position.set(14, 24, 12);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 50;
    dirLight.shadow.bias = -0.0005;
    scene.add(dirLight);

    // Electric Cyan Rim Light
    const cyanRim = new THREE.DirectionalLight(0x00D2FF, 2.4);
    cyanRim.position.set(-12, 8, -10);
    scene.add(cyanRim);

    // Emerald Green Underglow Light
    const greenGlow = new THREE.PointLight(0x10B981, 1.8, 20);
    greenGlow.position.set(0, 0.5, 0);
    scene.add(greenGlow);

    // Purple Subterranean Metro Glow
    const purpleGlow = new THREE.PointLight(0x8B5CF6, 1.6, 25);
    purpleGlow.position.set(0, -3.2, 0);
    scene.add(purpleGlow);

    // 5. Build Procedural 3D BMTC Electric Bus
    buildElectricTransitScene();

    // 6. Setup Interactions
    setupInteractions();

    // 7. Start Render Loop
    handleScroll();
    animate();
  }

  function buildElectricTransitScene() {
    busRoot = new THREE.Group();
    scene.add(busRoot);

    // Layer 1: Subterranean Metro & Highway Ground
    layerMetro = createSubterraneanMetroLayer();
    busRoot.add(layerMetro);

    // Layer 2: Electric Chassis & Aero Wheels
    layerChassis = createElectricChassisLayer();
    busRoot.add(layerChassis);

    // Layer 3: Low-Floor Interior & Shakti Validator
    layerInterior = createLowFloorInteriorLayer();
    busRoot.add(layerInterior);

    // Layer 4: Aerodynamic EV Body & Horizon LED Lightbar
    layerBody = createElectricBodyShellLayer();
    busRoot.add(layerBody);

    // Layer 5: Roof-Mounted EV Battery Enclosure & Climate Pods
    layerRoof = createRoofBatteryEnclosureLayer();
    busRoot.add(layerRoof);

    // Layer 6: Orbital VTMS Satellite
    layerSatellite = createSatelliteTelemetryLayer();
    busRoot.add(layerSatellite);

    // Ambient Grid Plane
    const gridHelper = new THREE.GridHelper(36, 36, 0x0284C7, 0x1E293B);
    gridHelper.position.y = -2.8;
    scene.add(gridHelper);
  }

  // ==================== 3D PROCEDURAL BUILDERS ====================

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

    // Bus Lane Cyan Line
    const stripGeo = new THREE.BoxGeometry(16, 0.02, 0.25);
    const stripMat = new THREE.MeshBasicMaterial({ color: COLORS.evCyan });
    const strip = new THREE.Mesh(stripGeo, stripMat);
    strip.position.set(0, 0.02, 2.5);
    group.add(strip);

    // Platform Curb
    const curbGeo = new THREE.BoxGeometry(16, 0.35, 1.8);
    const curbMat = new THREE.MeshStandardMaterial({ color: 0x1E293B, roughness: 0.8 });
    const curb = new THREE.Mesh(curbGeo, curbMat);
    curb.position.set(0, 0.15, 3.8);
    curb.receiveShadow = true;
    group.add(curb);

    // Subterranean Metro Cutaway Bed
    const tunnelGeo = new THREE.BoxGeometry(18, 0.8, 4.2);
    const tunnelMat = new THREE.MeshStandardMaterial({ color: 0x05070D, roughness: 0.95 });
    const tunnel = new THREE.Mesh(tunnelGeo, tunnelMat);
    tunnel.position.set(0, -1.8, 0);
    group.add(tunnel);

    // Dual Metro Tracks (Purple Line & Green Line)
    const railMatPurple = new THREE.MeshStandardMaterial({ color: COLORS.metroPurple, roughness: 0.25, metalness: 0.85 });
    const railMatGreen = new THREE.MeshStandardMaterial({ color: COLORS.evGreen, roughness: 0.25, metalness: 0.85 });
    const railGeo = new THREE.CylinderGeometry(0.045, 0.045, 18, 8);

    [-0.8, -0.3].forEach((z) => {
      const rail = new THREE.Mesh(railGeo, railMatPurple);
      rail.rotation.z = Math.PI / 2;
      rail.position.set(0, -1.35, z);
      group.add(rail);
    });

    [0.3, 0.8].forEach((z) => {
      const rail = new THREE.Mesh(railGeo, railMatGreen);
      rail.rotation.z = Math.PI / 2;
      rail.position.set(0, -1.35, z);
      group.add(rail);
    });

    // Metro Concrete Sleepers
    const tieGeo = new THREE.BoxGeometry(0.14, 0.08, 2.4);
    const tieMat = new THREE.MeshStandardMaterial({ color: 0x1E293B, roughness: 0.9 });
    for (let x = -8; x <= 8; x += 0.9) {
      const tie = new THREE.Mesh(tieGeo, tieMat);
      tie.position.set(x, -1.42, 0);
      group.add(tie);
    }

    return group;
  }

  /** Layer 2: Electric Chassis, Underfloor Battery Tray & Aero Wheels */
  function createElectricChassisLayer() {
    const group = new THREE.Group();

    // Aluminum Monocoque Subframe Beams
    const beamGeo = new THREE.BoxGeometry(8.6, 0.2, 0.2);
    const beamMat = new THREE.MeshStandardMaterial({ color: COLORS.metalDark, roughness: 0.4, metalness: 0.85 });

    [-0.95, 0.95].forEach((z) => {
      const beam = new THREE.Mesh(beamGeo, beamMat);
      beam.position.set(0, 0.42, z);
      beam.castShadow = true;
      group.add(beam);
    });

    // Underfloor Lithium Battery Tray with Liquid Cooling Ribs
    const trayGeo = new THREE.BoxGeometry(5.2, 0.26, 1.9);
    const trayMat = new THREE.MeshStandardMaterial({ color: 0x0284C7, roughness: 0.3, metalness: 0.7 });
    const tray = new THREE.Mesh(trayGeo, trayMat);
    tray.position.set(0, 0.38, 0);
    group.add(tray);

    // High Voltage Cable Conduits
    const hvGeo = new THREE.CylinderGeometry(0.03, 0.03, 5.0, 8);
    const hvMat = new THREE.MeshBasicMaterial({ color: COLORS.hvOrange });
    const hvCable = new THREE.Mesh(hvGeo, hvMat);
    hvCable.rotation.z = Math.PI / 2;
    hvCable.position.set(0, 0.52, 0.75);
    group.add(hvCable);

    // Rear Permanent Magnet Electric Drive Motor
    const motorGeo = new THREE.CylinderGeometry(0.35, 0.35, 1.2, 16);
    const motorMat = new THREE.MeshStandardMaterial({ color: COLORS.metalMid, roughness: 0.3, metalness: 0.9 });
    const motor = new THREE.Mesh(motorGeo, motorMat);
    motor.rotation.x = Math.PI / 2;
    motor.position.set(-2.4, 0.44, 0);
    group.add(motor);

    // 6 EV Aero-Cover Wheels with Cyan Accents
    const wheelPositions = [
      [2.7, 0.42, 1.28],   // Front Right
      [2.7, 0.42, -1.28],  // Front Left
      [-2.4, 0.42, 1.30],  // Rear Right Outer
      [-2.4, 0.42, -1.30], // Rear Left Outer
      [-2.4, 0.42, 1.14],  // Rear Right Inner
      [-2.4, 0.42, -1.14], // Rear Left Inner
    ];

    const tireGeo = new THREE.CylinderGeometry(0.42, 0.42, 0.26, 22);
    const tireMat = new THREE.MeshStandardMaterial({ color: 0x0F172A, roughness: 0.95 });
    const aeroCoverGeo = new THREE.CylinderGeometry(0.28, 0.28, 0.27, 16);
    const aeroCoverMat = new THREE.MeshStandardMaterial({ color: COLORS.evWhite, roughness: 0.25, metalness: 0.6 });
    const cyanTrimGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.28, 12);
    const cyanTrimMat = new THREE.MeshBasicMaterial({ color: COLORS.evCyan });

    wheelPositions.forEach(([wx, wy, wz]) => {
      const tire = new THREE.Mesh(tireGeo, tireMat);
      tire.rotation.x = Math.PI / 2;
      tire.position.set(wx, wy, wz);
      tire.castShadow = true;

      const aeroCover = new THREE.Mesh(aeroCoverGeo, aeroCoverMat);
      tire.add(aeroCover);

      const cyanTrim = new THREE.Mesh(cyanTrimGeo, cyanTrimMat);
      tire.add(cyanTrim);

      group.add(tire);
    });

    return group;
  }

  /** Layer 3: Modern Low-Floor Interior, Ergonomic Seats & Shakti Tap Validator */
  function createLowFloorInteriorLayer() {
    const group = new THREE.Group();

    // Low-Floor Base Deck
    const floorGeo = new THREE.BoxGeometry(8.8, 0.08, 2.45);
    const floorMat = new THREE.MeshStandardMaterial({ color: 0x1E293B, roughness: 0.85 });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.position.set(0, 0.58, 0);
    floor.receiveShadow = true;
    group.add(floor);

    // Ergonomic Passenger Seats (Fresh Emerald / Cyan EV Upholstery)
    const seatGeo = new THREE.BoxGeometry(0.48, 0.48, 0.45);
    const seatMatCyan = new THREE.MeshStandardMaterial({ color: COLORS.evBlue, roughness: 0.6 });
    const seatMatGreen = new THREE.MeshStandardMaterial({ color: COLORS.evGreen, roughness: 0.6 });

    for (let x = -3.4; x <= 2.2; x += 0.9) {
      const sLeft = new THREE.Mesh(seatGeo, (Math.abs(x) < 1.2) ? seatMatGreen : seatMatCyan);
      sLeft.position.set(x, 0.88, -0.86);
      sLeft.castShadow = true;
      group.add(sLeft);

      const sRight = new THREE.Mesh(seatGeo, seatMatCyan);
      sRight.position.set(x, 0.88, 0.86);
      sRight.castShadow = true;
      group.add(sRight);
    }

    // Driver Glass Cockpit & Digital Multi-Function Display
    const consoleGeo = new THREE.BoxGeometry(0.65, 0.75, 0.85);
    const consoleMat = new THREE.MeshStandardMaterial({ color: 0x0B0F19, roughness: 0.4 });
    const consoleMesh = new THREE.Mesh(consoleGeo, consoleMat);
    consoleMesh.position.set(3.9, 0.96, -0.6);
    group.add(consoleMesh);

    // Digital Cluster Screen
    const screenGeo = new THREE.BoxGeometry(0.04, 0.22, 0.35);
    const screenMat = new THREE.MeshBasicMaterial({ color: COLORS.evCyan });
    const screen = new THREE.Mesh(screenGeo, screenMat);
    screen.position.set(3.8, 1.22, -0.6);
    group.add(screen);

    // Shakti Scheme Illuminated Contactless Validator near Front Entrance
    const standGeo = new THREE.CylinderGeometry(0.04, 0.04, 1.15, 8);
    const standMat = new THREE.MeshStandardMaterial({ color: COLORS.metalLight, metalness: 0.9 });
    const stand = new THREE.Mesh(standGeo, standMat);
    stand.position.set(2.6, 1.15, 1.05);
    group.add(stand);

    const valHeadGeo = new THREE.BoxGeometry(0.2, 0.28, 0.14);
    const valHeadMat = new THREE.MeshBasicMaterial({ color: COLORS.evGreen });
    const valHead = new THREE.Mesh(valHeadGeo, valHeadMat);
    valHead.position.set(2.6, 1.72, 1.05);
    group.add(valHead);

    return group;
  }

  /** Layer 4: Aerodynamic EV Body, Horizon LED Lightbar & Panoramic Glazing */
  function createElectricBodyShellLayer() {
    const group = new THREE.Group();

    // Sculpted EV Lower Body Skirt (Pearl White with Electric Teal / Green Ribbon)
    const lowerBodyGeo = new THREE.BoxGeometry(9.1, 0.82, 2.55);
    const bodyMat = new THREE.MeshStandardMaterial({
      color: COLORS.evWhite,
      roughness: 0.18,
      metalness: 0.2,
    });
    const lowerBody = new THREE.Mesh(lowerBodyGeo, bodyMat);
    lowerBody.position.set(0, 1.05, 0);
    lowerBody.castShadow = true;
    group.add(lowerBody);

    // Electric Teal Livery Accent Ribbon
    const tealRibbonGeo = new THREE.BoxGeometry(9.12, 0.16, 2.57);
    const tealRibbonMat = new THREE.MeshBasicMaterial({ color: COLORS.evCyan });
    const tealRibbon = new THREE.Mesh(tealRibbonGeo, tealRibbonMat);
    tealRibbon.position.set(0, 0.9, 0);
    group.add(tealRibbon);

    // Namma Green Bottom Skirt Stripe
    const greenStripeGeo = new THREE.BoxGeometry(9.12, 0.1, 2.57);
    const greenStripeMat = new THREE.MeshBasicMaterial({ color: COLORS.evGreen });
    const greenStripe = new THREE.Mesh(greenStripeGeo, greenStripeMat);
    greenStripe.position.set(0, 0.72, 0);
    group.add(greenStripe);

    // Futuristic Aerodynamic Front EV Nose Cap
    const noseGeo = new THREE.CylinderGeometry(1.27, 1.27, 0.75, 16, 1, false, -Math.PI / 2, Math.PI);
    const noseMat = new THREE.MeshStandardMaterial({ color: COLORS.evWhite, roughness: 0.18 });
    const nose = new THREE.Mesh(noseGeo, noseMat);
    nose.rotation.z = Math.PI / 2;
    nose.position.set(4.55, 1.05, 0);
    group.add(nose);

    // Full-Width Horizon LED Lightbar (Futuristic EV Signature Strip)
    const lightbarGeo = new THREE.BoxGeometry(0.12, 0.08, 2.3);
    const lightbarMat = new THREE.MeshBasicMaterial({ color: COLORS.evCyan });
    const lightbar = new THREE.Mesh(lightbarGeo, lightbarMat);
    lightbar.position.set(4.62, 1.15, 0);
    group.add(lightbar);

    // Dual Slim Projector Matrix Headlights
    const hlightGeo = new THREE.BoxGeometry(0.1, 0.14, 0.45);
    const hlightMat = new THREE.MeshBasicMaterial({ color: 0xFFFFFF });
    [-0.88, 0.88].forEach((lz) => {
      const hl = new THREE.Mesh(hlightGeo, hlightMat);
      hl.position.set(4.6, 0.92, lz);
      group.add(hl);
    });

    // Dark Window Pillars
    const pillarMat = new THREE.MeshStandardMaterial({ color: 0x0B0F19, roughness: 0.3 });
    [-4.4, -2.6, -0.8, 1.0, 2.8, 4.4].forEach((px) => {
      const p = new THREE.Mesh(new THREE.BoxGeometry(0.16, 1.15, 2.54), pillarMat);
      p.position.set(px, 1.95, 0);
      group.add(p);
    });

    // Panoramic Frameless Glazing (Dark Tinted Glass)
    const glassMat = new THREE.MeshPhysicalMaterial({
      color: COLORS.glassTint,
      transparent: true,
      opacity: 0.52,
      roughness: 0.04,
      metalness: 0.1,
      transmission: 0.78,
      ior: 1.5,
    });

    // Side Panoramic Glass Flush
    const sideGlassGeo = new THREE.BoxGeometry(8.6, 0.98, 0.04);
    [-1.27, 1.27].forEach((gz) => {
      const g = new THREE.Mesh(sideGlassGeo, glassMat);
      g.position.set(0, 1.95, gz);
      group.add(g);
    });

    // Curved Aerodynamic Front Windshield
    const frontWindshieldGeo = new THREE.BoxGeometry(0.06, 1.18, 2.4);
    const frontWindshield = new THREE.Mesh(frontWindshieldGeo, glassMat);
    frontWindshield.position.set(4.48, 1.95, 0);
    frontWindshield.rotation.z = -0.12;
    group.add(frontWindshield);

    // Front Destination LED Display ("378-P ELECTRIC")
    const ledGeo = new THREE.BoxGeometry(0.08, 0.28, 1.7);
    const ledMat = new THREE.MeshBasicMaterial({ color: COLORS.ledAmber });
    const ledBoard = new THREE.Mesh(ledGeo, ledMat);
    ledBoard.position.set(4.48, 2.45, 0);
    group.add(ledBoard);

    return group;
  }

  /** Layer 5: Aerodynamic Roof-Mounted EV Battery Enclosure & Dual Climate Pods */
  function createRoofBatteryEnclosureLayer() {
    const group = new THREE.Group();

    // White Aerodynamic Fiberglass Roof Plate
    const roofPlateGeo = new THREE.BoxGeometry(9.2, 0.18, 2.58);
    const roofPlateMat = new THREE.MeshStandardMaterial({ color: COLORS.evWhite, roughness: 0.25 });
    const roofPlate = new THREE.Mesh(roofPlateGeo, roofPlateMat);
    roofPlate.position.set(0, 2.58, 0);
    roofPlate.castShadow = true;
    group.add(roofPlate);

    // Roof-Mounted High-Capacity EV Battery Fairing (Extended Sleek Enclosure)
    const batFairingGeo = new THREE.BoxGeometry(4.8, 0.38, 1.9);
    const batFairingMat = new THREE.MeshStandardMaterial({
      color: 0x0284C7,
      roughness: 0.3,
      metalness: 0.5,
    });
    const batFairing = new THREE.Mesh(batFairingGeo, batFairingMat);
    batFairing.position.set(0.4, 2.84, 0);
    batFairing.castShadow = true;
    group.add(batFairing);

    // Dual Ultra-Low-Profile Air Conditioning Pods
    const acGeo = new THREE.BoxGeometry(1.6, 0.32, 1.8);
    const acMat = new THREE.MeshStandardMaterial({ color: COLORS.evWhite, roughness: 0.4 });
    const acRear = new THREE.Mesh(acGeo, acMat);
    acRear.position.set(-2.8, 2.82, 0);
    group.add(acRear);

    // Fast-Charging Pantograph Contact Rails on Rear
    const pantoRailGeo = new THREE.CylinderGeometry(0.04, 0.04, 1.4, 8);
    const pantoRailMat = new THREE.MeshStandardMaterial({ color: COLORS.metalLight, metalness: 0.95 });
    [-0.5, 0.5].forEach((pz) => {
      const rail = new THREE.Mesh(pantoRailGeo, pantoRailMat);
      rail.rotation.z = Math.PI / 2;
      rail.position.set(-2.8, 3.08, pz);
      group.add(rail);
    });

    // Roof High-Precision GPS Transceiver Dome
    const domeGeo = new THREE.SphereGeometry(0.15, 14, 14);
    const domeMat = new THREE.MeshStandardMaterial({ color: COLORS.evCyan, roughness: 0.2, metalness: 0.85 });
    const dome = new THREE.Mesh(domeGeo, domeMat);
    dome.position.set(2.9, 2.76, 0);
    group.add(dome);

    return group;
  }

  /** Layer 6: Orbital VTMS Satellite & Telemetry Radar Beam */
  function createSatelliteTelemetryLayer() {
    const group = new THREE.Group();

    // Satellite Core Body (Gold Multi-Layer Insulation Foil)
    const satBodyGeo = new THREE.BoxGeometry(0.9, 0.9, 0.9);
    const satBodyMat = new THREE.MeshStandardMaterial({
      color: COLORS.solarGold,
      roughness: 0.2,
      metalness: 0.92,
    });
    const satBody = new THREE.Mesh(satBodyGeo, satBodyMat);
    satBody.position.set(2.9, 5.8, 0);
    satBody.castShadow = true;
    group.add(satBody);

    // Downward Parabolic Antenna Dish
    const dishGeo = new THREE.CylinderGeometry(0.48, 0.06, 0.16, 16);
    const dishMat = new THREE.MeshStandardMaterial({ color: COLORS.metalLight, metalness: 0.95 });
    const dish = new THREE.Mesh(dishGeo, dishMat);
    dish.position.set(2.9, 5.24, 0);
    dish.rotation.x = Math.PI;
    group.add(dish);

    // Dual Photovoltaic Solar Panel Wings
    const panelGeo = new THREE.BoxGeometry(1.7, 0.04, 0.9);
    const panelMat = new THREE.MeshStandardMaterial({
      color: 0x1E3A8A,
      roughness: 0.2,
      metalness: 0.8,
    });

    solarPanelsLeft = new THREE.Mesh(panelGeo, panelMat);
    solarPanelsLeft.position.set(2.9, 5.8, -1.5);
    group.add(solarPanelsLeft);

    solarPanelsRight = new THREE.Mesh(panelGeo, panelMat);
    solarPanelsRight.position.set(2.9, 5.8, 1.5);
    group.add(solarPanelsRight);

    // Telemetry Radar Pulse Cone
    const coneGeo = new THREE.ConeGeometry(2.0, 3.2, 24, 1, true);
    const coneMat = new THREE.MeshBasicMaterial({
      color: COLORS.evCyan,
      transparent: true,
      opacity: 0.25,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    radarCone = new THREE.Mesh(coneGeo, coneMat);
    radarCone.position.set(2.9, 3.8, 0);
    group.add(radarCone);

    return group;
  }

  // ==================== NATURAL SCROLL & PARALLAX ENGINE ====================

  function setupInteractions() {
    // Mouse / Touch Drag to Orbit Model (Natural 360° Inspection)
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

    // Touch support for mobile
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

    // Natural Scroll-Triggered Dissection
    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', handleResize);
  }

  function handleScroll() {
    if (!showcaseSection) return;

    const rect = showcaseSection.getBoundingClientRect();
    const windowHeight = window.innerHeight;

    // Check if showcase section is visible in viewport
    isVisible = (rect.bottom > -100 && rect.top < windowHeight + 100);

    if (!isVisible) return;

    // Calculate natural scroll progress through showcase section
    const totalDist = showcaseSection.offsetHeight - windowHeight;
    const currentScroll = -rect.top;

    if (totalDist > 0) {
      const progress = Math.max(0, Math.min(1, currentScroll / totalDist));
      explodeTarget = progress;

      // Update active state on aesthetic story cards based on scroll depth
      syncStoryCards(progress);
    }
  }

  function syncStoryCards(progress) {
    if (!storyCards || storyCards.length === 0) return;
    const stepIdx = Math.min(storyCards.length - 1, Math.floor(progress * storyCards.length));

    storyCards.forEach((card, idx) => {
      card.classList.toggle('active', idx === stepIdx);
    });
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

  function applyExplosion(t) {
    // Layer 1: Subterranean Metro & Road descends into geological strata
    if (layerMetro) {
      layerMetro.position.y = -t * 2.8;
    }

    // Layer 2: Electric Chassis & Wheels stay anchored
    if (layerChassis) {
      layerChassis.position.y = 0;
    }

    // Layer 3: Low-Floor Deck & Shakti Validator floats up
    if (layerInterior) {
      layerInterior.position.y = t * 1.8;
    }

    // Layer 4: Aerodynamic EV Body & Horizon Lightbar lifts
    if (layerBody) {
      layerBody.position.y = t * 3.8;
    }

    // Layer 5: Roof-Mounted EV Battery Enclosure floats into stratosphere
    if (layerRoof) {
      layerRoof.position.y = t * 6.2;
    }

    // Layer 6: Orbital Satellite Telemetry deploys into orbit
    if (layerSatellite) {
      layerSatellite.position.y = t * 7.6;

      if (radarCone) {
        radarCone.scale.set(1 + t * 0.8, 1 + t * 1.2, 1 + t * 0.8);
        radarCone.material.opacity = 0.15 + Math.sin(Date.now() * 0.005) * 0.12;
      }

      if (solarPanelsLeft && solarPanelsRight) {
        solarPanelsLeft.rotation.z = Math.sin(Date.now() * 0.001) * 0.1;
        solarPanelsRight.rotation.z = -Math.sin(Date.now() * 0.001) * 0.1;
      }
    }

    // Dynamic Camera Orbit adjustments
    camera.position.y = 7.5 + t * 4.2;
    camera.position.z = 14 + t * 2.8;
  }

  function animate() {
    animFrameId = requestAnimationFrame(animate);

    if (!isVisible) return; // Pause WebGL rendering when outside viewport

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
