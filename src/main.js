/**
 * CA-410 色度分析仪 — 主逻辑
 * 状态机驱动测量流程
 */

import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { getCurrentWindow, Window } from "@tauri-apps/api/window";
import { save } from "@tauri-apps/plugin-dialog";

let displayWindow = null;
let portPath = null;

// =============================================
// State Machine
// =============================================
const State = {
  IDLE: "IDLE",
  CONNECTING: "CONNECTING",
  CONNECTED: "CONNECTED",
  MEASURING: "MEASURING",
  COMPLETED: "COMPLETED",
  ERROR: "ERROR",
};

let currentState = State.IDLE;
let measuredData = []; // [{gray, x, y, lv}]
let abortRequested = false;
let displayX = 0, displayY = 0, displayW = 512, displayH = 512;
let startGray = 0, endGray = 255;
let colorMode = "white";

function setState(newState) {
  currentState = newState;
  updateUI();
}

function updateUI() {
  const btnStart = document.getElementById("btn-start");
  const btnStop = document.getElementById("btn-stop");
  const btnReset = document.getElementById("btn-reset");
  const inputs = document.querySelectorAll(".param-input");
  const radios = document.querySelectorAll('input[name="color-mode"]');

  switch (currentState) {
    case State.IDLE:
      btnStart.disabled = false;
      btnStop.disabled = true;
      btnReset.disabled = false;
      inputs.forEach(i => i.disabled = false);
      radios.forEach(r => r.disabled = false);
      break;
    case State.CONNECTING:
      btnStart.disabled = true;
      btnStop.disabled = true;
      btnReset.disabled = true;
      inputs.forEach(i => i.disabled = true);
      radios.forEach(r => r.disabled = true);
      break;
    case State.CONNECTED:
      btnStart.disabled = true;
      btnStop.disabled = false;
      btnReset.disabled = true;
      inputs.forEach(i => i.disabled = true);
      radios.forEach(r => r.disabled = true);
      break;
    case State.MEASURING:
      btnStart.disabled = true;
      btnStop.disabled = false;
      btnReset.disabled = true;
      inputs.forEach(i => i.disabled = true);
      radios.forEach(r => r.disabled = true);
      break;
    case State.COMPLETED:
      btnStart.disabled = false;
      btnStop.disabled = true;
      btnReset.disabled = false;
      inputs.forEach(i => i.disabled = false);
      radios.forEach(r => r.disabled = false);
      break;
    case State.ERROR:
      btnStart.disabled = false;
      btnStop.disabled = true;
      btnReset.disabled = false;
      inputs.forEach(i => i.disabled = false);
      radios.forEach(r => r.disabled = false);
      break;
  }
}

// =============================================
// Logging
// =============================================
function log(msg) {
  const area = document.getElementById("log-area");
  const ts = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  area.value += `[${ts}] ${msg}\n`;
  area.scrollTop = area.scrollHeight;
}

function logClear() {
  document.getElementById("log-area").value = "";
}

// =============================================
// Preview Canvas
// =============================================
function updatePreview(gray) {
  const canvas = document.getElementById("preview-canvas");
  const ctx = canvas.getContext("2d");
  const [r, g, b] = grayToRGB(gray);
  ctx.fillStyle = `rgb(${r},${g},${b})`;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  document.getElementById("current-gray").textContent = gray;
  document.getElementById("current-rgb").textContent = `(${r},${g},${b})`;
}

function grayToRGB(gray) {
  switch (colorMode) {
    case "white": return [gray, gray, gray];
    case "red":   return [gray, 0, 0];
    case "green": return [0, gray, 0];
    case "blue":  return [0, 0, gray];
    default:      return [gray, gray, gray];
  }
}

// =============================================
// Progress
// =============================================
function updateProgress(current, total) {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0;
  document.getElementById("progress-bar").style.width = pct + "%";
  document.getElementById("progress-percent").textContent = pct + "%";
  document.getElementById("progress-text").textContent = `${current} / ${total}`;
}

