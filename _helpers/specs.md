# FabAssetsManager — Specifications & Development Notes

Version: 0.13.5
Last reviewed: 2026-04-15

## Context

Local application that allows an Epic Games / fab.com user to **retrieve, browse, enrich, and export** their owned asset library.

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

## Discovered API Endpoints

Source: current Flask routes and the Fab.com library access flow.

### Local configuration and diagnostics

```
GET  /api/config
POST /api/config
POST /api/config/logging
GET  /api/diagnostic
GET  /api/test
```

### Library synchronization and cache

```
POST /api/fetch
GET  /api/missing_details
GET  /api/cache-info
POST /api/clear_previews
POST /api/clear_cache
GET  /api/status
```

### Library data and export

```
GET  /api/assets
GET  /api/lookup
GET  /api/details/{uid}
GET  /api/image/{uid}
GET  /api/export-templates
POST /api/export/json
POST /api/export/csv
POST /api/export/headless
```

### Retrieve account ID

```
GET https://www.fab.com/i/users/me/
Headers: Cookie: <session cookies>
Response: { "uid": "<account_id>", ... }
```

### Library asset list

```
GET https://www.fab.com/i/library/
    ?sort_by=added_date
    &order=desc
    &count=100
    &start=0
Headers: Cookie: <session cookies>
Response: {
  "results": [ ...assets... ],
  "total": <int>,
  "next": "<next URL or null>"
}
```

Pagination: use `start` and `count`; loop until `next == null` or `start >= total`.

### Cache metadata

```
GET /api/cache-info
```

Used by the frontend badge to show the last cache synchronization time.

### Reference sources

- Full Rust app: https://github.com/AchetaGames/Epic-Asset-Manager
- Rust API library: https://github.com/AchetaGames/egs-api-rs
- fab.rs: https://raw.githubusercontent.com/AchetaGames/egs-api-rs/master/src/api/fab.rs
- Fab library types: https://raw.githubusercontent.com/AchetaGames/egs-api-rs/master/src/api/types/fab_library.rs
- Entitlement types: https://raw.githubusercontent.com/AchetaGames/egs-api-rs/master/src/api/types/fab_entitlement.rs

---

## Current Architecture

```
FabAssetsManager/
├── app.py                  # Local Flask server (port 5002 by default)
├── config_manager.py       # Centralized configuration parsing/validation/path resolution
├── cache_manager.py        # Local cache management (JSON files, paths, utilities)
├── fetch_fab_library.py    # API calls + pagination + cache logic
├── routes.py               # Flask API routes and UI endpoints
├── models.py               # Asset normalization and flattening model
├── errors.py                # Standardized API error helpers
├── requirements.txt        # python packages
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
│   ├── specs.md            # Initial specifications and notes
│   ├── TROUBLESHOOTING.md  # Troubleshooting guide
│   └── asset_example.json  # Data template reference
├── tests/                  # Unittests
│   └── test_connection.py  # Connection test routine
├── static/
│   ├── index.html          # SPA shell and page markup
│   ├── css/style.css       # Shared UI styling
│   └── js/app.js           # Frontend behavior
├── assets/                 # Cached asset metadata (.json files per UID)
└── previews/               # Cached preview images (.jpg files per UID)
```

### Runtime flow

1. `python app.py` starts the Flask server and loads persisted configuration from `config/config.json`.
2. Authentication relies on `config/cookies.txt` and `config/user_agent.txt`; the same machine/browser profile is expected when refreshing them.
3. Backend serves the cached assets from individual JSON files in `assets/` and cached thumbnails in `previews/`.
4. `routes.py` exposes JSON endpoints for config, cache maintenance, asset lookup, details enrichment, and export.
5. The UI in `static/index.html` and `static/js/app.js` manages sorting, filtering, detail modals, gallery navigation, and CSV/JSON export.

---

## Past Blocking Issue

**HTTP 403** despite seemingly valid cookies.

### Investigated causes

1. **Missing browser headers** (`sec-*`, `accept-language`, `referer`, etc.)
2. **TLS fingerprinting** by Cloudflare (Python requests vs real Chrome)
3. **Expired `__cf_bm` / short-lived cookies**

### Best solution implemented: `curl_cffi`

```python
from curl_cffi import requests as cffi_requests

session = cffi_requests.Session(impersonate="chrome120")
resp = session.get(url, headers=headers, cookies=cookies)
```

`curl_cffi` emulates Chrome TLS fingerprint and significantly improves Cloudflare pass rate.

Installation: `pip install curl_cffi`

Fallback: the code still keeps a `requests` session available when `curl_cffi` is missing, but that mode is expected to be less reliable against Cloudflare.

### Alternative

If needed, use Playwright with an existing user profile to reuse authenticated browser context.

---

## Functional Improvement Ideas

_(Les détails et la planification se trouvent désormais dans les fichiers **TODO.md** et **PLAN_ACTIONS.md**)_

- Asset thumbnails in table (DONE)
- Direct link to each fab.com listing (DONE)
- Local cache with timestamps (WIP)
- Full gallery views (WIP)
- Category filter (WIP)
- Seller filter (WIP)
- Detection of new assets since last sync (WIP)
- Advanced batch detailing downloaded locally (WIP)
- Local tags without fab.com sync (WIP)
- Local favorites and comments without fab.com sync (DONE)

---

## Development Environment

- Python 3.x
- OS: likely Windows
- Browser: likely Chrome
- Current dependencies: `flask`, `requests`, `curl_cffi`
- Frontend state: favorites, comments, filters, selected columns, and debug preferences are persisted in browser `localStorage`

