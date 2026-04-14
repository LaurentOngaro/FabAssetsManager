# 🎮 FabAssetsManager

File version: 0.12.3

Local web application to manage and explore your **fab.com** asset library (Unreal Engine, Blender, etc.).

## ✨ Key Features

### 📦 Advanced Cache Management

- **Distributed cache**: each asset = individual JSON file (`assets/<UID>.json`)
- **Metadata**: `assets/last_update.txt` with count, oldest_created_at, timestamp
- **UI sync badge**: the home screen shows the last cache sync time
- **Partial updates**: early stopping when refetching if assets already cached
- **Cleanup**: easy cache deletion from interface
- **Metadata Enrichment**: batch download detailed information for all assets directly from the `fab.com` product pages.
- **Centralized mapping model**: backend now uses an `Asset` class to map and normalize asset list/detail payloads.

### 🖼️ Image Previews

- **Lazy loading**: on-demand download (click thumbnail)
- **Local caching**: `previews/<UID>.jpg`
- **Display modal**: fullscreen preview (click image)
- **Smart fallback**: 160×90px images by default, otherwise first available image

### 🎛️ Advanced Filtering & Sorting

- **Text search**: by title (real-time)
- **UE Versions**: filter by Unreal Engine versions
- **UE Max**: display and filter by maximum supported version (semantic sort)
- **Licenses**: multi-select filter
- **Options**: downloadable only, hide adult content
- **Sorting**: title (A↔Z), creation date, update date

### 📊 User Interface

- **Pagination**: 50 items/page, smooth navigation
- **Selection**: individual or entire page
- **Export**: CSV/JSON (selected or filtered assets)
- **CSV**: includes the asset UID first to simplify cache-file mapping
- **Dark mode**: clean design optimized for long reading

---

## 📋 Requirements

- Python 3.9+
- pip
- `curl_cffi` (**required** for Cloudflare)

## 🚀 Installation

```bash
cd FabAssetsManager
pip install -r requirements.txt
pip install curl_cffi  # CRITICAL for Cloudflare bypass
```

If `curl_cffi` has issues, try:

```bash
pip install --upgrade pip
pip install curl_cffi --prefer-binary
```

## 🎯 Launch

```bash
python app.py
```

Then open **http://localhost:5002** in your browser.
NOTE: 5002 is the default port for the web interface, but the it can be changed in `config/config.json`

---

## 🔑 Initial Configuration

### Step 1: Get Your Cookies

**⚠️ IMPORTANT**: Generate cookies **ON THE SAME MACHINE** where you run the app!

#### Recommended Method (Copy as cURL)

1. Open **fab.com** in Chrome/Edge/Firefox on this machine
2. Log in to your account
3. Navigate to https://www.fab.com/library
4. Open DevTools (`F12`) → **Network** tab
5. Reload the page (`F5`)
6. Look for a request to `fab.com` or `entitlements`
7. Right-click → **Copy** → **Copy as cURL**
8. Paste in a text editor and extract:
   - `cookie: ...` line → copy everything after `:` into **`config/cookies.txt`**
   - `user-agent: ...` line → copy everything after `:` into **`config/user_agent.txt`**

#### Manual Method

1. DevTools (`F12`) → **Network** → reload
2. Select a fab.com request
3. **Request Headers** tab:
   - Copy full `cookie` header value → **`config/cookies.txt`**
   - Copy full `user-agent` header value → **`config/user_agent.txt`**

**Essential Cookies:**

- `fab_csrftoken` — CSRF protection
- `fab_sessionid` — user session
- `cf_clearance` — 🔴 **CRITICAL** for Cloudflare (validated by IP + User-Agent)
- `__cf_bm` — bot management (expires ~30 min)

### Step 2: Test Configuration

Before launching the app, test your config:

```bash
python tests/test_connection.py
```

This script verifies:

- ✅ curl_cffi installed
- ✅ Cookies present
- ✅ Successful connection to fab.com

If you see `✅✅✅ SUCCESS!`, you're ready! Otherwise, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## 📖 Usage

### Initial Load

1. If `config/cookies.txt` and `config/user_agent.txt` exist → **automatic at startup**
2. Click **🔄 Get New Assets** to fetch assets
3. Data is cached in `assets/` (individual files)

### Filtering & Search

| Feature              | Description                                                    |
| -------------------- | -------------------------------------------------------------- |
| 🔍 **Search**        | Title in real-time, case-insensitive                           |
| **UE Versions**      | Filter by engine version (multi-select)                        |
| **UE Max**           | Maximum supported version (semantic sort: 4.27, 5.0, 5.3, ...) |
| **Licenses**         | Filter by license type (multi-select)                          |
| 📥 **Downloadable**  | Show only downloadable assets                                  |
| 🔞 **Adult Content** | Hide adult/mature content                                      |

