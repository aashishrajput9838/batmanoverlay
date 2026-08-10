# Codebase Architectural Index & Navigation Guide

> **Project**: `batmanoverlay` (v1.0.0)  
> **Type**: Portable Windows Desktop Assistant & Presentation Tool  
> **GUI & Tech Stack**: Python 3.11+, PySide6 (Qt 6.7), Qt WebEngine, PyWin32, C++ MSVC Extension DLL  

---

## 1. Executive Summary

`batmanoverlay` is a lightweight, portable Windows desktop assistant that integrates an embedded Chromium browser alongside a persistent smart clipboard, desktop window capture engine, and a realistic human character-by-character typing simulation engine.

The codebase strictly follows a **layered modular monolith** pattern enforced by static type checking (`mypy`), linting (`ruff`), and import boundary rules (`import-linter`).

---

## 2. Directory Tree Structure

```
batmanoverlay/
├── docs/                      # Technical design specifications, reports & manuals
├── scripts/                   # Build automation, DLL compiler & experiment harnesses
├── src/                       # Application source code
│   ├── browser/               # Embedded Chromium & CDP integration
│   │   └── cdp/               # Chrome DevTools Protocol sub-engine
│   ├── clipboard/             # Persistent clipboard monitoring & exporters
│   ├── core/                  # Configuration, themes, logging & signals
│   ├── models/                # Pydantic / Dataclass domain data models
│   ├── platform/              # Win32 API, Z-order management & DXGI screen capture
│   │   ├── native/            # Win32 C++ DLL source code
│   │   └── screenshot/        # Low-latency desktop duplication & frame analyzer
│   ├── storage/               # SQLite database, credential store & migrations
│   ├── typing/                # Human typing simulation, queues & worker threads
│   └── ui/                    # PySide6 frameless windows, panels & widgets
│       └── components/        # Reusable Qt UI components
└── tests/                     # Unit, integration, and UI test suite
    ├── integration/
    ├── ui/
    └── unit/
```

---

## 3. Layered Architectural Index

### Layer 1: Application Boot & Lifecycle
- [`src/main.py`](src/main.py): CLI/GUI entry point; configures Qt WebEngine Chromium flags (`--disable-blink-features=AutomationControlled`) and instantiates application shell.
- [`src/app.py`](src/app.py): `BatmanOverlayApp` dependency injection container managing boot sequence, global exception hook, splash screen, and graceful shutdown.
- [`src/constants.py`](src/constants.py): App-wide naming, vendor, and default path constants.
- [`src/version.py`](src/version.py): Package version metadata (`1.0.0`).

---

### Layer 2: User Interface (`src/ui/`)
- [`src/ui/main_window.py`](src/ui/main_window.py): Frameless main window shell, system tray integration, dynamic opacity, and layout manager.
- [`src/ui/title_bar.py`](src/ui/title_bar.py): Custom draggable frameless title bar.
- [`src/ui/sidebar.py`](src/ui/sidebar.py): Collapsible navigation bar for view switching.
- [`src/ui/browser_panel.py`](src/ui/browser_panel.py): Embedded Chromium browser panel with tab manager, bookmarks, and OAuth callback handler.
- [`src/ui/clipboard_panel.py`](src/ui/clipboard_panel.py): Searchable, filterable list of captured clipboard history items.
- [`src/ui/clipboard_card.py`](src/ui/clipboard_card.py): Widget representing an individual clipboard item card.
- [`src/ui/typing_panel.py`](src/ui/typing_panel.py): Human typing simulation control panel (WPM, error rates, target selector, preset loader).
- [`src/ui/overlay_visibility_panel.py`](src/ui/overlay_visibility_panel.py): Window transparency, click-through, Z-order mode selection, and screen capture diagnostic view.
- [`src/ui/settings_panel.py`](src/ui/settings_panel.py): Application preferences configuration UI.
- [`src/ui/status_bar.py`](src/ui/status_bar.py) & [`src/ui/toast.py`](src/ui/toast.py): Bottom status bar and overlay toast notifications.
- [`src/ui/splash_screen.py`](src/ui/splash_screen.py): Boot loading splash screen window.
- [`src/ui/dialogs.py`](src/ui/dialogs.py): Modals for error reports, confirmations, and exports.
- [`src/ui/icons.py`](src/ui/icons.py): Dynamic SVG icon painter.

---

### Layer 3: Subsystems & Services

#### A. Smart Clipboard (`src/clipboard/`)
- [`src/clipboard/monitor.py`](src/clipboard/monitor.py): System clipboard change listener (`QClipboard`).
- [`src/clipboard/service.py`](src/clipboard/service.py): Clipboard item deduplication, retention limits, and storage persistence controller.
- [`src/clipboard/exporters.py`](src/clipboard/exporters.py): Exporters for JSON, TXT, and CSV format data export.