// =============================================
// Data Table
// =============================================
function addDataRow(gray, x, y, lv) {
  const tbody = document.getElementById("data-tbody");
  const tr = document.createElement("tr");
  tr.innerHTML = `<td>${gray}</td><td>${x.toFixed(4)}</td><td>${y.toFixed(4)}</td><td>${lv.toFixed(4)}</td>`;
  tbody.appendChild(tr);
  tbody.parentElement.parentElement.scrollTop = tbody.parentElement.parentElement.scrollHeight;
}

function clearDataTable() {
  document.getElementById("data-tbody").innerHTML = "";
}

// =============================================
// Display Window
// =============================================
async function openDisplayWindow(x, y, w, h, gray) {
  try {
    const { WebviewWindow } = await import("@tauri-apps/api/webviewWindow");
    const { launchWebview } = await import("@tauri-apps/api/webview");

    if (displayWindow) {
      try { await displayWindow.close(); } catch {}
    }

    displayWindow = new WebviewWindow("display", {
      url: "display.html",
      title: "打屏窗口",
      width: w,
      height: h,
      x: x,
      y: y,
      alwaysOnTop: true,
      resizable: false,
      decorations: false,
      closable: false,
      focus: false,
    });

    displayWindow.once("tauri://created", () => {
      const [r, g, b] = grayToRGB(gray);
      displayWindow.emit("set-color", { r, g, b, gray });
    });

    displayWindow.once("tauri://error", (e) => {
      log(`打屏窗口创建失败: ${e}`);
    });
  } catch (e) {
    log(`打屏窗口错误: ${e}`);
  }
}

async function updateDisplayColor(gray) {
  if (!displayWindow) return;
  try {
    const [r, g, b] = grayToRGB(gray);
    await displayWindow.emit("set-color", { r, g, b, gray });
  } catch (e) {
    // ignore
  }
}

async function closeDisplayWindow() {
  if (!displayWindow) return;
  try {
    await displayWindow.close();
  } catch {}
  displayWindow = null;
}

