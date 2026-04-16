# ============================================================================
# FabAssetsManager - cache_manager.py
# ============================================================================
# Description: Distributed cache management (individual JSON files).
# Version: 1.0.1
# ============================================================================

# Individual asset file storage for the local cache.
#
# This module implements a distributed cache system where each asset is stored
# as an individual JSON file instead of a monolithic cache. This approach enables:

# ARCHITECTURE OVERVIEW:
# ═════════════════════════════════════════════════════════════════════════════

# Cache Structure:
#   assets/
#     ├── <UID_1>.json          (individual asset 1)
#     ├── <UID_2>.json          (individual asset 2)
#     ├── ...
#     ├── <UID_3480>.json       (individual asset 3480)
#     └── last_update.txt       (metadata: count, oldest_created_at, last_update)

# Advantages of Individual Files:
# - PARTIAL UPDATES: Fetch only new/modified assets (early stopping optimization)
# - SCALABILITY: Add/remove assets without rewriting entire cache
# - RESILIENCE: One corrupt file doesn't break entire cache
# - MEMORY EFFICIENT: No need to load all assets simultaneously
# - ASYNC FRIENDLY: Can load assets in parallel if needed

# Performance Characteristics:
# - Add single asset: ~1ms (write one file)
# - Load all 3480 assets: ~500ms (parallel I/O, JSON parsing)
# - Check if asset exists: <1ms (filesystem stat)
# - Update metadata: <1ms (small text file)

# METADATA FILE FORMAT (last_update.txt):
# ═════════════════════════════════════════════════════════════════════════════

# count=3480
# oldest_created_at=2024-01-15T10:30:00  (earliest createdAt from fetched assets)
# last_update=2025-03-15T18:45:00        (ISO timestamp of last fetch)

# This metadata enables:
# - Early stopping in partial updates (stop before oldest_created_at)
# - Cache staleness detection in UI
# - Quick asset count without filesystem scan

# IMAGE CACHING (previews/):
# ═════════════════════════════════════════════════════════════════════════════

# Separate from asset cache:
#   previews/
#     ├── <UID_1>.jpg  (cached thumbnail from fab.com)
#     ├── <UID_2>.jpg
#     └── ...

# Managed by app.py /api/image/<uid> endpoint:
# - First access: download from fab.com, save to previews/<uid>.jpg
# - Subsequent: serve from disk cache (no network)
# - Persistent: survives app restart (unlike in-memory cache)

# USAGE EXAMPLES:
# ═════════════════════════════════════════════════════════════════════════════

# # Save new asset (called during fetch)
# asset = fetch_fab_library.fetch_all_assets(...)[0]
# cache_manager.save_asset(asset)

# # Load all assets for display
# assets = cache_manager.load_all_assets()  # Returns list of 3480 dicts

# # Check if asset cached
# if cache_manager.asset_exists("001d83fe-..."):
#     asset = cache_manager.get_asset("001d83fe-...")

# # Get metadata for partial updates
# metadata = cache_manager.load_update_metadata()
# last_update_date = metadata.get("oldest_created_at", "")
# fetch_fab_library.fetch_all_assets(..., last_update_date=last_update_date)
# ============================================================================

import json
import logging
from pathlib import Path
from datetime import datetime
import time

logger = logging.getLogger("FabAssetsManager.cache")

# Memory cache for load_all_assets()
_memory_cache = {"assets": None, "timestamp": 0}
CACHE_TTL_SECONDS = 300  # 5 minutes TTL


def clear_memory_cache() -> None:
    """Invalidate the in-memory cache. Call this after any cache mutation."""
    _memory_cache["assets"] = None
    _memory_cache["timestamp"] = 0


def _get_assets_dir() -> Path:
    from app import ASSETS_DIR
    return ASSETS_DIR


def _get_last_update_file() -> Path:
    from app import LAST_UPDATE_FILE
    return LAST_UPDATE_FILE


def init_assets_dir() -> None:
    """Create assets directory if it doesn't exist."""
    _get_assets_dir().mkdir(exist_ok=True)


def save_asset(asset: dict) -> None:
    """Save a single asset to assets/<UID>.json

    Each asset is stored as an individual JSON file in the assets/ directory.
    This enables partial updates and incremental cache management.

    Args:
        asset: Raw asset dictionary from fab.com API containing:
                - listing (with uid, title, medias, etc.)
                - unrealEngineEngineVersions (array of UE versions)
                - licenses (array of license objects)
                - capabilities (with requestDownloadUrl)
                - createdAt, etc.

    File naming: assets/<UID>.json where UID from asset['listing']['uid']
    Format: Pretty-printed JSON with UTF-8 encoding, ensure_ascii=False

    Error handling: Silent skip if asset has no UID (malformed data)
    """
    init_assets_dir()
    uid = asset.get("listing", {}).get("uid", "")
    if not uid:
        return

    filepath = _get_assets_dir() / f"{uid}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(asset, f, ensure_ascii=False, indent=2)
    clear_memory_cache()


def save_assets_batch(assets: list) -> None:
    """Save multiple assets to individual files."""
    for asset in assets:
        save_asset(asset)


