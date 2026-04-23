# ============================================================================
# FabAssetsManager - fetch_fab_library.py
# ============================================================================
# Description: Fab.com library crawler (API calls + pagination + cache logic).
# Version: 1.0.4
# ============================================================================

import csv
import json
import sys
import time
import argparse
import re
import requests  # Fallback always available
import logging
from .models import Asset

logger = logging.getLogger("FabAssetsManager.fetch")

# Try curl_cffi (emulates Chrome TLS fingerprint to bypass Cloudflare)
cffi_requests = None
try:
    from curl_cffi import requests as cffi_requests  # type: ignore[import-not-found]
    USE_CURL_CFFI = True
except ImportError:
    USE_CURL_CFFI = False

BASE_URL = "https://www.fab.com"
ENTITLEMENTS_URL = f"{BASE_URL}/i/library/search"

DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://www.fab.com/library",
    "Origin": "https://www.fab.com",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "Connection": "keep-alive",
    "DNT": "1",
    "Sec-GPC": "1",
}


def get_chrome_major(user_agent: str) -> str:
    """Extract Chrome major version from User-Agent, or empty if unavailable."""
    if not user_agent:
        return ""
    match = re.search(r"Chrome/(\d+)", user_agent)
    return match.group(1) if match else ""


def build_headers_for_user_agent(user_agent: str) -> dict:
    """Build UA-dependent Client Hints for Chromium browsers.

    Keeping these hints aligned with the real browser reduces Cloudflare mismatches.
    """
    if "Chrome/" not in user_agent and "Chromium/" not in user_agent and "Edg/" not in user_agent:
        return {}

    chrome_major = get_chrome_major(user_agent) or "133"

    if "Android" in user_agent:
        platform = "Android"
    elif "Windows" in user_agent:
        platform = "Windows"
    elif "Macintosh" in user_agent or "Mac OS X" in user_agent:
        platform = "macOS"
    elif "Linux" in user_agent:
        platform = "Linux"
    else:
        platform = "Unknown"

    is_mobile = "Mobile" in user_agent or "Android" in user_agent or "iPhone" in user_agent

    return {
        "sec-ch-ua": f'"Chromium";v="{chrome_major}", "Not-A.Brand";v="99", "Google Chrome";v="{chrome_major}"',
        "sec-ch-ua-mobile": "?1" if is_mobile else "?0",
        "sec-ch-ua-platform": f'"{platform}"',
    }


def create_http_session(user_agent: str = "", debug: bool = False):
    """Create a session with best-effort curl_cffi browser impersonation."""

    if USE_CURL_CFFI and cffi_requests is not None:
        candidates = ["chrome120", "chrome"]

        seen = set()
        for impersonation in candidates:
            if impersonation in seen:
                continue
            seen.add(impersonation)
            try:
                session = cffi_requests.Session(impersonate=impersonation)  # type: ignore[attr-defined]
                if debug:
                    logger.info(f"✅ Using curl_cffi impersonation: {impersonation}")
                return session
            except Exception as e:
                if debug:
                    logger.info(f"⚠️  curl_cffi impersonation failed ({impersonation}): {e}")

    if debug:
        logger.info("⚠️ curl_cffi unavailable or incompatible — using requests (may fail with Cloudflare)")
    return requests.Session()


def parse_cookies(cookie_string: str) -> dict:
    cookies = {}
    for item in cookie_string.split(";"):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            cookies[key.strip()] = value.strip()
    return cookies


