# 🔧 Troubleshooting Guide - 403 Error when accessing FAB

## Step 1: Verify curl_cffi installation

Cloudflare bypass **requires** curl_cffi:

```bash
pip install curl_cffi
```

If installation fails on Windows, try:

```bash
pip install --upgrade pip
pip install curl_cffi --prefer-binary
```

## Step 2: Test your configuration

Run the diagnostic script:

```bash
python tests/test_connection.py
```

The script checks:

- ✅ Whether curl_cffi is installed
- ✅ Whether cookies are present and valid
- ✅ Whether the connection to fab.com works

## Step 3: Regenerate cookies (if needed)

**IMPORTANT**: Cookies must be generated **ON THE SAME MACHINE** where you run the app.

### How to generate valid cookies

1. **On this machine**, open Chrome/Edge/Firefox
2. Log in to https://www.fab.com
3. Go to https://www.fab.com/library (important)
4. Open DevTools (F12)
5. Open the **Network** tab
6. Reload the page (F5)
7. Find a request to `entitlements` (or any fab.com request)
8. Right-click → Copy → **Copy as cURL**

### Extract data from copied cURL

In the cURL text, find:

```bash
# Cookie line: (everything after -H 'cookie: ')
cookie: fab_csrftoken=...; fab_sessionid=...; cf_clearance=...; __cf_bm=...

# User-Agent line: (everything after -H 'user-agent: ')
user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...
```

### Copy values into files

**config/cookies.txt**: copy EXACTLY what comes after `cookie:` (full value, including all `;`)

**user_agent.txt**: copy EXACTLY what comes after `user-agent:`

## Step 4: Run the test again

```bash
python test_connection.py
```

You should see:

```
✅ curl_cffi is installed
✅ Cookies loaded: XXX characters
✅ User-Agent: Mozilla/5.0...
✅ All critical cookies are present
🚀 Using curl_cffi with Chrome 120 impersonation
✅✅✅ SUCCESS! Connection works!
```

## Common issues

### ❌ "curl_cffi is NOT installed"

→ Run `pip install curl_cffi`

### ❌ "Missing cookies: cf_clearance"

→ The `cf_clearance` cookie was not copied. It is **essential**.
→ Regenerate cookies by following step 3.

### ❌ HTTP 403 even with curl_cffi

→ **Likely cause**: Cookies were generated on another machine or with another browser
→ **Solution**: Regenerate cookies **on this machine**

### ❌ "cf_clearance" is tied to IP

→ If you use a VPN or your IP changes, cf_clearance becomes invalid
→ Regenerate cookies after each IP change

### ❌ Cookies expire after a few hours

→ This is normal: `__cf_bm` expires after ~30 min, `cf_clearance` after a few hours
→ Regenerate when error 403 appears

## Step 5: If it works, start the app

```bash
python app.py
```

Then open http://localhost:5002 and click **🔄 Get New Assets**.
  NOTE: 5002 is the default port for the web interface, but the it can be changed in `config/config.json`

---

## Alternative: Use existing Chrome profile

If nothing works, a more robust option is to use Playwright with your Chrome profile:

```bash
pip install playwright
playwright install chromium
```

Then run the app with a `--use-browser` option (feature to implement if needed).