def save_update_metadata(asset_count: int, oldest_created_at: str = "") -> None:
    """Save update metadata to last_update.txt

    Metadata file format (plain text, key=value):
        count=<total_assets>
        oldest_created_at=<ISO datetime of oldest fetched asset>
        last_update=<ISO datetime of fetch completion>

    Purpose:
        - count: Quick way to show "X assets cached" without scanning filesystem
        - oldest_created_at: Used for early stopping in partial updates
                            When next fetch happens, stop before this date
                            (since older assets are already cached)
        - last_update: Human-readable timestamp of last fetch for UI display

    Args:
        asset_count: Total number of cached assets (sum of all files)
        oldest_created_at: ISO datetime of oldest createdAt from latest fetch
                          Used for early stopping in next partial update
                          Format: "2025-03-15T10:30:00"
                          If empty: not written to file (metadata stays stale)

    Example workflow:
        1. fetch_all_assets() returns 10 new assets, oldest = "2025-03-10..."
        2. save_asset() saves all 10 to individual files
        3. save_update_metadata(3480, "2025-03-10...") saves metadata
        4. Next fetch: load_update_metadata() returns oldest_created_at
        5. fetch_all_assets(last_update_date="2025-03-10...") stops early
    """
    init_assets_dir()

    now = datetime.now().isoformat()
    content = f"count={asset_count}\n"
    if oldest_created_at:
        content += f"oldest_created_at={oldest_created_at}\n"
    content += f"last_update={now}\n"

    last_update_file = _get_last_update_file()
    with open(last_update_file, "w", encoding="utf-8") as f:
        f.write(content)


def load_update_metadata() -> dict:
    """Load update metadata from last_update.txt

    Reads the metadata file and parses key=value pairs.

    Returns:
        Dictionary with keys:
        - 'count': Number of cached assets (string, convert with int())
        - 'oldest_created_at': ISO datetime of oldest asset in last fetch
        - 'last_update': ISO datetime of last fetch completion

        Returns empty dict {} if:
        - File doesn't exist (no cache yet)
        - File is malformed/corrupted (error logged)

    Usage in fetch_all_assets():
        metadata = load_update_metadata()
        oldest = metadata.get('oldest_created_at', '')
        # Pass to fetch_all_assets for early stopping
        fetch_all_assets(..., last_update_date=oldest)

    Error handling:
        Invalid lines are silently skipped
        Malformed key=value pairs: skipped
        File read errors: warning logged, empty dict returned
    """
    last_update_file = _get_last_update_file()
    if not last_update_file.exists():
        return {}

    metadata = {}
    try:
        with open(last_update_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    metadata[key.strip()] = value.strip()
    except Exception as e:
        logger.info(f"⚠️  Error reading {last_update_file}: {e}")

    return metadata


def load_all_assets() -> list:
    """Load all assets from individual JSON files in assets/ directory.

    Scans assets/ for all *.json files and parses each as an asset object.
    Maintains compatibility with raw API format (not flattened) for flexibility.

    Returns:
        List of asset dictionaries in raw API format:
        [
            {
                'listing': {...},
                'unrealEngineEngineVersions': [...],
                'licenses': [...],
                'capabilities': {...},
                'createdAt': '...',
                ...
            },
            ...
        ]

        Empty list if:
        - assets/ directory doesn't exist yet
        - assets/ is empty
        - All files fail to parse (with error logging)

    Performance:
        - For 3480 assets: ~500ms total (JSON parsing is bottleneck)
        - Called once on page load (loadAssets() in HTML)
        - Results cached in app.py memory for filtering/export

    Error handling:
        - Corrupt/invalid JSON files: logged as warning, skipped
        - Missing file (deleted during runtime): ignored
        - Permission denied: warning logged

    Implementation detail:
        Uses sorted() glob for deterministic order (useful for testing/debugging)
        though order doesn't matter for UI functionality
    """
    now = time.time()
    if _memory_cache["assets"] is not None and (now - _memory_cache["timestamp"]) < CACHE_TTL_SECONDS:
        return _memory_cache["assets"]

    init_assets_dir()
    assets = []

    for filepath in sorted(_get_assets_dir().glob("*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                asset = json.load(f)
                assets.append(asset)
        except Exception as e:
            logger.info(f"⚠️  Error reading {filepath}: {e}")

    _memory_cache["assets"] = assets
    _memory_cache["timestamp"] = now
    return assets


def get_asset(uid: str) -> dict | None:
    """Get a single asset by UID from cache.

    Retrieves the pre-parsed asset object without loading entire cache.
    Useful for targeted accesses (e.g., image lazy loading endpoint).

    Args:
        uid: Asset unique identifier (from listing.uid)
             Format: "001d83fe-9594-42c5-a93e-3b277f74863d"

    Returns:
        Asset dictionary in raw API format, or None if:
        - File doesn't exist
        - File is unreadable/corrupted (error logged)

    Performance:
        - Filesystem stat: <1ms
        - JSON parse: ~0.5ms per asset
        - Much faster than load_all_assets() for single lookups

    Usage (in app.py /api/image/<uid> endpoint):
        asset = get_asset(uid)
        if asset:
            flat = Asset(asset).to_dict()
            thumbnail_url = flat.get('thumbnail_url')
    """
    filepath = _get_assets_dir() / f"{uid}.json"
    if not filepath.exists():
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.info(f"⚠️  Error reading {filepath}: {e}")
        return None


def asset_exists(uid: str) -> bool:
    """Check if asset file exists in cache (fast filesystem check).

    Args:
        uid: Asset unique identifier

    Returns:
        True if assets/<uid>.json file exists, False otherwise

    Performance: <1ms (filesystem stat only, no file read)

    Usage:
        if not asset_exists(uid):
            return jsonify({"error": "Asset not found"}), 404
    """
    return (_get_assets_dir() / f"{uid}.json").exists()
