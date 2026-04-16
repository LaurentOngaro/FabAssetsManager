# ============================================================================
# FabAssetsManager - API Test
# ============================================================================
# Description: Diagnostic script to test connection to fab.com and troubleshoot Cloudflare issues.
# Version: 1.0.2
# ============================================================================

import sys
import importlib
from pathlib import Path

# Ensure project root is importable when script is run from _helpers/
APP_DIR = Path(__file__).parent
ROOT_DIR = APP_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

fetch_fab_library = importlib.import_module("lib.fetch_fab_library")
build_headers_for_user_agent = fetch_fab_library.build_headers_for_user_agent
create_http_session = fetch_fab_library.create_http_session

# Check curl_cffi
try:
    import curl_cffi  # type: ignore[import-not-found]
    version = getattr(curl_cffi, "__version__", "unknown")
    print(f"✅ curl_cffi is installed (v{version})")
except ImportError:
    print("❌ curl_cffi is NOT installed")
    print("   Install it with: pip install curl_cffi")

# Load config
CONFIG_DIR = APP_DIR / "../config"
COOKIES_FILE = CONFIG_DIR / "cookies.txt"
UA_FILE = CONFIG_DIR / "user_agent.txt"

if not COOKIES_FILE.exists():
    print(f"\n❌ File {COOKIES_FILE} not found")
    sys.exit(1)

if not UA_FILE.exists():
    print(f"\n❌ File {UA_FILE} not found")
    sys.exit(1)

cookie_string = COOKIES_FILE.read_text(encoding="utf-8").strip()
user_agent = UA_FILE.read_text(encoding="utf-8").strip()

print(f"\n✅ Cookies loaded: {len(cookie_string)} characters")
print(f"✅ User-Agent: {user_agent[:60]}...")

# Parse cookies
cookies = {}
for item in cookie_string.split(";"):
    item = item.strip()
    if "=" in item:
        key, value = item.split("=", 1)
        cookies[key.strip()] = value.strip()

print(f"\n📊 Cookies found ({len(cookies)}):")
for k in cookies.keys():
    print(f"   - {k}")

# Check critical cookies
REQUIRED_COOKIES = ["cf_clearance", "fab_sessionid", "fab_csrftoken"]
missing = [c for c in REQUIRED_COOKIES if c not in cookies]
if missing:
    print(f"\n⚠️  Missing cookies: {', '.join(missing)}")
else:
    print("\n✅ All critical cookies are present")

# Prepare session (same logic as production fetch code)
session = create_http_session(user_agent=user_agent, debug=True)

session.cookies.update(cookies)

# Headers
headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://www.fab.com/library",
    "Origin": "https://www.fab.com",
    "User-Agent": user_agent,
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "Connection": "keep-alive",
    "DNT": "1",
    "Sec-GPC": "1",
}

headers.update(build_headers_for_user_agent(user_agent))

if "fab_csrftoken" in cookies:
    headers["X-CSRFToken"] = cookies["fab_csrftoken"]

session.headers.update(headers)

print("\n📤 Configured headers:")
for k, v in headers.items():
    v_str = str(v) if v is not None else "None"
    print(f"   {k}: {v_str[:60]}..." if len(v_str) > 60 else f"   {k}: {v_str}")

# Connection test
print("\n🔄 Testing connection to fab.com/i/library/search...")
url = "https://www.fab.com/i/library/search"
params = {"count": 10, "sort_by": "-createdAt"}

try:
    resp = session.get(url, params=params, timeout=30)
    print(f"\n📥 HTTP response: {resp.status_code}")
    print(f"   Content-Type: {resp.headers.get('content-type', 'N/A')}")
    print(f"   CF-Ray: {resp.headers.get('cf-ray', 'N/A')}")
    print(f"   Server: {resp.headers.get('server', 'N/A')}")

    if resp.status_code == 200:
        print("\n✅✅✅ SUCCESS! Connection works!")
        data = resp.json()
        count = data.get("count", data.get("total", "unknown"))
        results = len(data.get("results", []))
        print(f"   Total assets: {count}")
        print(f"   Assets on this page: {results}")
    elif resp.status_code == 403:
        print("\n❌ HTTP 403 - Cloudflare is blocking the request")
        print("\n💡 Possible causes:")
        print("   1. Cookies were generated on another machine")
        print("   2. User-Agent does not match the browser")
        print("   3. Cookies have expired")
        print("   4. IP changed since cookie generation")
        print("\n📄 Response (first 500 characters):")
        print(resp.text[:500])
    else:
        print(f"\n⚠️  Unexpected HTTP code: {resp.status_code}")
        print("\n📄 Response (first 300 characters):")
        print(resp.text[:300])

except Exception as e:
    print(f"\n❌ Request error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("End of diagnostics")