def fetch_all_assets(cookie_string: str, user_agent: str = "", verbose: bool = True, debug: bool = False, last_update_date: str = "") -> list:
    """Fetch assets from fab.com API with support for partial updates.

    Connects to fab.com's entitlements API endpoint which returns assets sorted by
    creation date (newest first). Implements early-stopping optimization for partial
    updates: when an asset's createdAt is older than last_update_date, subsequent
    assets are guaranteed to be older, so fetching stops early.

    Args:
        cookie_string: Complete cookie string from browser session (must include
                      fab_csrftoken, fab_sessionid, and cf_clearance - the last one
                      is critical for Cloudflare bypass)
        user_agent: User-Agent header value (should match browser that generated cookies,
                      as cf_clearance is bound to IP + User-Agent combination)
        verbose: Print progress messages during fetch (page count, asset count)
        debug: Enable verbose logging of headers, cookies, and error details
        last_update_date: ISO datetime string (e.g., "2025-03-15T10:30:00") - when set,
                          fetches only assets created after this date (early stopping)
                          Empty string = full fetch (default behavior)

    Returns:
        List of raw asset dictionaries from API (not flattened). Each asset contains:
        - listing: metadata (uid, title, medias with images, etc.)
        - unrealEngineEngineVersions: list of supported UE versions
        - licenses: list of license objects with 'name' field
        - capabilities: object with requestDownloadUrl boolean
        - createdAt: ISO timestamp
        - + other API fields

    Raises:
        (none - returns empty list on error)

    Example:
        >>> cookies = "fab_csrftoken=...;fab_sessionid=...;cf_clearance=..."
        >>> user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        >>> assets = fetch_all_assets(cookies, user_agent, verbose=True)
        >>> logger.info(f"Fetched {len(assets)} assets")
        Fetched 3480 assets
    """
    # Parse cookie string into dictionary (format: "key1=val1;key2=val2;...")
    cookies = parse_cookies(cookie_string)

    # Initialize HTTP session with TLS fingerprint emulation (curl_cffi) if available
    # curl_cffi impersonates Chrome's TLS fingerprint to bypass Cloudflare's bot detection
    # Fallback to standard requests library if curl_cffi not installed (may fail on Cloudflare)
    session = create_http_session(user_agent=user_agent, debug=debug)

    # Add parsed cookies to session
    session.cookies.update(cookies)

    # Debug output: show parsed cookies for troubleshooting
    if debug:
        logger.info("🔍 Parsed cookies:")
        for k, v in cookies.items():
            # Truncate long values for readability
            logger.info(f"   {k} = {v[:30]}..." if len(v) > 30 else f"   {k} = {v}")
        logger.info(f"\n🌐 cf_clearance present: {'cf_clearance' in cookies}")
        logger.info(f"🌐 fab_sessionid present: {'fab_sessionid' in cookies}")

    # Prepare HTTP headers
    headers = dict(DEFAULT_HEADERS)

    # Set User-Agent: use provided value (MUST match browser that generated cf_clearance)
    # If none provided, use default Chrome UA
    if user_agent:
        headers["User-Agent"] = user_agent
    else:
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

    # Generate coherent Client Hints from current User-Agent.
    headers.update(build_headers_for_user_agent(headers["User-Agent"]))

    # Add CSRF token if present (Django CSRF protection requirement)
    if "fab_csrftoken" in cookies:
        headers["X-CSRFToken"] = cookies["fab_csrftoken"]

    session.headers.update(headers)

    # Initialize pagination state
    all_assets = []
    cursor = None
    page = 1
    early_stop = False

    # Show partial update mode if active
    if last_update_date and verbose:
        logger.info(f"📅 Partial update mode (stop before {last_update_date})")

    # Pagination loop: fetch pages until all assets retrieved or early stop triggered
    while True:
        # API parameters: count per page, sort by creation date (newest first)
        params = {"count": 100, "sort_by": "-createdAt"}
        if cursor:
            params["cursor"] = cursor

        if verbose:
            logger.info(f"📦 Page {page}...")

        # HTTP request with timeout
        try:
            resp = session.get(ENTITLEMENTS_URL, params=params, timeout=30)
        except Exception as e:
            logger.info(f"\n❌ Network error: {e}")
            break

        # Handle HTTP 403 (Cloudflare block or cookie expiration)
        if resp.status_code == 403:
            logger.info("\n❌ HTTP 403 — cookies expired or Cloudflare is blocking.")
            logger.info("   Make sure you run this script on the same machine as your browser.")
            if not USE_CURL_CFFI:
                logger.info("   💡 Install curl_cffi to bypass detection: pip install curl_cffi")
            if debug:
                logger.info("\n🔍 DEBUG - Sent Headers:")
                for k, v in session.headers.items():
                    v_str = str(v) if v is not None else "None"
                    logger.info(f"   {k}: {v_str[:60]}..." if len(v_str) > 60 else f"   {k}: {v_str}")
                logger.info("\n🔍 DEBUG - 403 Response:")
                logger.info(f"   Content-Type: {resp.headers.get('content-type', 'N/A')}")
                logger.info(f"   Cloudflare: {resp.headers.get('cf-ray', 'N/A')}")
                logger.info(f"   Response (first 300 chars): {resp.text[:300]}")
            return []
        elif resp.status_code != 200:
            logger.info(f"\n❌ HTTP {resp.status_code}: {resp.text[:300]}")
            break

        # Parse JSON response
        try:
            data = resp.json()
        except json.JSONDecodeError:
            logger.info("\n❌ Non-JSON response received.")
            break

        results = data.get("results", [])

        # Early stopping optimization for partial updates
        # Since API returns assets sorted by -createdAt (newest first):
        # If asset.createdAt < last_update_date, all subsequent pages will also be < last_update_date
        # So we can stop fetching and avoid unnecessary API calls
        if last_update_date and results:
            new_results = []
            for asset in results:
                created_at = asset.get("createdAt", "")
                # ISO datetime comparison works because formatted consistently
                if created_at and created_at < last_update_date:
                    # This asset and all following are older than last update
                    early_stop = True
                    if verbose:
                        logger.info(f"\n⏹️  Early stop: asset created before {last_update_date}")
                    break
                new_results.append(asset)
            results = new_results

        # Accumulate results
        all_assets.extend(results)

        # Progress output
        total = data.get("count", "?")
        if verbose:
            logger.info(f"✅ +{len(results)} (total: {len(all_assets)}/{total})")

        # Exit if early stop triggered
        if early_stop:
            break

        # Check for next page
        cursors = data.get("cursors") or {}
        next_cursor = cursors.get("next")

        # Exit if no more pages or empty results
        if not next_cursor or not results:
            break

        # Move to next page and add small delay to avoid server throttling
        cursor = next_cursor
        page += 1
        time.sleep(0.3)

    return all_assets


