/* Rubik Studio: local UI. No physical movement is sent by this frontend. */
"use strict";
const $ = (id) => document.getElementById(id);
const FACE_ORDER = "URFDLB";
const FACE_COLORS = {
  U: "white",
  R: "red",
  F: "green",
  D: "yellow",
  L: "orange",
  B: "blue",
};
const COLOR_HEX = {
  white: "#f4f5f7",
  red: "#ee5261",
  green: "#29bf91",
  yellow: "#f6ce50",
  orange: "#ff943e",
  blue: "#4387ec",
  unknown: "#455469",
};
const COLOR_NAMES = {
  white: "Trắng",
  red: "Đỏ",
  green: "Xanh lá",
  yellow: "Vàng",
  orange: "Cam",
  blue: "Xanh biển",
};
const EXAMPLE = "DUUBULDBFRBFRRULLLBRDFFFBLURDBFDFDRFRULBLUFDURRBLBDUDL";
const DEFAULT_ROI = [
  [0.28, 0.2],
  [0.72, 0.2],
  [0.72, 0.8],
  [0.28, 0.8],
];
let state = {
  camera: {
    colors: [],
    confidence: [],
    stable: 0,
    seq: 0,
    corners: DEFAULT_ROI,
    calibration: [],
  },
  faces: {},
};
let currentTab = "guide",
  level = "easy",
  paint = "white",
  task = null;
let selectingROI = false,
  selectedPoints = [],
  demoTimer = null,
  toastTimer = null;
const drafts = {};

/** Input: API URL/body. Output: decoded response; throws server's error. */
async function api(path, body) {
  const response = await fetch(
    path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error || "Không kết nối được máy chủ.");
  return data;
}

/** Input: message and success flag. Output: accessible transient notice. */
function notify(message, success = false) {
  $("notice").textContent = message;
  $("notice").className = success ? "success" : "";
  $("notice").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(
    () => {
      $("notice").hidden = true;
    },
    success ? 5500 : 14000,
  );
}

/** Input: action button and async operation. Output: busy state and errors shown in UI. */
async function action(button, operation) {
  button.disabled = true;
  try {
    await operation();
    await refresh();
  } catch (error) {
    notify(error.message);
  } finally {
    button.disabled = false;
  }
}

/** Input: mode name. Output: corresponding workspace and navigation. */
function switchTab(tab) {
  currentTab = tab;
  const headings = {
    guide: [
      "Nhìn rõ. Xoay đúng.",
      "Quét trạng thái, tìm lời giải và theo từng bước ngay trên camera.",
      "Hướng dẫn giải",
    ],
    scramble: [
      "Một khối. Ba thử thách.",
      "Tạo bộ đề có thể tái lập, kiểm chứng lời giải và xuất từng lệnh xoay.",
      "Tạo bộ đề",
    ],
    auto: [
      "Sáu mặt. Một quy trình.",
      "Quét theo tư thế cố định, xác minh trạng thái và xuất lời giải cho UART.",
      "Giải tự động",
    ],
  };
  $("page-title").textContent = headings[tab][0];
  $("page-subtitle").textContent = headings[tab][1];
  $("breadcrumb").textContent = headings[tab][2];
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tab);
    button.setAttribute(
      "aria-current",
      button.dataset.tab === tab ? "page" : "false",
    );
  });
  $("camera-workspace").hidden = tab === "scramble";
  $("scramble-workspace").hidden = tab !== "scramble";
  $("guide-panel").hidden = tab !== "guide";
  $("auto-panel").hidden = tab !== "auto";
  $("scan-settings").hidden = tab === "guide";
  $("face-editor-tools").hidden = tab === "guide";
  $("camera-overlay").toggleAttribute("hidden", tab === "guide");
  $("roi-hint").textContent =
    tab === "guide" ? "ĐƯỜNG BAO & MŨI TÊN TRỰC TIẾP" : "KHUNG LẤY MẪU 3×3";
  $("open-camera-main").textContent =
    tab === "guide" ? "Bắt đầu quét & hướng dẫn" : "Mở camera Logitech";
  render();
}

