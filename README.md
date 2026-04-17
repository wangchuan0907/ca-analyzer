# CA-Analyzer

一款基于串口协议的彩色分析测量工具，支持屏幕颜色采集、参数配置与数据导出。

## 功能特性

- 串口通讯：支持参数化配置（波特率、数据位、停止位、校验位）
- 屏幕采集：坐标区域 + 颜色通道范围控制
- 双窗口架构：控制窗口 + 独立打屏窗口
- CSV 数据导出
- PyInstaller 打包为独立 EXE

## 技术栈

- Python 3.10+
- tkinter（控制窗口）
- pygame（打屏窗口）
- pyserial（串口通讯）
- pywin32（Windows API）
- PyInstaller（打包）

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py

# 打包
pyinstaller --onefile --windowed --icon=resources/icons/logo.ico main.py
```

## 项目结构

```
ca-analyzer/
├── main.py
├── requirements.txt
├── README.md
├── SPEC.md
├── resources/
│   └── icons/
│       └── logo.ico
└── src/
    ├── __init__.py
    ├── serial_protocol.py
    ├── measurement_controller.py
    ├── csv_exporter.py
    └── display_window.py
```
