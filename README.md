# batmanoverlay

> **Portable Windows Productivity & Presentation Assistant**

`batmanoverlay` is a lightweight, portable Windows desktop assistant that embeds a Chromium browser alongside a persistent smart clipboard and character-by-character typing simulation engine.

---

## Technical Specifications

- **Language:** Python 3.11+
- **GUI Framework:** PySide6 (Qt 6.7) + Qt WebEngine
- **Architecture:** Layered, Event-Driven Modular Monolith
- **Data Gravity:** Local-only, isolated `./data/` runtime storage

---

## Development Setup

```powershell
# 1. Clone repository
git clone https://github.com/batmanoverlay/batmanoverlay.git
cd batmanoverlay

# 2. Setup virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements-dev.txt

# 4. Run lint & tests
python scripts/lint.py
pytest
```

---

## Build Instructions

```powershell
python scripts/build.py
```

Portable build output will be generated in `dist/batmanoverlay/`.

---

## License

[MIT License](LICENSE)
