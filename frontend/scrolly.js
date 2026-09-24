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
  let targetRotationY = 0.55;
  let targetRotationX = 0.16;
  let currentRotationY = 0.55;
  let currentRotationX = 0.16;
  let lastMouseX = 0, lastMouseY = 0;
  let explodeTarget = 0.0;
  let explodeCurrent = 0.0;
  let isVisible = false;
  let animFrameId = null;

  // Authentic BMTC Color Palette (Daylight Architectural Render)
  const COLORS = {
    bmtcBlue: 0x0284C7,       // BMTC Primary Livery Blue
    bmtcTeal: 0x00A896,       // BMTC Accent Teal / Aqua
    bmtcWhite: 0xF8FAFC,      // BMTC Clean Upper White
    bmtcGreen: 0x059669,      // BMTC Eco Green / Shakti
    bmtcDarkBlue: 0x0369A1,   // BMTC Deep Blue Skirt
    metroPurple: 0x8B5CF6,    // BMRCL Purple Line
    metroGreen: 0x10B981,     // BMRCL Green Line
    metalDark: 0x334155,      // Chassis Steel
    metalMid: 0x64748B,       // Mechanical Steel
    metalLight: 0xE2E8F0,     // Stainless Steel Grab Poles & Panto
    glassTint: 0x0284C7,      // Bus Window Tint
    roadDark: 0x475569,       // Transit Asphalt
    solarGold: 0xF59E0B,      // Satellite MLI Foil
    ledAmber: 0xF59E0B,       // BMTC LED Destination Display
    hvOrange: 0xEA580C,       // High Voltage EV Cables
    taillightRed: 0xEF4444,   // Rear Stop Lights
    headlightWarm: 0xFFFBEB,  // Dual Halogen/LED Matrix
  };

  function initThree() {
    // 1. Scene Setup
    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0xF8FAFC, 0.015);

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
    renderer.toneMappingExposure = 1.05;

    // 4. Studio Lighting - Bright Clean Daylight Environment
    const ambientLight = new THREE.AmbientLight(0xFFFFFF, 1.1);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xFFFFFF, 1.6);
    dirLight.position.set(14, 24, 12);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 50;
    dirLight.shadow.bias = -0.0005;
    scene.add(dirLight);

    // Subtle Sky Soft Fill Light
    const skyFill = new THREE.DirectionalLight(0xBAE6FD, 0.8);
    skyFill.position.set(-12, 10, -10);
    scene.add(skyFill);

    // Subtle Warm Bounce Light
    const groundBounce = new THREE.DirectionalLight(0xFEF3C7, 0.4);
    groundBounce.position.set(0, -5, 5);
    scene.add(groundBounce);

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

    // Layer 3: Low-Floor Interior, Grab Poles & Shakti Validator
    layerInterior = createLowFloorInteriorLayer();
    busRoot.add(layerInterior);

    // Layer 4: Authentic BMTC Electric Body Shell with Livery & Doors
    layerBody = createElectricBodyShellLayer();
    busRoot.add(layerBody);

    // Layer 5: Roof-Mounted EV Battery Enclosure & Climate Pods
    layerRoof = createRoofBatteryEnclosureLayer();
    busRoot.add(layerRoof);

    // Layer 6: Orbital VTMS Satellite
    layerSatellite = createSatelliteTelemetryLayer();
    busRoot.add(layerSatellite);

    // Ambient Grid Plane (Clean Architectural Light Grid)
    const gridHelper = new THREE.GridHelper(36, 36, 0xCBD5E1, 0xE2E8F0);
    gridHelper.position.y = -2.8;
    scene.add(gridHelper);
  }

  // ==================== 3D PROCEDURAL BUILDERS ====================

  /** Helper: Procedural Canvas Texture for Destination Display */
  function createLedBoardTexture(text) {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 80;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#0F172A';
    ctx.fillRect(0, 0, 512, 80);
    // LED Dot Matrix styling
    ctx.fillStyle = '#F59E0B';
    ctx.font = 'bold 36px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 256, 42);
    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    return texture;
  }

  /** Helper: BMTC Emblem / Crest Texture */
  function createBmtcEmblemTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#0284C7';
    ctx.beginPath();
    ctx.arc(64, 64, 56, 0, Math.PI * 2);
    ctx.fill();
    ctx.lineWidth = 4;
    ctx.strokeStyle = '#FFFFFF';
    ctx.stroke();
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 26px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('BMTC', 64, 64);
    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    return texture;
  }

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

    // Bus Lane Yellow/Cyan Line
    const stripGeo = new THREE.BoxGeometry(16, 0.02, 0.25);
    const stripMat = new THREE.MeshBasicMaterial({ color: 0xF59E0B });
    const strip = new THREE.Mesh(stripGeo, stripMat);
    strip.position.set(0, 0.02, 2.5);
    group.add(strip);

    // Platform Curb
    const curbGeo = new THREE.BoxGeometry(16, 0.35, 1.8);
    const curbMat = new THREE.MeshStandardMaterial({ color: 0xE2E8F0, roughness: 0.7 });
    const curb = new THREE.Mesh(curbGeo, curbMat);
    curb.position.set(0, 0.15, 3.8);
    curb.receiveShadow = true;
    group.add(curb);

    // Subterranean Metro Cutaway Bed
    const tunnelGeo = new THREE.BoxGeometry(18, 0.8, 4.2);
    const tunnelMat = new THREE.MeshStandardMaterial({ color: 0x94A3B8, roughness: 0.9 });
    const tunnel = new THREE.Mesh(tunnelGeo, tunnelMat);
    tunnel.position.set(0, -1.8, 0);
    group.add(tunnel);

    // Dual Metro Tracks (Purple Line & Green Line)
    const railMatPurple = new THREE.MeshStandardMaterial({ color: COLORS.metroPurple, roughness: 0.25, metalness: 0.85 });
    const railMatGreen = new THREE.MeshStandardMaterial({ color: COLORS.metroGreen, roughness: 0.25, metalness: 0.85 });
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
    const tieMat = new THREE.MeshStandardMaterial({ color: 0x64748B, roughness: 0.9 });
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
    const trayMat = new THREE.MeshStandardMaterial({ color: COLORS.bmtcDarkBlue, roughness: 0.3, metalness: 0.7 });
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

    // 6 EV Aero-Cover Wheels with BMTC Hub
    const wheelPositions = [
      [2.7, 0.42, 1.28],   // Front Right
      [2.7, 0.42, -1.28],  // Front Left
      [-2.4, 0.42, 1.30],  // Rear Right Outer
      [-2.4, 0.42, -1.30], // Rear Left Outer
      [-2.4, 0.42, 1.14],  // Rear Right Inner
      [-2.4, 0.42, -1.14], // Rear Left Inner
    ];

    const tireGeo = new THREE.CylinderGeometry(0.42, 0.42, 0.26, 24);
    const tireMat = new THREE.MeshStandardMaterial({ color: 0x0F172A, roughness: 0.95 });
    const rimGeo = new THREE.CylinderGeometry(0.28, 0.28, 0.27, 16);
    const rimMat = new THREE.MeshStandardMaterial({ color: COLORS.metalLight, roughness: 0.2, metalness: 0.8 });
    const hubGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.28, 12);
    const hubMat = new THREE.MeshStandardMaterial({ color: COLORS.bmtcBlue, roughness: 0.3 });

    wheelPositions.forEach(([wx, wy, wz]) => {
      const tire = new THREE.Mesh(tireGeo, tireMat);
      tire.rotation.x = Math.PI / 2;
      tire.position.set(wx, wy, wz);
      tire.castShadow = true;

      const rim = new THREE.Mesh(rimGeo, rimMat);
      tire.add(rim);

      const hub = new THREE.Mesh(hubGeo, hubMat);
      tire.add(hub);

      group.add(tire);
    });

    return group;
  }

  /** Layer 3: Modern Low-Floor Interior, BMTC Grab Poles & Shakti Tap Validator */
  function createLowFloorInteriorLayer() {
    const group = new THREE.Group();

    // Low-Floor Base Deck
    const floorGeo = new THREE.BoxGeometry(8.8, 0.08, 2.45);
    const floorMat = new THREE.MeshStandardMaterial({ color: 0x1E293B, roughness: 0.85 });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.position.set(0, 0.58, 0);
    floor.receiveShadow = true;
    group.add(floor);

    // Passenger Seats (BMTC Blue & Women Shakti Green Seats)
    const seatGeo = new THREE.BoxGeometry(0.48, 0.48, 0.45);
    const seatMatBlue = new THREE.MeshStandardMaterial({ color: COLORS.bmtcBlue, roughness: 0.6 });
    const seatMatShakti = new THREE.MeshStandardMaterial({ color: COLORS.bmtcGreen, roughness: 0.6 });

    for (let x = -3.4; x <= 2.2; x += 0.9) {
      // Priority/Shakti seats in middle/front
      const isShakti = (x > -0.5 && x < 1.8);
      const sLeft = new THREE.Mesh(seatGeo, isShakti ? seatMatShakti : seatMatBlue);
      sLeft.position.set(x, 0.88, -0.86);
      sLeft.castShadow = true;
      group.add(sLeft);

      const sRight = new THREE.Mesh(seatGeo, seatMatBlue);
      sRight.position.set(x, 0.88, 0.86);
      sRight.castShadow = true;
      group.add(sRight);
    }

    // Yellow / Stainless Steel Handrail Overhead Pipes (Typical BMTC Interior)
    const pipeMat = new THREE.MeshStandardMaterial({ color: 0xFBBF24, roughness: 0.3, metalness: 0.6 });
    const pipeGeo = new THREE.CylinderGeometry(0.02, 0.02, 7.8, 8);
    [-0.5, 0.5].forEach((pz) => {
      const pipe = new THREE.Mesh(pipeGeo, pipeMat);
      pipe.rotation.z = Math.PI / 2;
      pipe.position.set(-0.5, 2.15, pz);
      group.add(pipe);
    });

    // Vertical Grab Stanchion Poles
    const stanchionGeo = new THREE.CylinderGeometry(0.02, 0.02, 1.6, 8);
    [-2.2, 0.0, 2.0].forEach((sx) => {
      const stLeft = new THREE.Mesh(stanchionGeo, pipeMat);
      stLeft.position.set(sx, 1.4, -0.5);
      group.add(stLeft);

      const stRight = new THREE.Mesh(stanchionGeo, pipeMat);
      stRight.position.set(sx, 1.4, 0.5);
      group.add(stRight);
    });

    // Driver Glass Cockpit & Steering Console
    const consoleGeo = new THREE.BoxGeometry(0.65, 0.75, 0.85);
    const consoleMat = new THREE.MeshStandardMaterial({ color: 0x0B0F19, roughness: 0.4 });
    const consoleMesh = new THREE.Mesh(consoleGeo, consoleMat);
    consoleMesh.position.set(3.9, 0.96, -0.6);
    group.add(consoleMesh);

    // Driver Steering Wheel
    const wheelTorusGeo = new THREE.TorusGeometry(0.18, 0.025, 8, 16);
    const wheelTorusMat = new THREE.MeshStandardMaterial({ color: 0x1E293B, roughness: 0.5 });
    const wheelMesh = new THREE.Mesh(wheelTorusGeo, wheelTorusMat);
    wheelMesh.rotation.y = Math.PI / 2;
    wheelMesh.rotation.z = 0.5;
    wheelMesh.position.set(3.7, 1.25, -0.6);
    group.add(wheelMesh);

    // Shakti Scheme Illuminated Contactless Smart Card Validator
    const standGeo = new THREE.CylinderGeometry(0.04, 0.04, 1.15, 8);
    const standMat = new THREE.MeshStandardMaterial({ color: COLORS.metalLight, metalness: 0.9 });
    const stand = new THREE.Mesh(standGeo, standMat);
    stand.position.set(2.6, 1.15, 1.05);
    group.add(stand);

    const valHeadGeo = new THREE.BoxGeometry(0.2, 0.28, 0.14);
    const valHeadMat = new THREE.MeshBasicMaterial({ color: COLORS.bmtcGreen });
    const valHead = new THREE.Mesh(valHeadGeo, valHeadMat);
    valHead.position.set(2.6, 1.72, 1.05);
    group.add(valHead);

    return group;
  }

  /** Layer 4: Authentic BMTC Electric Bus Body Shell & Signature Livery */
  function createElectricBodyShellLayer() {
    const group = new THREE.Group();

    // 1. Lower Body Skirt in Authentic BMTC Royal Blue
    const lowerBodyGeo = new THREE.BoxGeometry(9.1, 0.82, 2.55);
    const lowerBodyMat = new THREE.MeshStandardMaterial({
      color: COLORS.bmtcBlue,
      roughness: 0.2,
      metalness: 0.25,
    });
    const lowerBody = new THREE.Mesh(lowerBodyGeo, lowerBodyMat);
    lowerBody.position.set(0, 1.05, 0);
    lowerBody.castShadow = true;
    group.add(lowerBody);

    // 2. Deep Navy Blue Bottom Sill Stripe
    const darkSillGeo = new THREE.BoxGeometry(9.12, 0.12, 2.57);
    const darkSillMat = new THREE.MeshStandardMaterial({ color: COLORS.bmtcDarkBlue, roughness: 0.4 });
    const darkSill = new THREE.Mesh(darkSillGeo, darkSillMat);
    darkSill.position.set(0, 0.70, 0);
    group.add(darkSill);

    // 3. Signature BMTC Electric Teal Livery Ribbon (The recognizable Bangalore stripe)
    const tealStripeGeo = new THREE.BoxGeometry(9.12, 0.16, 2.57);
    const tealStripeMat = new THREE.MeshBasicMaterial({ color: COLORS.bmtcTeal });
    const tealStripe = new THREE.Mesh(tealStripeGeo, tealStripeMat);
    tealStripe.position.set(0, 1.38, 0);
    group.add(tealStripe);

    // 4. Upper Window Belt Clean White Frame
    const upperWhiteGeo = new THREE.BoxGeometry(9.1, 0.10, 2.55);
    const upperWhiteMat = new THREE.MeshStandardMaterial({ color: COLORS.bmtcWhite, roughness: 0.2 });
    const upperWhite = new THREE.Mesh(upperWhiteGeo, upperWhiteMat);
    upperWhite.position.set(0, 2.48, 0);
    group.add(upperWhite);

    // 5. Authentic Front Nose & Grill with BMTC Emblem
    const noseGeo = new THREE.CylinderGeometry(1.27, 1.27, 0.75, 20, 1, false, -Math.PI / 2, Math.PI);
    const noseMat = new THREE.MeshStandardMaterial({ color: COLORS.bmtcBlue, roughness: 0.2 });
    const nose = new THREE.Mesh(noseGeo, noseMat);
    nose.rotation.z = Math.PI / 2;
    nose.position.set(4.55, 1.05, 0);
    group.add(nose);

    // BMTC Front Emblem Crest
    const emblemGeo = new THREE.PlaneGeometry(0.32, 0.32);
    const emblemMat = new THREE.MeshBasicMaterial({
      map: createBmtcEmblemTexture(),
      transparent: true,
    });
    const emblem = new THREE.Mesh(emblemGeo, emblemMat);
    emblem.rotation.y = Math.PI / 2;
    emblem.position.set(4.94, 1.15, 0);
    group.add(emblem);

    // Dual Front LED Projector Headlights
    const hlightGeo = new THREE.BoxGeometry(0.08, 0.14, 0.38);
    const hlightMat = new THREE.MeshBasicMaterial({ color: COLORS.headlightWarm });
    [-0.88, 0.88].forEach((lz) => {
      const hl = new THREE.Mesh(hlightGeo, hlightMat);
      hl.position.set(4.68, 0.92, lz);
      group.add(hl);
    });

    // Front Fog / DRL Accents
    const drlGeo = new THREE.BoxGeometry(0.04, 0.05, 0.22);
    const drlMat = new THREE.MeshBasicMaterial({ color: 0x38BDF8 });
    [-0.92, 0.92].forEach((lz) => {
      const drl = new THREE.Mesh(drlGeo, drlMat);
      drl.position.set(4.70, 0.74, lz);
      group.add(drl);
    });

    // Rear Taillights (Vertical Stack Red & Amber)
    const taillightGeo = new THREE.BoxGeometry(0.06, 0.28, 0.12);
    const taillightMat = new THREE.MeshBasicMaterial({ color: COLORS.taillightRed });
    [-1.05, 1.05].forEach((rz) => {
      const tl = new THREE.Mesh(taillightGeo, taillightMat);
      tl.position.set(-4.56, 1.25, rz);
      group.add(tl);
    });

    // Large Bus Side Mirrors (Left & Right)
    const mirrorArmGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.5, 6);
    const mirrorArmMat = new THREE.MeshStandardMaterial({ color: 0x0F172A });
    const mirrorHeadGeo = new THREE.BoxGeometry(0.08, 0.36, 0.16);
    const mirrorHeadMat = new THREE.MeshStandardMaterial({ color: 0x0F172A, roughness: 0.3 });

    [-1.38, 1.38].forEach((mz) => {
      const arm = new THREE.Mesh(mirrorArmGeo, mirrorArmMat);
      arm.rotation.x = mz > 0 ? 0.6 : -0.6;
      arm.position.set(4.35, 1.95, mz * 0.95);
      group.add(arm);

      const head = new THREE.Mesh(mirrorHeadGeo, mirrorHeadMat);
      head.position.set(4.45, 2.05, mz);
      group.add(head);
    });

    // Windshield Wipers
    const wiperGeo = new THREE.BoxGeometry(0.02, 0.45, 0.02);
    const wiperMat = new THREE.MeshBasicMaterial({ color: 0x0F172A });
    [-0.45, 0.45].forEach((wz) => {
      const wiper = new THREE.Mesh(wiperGeo, wiperMat);
      wiper.rotation.z = -0.3;
      wiper.position.set(4.50, 1.62, wz);
      group.add(wiper);
    });

    // Dual Passenger Entrance Doors (Low-Floor Double Inward Glazed Doors)
    const doorFrameMat = new THREE.MeshStandardMaterial({ color: 0x0B0F19, roughness: 0.3 });
    const doorGlassMat = new THREE.MeshPhysicalMaterial({
      color: COLORS.glassTint,
      transparent: true,
      opacity: 0.7,
      transmission: 0.6,
      roughness: 0.1,
    });

    [2.3, -0.6].forEach((dx) => {
      const dFrame = new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.82, 0.06), doorFrameMat);
      dFrame.position.set(dx, 1.48, 1.28);
      group.add(dFrame);

      const dGlass = new THREE.Mesh(new THREE.BoxGeometry(0.78, 1.5, 0.08), doorGlassMat);
      dGlass.position.set(dx, 1.55, 1.28);
      group.add(dGlass);
    });

    // Dark Window Pillars
    const pillarMat = new THREE.MeshStandardMaterial({ color: 0x0B0F19, roughness: 0.3 });
    [-4.4, -2.6, -1.3, 0.5, 1.6, 3.2, 4.4].forEach((px) => {
      const p = new THREE.Mesh(new THREE.BoxGeometry(0.14, 1.05, 2.54), pillarMat);
      p.position.set(px, 1.95, 0);
      group.add(p);
    });

    // Panoramic Glazing (Bus Passenger Windows)
    const glassMat = new THREE.MeshPhysicalMaterial({
      color: COLORS.glassTint,
      transparent: true,
      opacity: 0.55,
      roughness: 0.05,
      metalness: 0.1,
      transmission: 0.75,
      ior: 1.5,
    });

    // Side Windows
    const sideGlassGeo = new THREE.BoxGeometry(8.6, 0.95, 0.04);
    [-1.27, 1.27].forEach((gz) => {
      const g = new THREE.Mesh(sideGlassGeo, glassMat);
      g.position.set(0, 1.95, gz);
      group.add(g);
    });

    // Curved Front Windshield
    const frontWindshieldGeo = new THREE.BoxGeometry(0.06, 1.15, 2.4);
    const frontWindshield = new THREE.Mesh(frontWindshieldGeo, glassMat);
    frontWindshield.position.set(4.48, 1.95, 0);
    frontWindshield.rotation.z = -0.12;
    group.add(frontWindshield);

    // Front Destination LED Display ("500-D SILK BOARD - HEBBAL")
    const frontLedMat = new THREE.MeshBasicMaterial({
      map: createLedBoardTexture('500-D SILK BOARD - HEBBAL'),
    });
    const frontLedGeo = new THREE.BoxGeometry(0.06, 0.28, 1.8);
    const frontLed = new THREE.Mesh(frontLedGeo, frontLedMat);
    frontLed.position.set(4.50, 2.44, 0);
    group.add(frontLed);

    // Side Destination LED Display Above Doors
    const sideLedMat = new THREE.MeshBasicMaterial({
      map: createLedBoardTexture('500-D ELECTRIC'),
    });
    const sideLedGeo = new THREE.BoxGeometry(1.2, 0.18, 0.06);
    const sideLed = new THREE.Mesh(sideLedGeo, sideLedMat);
    sideLed.position.set(0.8, 2.46, 1.28);
    group.add(sideLed);

    return group;
  }

  /** Layer 5: Aerodynamic Roof-Mounted EV Battery Enclosure & Dual Climate Pods */
  function createRoofBatteryEnclosureLayer() {
    const group = new THREE.Group();

    // Clean White Aerodynamic Fiberglass Roof Plate
    const roofPlateGeo = new THREE.BoxGeometry(9.2, 0.18, 2.58);
    const roofPlateMat = new THREE.MeshStandardMaterial({ color: COLORS.bmtcWhite, roughness: 0.25 });
    const roofPlate = new THREE.Mesh(roofPlateGeo, roofPlateMat);
    roofPlate.position.set(0, 2.58, 0);
    roofPlate.castShadow = true;
    group.add(roofPlate);

    // Roof-Mounted High-Capacity EV Battery Fairing in BMTC Livery
    const batFairingGeo = new THREE.BoxGeometry(4.8, 0.38, 1.9);
    const batFairingMat = new THREE.MeshStandardMaterial({
      color: COLORS.bmtcBlue,
      roughness: 0.3,
      metalness: 0.4,
    });
    const batFairing = new THREE.Mesh(batFairingGeo, batFairingMat);
    batFairing.position.set(0.4, 2.84, 0);
    batFairing.castShadow = true;
    group.add(batFairing);

    // Dual Air Conditioning Pods
    const acGeo = new THREE.BoxGeometry(1.6, 0.32, 1.8);
    const acMat = new THREE.MeshStandardMaterial({ color: COLORS.bmtcWhite, roughness: 0.4 });
    const acRear = new THREE.Mesh(acGeo, acMat);
    acRear.position.set(-2.8, 2.82, 0);
    group.add(acRear);

    // Fast-Charging Pantograph Rails on Rear Roof
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
    const domeMat = new THREE.MeshStandardMaterial({ color: 0x00D2FF, roughness: 0.2, metalness: 0.85 });
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
