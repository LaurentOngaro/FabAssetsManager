# API Guide - FabAssetsManager

**Version:** 0.13.1
This guide explains how to integrate the FabAssetsManager API into your workflows (e.g., TerraBloom curation pipeline).

## 🚀 Quick Start

The API is available at `http://localhost:5002`. Most endpoints return flattened JSON objects.
(5002 is the default port for the web interface, but the it can be changed in `config/config.json`)

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

### 3. Asset Management

- **`GET /api/assets`**: Retourne une liste des assets disponibles dans le cache local.
- **`GET /api/assets/{uid}`**: Retourne les détails d'un asset spécifique.
- **`POST /api/assets`**: Ajoute un nouvel asset au cache local.

### 4. Cache & Maintenance

- **`GET /api/cache-info`**: Retourne des statistiques sur le cache local (nombre d'assets, taille totale, espace libre, date de dernière mise à jour).
- **`POST /api/clear_previews`**: Supprime toutes les images de prévisualisation enregistrées localement dans le dossier des previews.
- **`POST /api/clear_cache`**: Supprime tous les fichiers de cache des assets et remet à zéro l'état du cache local.

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

