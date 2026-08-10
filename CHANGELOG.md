# Changelog

All notable changes to **BatmanOverlay** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-08-11

### 🎉 First Stable Release

BatmanOverlay v1.0.0 is the first stable release of the application with the verified embedded browser architecture and integrated desktop features.

### ✨ Added & Featured

- **Embedded QtWebEngine Browser**: In-process rendering powered by `QWebEngineView`, `QWebEnginePage`, and `QWebEngineProfile`.
- **Authentication Support**: Fully verified native Google Sign-In and ChatGPT session authentication and persistence.
- **DirectX DXGI Screen Capture Engine**: Low-latency GPU-accelerated desktop duplication API capture, with fallback support for Windows Graphics Capture and BitBlt virtual metrics.
- **Native Win32 Z-Order Management**: C++ extension watchdog DLL (`batmanoverlay_zorder.cpp`) for HWND pinning (`TopMost`, `Desktop Pin`, opacity, and pass-through modes).
- **DPAPI Encrypted Credential Store**: Windows-native secure secret persistence via Data Protection API (`credential_store.py`).
- **System Tray Lifecycle & Transparency Controls**: Minimize-to-tray, taskbar button suppression, status bar indicators, and 99.99% window opacity mapping.
- **Protected Content Notifications**: Automatic toast alerts for DRM-protected applications (`WDA_EXCLUDEFROMCAPTURE`).
- **Frame Analyzer & Window Detector**: Pixel frame deltas and application-aware screenshot prefixing.
- **Official App Branding**: Embedded high-resolution app icon logo across title bar, system tray, and executable file header.

### 🔐 Security & Browser Architecture

- 100% pure in-process `QWebEngineView` architecture.
- Zero external Chrome process spawning and zero CDP (Chrome DevTools Protocol) WebSockets.

### 🧪 Verification Metrics

- **169 / 169 Unit Tests Passed** (`pytest -m unit`).
- Clean static analysis (`mypy src`, `ruff check src`).
- Standalone portable binary distribution created and verified at `dist/batmanoverlay/batmanoverlay.exe`.