#### B. Browser Engine & CDP (`src/browser/`)
- [`src/browser/service.py`](src/browser/service.py): Browser profile and tab manager service.
- [`src/browser/profile_manager.py`](src/browser/profile_manager.py): Chromium profile storage, cookies, local storage, and cache persistence.
- [`src/browser/session_manager.py`](src/browser/session_manager.py): Multi-tab session restore manager.
- [`src/browser/oauth_manager.py`](src/browser/oauth_manager.py): OAuth2 authentication flow engine (Google, Microsoft, GitHub) via local loopback web server.
- **CDP Engine** (`src/browser/cdp/`):
  - [`src/browser/cdp/chrome_process.py`](src/browser/cdp/chrome_process.py): Headless Chrome process wrapper with remote debugging port.
  - [`src/browser/cdp/cdp_client.py`](src/browser/cdp/cdp_client.py): WebSocket client for Chrome DevTools Protocol.
  - [`src/browser/cdp/cdp_browser_widget.py`](src/browser/cdp/cdp_browser_widget.py): Qt widget rendering CDP remote streams.

#### C. Human Typing Simulator (`src/typing/`)
- [`src/typing/engine.py`](src/typing/engine.py): Main typing session controller.
- [`src/typing/simulator.py`](src/typing/simulator.py): Human typing latency distribution, realistic typos, backspacing corrections, and pause models.
- [`src/typing/worker.py`](src/typing/worker.py): Asynchronous background `QThread` dispatching Win32 `SendInput` keystrokes.
- [`src/typing/queue.py`](src/typing/queue.py) & [`src/typing/scheduler.py`](src/typing/scheduler.py): Typing job queue and delayed job execution scheduler.

---

### Layer 4: Core Framework (`src/core/`)
- [`src/core/config_manager.py`](src/core/config_manager.py): App configuration store (`./data/config.json`).
- [`src/core/events.py`](src/core/events.py): Decoupled Qt signal bus (`AppSignals`).
- [`src/core/theme_manager.py`](src/core/theme_manager.py): Dynamic dark/light QSS theme stylesheet manager.
- [`src/core/logger.py`](src/core/logger.py): Loguru logging setup writing rotating logs to disk.
- [`src/core/notification_manager.py`](src/core/notification_manager.py): Notification and system tray event dispatcher.
- [`src/core/exceptions.py`](src/core/exceptions.py): Custom application domain error hierarchy.

---

### Layer 5: Data Storage (`src/storage/`)
- [`src/storage/sqlite_store.py`](src/storage/sqlite_store.py): SQLite database manager with transaction support.
- [`src/storage/clipboard_repository.py`](src/storage/clipboard_repository.py): SQLite CRUD operations for clipboard items.
- [`src/storage/credential_store.py`](src/storage/credential_store.py): Windows DPAPI encrypted secret storage for OAuth credentials.
- [`src/storage/json_store.py`](src/storage/json_store.py): Atomic JSON configuration file fallback store.

---

### Layer 6: Windows Platform Layer (`src/platform/`)
- [`src/platform/windows_target.py`](src/platform/windows_target.py): Active window detection (`GetForegroundWindow`), window handle binding, and target matching.
- [`src/platform/zorder_manager.py`](src/platform/zorder_manager.py): Window Z-order manager (TopMost, Desktop Pin, click-through pass-through).
- [`src/platform/global_hotkey.py`](src/platform/global_hotkey.py): Global hotkey registrar (`RegisterHotKey`).
- [`src/platform/native/batmanoverlay_zorder.cpp`](src/platform/native/batmanoverlay_zorder.cpp): Low-level Win32 C++ extension DLL source for native Z-order pin control.
- **Screen Capture Engine** (`src/platform/screenshot/`):
  - [`src/platform/screenshot/screenshot_service.py`](src/platform/screenshot/screenshot_service.py): Multi-backend screenshot orchestrator.
  - [`src/platform/screenshot/dxgi_desktop_duplication.py`](src/platform/screenshot/dxgi_desktop_duplication.py): DirectX DXGI Desktop Duplication API capture engine.
  - [`src/platform/screenshot/windows_capture.py`](src/platform/screenshot/windows_capture.py) & [`src/platform/screenshot/windows_graphics_capture.py`](src/platform/screenshot/windows_graphics_capture.py): Win32 BitBlt & Windows Graphics Capture backends.
  - [`src/platform/screenshot/window_detector.py`](src/platform/screenshot/window_detector.py): Enumerates open windows, geometry, and process info.

---

### Layer 7: Data Models (`src/models/`)
- [`src/models/clipboard.py`](src/models/clipboard.py): `ClipboardItem` and filter schemas.
- [`src/models/settings.py`](src/models/settings.py): `AppSettings` configuration dataclass models.
- [`src/models/auth.py`](src/models/auth.py): OAuth session and user token models.
- [`src/models/session.py`](src/models/session.py): Active tab and window session state models.

---

## 5. Build Automation & Scripts (`scripts/`)
- [`scripts/build.py`](scripts/build.py): PyInstaller compilation script creating portable binary distribution in `dist/batmanoverlay/`.
- [`scripts/build_zorder_dll.py`](scripts/build_zorder_dll.py): Compiles native `batmanoverlay_zorder.cpp` into a Win32 `.dll`.
- [`scripts/lint.py`](scripts/lint.py): Unified lint verification script running Ruff, MyPy, and Import-Linter.

---

## 6. Development Commands

```powershell
# Setup virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements-dev.txt

# Run static analysis and linting
python scripts/lint.py

# Run test suite
pytest

# Build portable executable
python scripts/build.py
```