---

## Attempt History

| Date       | Attempt                                        | Result                             |
| ---------- | ---------------------------------------------- | ---------------------------------- |
| 2026-03-04 | Python script with `requests` + copied cookies | 403                                |
| 2026-03-04 | Custom User-Agent from `user_agent.txt`        | 403                                |
| 2026-03-04 | `curl_cffi` integration (Chrome TLS emulation) | ✅ Cloudflare bypass successful    |
| 2026-03-04 | Saved config auto-fetch + debug mode           | ✅ UX improved, modal now optional |

---

## Applied Fixes (2026-03-04)

### 1) Mandatory modal despite existing config

- Added `/api/config` (GET) to detect saved config server-side
- UI now auto-fetches when config exists
- Modal opens only when config is missing or fetch fails

### 2) HTTP 403 with valid cookies

- Integrated `curl_cffi` for Chrome TLS impersonation
- Kept automatic fallback to `requests` with warning
- Added `curl_cffi>=0.5.0` to dependencies

### 3) Persistent debug mode

- Added "Enable debug mode" checkbox in UI
- State saved in browser localStorage and restored on load
- Extra cookie/header diagnostics shown in logs

### Impact

- **UX**: users no longer re-enter cookies/UA on each launch when valid files exist
- **Reliability**: better success rate against Cloudflare with `curl_cffi`
- **Debuggability**: easier troubleshooting when requests fail

---

Last update: 2026-04-13

---

## v0.9.0 Changes (2026-04-13)

### REF1: central Asset model

- **Problem**: Le mapping des assets reposait sur une fonction legacy `flatten_asset()` dispersée dans plusieurs points du backend, ce qui compliquait la maintenance et les futurs changements de schéma API.
- **Fix**:
  - Ajout du module `models.py` avec la dataclass `Asset` comme source unique de mapping.
  - Remplacement des usages legacy dans `app.py` et `fetch_fab_library.py` par `Asset(...).to_dict()`.
  - Centralisation de la logique de fusion des payloads de détail dans `Asset.merge_detail_payload()` et de normalisation de forme dans `Asset.extract_detail_listing()`.
  - Conservation du format JSON de cache existant (`assets/<uid>.json`) pour garantir la compatibilité.

---

## v0.7.1 Changes (2026-04-13)

### CI7 Hotfix: real detail payload merge + stale cache recovery

- **Problem**: `/api/details/<uid>` merged `details["listing"]` only, but fab.com detail endpoint can return a direct `listing` payload object. Result: `details_fetched=true` without actual enriched fields in cache.
- **Fix**:
  - Backend now supports both payload shapes (`{listing:{...}}` and direct listing object).
  - `details_fetched` is now validated against the real presence of detail fields in `asset["listing"]`.
  - `/api/missing_details` now treats stale/incomplete detail cache entries as missing, enabling proper re-enrichment.

### Frontend hardening (modal)

- Modal detail fetch now retries when local cache is flagged detailed but still incomplete.
- Description and technical specs HTML rendering now uses sanitized content.
- Gallery image navigation now resolves current asset by UID instead of title.

---

## v0.7.2 Changes (2026-04-13)

### BUG2: persisted logging options

- **Problem**: log level and log output UI options were not restored from the project config at startup.
- **Fix**:
  - Added `config/config.json` persistence for `log_level`, `log_output`, and `debug_mode`.
  - `/api/config` now returns these values to the frontend.
  - `/api/config/logging` saves changes immediately and reconfigures the backend logger live.
  - The frontend restores the options at startup and saves changes as soon as the user edits them.

---

## v0.7.3 Changes (2026-04-13)

### BUG2 extension: DEBUG route tracing

- **Problem**: enabling DEBUG only changed the logger level; route calls were not emitted with enough detail to `app.log`.
- **Fix**:
  - Added Flask `before_request` and `after_request` hooks.
  - Each route call now logs method, endpoint, path, query arguments, status code, and request duration at DEBUG level.

---

## v0.7.0 Changes (2026-04-13)

### BUG1: "Get New Assets" error when no new assets

- **Problem**: Clicking "Get New Assets" (partial mode) returned HTTP 403 when no new assets existed.
- **Fix**: Backend `/api/fetch` now distinguishes between "full" and "partial" modes. In partial mode, 0 results = success with message "No new assets — your library is up to date!".

### CI7: Enriched Asset Details Modal

- **Problem**: Modal only showed basic listing data (title, seller name, type, formats, UE versions, licenses, rating, added date, tags, description).
- **Fix**:
  - Lazy loading: modal fetches details from `/api/details/<uid>` on first open if `details_fetched` is false.
  - New fields displayed: seller avatar, price, updated date, review count, technical specs (HTML), media gallery.
  - Loading indicator shown while fetching details.
  - Initial merge fix attempted in `/api/details/<uid>`.
  - `flatten_asset()` now extracts: `seller_avatar_url` (from `listing.user.profileImageUrl`), `technical_specs` (from `assetFormats[].technicalSpecs.technicalDetails`), `media_urls` (from `listing.medias[].mediaUrl`), `review_count` (from `listing.reviewCount`).

### CI11: Improved "Get Details" Button

- **Problem**: Batch always fetched all missing assets; no way to stop; UI blocked.
- **Fix**:
  - If assets are selected (checkboxes), only those are fetched.
  - Added "Stop Scraping" button (replaces "Get Details" during batch).
  - Uses `AbortController` for clean AJAX cancellation.
  - `/api/missing_details` now accepts `?uids=uid1,uid2,...` query param to check specific UIDs only.
