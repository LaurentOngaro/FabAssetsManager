# FabAssetsManager API Guide

**Version:** 1.0.3

This guide explains how to integrate the FabAssetsManager API into your workflows (e.g., TerraBloom curation pipeline).

## 🚀 Quick Start

The API is available at `http://localhost:5002`. Most endpoints return flattened JSON objects.
(5002 is the default port for the web interface, but it can be changed in `config/config.json`)

### Local Configuration

- `GET /api/config` returns the current runtime state, including whether cookies and a user-agent are configured.
- `POST /api/config` saves cookies, user-agent, and logging preferences from the web interface.
- `POST /api/config/logging` saves logging preferences and applies them immediately.
- `GET /api/diagnostic` returns a local backend diagnostic report (auth/config/storage/cache) without calling Fab.com.
- `GET /api/test` returns a simple Flask health response.

### 🔍 Finding an Asset

Use `/api/lookup` to find assets in your local cache.

| Search by | Parameter | Example                                 |
| --------- | --------- | --------------------------------------- |
| **UID**   | `uid`     | `?uid=001d83fe-...`                     |
| **Name**  | `name`    | `?name=dungeon`                         |
| **URL**   | `url`     | `?url=https://www.fab.com/listings/...` |

**Example Response:**

```json
{
  "count": 1,
  "matches": [{ "uid": "...", "title": "...", "fab_url": "..." }]
}
```

---

## 🛠️ Key Workflows

### 1. Asset Enrichment (Lazy Loading)

If an asset is missing details (images, technical specs), call `/api/details/{uid}`.

- If cached: returns immediately.
- If not cached: fetches from Fab.com, updates local JSON, and returns.

### 2. Image Retrieval

To display thumbnails, use `/api/image/{uid}`.

- Downloads the image on the first call.
- Subsequent calls serve from `previews/` disk cache.

### 3. Asset Discovery and Status

- **`GET /api/assets`**: Retourne l'ensemble des assets disponibles dans le cache local, déjà aplatis pour l'usage côté client.
- **`POST /api/assets/query`**: Requête paginée/filtrée/triée côté backend (pagination server-side + facettes pour alimenter les filtres UI).
- **`GET /api/lookup`**: Recherche un asset par `uid`, `name` ou `url`.
- **`GET /api/status`**: Retourne un résumé léger de l'état du cache local.
- **`GET /api/missing_details`**: Retourne la liste des UID qui doivent encore être enrichis; accepte un paramètre `uids` ou un corps JSON.

### 4. Cache & Maintenance

- **`GET /api/cache-info`**: Retourne les métadonnées de synchronisation du cache local (`has_cache`, `count`, `last_sync_at`, `last_sync_label`, `age_seconds`, `age_human`).
- **`POST /api/fetch`**: Synchronise la bibliothèque Fab en utilisant les cookies et le User-Agent configurés localement.
- **`POST /api/clear_previews`**: Supprime toutes les images de prévisualisation enregistrées localement dans le dossier des previews.
- **`POST /api/clear_cache`**: Supprime tous les fichiers de cache des assets et remet à zéro l'état du cache local.

### 5. Custom Export Profiles

- **`GET /api/export-templates`**: Retourne les profils d'export personnalisés utilisés par la modale **Custom Export**.
- **`POST /api/export/json`** et **`POST /api/export/csv`**: exportent les assets, avec filtrage optionnel par UID sélectionnés.
- **`POST /api/export/headless`**: exporte directement vers un fichier local via `output_path` ou `output_dir` + `file_name` (mode automatisation sans téléchargement navigateur).
- Le frontend applique le pattern sélectionné asset par asset, puis choisit automatiquement l'extension du fichier exporté:
  - `.csv` pour les profils CSV
  - `.md` pour les profils Markdown
  - `.txt` pour les autres profils texte

### 6. Local User Annotations (FEAT3 / FEAT5)

- Favorites and per-asset comments are managed in the frontend and stored in browser localStorage, keyed by asset UID.
- No dedicated REST endpoint is required for these annotations.
- Since they are independent from `assets/*.json`, they are preserved when `/api/clear_cache` is used.

---

## ⚠️ Error Handling (Standardized)

All errors follow a unified structure based on **ErrorCode** and **HTTP Status**.

### Error Object Structure

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable explanation",
    "http_status": 404,
    "timestamp": "ISO-TIMESTAMP",
    "path": "/api/some-endpoint",
    "details": { "hint": "..." }
  }
}
```

### Common Error Codes

- `ASSET_NOT_FOUND` (404): Asset not in local cache. Synchronize your library first.
- `UNAUTHORIZED` (401): Cookies/User-Agent missing or expired.
- `CONNECTION_ERROR` (503): Fab.com API is unreachable or rate-limiting.
- `MISSING_PARAMETER` (400): Request is missing required fields.

---

## 📖 Reference Documents

- **Full API Specification**: [openapi.yaml](openapi.yaml)
- **Data Contract (Asset)**: [\_helpers/asset_output_schema_full.json](_helpers/asset_output_schema_full.json)
- **Data Contract (Error)**: [\_helpers/error_response_contract.json](_helpers/error_response_contract.json)

---

## 🐍 Integration Example (Python)

```python
import requests

BASE_URL = "http://localhost:5002/api"
# 5002 is the default port for the web interface, but the it can be changed in `config/config.json`

def get_asset_by_url(fab_url):
    response = requests.get(f"{BASE_URL}/lookup", params={"url": fab_url})
    if response.ok:
        matches = response.json().get("matches", [])
        return matches[0] if matches else None
    else:
        error = response.json().get("error", {})
        print(f"Error [{error.get('code')}]: {error.get('message')}")
    return None
```