def fetch_asset_details(uid: str, cookie_string: str, user_agent: str = "", debug: bool = False) -> dict:
    """Fetch detailed information for a single asset via its UID.

    Connects to fab.com/i/listings/<uid> to retrieve extended metadata
    (like full media gallery, specific formats, extended descriptions).
    """
    cookies = parse_cookies(cookie_string)
    session = create_http_session(user_agent=user_agent, debug=debug)
    session.cookies.update(cookies)

    headers = dict(DEFAULT_HEADERS)
    if user_agent:
        headers["User-Agent"] = user_agent
    else:
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    headers.update(build_headers_for_user_agent(headers["User-Agent"]))
    if "fab_csrftoken" in cookies:
        headers["X-CSRFToken"] = cookies["fab_csrftoken"]
    session.headers.update(headers)

    url = f"{BASE_URL}/i/listings/{uid}"
    try:
        resp = session.get(url, timeout=30)
    except Exception as e:
        logger.info(f"\n❌ Network error fetching details for {uid}: {e}")
        return {}

    if resp.status_code != 200:
        if debug:
            logger.info(f"\n❌ HTTP {resp.status_code} fetching details for {uid}: {resp.text[:300]}")
        return {}

    try:
        data = resp.json()
        return data
    except json.JSONDecodeError:
        if debug:
            logger.info(f"\n❌ Non-JSON response for {uid}")
        return {}


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Fetch your fab.com library")
    parser.add_argument("--cookies", required=True, help="Complete cookie string")
    parser.add_argument("--output", default="fab_library", help="Output file name")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    logger.info("🚀 Connecting to fab.com...")
    assets = fetch_all_assets(args.cookies, debug=args.debug)

    if not assets:
        logger.info("❌ No assets retrieved.")
        sys.exit(1)

    logger.info(f"\n🎉 {len(assets)} assets retrieved!")

    if args.format in ("json", "both"):
        out = f"{args.output}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(assets, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ JSON → {out}")

    if args.format in ("csv", "both"):
        out = f"{args.output}.csv"
        flat = [Asset(a).to_dict() for a in assets]
        with open(out, "w", newline="", encoding="utf-8") as f:
            if flat:
                writer = csv.DictWriter(f, fieldnames=flat[0].keys())
                writer.writeheader()
                writer.writerows(flat)
        logger.info(f"✅ CSV → {out}")