/** Input: container, move list and current index. Output: safe move token elements. */
function drawMoves(container, moves, index = -1) {
  container.replaceChildren();
  moves.forEach((move, i) => {
    const token = document.createElement("span");
    token.className =
      "move-token" + (i === index ? " current" : i < index ? " done" : "");
    token.textContent = move;
    container.append(token);
  });
}

/** Input: nine colors or face letters. Output: visible 3×3 grid. */
function drawMini(container, values) {
  container.replaceChildren();
  for (let i = 0; i < 9; i++) {
    const tile = document.createElement("span");
    tile.className = "sticker";
    tile.style.background =
      COLOR_HEX[FACE_COLORS[values[i]] || values[i] || "unknown"];
    container.append(tile);
  }
}

/** Input: net element, face grids and edit flag. Output: canonical URFDLB face net. */
function drawNet(container, faces, editable = false) {
  const offsets = {
    U: [3, 0],
    R: [6, 3],
    F: [3, 3],
    D: [3, 6],
    L: [0, 3],
    B: [9, 3],
  };
  container.replaceChildren();
  for (const face of FACE_ORDER) {
    const grid = document.createElement("div");
    grid.className = "net-face";
    grid.style.gridColumn = `${offsets[face][0] + 1} / span 3`;
    grid.style.gridRow = `${offsets[face][1] + 1} / span 3`;
    const values =
      (editable && drafts[face]) ||
      faces[face] ||
      Array.from({ length: 9 }, (_, i) =>
        i === 4 ? FACE_COLORS[face] : "unknown",
      );
    values.forEach((color, i) => {
      const tile = document.createElement(editable ? "button" : "span");
      tile.className = "sticker";
      tile.style.background = COLOR_HEX[color];
      tile.textContent = i === 4 ? face : "";
      tile.title = `${face}${i + 1}: ${COLOR_NAMES[color] || "Chưa ghi"}`;
      if (editable)
        tile.addEventListener("click", () => editSticker(face, i, values));
      grid.append(tile);
    });
    container.append(grid);
  }
}

/** Input: face/index/current colors. Output: edited face, persisted when all colors exist. */
async function editSticker(face, index, values) {
  if (
    state.scan &&
    !["complete", "cancelled", "error"].includes(state.scan.status)
  ) {
    notify("Huỷ lượt quét trước khi sửa màu.");
    return;
  }
  drafts[face] = values.slice();
  drafts[face][index] = paint;
  drawNet($("cube-net"), state.faces, true);
  if (drafts[face].every((color) => color !== "unknown")) {
    try {
      await api("/api/faces/capture", { face, colors: drafts[face] });
      delete drafts[face];
      await refresh();
    } catch (error) {
      notify(error.message);
    }
  }
}

/** Input: normalized point inside ROI. Output: bilinear overlay coordinate. */
function roiPoint(u, v, corners) {
  return [0, 1].map(
    (axis) =>
      1000 *
      ((1 - u) * (1 - v) * corners[0][axis] +
        u * (1 - v) * corners[1][axis] +
        u * v * corners[2][axis] +
        (1 - u) * v * corners[3][axis]),
  );
}

/** Input: scan camera ROI. Output: grid and editable perspective points. */
function drawOverlay() {
  const corners = state.camera.corners || DEFAULT_ROI,
    group = $("roi-drawing");
  group.replaceChildren();
  const polygon = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "polygon",
  );
  polygon.setAttribute(
    "points",
    corners.map((p) => p.map((v) => v * 1000).join(",")).join(" "),
  );
  polygon.setAttribute("fill", "none");
  polygon.setAttribute("stroke", "#76d5bc");
  polygon.setAttribute("stroke-width", "2");
  group.append(polygon);
  for (const fraction of [1 / 3, 2 / 3])
    for (const vertical of [true, false]) {
      const line = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "line",
      );
      const a = roiPoint(
          vertical ? fraction : 0,
          vertical ? 0 : fraction,
          corners,
        ),
        b = roiPoint(vertical ? fraction : 1, vertical ? 1 : fraction, corners);
      for (const [key, value] of Object.entries({
        x1: a[0],
        y1: a[1],
        x2: b[0],
        y2: b[1],
        stroke: "#76d5bc88",
        "stroke-width": 1,
      }))
        line.setAttribute(key, value);
      group.append(line);
    }
  if (selectingROI)
    selectedPoints.forEach((p, i) => {
      const dot = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "circle",
      );
      dot.setAttribute("cx", p[0] * 1000);
      dot.setAttribute("cy", p[1] * 1000);
      dot.setAttribute("r", 10);
      dot.setAttribute("fill", "#e7ff89");
      group.append(dot);
    });
}

