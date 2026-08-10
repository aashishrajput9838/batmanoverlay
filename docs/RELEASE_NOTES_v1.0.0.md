# BatmanOverlay v1.0.0

## 🎉 First Stable Release

BatmanOverlay v1.0.0 is the first stable release of the application with the verified embedded browser architecture and integrated desktop features.

### ✨ Highlights

- Embedded QtWebEngine browser
- Persistent browser sessions
- Google authentication support
- ChatGPT authentication support
- DirectX desktop screenshot capture
- Windows Graphics Capture / fallback capture support
- Native Win32 Z-order management
- DPAPI-based credential storage
- System tray lifecycle management
- Protected screen-capture notifications
- Window detection and frame analysis
- 99.99% opacity controls

### 🔐 Browser Architecture

The browser uses the original in-process:

- `QWebEngineView`
- `QWebEnginePage`
- `QWebEngineProfile`

No external Chrome/CDP architecture is used in this release.

### 🧪 Verification

- 169/169 unit tests passing
- Ruff checks passing
- Mypy checks passing
- PyInstaller build successful
- Application boot verification passed
- Google authentication manually verified
- ChatGPT authentication manually verified

### 📦 Build

Standalone Windows executable:

`batmanoverlay.exe`

Build artifact:

`dist/batmanoverlay/batmanoverlay.exe`
