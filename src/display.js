/**
 * 打屏窗口 — 接收主窗口消息更新背景色
 */
import { listen } from "@tauri-apps/api/event";
import { getCurrentWindow } from "@tauri-apps/api/webviewWindow";

async function init() {
  const block = document.getElementById("color-block");

  // Listen for color updates from main window
  await listen("set-color", (event) => {
    const { r, g, b } = event.payload;
    block.style.backgroundColor = `rgb(${r},${g},${b})`;
  });
}

window.addEventListener("DOMContentLoaded", init);