/** Input: backend status. Output: camera, workflow and result components. */
function render() {
  const tutorial = state.tutorial || {
      phase: "idle",
      faces: {},
      colors: [],
      stable: 0,
      seq: 0,
    },
    useTutorial = currentTab === "guide",
    camera = useTutorial
      ? {
          ...state.camera,
          running: tutorial.running,
          index: tutorial.camera_index ?? 1,
          backend: tutorial.backend || "dshow",
          colors: tutorial.colors,
          seq: tutorial.seq,
          stable: tutorial.stable,
          error: tutorial.error,
          ready: tutorial.colors.length === 9,
          confidence: [],
          reason: "Đang tìm đủ 9 ô bằng đường bao.",
        }
      : state.camera,
    stable = camera.stable || 0;
  $("connection").textContent = "đã kết nối";
  $("camera-metric").textContent = camera.running
    ? `ID ${camera.index} · ${camera.backend}`
    : "Chưa mở";
  $("camera-info").textContent = `USB · ID ${camera.index} · ${camera.backend}`;
  $("calibration-metric").textContent = useTutorial
    ? "BGR"
    : camera.calibration.length;
  $("color-metric-label").textContent = useTutorial
    ? "BỘ NHẬN DIỆN"
    : "MÀU ĐÃ HIỆU CHỈNH";
  $("calibration-unit").hidden = useTutorial;
  $("faces-metric").textContent = Object.keys(
    useTutorial ? tutorial.faces : state.scan?.faces || state.faces,
  ).length;
  $("camera-dot").classList.toggle("on", camera.running && !camera.error);
  const required = useTutorial ? (tutorial.phase === "guiding" ? 10 : 5) : 8;
  $("stability-dot").classList.toggle("on", stable >= required);
  $("stability-text").textContent =
    camera.error ||
    (!camera.ready
      ? camera.reason || "Màu chưa đủ tin cậy"
      : stable >= required
        ? "Đã nhận đủ mẫu màu"
        : `Đang lấy mẫu ${stable}/${required} khung hình`);
  $("stability-bar").style.width = `${Math.min(stable / required, 1) * 100}%`;
  $("confidence").textContent = camera.confidence.length
    ? `${Math.round(Math.min(...camera.confidence) * 100)}% min`
    : "—";
  const hasFrame =
    camera.seq > 0 && (useTutorial || (camera.running && !camera.error));
  $("camera-image").hidden = !hasFrame;
  $("camera-placeholder").hidden = hasFrame;
  if (hasFrame && !$("camera-image").dataset.loading) {
    $("camera-image").dataset.loading = "1";
    $("camera-image").src =
      `${useTutorial ? "/api/tutorial/frame.jpg" : "/api/frame.jpg"}?t=${camera.seq}`;
  }
  document
    .querySelectorAll("[data-calibrate]")
    .forEach((button) =>
      button.classList.toggle(
        "saved",
        camera.calibration.includes(FACE_COLORS[button.dataset.calibrate]),
      ),
    );
  $("calibration-status").textContent = state.calibration_error
    ? `Profile cần kiểm tra: ${state.calibration_error}`
    : `Đã lưu ${camera.calibration.length}/6 mẫu. ${camera.calibration.length === 6 ? "Đang dùng LAB đã hiệu chỉnh." : "Dùng ngưỡng màu BGR khi chưa đủ mẫu."}`;
  drawMini($("live-colors"), camera.colors);
  drawNet(
    $("cube-net"),
    useTutorial ? tutorial.faces : state.faces,
    !useTutorial,
  );
  $("workflow-metric").textContent =
    state.scan &&
    !["complete", "cancelled", "error"].includes(state.scan.status)
      ? "Đang quét"
      : tutorial.running
        ? "Đang hướng dẫn"
        : "Sẵn sàng";
  $("guide-empty").hidden = tutorial.phase !== "idle";
  $("guide-active").hidden = tutorial.phase === "idle";
  if (tutorial.phase !== "idle") {
    $("guide-move").textContent =
      tutorial.phase === "complete" ? "✓" : tutorial.move || "SCAN";
    $("guide-counter").textContent =
      `${tutorial.index || 0}/${tutorial.solution?.count || 0}`;
    $("guide-instruction").textContent =
      [tutorial.instruction, tutorial.error].filter(Boolean).join(" · ") ||
      tutorial.phase;
    drawMoves($("guide-moves"), tutorial.solution?.moves || [], tutorial.index);
  }
  if (state.solution) {
    $("solution-count").textContent = `${state.solution.count} NƯỚC`;
    drawMoves($("solution-moves"), state.solution.moves);
    $("solution-uart").textContent =
      state.solution.uart.join("\n") || "# Cube đã giải, không cần lệnh.";
    if (document.activeElement !== $("cube-string"))
      $("cube-string").value = state.solution.state;
  } else {
    $("solution-count").textContent = "—";
    $("solution-moves").textContent = "Chưa có lời giải.";
    $("solution-uart").textContent = "# Chưa có lệnh";
  }
  renderScan();
  drawOverlay();
}

