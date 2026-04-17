# CA-410 色度分析仪

一款基于 Tauri v2 的色度分析测量工具，支持通过串口协议控制色度仪，按灰阶/颜色通道循环打屏并测量 xy/Lv 数据，最终导出 CSV。

## 功能特性

- 串口通讯：自动扫描连接色度仪
- 双窗口架构：控制窗口 + 独立打屏窗口（始终置顶）
- 颜色模式：白色/红色/绿色/蓝色单通道或灰阶
- 实时预览：Canvas 显示当前色块、数据表格、测量进度
- CSV 导出：自动命名，含灰阶、x、y、Lv 数据
- 亮/暗主题切换

## 技术栈

- **框架**: Tauri v2（Rust 后端 + Web 前端）
- **前端**: 原生 JavaScript + HTML5 Canvas
- **串口**: tauri-plugin-serial
- **打包**: Tauri bundler（Windows MSI/NSIS）
- **体积目标**: ~8 MB

## 快速开始

### 环境要求

- Node.js 18+
- Rust 1.70+
- Windows 10/11 (x64)

### 安装依赖

```bash
# 安装 Node 依赖
npm install

# 安装 Rust 依赖（通过 tauri CLI）
npm run tauri build
```

### 开发调试

```bash
npm run tauri dev
```

### 构建发布

```bash
npm run tauri build
```

输出位于 `src-tauri/target/release/bundle/` 目录。

## 项目结构

```
ca-analyzer/
├── SPEC.md                 # 完整规格说明书
├── README.md
├── package.json
├── src-tauri/
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── icons/
│   │   └── logo.ico
│   └── src/
│       ├── main.rs
│       └── serial.rs
├── src/
│   ├── index.html
│   ├── main.js
│   ├── preview.js
│   ├── theme.js
│   └── style.css
└── resources/
    └── icons/
        └── logo.ico
```
