<div align="center">

# 🦇 batmanoverlay

**Portable Windows Productivity, Presentation & Desktop Overlay Assistant**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PySide6 / Qt 6.7](https://img.shields.io/badge/PySide6-Qt_6.7-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://www.qt.io/)
[![Platform Windows](https://img.shields.io/badge/Platform-Windows_10%2F11-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Code Style Ruff](https://img.shields.io/badge/Code_Style-Ruff-261230?style=for-the-badge&logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
[![Type Checking MyPy](https://img.shields.io/badge/Type_Checked-MyPy_Strict-blue?style=for-the-badge)](https://mypy-lang.org/)
[![License MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<p align="center">
  A high-performance, portable Windows application combining an embedded Chromium engine, smart persistent clipboard, realistic human typing simulator, and low-latency DirectX screen capture overlay.
</p>

[Key Features](#-key-features) •
[Architecture](#%EF%B8%8F-architecture) •
[Getting Started](#-getting-started) •
[Build Instructions](#-build-instructions) •
[Documentation](#-repository-directory-overview)

---

</div>

## 🌟 Key Features

### 🌐 Embedded Chromium & CDP Automation
- **Isolated Browser Engine**: Built on PySide6 `QtWebEngine` with isolated `./data/browser_profiles/` runtime storage.
- **Chrome DevTools Protocol (CDP)**: Integrated WebSocket client and process controller for headless Chrome session control and live remote streaming.
- **Session & Tab Manager**: Multi-tab support with persistent session restoration, cookies, and local storage.
- **OAuth2 Handoff**: Built-in loopback authentication server for seamless sign-in with Google, Microsoft, GitHub, and custom providers.

### 📋 Smart Persistent Clipboard
- **Real-Time Monitoring**: Automatically intercepts system clipboard events (`QClipboard`) for text, URLs, HTML, images, and code snippets.
- **SQLite Data Storage**: Thread-safe local storage with auto-deduplication, fuzzy search, retention management, and item pinning.
- **Data Exporters**: Export clipboard data directly to JSON, Plain Text, or CSV files.

### ⌨️ Realistic Human Typing Simulator
- **Natural Cadence Engine**: Simulates human keystroke speed distributions (WPM targets, Log-Normal latency jitter).
- **Typo & Pause Simulation**: Realistic error insertion, automatic backspacing corrections, and punctuation pauses.
- **Asynchronous Execution**: Keystrokes dispatched via Win32 `SendInput` API inside a dedicated background `QThread`, keeping the UI responsive.

### 🖼️ Low-Latency Screen Capture & Desktop Overlay
- **DirectX DXGI Duplication API**: High-fps, GPU-accelerated desktop capture engine.
- **Win32 Z-Order Pinning**: Custom C++ native extension (`batmanoverlay_zorder.dll`) for desktop pin modes, `HWND` matching, always-on-top, dynamic transparency, and click-through pass-through.
- **Frame Analyzer**: Diagnostics for motion detection and window boundary tracking.

---

## 🏗️ Architecture

`batmanoverlay` is architected as a **layered modular monolith** with strict unidirectional dependencies enforced by `import-linter`.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            User Interface (PySide6)                         │
│     (Frameless Main Window, Custom Titlebar, Panel Stack, Tray & Toasts)    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                              Domain Subsystems                              │
│       ┌──────────────────────┬──────────────────────┬───────────────┐       │
│       │   Browser Engine     │  Smart Clipboard     │ Human Typing  │       │
│       │  (QtWebEngine/CDP)   │   (Monitor/Export)   │  (Simulator)  │       │
│       └──────────────────────┴──────────────────────┴───────────────┘       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                           Core Application Services                         │
│      (ConfigManager, ThemeManager, AppSignals Bus, Logger, Notifications)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                              Data Storage Layer                             │
│     (SQLite Store, Clipboard Repository, DPAPI Encrypted Credential Store)  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                           Windows Platform Layer                            │
│     (Win32 Target API, Z-Order C++ DLL, Global Hotkeys, DXGI Desktop Dup)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

> 📖 For a deep dive into every file and component in the codebase, consult the [Codebase Architectural Index](INDEX.md) or [docs/INDEX.md](docs/INDEX.md).

---

## 🛠️ Technical Specifications

| Component | Specification |
| :--- | :--- |
| **Language** | Python 3.11+ |
| **GUI Framework** | PySide6 (Qt 6.7) + Qt WebEngine |
| **Native Extension** | MSVC C++ Win32 Z-Order DLL |
| **Persistence** | SQLite3, DPAPI Credential Store, JSON |
| **Screen Capture** | DirectX DXGI Desktop Duplication / Win32 BitBlt |
| **Input Emulation** | Win32 `SendInput` API |
| **Data Isolation** | 100% Local-only (`./data/` directory) |
| **Code Quality** | Strict MyPy types, Ruff linter, Pytest coverage > 80% |

---

## 🚀 Getting Started

### Prerequisites
- **Windows 10 / 11** (64-bit)
- **Python 3.11+** installed and added to PATH
- **C++ Build Tools** (Optional, for re-compiling native Z-Order DLL)

### Installation

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/batmanoverlay/batmanoverlay.git
   cd batmanoverlay
   ```

2. **Set up virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```powershell
   pip install -r requirements-dev.txt
   ```

4. **Verify static analysis and run tests**:
   ```powershell
   # Run linters (Ruff, MyPy, Import-Linter)
   python scripts/lint.py

   # Run test suite
   pytest
   ```

5. **Launch application**:
   ```powershell
   python -m src.main --debug
   ```

---

## 📦 Build Instructions

To build a standalone, zero-dependency portable executable package for Windows:

```powershell
# Compile the portable distribution
python scripts/build.py
```

The output will be generated in `dist/batmanoverlay/` containing `batmanoverlay.exe` along with all required Qt, WebEngine, and native binaries.

---

## 📁 Repository Directory Overview

```
batmanoverlay/
├── INDEX.md                   # Complete codebase architectural index & file guide
├── README.md                  # Project overview and developer documentation
├── pyproject.toml             # Project config, Ruff, MyPy & Import-Linter rules
├── docs/                      # PRD, Architecture Specs, and Technical Reports
├── scripts/                   # Build scripts, DLL compilers, diagnostic harnesses
│   ├── build.py               # PyInstaller executable packager
│   ├── build_zorder_dll.py    # MSVC C++ DLL compiler
│   └── lint.py                # Quality assurance runner
├── src/                       # Application source directory
│   ├── app.py                 # Dependency container & lifecycle boot
│   ├── main.py                # CLI entry point
│   ├── browser/               # Embedded Chromium, CDP & OAuth flow
│   ├── clipboard/             # Clipboard monitor, SQLite repo & exporters
│   ├── core/                  # Event bus, logger, themes & preferences
│   ├── models/                # Pydantic data schemas
│   ├── platform/              # Win32 API, Z-Order DLL & DXGI capture
│   ├── storage/               # SQLite engine & encrypted credential store
│   ├── typing/                # Human typing simulation engine & worker
│   └── ui/                    # Qt main window, custom panels & dialogs
└── tests/                     # Unit, integration & UI test suite
```

---

## 🧪 Testing & Quality Assurance

We enforce high code standards and full test coverage:

```powershell
# Run unit tests only
pytest -m unit

# Run UI widget tests
pytest -m ui

# Run test coverage report
pytest --cov=src --cov-report=term-missing
```

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