### Sorting

Click **Title**, **Added**, or **Updated** to toggle sort ascending ↔ descending.

### Selection & Export

1. Check assets to export (or select entire page)
2. Click **⬇ CSV** or **⬇ JSON**
3. If no selection → exports all **filtered** assets
4. File named: `fab_export_YYYY-MM-DD.csv|json`

### Image Preview (Lazy Loading)

1. Thumbnails display on page load
2. Click image to see **fullscreen preview**
3. Images cached in `previews/` (one-time download)
4. Press **Escape** to close modal

### Cache Update

#### "Get Details" (batch metadata enrichment)

- If assets are **selected** (checkboxes), only those are enriched.
- If no selection, proposes batch enrichment for **all** assets missing details.
- **Stop Scraping** button available to interrupt the process at any time.
- Fetches complete product descriptions, technical specs, media galleries, seller avatars, and review counts.
- Updates the `assets/<UID>.json` file seamlessly.

#### "Get New Assets" (partial mode)

- Fetch new assets from fab.com
- Early stop if assets already cached (optimized)
- Merge with existing cache
- Shows "No new assets — your library is up to date!" when nothing new
- ⚡ Fast for small updates

#### "Full Update" (full mode)

- Asks for confirmation (slow)
- Download **all assets** without cache check
- Replace entire cache
- Guarantees 100% freshness

---

## 🗂️ Project Structure

```
FabAssetsManager/
├── _helpers/               # Dev files and tools
│   ├── asset_example.json  # Example asset content
│   ├── specs.md            # INITIAL specs and technical notes
│   ├── TROUBLESHOOTING.md  # Troubleshooting info
│   └── test_connection.py  # Connection test script
├── app.py                  # Main Flask server
├── cache_manager.py        # Cache system management
├── fetch_fab_library.py    # Client API fab.com
├── assets/                 # Asset cache (auto-created)
│   ├── <UID>.json          # Individual files
│   └── last_update.txt     # Update metadata
├── previews/               # Image cache (auto-generated)
│   └── <UID>.jpg
├── static/
│   ├── index.html          # Web interface
│   └── ...
├── config/                 # User specific config
│   ├── cookies.txt         # To fill in: your session cookie (KEEP THIS SECRET)
│   └── user_agent.txt      # To fill in: your User-Agent (leave as-is unless connection issues)
├── requirements.txt        # Python dependencies
├── TODO.md                 # Tasks / known bugs / improvements
├── LICENCE                 # Project license (MIT)
└── README.md               # This file
```

---

## 🔌 API Documentation

The FabAssetsManager provides a local REST API for integration with other tools (like curation pipelines).

- **Practical Integration Guide**: 📖 [API_GUIDE.md](API_GUIDE.md) (Workflows, Errors, Examples)
- **Technical Reference**: 📄 [openapi.yaml](openapi.yaml) (Standard OpenAPI 3.1 Specification)

### Quick Examples

- `GET /api/lookup?uid=...` : Find an asset by UID, Name, or URL.
- `GET /api/details/{uid}` : Get full metadata (lazy-loaded).
- `GET /api/image/{uid}` : Serve/Download asset thumbnail.

---

## 🛠️ Tools & Scripts

### tests/test_connection.py

Verify your configuration before launching:

```bash
python tests/test_connection.py
```

### fetch_fab_library.py (standalone usage)

Fetch assets from command line:

```bash
python fetch_fab_library.py \
  --cookies "fab_csrftoken=...;..." \
  --output my_library \
  --format both \
  --debug
```

---

## ⚠️ Important Notes

### Cookie Security

- `cf_clearance` token is bound to your **IP + User-Agent**
- **NEVER** share your cookies (equivalent to a password)
- Cookies expire in ~24-48h → regenerate if HTTP 403 error

### Cloudflare

- This app uses **curl_cffi** to emulate Chrome's TLS fingerprint
- This bypasses Cloudflare bot detection (CFFI-compliant)
- Reference: [Epic-Asset-Manager](https://github.com/AchetaGames/Epic-Asset-Manager)

### Limitations

- Local data only: **no cloud sync**
- Cache size: ~500MB-1GB for 3480 assets (metadata) plus images
- Performance: 50 items/page (optimized for smoothness)

---

## 📚 Resources

- **fab.com API**: based on work by [AchetaGames/egs-api-rs](https://github.com/AchetaGames/egs-api-rs)
- **Cloudflare bypass**: [curl_cffi docs](https://github.com/lexiforest/curl_cffi)
- **Problems?** → See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 📝 License

MIT

---

**Last updated**: April 2026
**Version**: 0.11.0 (Standardized API docs & unified guide)