/** Input: public scan. Output: pending capture/ACK and route progress. */
function renderScan() {
  const scan = state.scan;
  $("ack-scan").hidden = true;
  if (!scan) {
    $("scan-current").textContent = "Chưa bắt đầu lượt quét.";
    $("scan-route").replaceChildren();
    return;
  }
  const next = scan.next;
  const messages = {
    complete: "Đã quét đủ 6 mặt, trả về tư thế gốc và xác minh lời giải.",
    cancelled: "Đã huỷ. Đặt khối về tư thế ban đầu trước lần quét mới.",
    error: `Không giải được trạng thái: ${scan.error}`,
    capturing: `Đang chờ mặt ${next?.face} ổn định dưới camera…`,
    waiting_done: `Chờ hoàn tất: ${next?.uart}`,
  };
  $("scan-current").textContent =
    (scan.mode === "demo" ? "[MÔ PHỎNG] " : "") +
    (messages[scan.status] || scan.status) +
    (scan.error && scan.status !== "error" ? ` ${scan.error}` : "");
  $("ack-scan").hidden = !(
    scan.status === "waiting_done" && scan.mode === "manual"
  );
  $("scan-route").replaceChildren();
  scan.route.forEach((step, i) => {
    const li = document.createElement("li");
    li.className = i === scan.index ? "current" : i < scan.index ? "done" : "";
    const number = document.createElement("span");
    number.textContent = String(step.id).padStart(2, "0");
    li.append(
      number,
      document.createTextNode(
        step.kind === "capture" ? `Chụp mặt ${step.face}` : step.uart,
      ),
    );
    $("scan-route").append(li);
  });
}

/** Input: none. Output: one refreshed status; does not access camera device itself. */
async function refresh() {
  state = await api("/api/status");
  render();
}

/** Input: none. Output: bounded sequential polling, with visible connection failures. */
async function poll() {
  try {
    await refresh();
  } catch (error) {
    $("connection").textContent = "mất kết nối";
  }
  setTimeout(poll, 450);
}