// =============================================
// Modal
// =============================================
function showModal(title, message) {
  let overlay = document.querySelector(".modal-overlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML = `
      <div class="modal-box">
        <h2 id="modal-title"></h2>
        <p id="modal-msg"></p>
        <button id="modal-close" class="btn btn-start">确定</button>
      </div>`;
    document.body.appendChild(overlay);
    overlay.querySelector("#modal-close").addEventListener("click", () => {
      overlay.classList.add("hidden");
    });
  }
  overlay.querySelector("#modal-title").textContent = title;
  overlay.querySelector("#modal-msg").textContent = message;
  overlay.classList.remove("hidden");
}

// =============================================
// Theme
// =============================================
function initTheme() {
  const stored = localStorage.getItem("theme") || "dark";
  applyTheme(stored);
  document.getElementById("theme-toggle").addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    applyTheme(next);
    localStorage.setItem("theme", next);
  });
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  document.getElementById("theme-toggle").textContent = theme === "dark" ? "🌙" : "☀️";
}

// =============================================
// Parameter Reading
// =============================================
function readParams() {
  displayX = parseInt(document.getElementById("param-x").value) || 0;
  displayY = parseInt(document.getElementById("param-y").value) || 0;
  displayW = parseInt(document.getElementById("param-width").value) || 512;
  displayH = parseInt(document.getElementById("param-height").value) || 512;
  startGray = parseInt(document.getElementById("param-start").value) || 0;
  endGray = parseInt(document.getElementById("param-end").value) || 255;
  colorMode = document.querySelector('input[name="color-mode"]:checked').value || "white";
}

function validateParams() {
  if (displayW < 1 || displayH < 1) {
    showModal("参数错误", "宽度和高度必须 ≥ 1");
    return false;
  }
  if (startGray < 0 || endGray > 255 || startGray > endGray) {
    showModal("参数错误", "灰阶范围无效（开始 ≤ 结束，0~255）");
    return false;
  }
  return true;
}

// =============================================
// Measurement Flow
// =============================================
async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function scanPort() {
  log("正在扫描串口...");
  let ports;
  try {
    ports = await invoke("list_ports");
  } catch (e) {
    log(`扫描串口失败: ${e}`);
    return null;
  }

  if (ports.length === 0) {
    log("未找到可用串口");
    return null;
  }

  for (const p of ports) {
    log(`发现串口: ${p}`);
  }

  // Use first port (or filter for Measuring Instruments / USB 串行设备)
  const target = ports[0];
  log(`使用串口: ${target}`);
  return target;
}

async function startMeasure() {
  readParams();
  if (!validateParams()) {
    setState(State.IDLE);
    return;
  }

  measuredData = [];
  abortRequested = false;
  clearDataTable();
  logClear();
  setState(State.CONNECTING);
  log("======== 开始测量 ========");

  // Step 1: Open display window
  await openDisplayWindow(displayX, displayY, displayW, displayH, startGray);
  updatePreview(startGray);

  // Step 2: Scan & open port
  const path = await scanPort();
  if (!path) {
    showModal("连接失败", "色度仪未连接，请检查设备连接");
    await closeDisplayWindow();
    setState(State.ERROR);
    return;
  }

  try {
    await invoke("open_port", { path });
    portPath = path;
    log(`已打开串口: ${path}`);
  } catch (e) {
    log(`打开串口失败: ${e}`);
    showModal("连接失败", `无法打开串口: ${path}`);
    await closeDisplayWindow();
    setState(State.ERROR);
    return;
  }

  setState(State.CONNECTED);

  // Step 3: COM,1
  log("开启设备通讯...");
  try {
    const resp = await invoke("send_command", { cmd: "COM,1" });
    if (!resp.startsWith("OK00")) {
      log(`通讯开启失败: ${resp}`);
      showModal("通讯失败", "色度仪通讯失败");
      await cleanupPort();
      await closeDisplayWindow();
      setState(State.ERROR);
      return;
    }
    log(`通讯开启成功: ${resp}`);
  } catch (e) {
    log(`通讯命令失败: ${e}`);
    showModal("通讯失败", "色度仪通讯命令失败");
    await cleanupPort();
    await closeDisplayWindow();
    setState(State.ERROR);
    return;
  }

  // Step 4: ZRC
  log("执行校准...");
  try {
    const resp = await invoke("send_command", { cmd: "ZRC" });
    if (!resp.startsWith("OK00")) {
      log(`校准失败: ${resp}`);
      showModal("校准失败", "色度仪校准失败");
      await cleanupPort();
      await closeDisplayWindow();
      setState(State.ERROR);
      return;
    }
    log(`校准成功: ${resp}`);
  } catch (e) {
    log(`校准命令失败: ${e}`);
    showModal("校准失败", "色度仪校准命令失败");
    await cleanupPort();
    await closeDisplayWindow();
    setState(State.ERROR);
    return;
  }

  // Step 5: Loop
  setState(State.MEASURING);
  const totalSteps = endGray - startGray + 1;
  let currentStep = 0;

  for (let gray = startGray; gray <= endGray; gray++) {
    if (abortRequested) {
      log("用户中止测量");
      break;
    }

    currentStep++;
    updateProgress(currentStep, totalSteps);
    updatePreview(gray);
    await updateDisplayColor(gray);
    log(`测量灰阶 ${gray}...`);

    // Sleep before measurement
    await sleep(100);

    // Measure
    try {
      const result = await invoke("measure_once");
      const [x, y, lv] = result;
      log(`  → x=${x.toFixed(4)}, y=${y.toFixed(4)}, Lv=${lv.toFixed(4)}`);

      measuredData.push({ gray, x, y, lv });
      addDataRow(gray, x, y, lv);
    } catch (e) {
      log(`测量失败: ${e}`);
      showModal("测量失败", `第 ${gray} 灰阶测量失败`);
      await cleanupPort();
      await closeDisplayWindow();
      setState(State.ERROR);
      return;
    }

    // Small delay between measurements
    await sleep(50);
  }

  // Step 6: Close
  log("关闭设备通讯...");
  try {
    const resp = await invoke("send_command", { cmd: "COM,0" });
    if (!resp.startsWith("OK00")) {
      log(`关闭失败: ${resp}`);
      showModal("关闭失败", "色度仪关闭失败");
    } else {
      log(`关闭成功: ${resp}`);
    }
  } catch (e) {
    log(`关闭命令失败: ${e}`);
    showModal("关闭失败", "色度仪关闭失败");
  }

  await cleanupPort();
  await closeDisplayWindow();

  // Step 7: Export CSV
  await exportCSV();

  // Step 8: Done
  log("======== 测量完成 ========");
  document.getElementById("progress-text").textContent = "完成";
  setState(State.COMPLETED);
}

async function cleanupPort() {
  try {
    await invoke("close_port");
    portPath = null;
    log("串口已关闭");
  } catch (e) {
    log(`关闭串口异常: ${e}`);
  }
}

function stopMeasure() {
  abortRequested = true;
  log("正在停止...");
  document.getElementById("btn-stop").disabled = true;
}

// =============================================
// CSV Export
// =============================================
async function exportCSV() {
  if (measuredData.length === 0) {
    log("无测量数据可导出");
    return;
  }

  const now = new Date();
  const ts = now.toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const defaultName = `色度测量-${startGray}-${endGray}-${ts}.csv`;

  let savePath;
  try {
    savePath = await save({
      defaultPath: defaultName,
      filters: [{ name: "CSV", extensions: ["csv"] }],
    });
  } catch (e) {
    log(`保存对话框取消或失败: ${e}`);
    savePath = null;
  }

  if (!savePath) {
    log("未选择保存路径");
    return;
  }

  // Write file via Rust
  const lines = ["灰阶,x,y,Lv"];
  for (const d of measuredData) {
    lines.push(`${d.gray},${d.x},${d.y},${d.lv}`);
  }
  const csvContent = "\uFEFF" + lines.join("\r\n"); // BOM for Excel

  try {
    await invoke("write_csv_file", { path: savePath, content: csvContent });
    log(`CSV 已导出: ${savePath}`);
  } catch (e) {
    log(`CSV 导出失败: ${e}`);
    showModal("导出失败", "CSV 导出失败，请检查磁盘空间和权限");
  }
}

// =============================================
// Reset
// =============================================
function resetParams() {
  document.getElementById("param-x").value = 0;
  document.getElementById("param-y").value = 0;
  document.getElementById("param-width").value = 512;
  document.getElementById("param-height").value = 512;
  document.getElementById("param-start").value = 0;
  document.getElementById("param-end").value = 255;
  document.querySelector('input[name="color-mode"][value="white"]').checked = true;
  clearDataTable();
  logClear();
  measuredData = [];
  updateProgress(0, 100);
  document.getElementById("current-gray").textContent = "--";
  document.getElementById("current-rgb").textContent = "(--,--,--)";
  document.getElementById("progress-text").textContent = "待连接";
  const canvas = document.getElementById("preview-canvas");
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  setState(State.IDLE);
}

// =============================================
// Init
// =============================================
async function init() {
  initTheme();
  updateUI();

  document.getElementById("btn-start").addEventListener("click", startMeasure);
  document.getElementById("btn-stop").addEventListener("click", stopMeasure);
  document.getElementById("btn-reset").addEventListener("click", resetParams);

  // Update display window on param change
  const paramInputs = document.querySelectorAll(".param-input");
  for (const inp of paramInputs) {
    inp.addEventListener("change", () => {
      readParams();
      if (currentState === State.IDLE || currentState === State.COMPLETED) {
        openDisplayWindow(displayX, displayY, displayW, displayH, startGray).catch(() => {});
      }
    });
  }

  const radioInputs = document.querySelectorAll('input[name="color-mode"]');
  for (const r of radioInputs) {
    r.addEventListener("change", () => {
      colorMode = r.value;
      if (currentState === State.IDLE || currentState === State.COMPLETED) {
        openDisplayWindow(displayX, displayY, displayW, displayH, startGray).catch(() => {});
      }
    });
  }

  // Initial preview
  const canvas = document.getElementById("preview-canvas");
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  log("CA-410 色度分析仪 已就绪");
  updateProgress(0, 100);
}

window.addEventListener("DOMContentLoaded", init);
