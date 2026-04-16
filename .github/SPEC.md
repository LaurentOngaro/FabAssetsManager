# FabAssetsManager — Specifications & Development Notes

Version: 1.0.2
Last reviewed: 2026-04-16

## Context

Local application that allows an Epic Games / fab.com user to **retrieve, browse, enrich, and export** their owned asset library.

---

## Architecture Technical Structure

### 1. File Structure

- `app.py`: Main entry point (Flask server).
- `lib/`: Business logic package.
  - `app_settings.py`: Constants and default paths (aligned with UAM).
  - `routes.py`: API and web route definitions.
  - `config_manager.py`: Centralized configuration (JSON files, cookies, UA).
  - `cache_manager.py`: Distributed cache management (individual JSON files).
  - `fetch_fab_library.py`: Integration with fab.com library search (session-based).
  - `models.py`: Data models and mapping logic.
  - `logging_setup.py`: Unified logging configuration.
  - `errors.py`: API error contract and helpers.
- `static/`: Frontend assets (Vanilla JS, CSS, HTML).
- `assets/`: Individual JSON cache files.
- `previews/`: Cached image thumbnails.
- `config/`: User credentials and settings.

---

## User Request

- Interactive local web interface listing all assets owned on fab.com
- **Sorting** (title, added date, updated date) and **filters** (Unreal Engine version, license, downloadable)
- **Title search**
- **CSV and JSON export** of filtered list, with UID always included in CSV output
- Standalone local Python app

---

## Identified Technical Constraints

### 1. Cloudflare protection

fab.com is protected by Cloudflare (WAF + JS challenge).

- `cf_clearance` cookie is tied to the browser's **IP + User-Agent** combination
- Requests from another context (different IP or UA) can return **HTTP 403**
- **Consequence**: script should run on **the same machine** as the browser used for login
- Requests from remote servers often fail even with copied cookies

### 2. Authentication

No documented public API. Access relies on session cookies:

- `fab_csrftoken` — CSRF token
- `fab_sessionid` — Django/backend session on fab.com
- `cf_clearance` — Cloudflare validation (tied to IP+UA)
- `__cf_bm` — Cloudflare bot-management cookie (secondary)

### 3. User-Agent

Because `cf_clearance` is tied to the exact browser UA, Python must send **the exact same User-Agent** used when cookies were generated.

### 4. Local configuration files

- `config/config.json` stores persisted application settings.
- `config/cookies.txt` and `config/user_agent.txt` are the user-provided authentication inputs.
- `assets/last_update.txt` stores cache metadata used by the UI badge and freshness checks.

---

## API & Documentation

For detailed information on API endpoints, request/response formats, and integration workflows, please refer to:

- **[API_GUIDE.md](../API_GUIDE.md)**: Main developer reference for the local API.

---

## Technical Architecture Deep-Dive

```
FabAssetsManager/
├── app.py                  # Entry point (port 5002 by default)
├── lib/                    # Core business logic
│   ├── __init__.py
│   ├── config_manager.py   # Config parsing & path resolution
│   ├── cache_manager.py    # Local cache management
│   ├── fetch_fab_library.py# Fab.com library crawler
│   ├── routes.py           # Flask API routes
│   ├── models.py           # Data models
│   ├── logging_setup.py    # Logging configuration
│   └── errors.py           # API error contract
├── requirements.txt        # Python packages
├── README.md
├── TODO.md                 # Prioritized tasks list
├── VERSION.txt
├── CHANGELOG.md
├── config/
│   ├── config.json         # Persisted runtime settings
│   ├── cookies.txt         # Created on first setup (requires matching UA for Cloudflare)
│   └── user_agent.txt      # Created on first setup (must match the browser UA)
├── start_FabAssetsManager.bat
├── _helpers/               # Development and planning documents
│   ├── PLAN_ACTIONS.md     # Detailed roadmap for current and future features
│   ├── specs.md            # Specifications and notes
│   ├── TROUBLESHOOTING.md  # Troubleshooting guide
│   └── asset_example.json  # Data template reference
├── tests/                  # Unittests
├── static/                 # Frontend assets (Vanilla JS, CSS, HTML)
├── assets/                 # Cached asset metadata (.json files per UID)
└── previews/               # Cached preview images (.jpg files per UID)
```

### Runtime flow

1. `python app.py` starts the Flask server and loads persisted configuration via `lib/config_manager.py`.
2. Authentication relies on `config/cookies.txt` and `config/user_agent.txt`.
3. Backend serves the cached assets from individual JSON files in `assets/` and cached thumbnails in `previews/`.
4. `lib/routes.py` exposes JSON endpoints for config, cache maintenance, asset lookup, details enrichment, and export.
5. The UI in `static/` manages sorting, filtering, detail modals, gallery navigation, and CSV/JSON export.

---

## Notable Technical Points

### 1. Cloudflare Bypass (`curl_cffi`)

fab.com uses Cloudflare WAF. To bypass 403 errors, the application uses `curl_cffi` to impersonate a Chrome TLS fingerprint. Authentication relies on a shared IP/User-Agent between the browser and the app.

### 2. Distributed Cache Architecture

Instead of a monolithic database, each asset is stored as an individual JSON file in `assets/`. This allows for fast atomic updates, easy manual inspection, and prevents data loss if one file is corrupted.

### 3. Unified Asset Model

The backend uses a centralized `Asset` class (`lib/models.py`) to map and normalize raw API payloads (list vs. detail). This ensures consistent data structure across all endpoints and filters.

---

## Development Environment

- **Backend**: Python 3.x / Flask.
- **Frontend**: Vanilla JS / CSS (No frameworks).
- **Persistence**:
  - Library: Distributed JSON files.
  - User Annotations (Favorites/Comments): Browser `localStorage`.
  - Credentials/Settings: `config/` (Local files).

---