/** Input: filename and text/JSON. Output: browser download, no UART transmission. */
function download(name, value) {
  const isText = typeof value === "string";
  const blob = new Blob([isText ? value : JSON.stringify(value, null, 2)], {
    type: isText ? "text/plain;charset=utf-8" : "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Input: generated task. Output: distinct scramble/solution displays and target state. */
function renderTask() {
  $("scramble-result").hidden = false;
  $("scramble-count").textContent = `${task.scramble.length} NƯỚC TRỘN`;
  drawMoves($("scramble-moves"), task.scramble);
  $("scramble-uart").textContent = task.scramble_uart.join("\n");
  $("task-solution-count").textContent = `${task.solution.count} NƯỚC GIẢI`;
  drawMoves($("task-solution-moves"), task.solution.moves);
  $("task-solution-uart").textContent = task.solution.uart.join("\n");
  const faces = {};
  for (let i = 0; i < 6; i++)
    faces[FACE_ORDER[i]] = [...task.state.slice(i * 9, i * 9 + 9)].map(
      (f) => FACE_COLORS[f],
    );
  drawNet($("scramble-net"), faces);
}

/** Input: none. Output: one acknowledged/captured demo stage, until completion. */
async function runDemo() {
  if (
    state.scan?.mode !== "demo" ||
    ["complete", "cancelled", "error"].includes(state.scan.status)
  )
    return;
  try {
    await api("/api/scan/demo-step", {});
    await refresh();
    demoTimer = setTimeout(runDemo, 650);
  } catch (error) {
    notify(error.message);
  }
}

/** Input: none. Output: known valid example stored as six editable faces. */
async function loadExample() {
  clearTimeout(demoTimer);
  await api("/api/clear", {});
  Object.keys(drafts).forEach((key) => delete drafts[key]);
  for (let i = 0; i < 6; i++)
    await api("/api/faces/capture", {
      face: FACE_ORDER[i],
      colors: [...EXAMPLE.slice(i * 9, i * 9 + 9)].map((f) => FACE_COLORS[f]),
    });
  notify(
    "Đã nạp cube mẫu. Đây là dữ liệu mô phỏng, không phải trạng thái camera.",
    true,
  );
}

/** Input: none. Output: events bound once; no camera opens automatically. */
function initialize() {
  document
    .querySelectorAll("[data-tab]")
    .forEach((button) =>
      button.addEventListener("click", () => switchTab(button.dataset.tab)),
    );
  document.querySelectorAll("[data-level]").forEach((button) =>
    button.addEventListener("click", () => {
      level = button.dataset.level;
      document
        .querySelectorAll("[data-level]")
        .forEach((other) => other.classList.toggle("active", other === button));
    }),
  );
  for (const [face, color] of Object.entries(FACE_COLORS)) {
    const button = document.createElement("button");
    button.dataset.calibrate = face;
    button.innerHTML = `<span class="swatch" style="background:${COLOR_HEX[color]}"></span>${face} · ${COLOR_NAMES[color]}`;
    button.addEventListener("click", () =>
      action(button, async () => {
        await api("/api/calibrate", { face });
        notify(`Đã lưu mẫu tâm ${COLOR_NAMES[color]}.`, true);
      }),
    );
    $("calibration-buttons").append(button);
    const swatch = document.createElement("button");
    swatch.style.background = COLOR_HEX[color];
    swatch.title = COLOR_NAMES[color];
    swatch.setAttribute("aria-label", `Tô màu ${COLOR_NAMES[color]}`);
    swatch.className = color === paint ? "active" : "";
    swatch.addEventListener("click", () => {
      paint = color;
      $("paint-palette")
        .querySelectorAll("button")
        .forEach((item) => item.classList.toggle("active", item === swatch));
    });
    $("paint-palette").append(swatch);
  }
  for (const id of ["open-camera-main", "open-camera"])
    $(id).addEventListener("click", () =>
      action($(id), () =>
        api(
          currentTab === "guide" ? "/api/tutorial/start" : "/api/camera/start",
          {
            index: Number($("camera-id").value),
            backend: $("camera-backend").value,
          },
        ),
      ),
    );
  $("stop-camera").addEventListener("click", () =>
    action($("stop-camera"), () =>
      api(
        currentTab === "guide" ? "/api/tutorial/stop" : "/api/camera/stop",
        {},
      ),
    ),
  );
  $("camera-image").addEventListener("load", () => {
    delete $("camera-image").dataset.loading;
  });
  $("camera-image").addEventListener("error", () => {
    delete $("camera-image").dataset.loading;
  });
  $("detector").addEventListener("change", () =>
    action($("detector"), () =>
      api("/api/camera/config", { mode: $("detector").value }),
    ),
  );
  $("select-roi").addEventListener("click", () => {
    selectingROI = true;
    selectedPoints = [];
    $("camera-overlay").classList.add("selecting");
    notify("Bấm 4 góc: trái-trên → phải-trên → phải-dưới → trái-dưới.", true);
  });
  $("camera-overlay").addEventListener("click", async (event) => {
    if (!selectingROI) return;
    const rect = $("camera-overlay").getBoundingClientRect();
    selectedPoints.push([
      (event.clientX - rect.left) / rect.width,
      (event.clientY - rect.top) / rect.height,
    ]);
    drawOverlay();
    if (selectedPoints.length === 4) {
      selectingROI = false;
      $("camera-overlay").classList.remove("selecting");
      try {
        await api("/api/camera/config", { corners: selectedPoints });
        await refresh();
      } catch (error) {
        notify(error.message);
      }
    }
  });
  $("reset-roi").addEventListener("click", () =>
    action($("reset-roi"), () =>
      api("/api/camera/config", { corners: DEFAULT_ROI }),
    ),
  );
  $("clear-faces").addEventListener("click", () =>
    action($("clear-faces"), async () => {
      clearTimeout(demoTimer);
      Object.keys(drafts).forEach((key) => delete drafts[key]);
      await api("/api/clear", {});
    }),
  );
  $("start-guide").addEventListener("click", () =>
    action($("start-guide"), async () => {
      await api("/api/tutorial/start", {
        index: Number($("camera-id").value),
        backend: $("camera-backend").value,
      });
      notify(
        "Đưa lần lượt F → U → D → R → L → B theo lời nhắc. Sau đó làm theo mũi tên trực tiếp trên video.",
        true,
      );
    }),
  );
  $("stop-guide").addEventListener("click", () =>
    action($("stop-guide"), () => api("/api/tutorial/stop", {})),
  );
  $("solve-string").addEventListener("click", () =>
    action($("solve-string"), () =>
      api("/api/solve", { state: $("cube-string").value.trim() }),
    ),
  );
  $("load-example").addEventListener("click", () =>
    action($("load-example"), loadExample),
  );
  $("generate-scramble").addEventListener("click", () =>
    action($("generate-scramble"), async () => {
      const value = $("scramble-seed").value;
      task = await api("/api/scramble", {
        level,
        seed: value === "" ? null : Number(value),
      });
      renderTask();
    }),
  );
  $("export-scramble").addEventListener("click", () => {
    if (task)
      download(
        `rubik-${task.level}-TRON.txt`,
        task.scramble_uart.join("\n") + "\n",
      );
  });
  $("export-task").addEventListener("click", () => {
    if (task) download(`rubik-${task.level}.json`, task);
  });
  $("export-task-solution").addEventListener("click", () => {
    if (task)
      download(
        `rubik-${task.level}-GIAI.txt`,
        task.solution.uart.join("\n") + "\n",
      );
  });
  $("export-solution").addEventListener("click", () => {
    if (state.solution)
      download("rubik-GIAI.txt", state.solution.uart.join("\n") + "\n");
    else notify("Chưa có lời giải để xuất.");
  });
  $("start-scan").addEventListener("click", () =>
    action($("start-scan"), async () => {
      clearTimeout(demoTimer);
      Object.keys(drafts).forEach((key) => delete drafts[key]);
      await api("/api/scan/start", { mode: $("scan-mode").value });
      await refresh();
      if ($("scan-mode").value === "demo") runDemo();
    }),
  );
  $("ack-scan").addEventListener("click", () =>
    action($("ack-scan"), () =>
      api("/api/scan/ack", { id: state.scan.next.id, result: "DONE" }),
    ),
  );
  $("cancel-scan").addEventListener("click", () =>
    action($("cancel-scan"), async () => {
      clearTimeout(demoTimer);
      await api("/api/scan/cancel", {});
    }),
  );
  $("export-route").addEventListener("click", () =>
    action($("export-route"), async () => {
      const plan = await api("/api/scan");
      download("rubik-SCAN-PLAN.json", {
        frame: "+X=R,+Y=U,+Z=F; camera up=B/right=R",
        requires:
          "Whole-cube X/Z reorientation; external controller must send DONE",
        route: plan.route,
      });
    }),
  );
  switchTab("guide");
  poll();
}
initialize();
