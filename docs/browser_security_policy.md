# batmanoverlay — Browser Security Policy Specification

> **Document Version:** 1.0.0
> **Date:** 2026-08-07
> **Status:** Approved Specification — Milestone-2 / Sprint-003A
> **Upstream Dependencies:**
> - PRD v1.0.0 (§10 Security Requirements)
> - SAD v1.0.0 (§7 Security Architecture)

---

## Executive Overview

This document specifies the default browser security permissions, content security policies (CSP), and privacy sandboxing rules for the `batmanoverlay` integrated browser engine (`src/browser/`).

All default settings enforce **Zero-Trust Hardened Security Defaults** to prevent unauthorized hardware access, malicious popups, stealth tracking, and cross-site script injection.

---

## 1. Default Security Permission Matrix

| Resource / Feature | Default Permission State | Policy Description |
|---|---|---|
| **Camera Access** | ❌ **Disabled (Blocked)** | Hardware video capture devices are denied explicitly. |
| **Microphone Access** | ❌ **Disabled (Blocked)** | Hardware audio capture devices are denied explicitly. |
| **Desktop Notifications** | ❌ **Disabled (Blocked)** | Web notification popups are blocked by default. |
| **Geolocation API** | ❌ **Disabled (Blocked)** | Location services and GPS queries return position denied. |
| **Clipboard Read** | ⚠️ **Ask (Prompt User)** | Web pages requesting clipboard content must prompt for confirmation. |
| **Clipboard Write** | ✅ **Allowed** | Web pages copying text to system clipboard (e.g. code snippet copy buttons) are permitted. |
| **JavaScript Engine** | ✅ **Enabled** | Standard ECMAScript execution enabled with modern V8 sandbox. |
| **PDF Viewer** | ✅ **Enabled** | Embedded PDF document rendering enabled securely. |
| **Popups & New Windows** | 🚫 **Blocked** | `window.open()` popups are automatically blocked unless initiated by user click. |
| **Browser Plugins** | ❌ **Disabled** | NPAPI / PPAPI legacy third-party plugins are disabled. |

---

## 2. Storage & Cookie Privacy Architecture

- **Cookies**: Isolated per-workspace profile (`data/browser/profiles/{profile_id}/cookies/`). Third-party tracking cookies are restricted.
- **Cache Storage**: Isolated disk cache per profile (`data/browser/profiles/{profile_id}/cache/`).
- **IndexedDB & Local Storage**: Sandboxed within profile storage tree. Automatically cleared upon explicit workspace profile purge.

---

## 3. Extension Points for Sprint-003B UI Integration

1. **Security Badge Indicator**: Green SSL lock badge for secure `https://` URLs; warning badge for `http://` or invalid certificates.
2. **Permission Prompts**: Event signals emitted when a site requests non-standard permissions.
