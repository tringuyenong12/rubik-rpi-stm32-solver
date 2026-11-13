/**
 * Rubik RPi-STM32 Solver - 3D Digital Twin & Real-Time Visualization
 */

(function () {
  "use strict";

  // Color mapping matching Herbert Kociemba definitions and docs
  const COLORS = {
    U: 0xffd500, // Yellow
    R: 0x009b48, // Green
    F: 0xb71234, // Red
    D: 0xffffff, // White
    L: 0x0046ad, // Blue
    B: 0xff5800, // Orange
    INTERNAL: 0x18181b, // Dark grey/black for inner faces
  };

  const COLOR_HEX_STRINGS = {
    U: "#ffd500",
    R: "#009b48",
    F: "#b71234",
    D: "#ffffff",
    L: "#0046ad",
    B: "#ff5800",
  };

  const SOLVED_CUBE = "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB";

  // App State
  let currentCube = SOLVED_CUBE;
  let activePaintColor = "U";
  let sseSource = null;
  let isAnimating = false;
  let moveQueue = [];

  // Three.js instances
  let scene, camera, renderer, controls;
  let cubeGroup;
  const cubies = [];

  // DOM Elements
  const dom = {
    connectionBadge: document.getElementById("connectionBadge"),
    hardwareBadge: document.getElementById("hardwareBadge"),
    solverStateBadge: document.getElementById("solverStateBadge"),
    btnSolve: document.getElementById("btnSolve"),
    btnPause: document.getElementById("btnPause"),
    btnResume: document.getElementById("btnResume"),
    btnStep: document.getElementById("btnStep"),
    btnStop: document.getElementById("btnStop"),
    progressBarFill: document.getElementById("progressBarFill"),
    progressText: document.getElementById("progressText"),
    timeText: document.getElementById("timeText"),
    activeMoveToken: document.getElementById("activeMoveToken"),
    activeMoveDescVi: document.getElementById("activeMoveDescVi"),
    activeMoveDescEn: document.getElementById("activeMoveDescEn"),
    solutionTape: document.getElementById("solutionTape"),
    stepsSummaryBadge: document.getElementById("stepsSummaryBadge"),
    movesRemainingText: document.getElementById("movesRemainingText"),
    scrambleDisplay: document.getElementById("scrambleDisplay"),
    btnResetCube: document.getElementById("btnResetCube"),
    cubeNetGrid: document.getElementById("cubeNetGrid"),
    paletteButtons: document.getElementById("paletteButtons"),
    cubeStringInput: document.getElementById("cubeStringInput"),
    btnApplyCubeString: document.getElementById("btnApplyCubeString"),
    netValidityBadge: document.getElementById("netValidityBadge"),
    uartTerminal: document.getElementById("uartTerminal"),
    btnClearLogs: document.getElementById("btnClearLogs"),
    motionHud: document.getElementById("motionHud"),
    hudText: document.getElementById("hudText"),
    // Settings modal
    btnOpenSettings: document.getElementById("btnOpenSettings"),
    settingsModal: document.getElementById("settingsModal"),
    btnCloseSettings: document.getElementById("btnCloseSettings"),
    btnSaveSettings: document.getElementById("btnSaveSettings"),
    settingPort: document.getElementById("settingPort"),
    settingBaudrate: document.getElementById("settingBaudrate"),
    settingFaceCmd: document.getElementById("settingFaceCmd"),
    settingDuration: document.getElementById("settingDuration"),
    durationVal: document.getElementById("durationVal"),
  };

  // ==========================================
  // 1. Three.js 3D Setup & Rubik Construction
  // ==========================================

  function initThreeScene() {
    const container = document.getElementById("canvasContainer");
    const width = container.clientWidth;
    const height = container.clientHeight;

    scene = new THREE.Scene();

    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    setCameraView("iso");

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);

    // OrbitControls
    if (THREE.OrbitControls) {
      controls = new THREE.OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.05;
      controls.rotateSpeed = 0.8;
      controls.minDistance = 3;
      controls.maxDistance = 15;
    }

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.6);
    dirLight1.position.set(6, 10, 8);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.4);
    dirLight2.position.set(-8, -6, -8);
    scene.add(dirLight2);

    // Cube group
    cubeGroup = new THREE.Group();
    scene.add(cubeGroup);

    build3DCube();

    window.addEventListener("resize", onWindowResize);
    animate();
  }

  function setCameraView(preset) {
    if (!camera) return;
    switch (preset) {
      case "iso":
        camera.position.set(4.5, 3.8, 5.0);
        break;
      case "top": // U face
        camera.position.set(0.01, 6.5, 0);
        break;
      case "front": // F face
        camera.position.set(0, 0, 6.5);
        break;
      case "right": // R face
        camera.position.set(6.5, 0, 0);
        break;
      case "bottom": // D face
        camera.position.set(0.01, -6.5, 0);
        break;
      case "left": // L face
        camera.position.set(-6.5, 0, 0);
        break;
      case "back": // B face
        camera.position.set(0, 0, -6.5);
        break;
      case "reset":
        camera.position.set(4.5, 3.8, 5.0);
        break;
    }
    camera.lookAt(0, 0, 0);
    if (controls) {
      controls.target.set(0, 0, 0);
      controls.update();
    }
  }

  function onWindowResize() {
    const container = document.getElementById("canvasContainer");
    if (!container || !renderer || !camera) return;
    const width = container.clientWidth;
    const height = container.clientHeight;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }

  function build3DCube() {
    // Clear any existing cubies
    while (cubeGroup.children.length > 0) {
      cubeGroup.remove(cubeGroup.children[0]);
    }
    cubies.length = 0;

    const cubieSize = 0.94;
    const cubieGeo = new THREE.BoxGeometry(cubieSize, cubieSize, cubieSize);
    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0x12141a,
      roughness: 0.6,
      metalness: 0.1,
    });

    const stickerSize = 0.82;
    const stickerOffset = cubieSize / 2 + 0.005;
    const stickerGeo = new THREE.PlaneGeometry(stickerSize, stickerSize);

    // Create sticker planes for each face direction
    // Rotations to point planes in +X, -X, +Y, -Y, +Z, -Z
    const faceConfigs = [
      { dir: "R", pos: [stickerOffset, 0, 0], rot: [0, Math.PI / 2, 0], check: (x, y, z) => x === 1 },
      { dir: "L", pos: [-stickerOffset, 0, 0], rot: [0, -Math.PI / 2, 0], check: (x, y, z) => x === -1 },
      { dir: "U", pos: [0, stickerOffset, 0], rot: [-Math.PI / 2, 0, 0], check: (x, y, z) => y === 1 },
      { dir: "D", pos: [0, -stickerOffset, 0], rot: [Math.PI / 2, 0, 0], check: (x, y, z) => y === -1 },
      { dir: "F", pos: [0, 0, stickerOffset], rot: [0, 0, 0], check: (x, y, z) => z === 1 },
      { dir: "B", pos: [0, 0, -stickerOffset], rot: [0, Math.PI, 0], check: (x, y, z) => z === -1 },
    ];

    for (let x = -1; x <= 1; x++) {
      for (let y = -1; y <= 1; y++) {
        for (let z = -1; z <= 1; z++) {
          const cubie = new THREE.Mesh(cubieGeo, bodyMat);
          cubie.position.set(x, y, z);
          cubie.castShadow = true;
          cubie.receiveShadow = true;

          // Initial grid coordinates (x, y, z)
          cubie.userData = {
            gridPos: new THREE.Vector3(x, y, z),
            stickers: {},
          };

          // Attach sticker meshes
          faceConfigs.forEach((cfg) => {
            const isExterior = cfg.check(x, y, z);
            const mat = new THREE.MeshStandardMaterial({
              color: isExterior ? COLORS[cfg.dir] : COLORS.INTERNAL,
              roughness: 0.3,
              metalness: 0.05,
            });

            const sticker = new THREE.Mesh(stickerGeo, mat);
            sticker.position.set(...cfg.pos);
            sticker.rotation.set(...cfg.rot);
            sticker.visible = isExterior;

            cubie.add(sticker);
            cubie.userData.stickers[cfg.dir] = sticker;
          });

          cubeGroup.add(cubie);
          cubies.push(cubie);
        }
      }
    }
  }

  function animate() {
    requestAnimationFrame(animate);
    if (controls) controls.update();
    renderer.render(scene, camera);
  }

  // ==========================================
  // 2. Real-Time Face Rotation Animation
  // ==========================================

  /**
   * Rotate a face in 3D WebGL matching mechanical turn parameters.
   * @param {string} face - 'U', 'R', 'F', 'D', 'L', 'B'
   * @param {number} turns - 1 (+90° CW), -1 (-90° CCW), 2 (180°)
   * @param {number} durationMs - execution duration in ms
   */
  function rotateFace3D(face, turns, durationMs = 450) {
    return new Promise((resolve) => {
      isAnimating = true;

      // Axis and angle mapping in Three.js right-handed coordinates
      let axis = new THREE.Vector3();
      let angle = 0;
      let coordinateCheck = null;

      switch (face) {
        case "U":
          axis.set(0, 1, 0);
          angle = -turns * (Math.PI / 2);
          coordinateCheck = (c) => Math.round(c.position.y) === 1;
          break;
        case "D":
          axis.set(0, 1, 0);
          angle = turns * (Math.PI / 2);
          coordinateCheck = (c) => Math.round(c.position.y) === -1;
          break;
        case "R":
          axis.set(1, 0, 0);
          angle = -turns * (Math.PI / 2);
          coordinateCheck = (c) => Math.round(c.position.x) === 1;
          break;
        case "L":
          axis.set(1, 0, 0);
          angle = turns * (Math.PI / 2);
          coordinateCheck = (c) => Math.round(c.position.x) === -1;
          break;
        case "F":
          axis.set(0, 0, 1);
          angle = -turns * (Math.PI / 2);
          coordinateCheck = (c) => Math.round(c.position.z) === 1;
          break;
        case "B":
          axis.set(0, 0, 1);
          angle = turns * (Math.PI / 2);
          coordinateCheck = (c) => Math.round(c.position.z) === -1;
          break;
      }

      // Collect the 9 cubies in this face
      const faceCubies = cubies.filter(coordinateCheck);

      const pivot = new THREE.Object3D();
      pivot.rotation.set(0, 0, 0);
      scene.add(pivot);

      // Attach face cubies to pivot
      faceCubies.forEach((cubie) => {
        pivot.attach(cubie);
      });

      const startTime = performance.now();

      function updateRotation(now) {
        const elapsed = now - startTime;
        const progress = Math.min(1.0, elapsed / durationMs);

        // Ease in-out cubic
        const ease = progress < 0.5 ? 4 * progress * progress * progress : 1 - Math.pow(-2 * progress + 2, 3) / 2;

        pivot.rotation.set(axis.x * angle * ease, axis.y * angle * ease, axis.z * angle * ease);

        if (progress < 1.0) {
          requestAnimationFrame(updateRotation);
        } else {
          // Finish and snap
          pivot.rotation.set(axis.x * angle, axis.y * angle, axis.z * angle);
          pivot.updateMatrixWorld();

          faceCubies.forEach((cubie) => {
            cubeGroup.attach(cubie);
            // Snap position to integer values to prevent drift
            cubie.position.x = Math.round(cubie.position.x);
            cubie.position.y = Math.round(cubie.position.y);
            cubie.position.z = Math.round(cubie.position.z);
          });

          scene.remove(pivot);
          isAnimating = false;
          resolve();
        }
      }

      requestAnimationFrame(updateRotation);
    });
  }

  // ==========================================
  // 3. Cube State Mapping & 2D Net View
  // ==========================================

  // Map 54 facelet indices to (face, row, col) and 3D positions
  // Grid layout for 2D net:
  // U face: rows 0..2, cols 3..5
  // L face: rows 3..5, cols 0..2
  // F face: rows 3..5, cols 3..5
  // R face: rows 3..5, cols 6..8
  // B face: rows 3..5, cols 9..11
  // D face: rows 6..8, cols 3..5

  const NET_LAYOUT = [
    { face: "U", startRow: 0, startCol: 3, offset: 0 },
    { face: "L", startRow: 3, startCol: 0, offset: 36 },
    { face: "F", startRow: 3, startCol: 3, offset: 18 },
    { face: "R", startRow: 3, startCol: 6, offset: 9 },
    { face: "B", startRow: 3, startCol: 9, offset: 45 },
    { face: "D", startRow: 6, startCol: 3, offset: 27 },
  ];

  function build2DNetGrid() {
    dom.cubeNetGrid.innerHTML = "";

    // 9 rows x 12 columns
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 12; c++) {
        // Find if this cell corresponds to a facelet
        let faceletIndex = -1;
        let faceCode = "";

        for (const sec of NET_LAYOUT) {
          if (r >= sec.startRow && r < sec.startRow + 3 && c >= sec.startCol && c < sec.startCol + 3) {
            const subRow = r - sec.startRow;
            const subCol = c - sec.startCol;
            faceletIndex = sec.offset + subRow * 3 + subCol;
            faceCode = sec.face;
            break;
          }
        }

        if (faceletIndex >= 0) {
          const tile = document.createElement("div");
          tile.className = "net-tile";
          tile.dataset.index = faceletIndex;
          tile.dataset.face = faceCode;
          tile.style.backgroundColor = COLOR_HEX_STRINGS[currentCube[faceletIndex] || faceCode];
          tile.title = `${faceCode}${faceletIndex % 9 + 1}`;

          tile.addEventListener("click", () => {
            onNetTileClicked(faceletIndex);
          });

          dom.cubeNetGrid.appendChild(tile);
        } else {
          // Empty filler cell
          const empty = document.createElement("div");
          empty.style.width = "18px";
          empty.style.height = "18px";
          dom.cubeNetGrid.appendChild(empty);
        }
      }
    }
  }

  function update2DNetColors(cubeStr) {
    const tiles = dom.cubeNetGrid.querySelectorAll(".net-tile");
    tiles.forEach((tile) => {
      const idx = parseInt(tile.dataset.index, 10);
      const char = cubeStr[idx] || "U";
      tile.style.backgroundColor = COLOR_HEX_STRINGS[char] || "#333";
    });

    validateCubeColors(cubeStr);
  }

  function validateCubeColors(cubeStr) {
    if (!cubeStr || cubeStr.length !== 54) {
      dom.netValidityBadge.textContent = "Invalid length";
      dom.netValidityBadge.style.color = "var(--accent-red)";
      return false;
    }

    const counts = { U: 0, R: 0, F: 0, D: 0, L: 0, B: 0 };
    for (const ch of cubeStr) {
      if (counts[ch] !== undefined) counts[ch]++;
    }

    const isValid = Object.values(counts).every((cnt) => cnt === 9);
    if (isValid) {
      dom.netValidityBadge.textContent = "Valid (54)";
      dom.netValidityBadge.style.color = "var(--accent-green)";
    } else {
      dom.netValidityBadge.textContent = "Incomplete/Invalid";
      dom.netValidityBadge.style.color = "var(--accent-yellow)";
    }
    return isValid;
  }

  function onNetTileClicked(index) {
    // Center facelets cannot be repainted to preserve face orientation
    if (index % 9 === 4) {
      return;
    }
    const arr = currentCube.split("");
    arr[index] = activePaintColor;
    const newCube = arr.join("");
    currentCube = newCube;
    dom.cubeStringInput.value = currentCube;
    update2DNetColors(currentCube);
    applyStickersTo3DCube(currentCube);

    // Send update to server if valid
    if (validateCubeColors(currentCube)) {
      fetch("/api/cube", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cube: currentCube }),
      }).catch(console.error);
    }
  }

  /**
   * Map 54 facelet characters directly to 3D cubie exterior sticker meshes.
   */
  function applyStickersTo3DCube(cubeStr) {
    if (!cubeStr || cubeStr.length !== 54) return;

    // Build map from facelet positions to cubies and face normals
    // U (0..8): y = 1
    const uCoords = [
      [-1, 1, -1], [0, 1, -1], [1, 1, -1],
      [-1, 1,  0], [0, 1,  0], [1, 1,  0],
      [-1, 1,  1], [0, 1,  1], [1, 1,  1],
    ];
    // R (9..17): x = 1
    const rCoords = [
      [1,  1,  1], [1,  1,  0], [1,  1, -1],
      [1,  0,  1], [1,  0,  0], [1,  0, -1],
      [1, -1,  1], [1, -1,  0], [1, -1, -1],
    ];
    // F (18..26): z = 1
    const fCoords = [
      [-1,  1, 1], [0,  1, 1], [1,  1, 1],
      [-1,  0, 1], [0,  0, 1], [1,  0, 1],
      [-1, -1, 1], [0, -1, 1], [1, -1, 1],
    ];
    // D (27..35): y = -1
    const dCoords = [
      [-1, -1,  1], [0, -1,  1], [1, -1,  1],
      [-1, -1,  0], [0, -1,  0], [1, -1,  0],
      [-1, -1, -1], [0, -1, -1], [1, -1, -1],
    ];
    // L (36..44): x = -1
    const lCoords = [
      [-1,  1, -1], [-1,  1, 0], [-1,  1, 1],
      [-1,  0, -1], [-1,  0, 0], [-1,  0, 1],
      [-1, -1, -1], [-1, -1, 0], [-1, -1, 1],
    ];
    // B (45..53): z = -1
    const bCoords = [
      [ 1,  1, -1], [0,  1, -1], [-1,  1, -1],
      [ 1,  0, -1], [0,  0, -1], [-1,  0, -1],
      [ 1, -1, -1], [0, -1, -1], [-1, -1, -1],
    ];

    const faceSpecs = [
      { coords: uCoords, faceDir: "U", offset: 0 },
      { coords: rCoords, faceDir: "R", offset: 9 },
      { coords: fCoords, faceDir: "F", offset: 18 },
      { coords: dCoords, faceDir: "D", offset: 27 },
      { coords: lCoords, faceDir: "L", offset: 36 },
      { coords: bCoords, faceDir: "B", offset: 45 },
    ];

    faceSpecs.forEach((spec) => {
      spec.coords.forEach(([tx, ty, tz], idx) => {
        const char = cubeStr[spec.offset + idx];
        const hex = COLORS[char] || COLORS.INTERNAL;

        // Find cubie currently at (tx, ty, tz) in world space
        const targetCubie = cubies.find((c) => {
          return (
            Math.round(c.position.x) === tx &&
            Math.round(c.position.y) === ty &&
            Math.round(c.position.z) === tz
          );
        });

        if (targetCubie) {
          // Find which sticker on this cubie is currently facing in spec.faceDir
          // We compute the world direction of each sticker normal
          for (const [stkDir, stkMesh] of Object.entries(targetCubie.userData.stickers)) {
            const worldNormal = new THREE.Vector3();
            stkMesh.getWorldDirection(worldNormal);

            let isMatchingDir = false;
            if (spec.faceDir === "U" && worldNormal.y > 0.8) isMatchingDir = true;
            if (spec.faceDir === "D" && worldNormal.y < -0.8) isMatchingDir = true;
            if (spec.faceDir === "R" && worldNormal.x > 0.8) isMatchingDir = true;
            if (spec.faceDir === "L" && worldNormal.x < -0.8) isMatchingDir = true;
            if (spec.faceDir === "F" && worldNormal.z > 0.8) isMatchingDir = true;
            if (spec.faceDir === "B" && worldNormal.z < -0.8) isMatchingDir = true;

            if (isMatchingDir) {
              stkMesh.material.color.setHex(hex);
              stkMesh.visible = true;
            }
          }
        }
      });
    });
  }

  // ==========================================
  // 4. Server-Sent Events (SSE) Real-Time Sync
  // ==========================================

  function connectSSE() {
    if (sseSource) {
      sseSource.close();
    }

    sseSource = new EventSource("/api/events");

    sseSource.onopen = () => {
      dom.connectionBadge.className = "status-pill connected";
      dom.connectionBadge.querySelector(".label").textContent = "Connected (SSE)";
    };

    sseSource.onerror = () => {
      dom.connectionBadge.className = "status-pill disconnected";
      dom.connectionBadge.querySelector(".label").textContent = "Reconnecting...";
    };

    sseSource.addEventListener("status", (e) => {
      const data = JSON.parse(e.data);
      handleStatusUpdate(data);
    });

    sseSource.addEventListener("move_start", (e) => {
      const action = JSON.parse(e.data);
      handleMoveStart(action);
    });

    sseSource.addEventListener("move_done", (e) => {
      const data = JSON.parse(e.data);
      handleMoveDone(data);
    });

    sseSource.addEventListener("solve_completed", (e) => {
      const data = JSON.parse(e.data);
      handleSolveCompleted(data);
    });

    sseSource.addEventListener("log", (e) => {
      const entry = JSON.parse(e.data);
      appendTerminalLog(entry);
    });

    sseSource.addEventListener("actuators", (e) => {
      const actStates = JSON.parse(e.data);
      updateActuatorStates(actStates);
    });
  }

  function handleStatusUpdate(state) {
    currentCube = state.cube || SOLVED_CUBE;
    dom.cubeStringInput.value = currentCube;
    update2DNetColors(currentCube);
    applyStickersTo3DCube(currentCube);

    // Update state badge
    dom.solverStateBadge.className = `status-pill state-badge ${state.solver_state.toLowerCase()}`;
    dom.solverStateBadge.querySelector(".label").textContent = state.solver_state;

    // Hardware mode badge
    dom.hardwareBadge.querySelector(".label").textContent =
      state.hardware_mode === "serial" ? `STM32 (${state.serial_port})` : "Simulator";

    // Update buttons
    const isSolving = state.solver_state === "SOLVING";
    const isPaused = state.solver_state === "PAUSED";

    dom.btnSolve.disabled = isSolving;
    dom.btnPause.disabled = !isSolving;
    dom.btnPause.style.display = isPaused ? "none" : "inline-flex";
    dom.btnResume.style.display = isPaused ? "inline-flex" : "none";
    dom.btnResume.disabled = !isPaused;
    dom.btnStep.disabled = !isPaused;
    dom.btnStop.disabled = !isSolving && !isPaused;

    // Solution Tape
    renderSolutionTape(state.solution, state.current_step);
    dom.stepsSummaryBadge.textContent = `${state.solution ? state.solution.length : 0} moves`;

    // Progress
    const total = state.total_steps || 0;
    const curr = state.current_step || 0;
    const pct = total > 0 ? Math.round((curr / total) * 100) : state.is_solved ? 100 : 0;
    dom.progressBarFill.style.width = `${pct}%`;
    dom.progressText.textContent = total > 0 ? `Bước ${curr}/${total} (${pct}%)` : state.is_solved ? "Hoàn thành 100%" : "Sẵn sàng";
    dom.timeText.textContent = `${(state.elapsed_ms / 1000).toFixed(1)}s`;

    // Actuators
    if (state.actuators) {
      updateActuatorStates(state.actuators);
    }
  }

  async function handleMoveStart(action) {
    // HUD overlay in 3D canvas
    dom.motionHud.classList.add("active");
    dom.hudText.textContent = `${action.wire} (${action.duration_ms}ms)`;

    // Callout in left sidebar
    dom.activeMoveToken.textContent = action.token;
    dom.activeMoveDescVi.textContent = action.desc_vi || "";
    dom.activeMoveDescEn.textContent = action.desc_en || "";

    // Highlight in solution tape
    highlightSolutionTapeStep(action.step);

    // Trigger physical 3D rotation animation
    await rotateFace3D(action.face, action.turns, action.duration_ms);
  }

  function handleMoveDone(data) {
    dom.motionHud.classList.remove("active");
    dom.hudText.textContent = "Mechanical Idle";

    currentCube = data.cube;
    dom.cubeStringInput.value = currentCube;
    update2DNetColors(currentCube);
    applyStickersTo3DCube(currentCube);

    const total = data.total || 1;
    const curr = data.step || 0;
    const pct = Math.round((curr / total) * 100);
    dom.progressBarFill.style.width = `${pct}%`;
    dom.progressText.textContent = `Bước ${curr}/${total} (${pct}%)`;
  }

  function handleSolveCompleted(state) {
    dom.motionHud.classList.remove("active");
    dom.hudText.textContent = "Solved! (Hoàn thành)";
    dom.activeMoveToken.textContent = "✓";
    dom.activeMoveDescVi.textContent = "Rubik đã được giải hoàn toàn!";
    dom.activeMoveDescEn.textContent = "Cube is fully solved!";
    handleStatusUpdate(state);
  }

  function renderSolutionTape(moves, activeIndex = 0) {
    if (!moves || moves.length === 0) {
      dom.solutionTape.innerHTML = '<span class="tape-empty">Chưa có lời giải</span>';
      dom.movesRemainingText.textContent = "0 còn lại";
      return;
    }

    dom.solutionTape.innerHTML = "";
    moves.forEach((move, i) => {
      const pill = document.createElement("span");
      pill.className = "move-pill";
      pill.dataset.step = i + 1;
      pill.textContent = move;

      if (i + 1 < activeIndex) {
        pill.classList.add("done");
      } else if (i + 1 === activeIndex) {
        pill.classList.add("active");
      }

      dom.solutionTape.appendChild(pill);
    });

    const remaining = Math.max(0, moves.length - activeIndex);
    dom.movesRemainingText.textContent = `${remaining} còn lại`;
  }

  function highlightSolutionTapeStep(stepIndex) {
    const pills = dom.solutionTape.querySelectorAll(".move-pill");
    pills.forEach((p) => {
      const s = parseInt(p.dataset.step, 10);
      p.classList.remove("active");
      if (s < stepIndex) {
        p.classList.add("done");
      } else if (s === stepIndex) {
        p.classList.add("active");
        p.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
      }
    });
  }

  function updateActuatorStates(actuators) {
    for (const [key, state] of Object.entries(actuators)) {
      let el = null;
      if (key === "carriage_nw" || key === "tool_nw") el = document.getElementById("act_carriage_nw");
      if (key === "carriage_ne" || key === "tool_ne") el = document.getElementById("act_carriage_ne");
      if (key === "carriage_sw" || key === "tool_sw") el = document.getElementById("act_carriage_sw");
      if (key === "carriage_se" || key === "tool_se") el = document.getElementById("act_carriage_se");
      if (key === "center_lift" || key === "center_rotate") el = document.getElementById("act_center");

      if (el) {
        el.querySelector(".node-state").textContent = state;
        el.classList.remove("active", "turning");
        if (state === "ENGAGED" || state === "APPROACH") el.classList.add("active");
        if (state === "TURNING") el.classList.add("turning");
      }
    }
  }

  function appendTerminalLog(entry) {
    const row = document.createElement("div");
    row.className = "term-row";

    const dirClass =
      entry.direction === "->" ? "out" : entry.direction === "<-" ? "in" : entry.direction === "ERR" ? "err" : "info";

    row.innerHTML = `
      <span class="term-ts">[${entry.timestamp}]</span>
      <span class="term-dir ${dirClass}">${entry.direction}</span>
      <span class="term-msg">${entry.message}</span>
    `;

    dom.uartTerminal.appendChild(row);
    dom.uartTerminal.scrollTop = dom.uartTerminal.scrollHeight;
  }

  // ==========================================
  // 5. User Actions & Event Listeners
  // ==========================================

  function bindEvents() {
    // Solve button
    dom.btnSolve.addEventListener("click", () => {
      fetch("/api/solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cube: currentCube,
          face_turn_command: dom.settingFaceCmd.value,
          duration_ms: parseInt(dom.settingDuration.value, 10),
          mode: document.querySelector('input[name="hardwareMode"]:checked').value,
          port: dom.settingPort.value,
        }),
      }).catch(console.error);
    });

    // Playback controls
    dom.btnPause.addEventListener("click", () => fetch("/api/pause", { method: "POST" }));
    dom.btnResume.addEventListener("click", () => fetch("/api/resume", { method: "POST" }));
    dom.btnStep.addEventListener("click", () => fetch("/api/step", { method: "POST" }));
    dom.btnStop.addEventListener("click", () => fetch("/api/stop", { method: "POST" }));

    // Scramble buttons
    document.querySelectorAll(".scramble-buttons button").forEach((btn) => {
      btn.addEventListener("click", () => {
        const level = btn.dataset.level || "medium";
        fetch("/api/scramble", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ level }),
        })
          .then((res) => res.json())
          .then((data) => {
            dom.scrambleDisplay.innerHTML = `<strong>${level.toUpperCase()}:</strong> ${data.scramble || ""}`;
          })
          .catch(console.error);
      });
    });

    // Reset Cube
    dom.btnResetCube.addEventListener("click", () => {
      fetch("/api/reset", { method: "POST" })
        .then(() => {
          dom.scrambleDisplay.textContent = "Trạng thái cube đã giải";
        })
        .catch(console.error);
    });

    // Manual Moves keypad
    document.querySelectorAll(".btn-move").forEach((btn) => {
      btn.addEventListener("click", () => {
        const move = btn.dataset.move;
        if (move && !isAnimating) {
          fetch("/api/move", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ move }),
          }).catch(console.error);
        }
      });
    });

    // 3D View Presets
    document.querySelectorAll(".btn-view").forEach((btn) => {
      btn.addEventListener("click", () => {
        setCameraView(btn.dataset.view);
      });
    });

    // Color Palette Swatches
    dom.paletteButtons.querySelectorAll(".palette-swatch").forEach((swatch) => {
      swatch.addEventListener("click", () => {
        dom.paletteButtons.querySelectorAll(".palette-swatch").forEach((s) => s.classList.remove("active"));
        swatch.classList.add("active");
        activePaintColor = swatch.dataset.color;
      });
    });

    // Apply Cube String
    dom.btnApplyCubeString.addEventListener("click", () => {
      const val = dom.cubeStringInput.value.trim().toUpperCase();
      if (val.length === 54) {
        fetch("/api/cube", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cube: val }),
        }).catch(console.error);
      } else {
        alert("Chuỗi cube phải có đúng 54 ký tự (chỉ gồm U, R, F, D, L, B)!");
      }
    });

    // Clear Terminal Logs
    dom.btnClearLogs.addEventListener("click", () => {
      dom.uartTerminal.innerHTML = "";
    });

    // Vision GUI sync help
    const btnVisionHelp = document.getElementById("btnVisionHelp");
    if (btnVisionHelp) {
      btnVisionHelp.addEventListener("click", () => {
        const currentPort = window.location.port || "8080";
        alert(
          "CÁCH NHẬP TRẠNG THÁI TỪ CAMERA (run_vision_gui.py):\n\n" +
          "1. Chạy camera tool:\n   python scripts/run_vision_gui.py\n\n" +
          "2. Trong giao diện Vision GUI:\n" +
          "   - Căn chỉnh 6 mặt Rubik trước webcam để nhận diện màu.\n" +
          `   - Nhập ô 'Port' thành: ${currentPort} (cùng port với web server này)\n` +
          "   - Bấm nút 'Solve' trong Vision GUI.\n\n" +
          "3. KẾT QUẢ:\n" +
          "   Cube nhận diện từ camera sẽ TỰ ĐỘNG truyền thẳng vào website này và mô hình 3D sẽ cập nhật ngay lập tức!\n\n" +
          "Hoặc bạn có thể copy chuỗi 54 ký tự in ra ở terminal của run_vision_gui.py và paste vào ô bên trên rồi bấm 'Áp Dụng'."
        );
      });
    }

    // Settings Modal
    dom.btnOpenSettings.addEventListener("click", () => {
      dom.settingsModal.style.display = "flex";
    });
    dom.btnCloseSettings.addEventListener("click", () => {
      dom.settingsModal.style.display = "none";
    });
    dom.settingDuration.addEventListener("input", (e) => {
      dom.durationVal.textContent = e.target.value;
    });
    dom.btnSaveSettings.addEventListener("click", () => {
      dom.settingsModal.style.display = "none";
      const mode = document.querySelector('input[name="hardwareMode"]:checked').value;
      dom.hardwareBadge.querySelector(".label").textContent =
        mode === "serial" ? `STM32 (${dom.settingPort.value})` : "Simulator";
    });

    // Check for query param ?cube=... in URL
    const urlParams = new URLSearchParams(window.location.search);
    const initialCube = urlParams.get("cube");
    if (initialCube && initialCube.length === 54) {
      dom.cubeStringInput.value = initialCube;
      fetch("/api/cube", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cube: initialCube }),
      }).catch(console.error);
    }
  }

  // ==========================================
  // Initialization
  // ==========================================
  window.addEventListener("DOMContentLoaded", () => {
    initThreeScene();
    build2DNetGrid();
    bindEvents();
    connectSSE();

    // Initial status fetch
    fetch("/api/status")
      .then((res) => res.json())
      .then(handleStatusUpdate)
      .catch(console.error);
  });
})();
