#!/usr/bin/env python3
"""Call CF precursor challenge API directly"""
from camoufox import Camoufox
import time, re, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# Get security token first
log("Getting security token...")
with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=30000)
    time.sleep(3)
    
    security_token = page.evaluate("() => document.querySelector('input[name=\"security_token\"]')?.value || ''")
    log(f"Security token: {security_token}")
    
    # Get cookies for API call
    cookies = ctx.cookies()
    cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
    log(f"Cookies: {len(cookies)} items")
    
    # Try precursor API
    precursor_urls = [
        f"https://dash.cloudflare.com/cdn-cgi/challenge-platform/scripts/precursor/main.js",
        f"https://dash.cloudflare.com/cdn-cgi/challenge/h?captcha=1&token={security_token}",
        f"https://challenges.cloudflare.com/turnstile/v0/widget?token={security_token}",
    ]
    
    for url in precursor_urls:
        try:
            r = requests.get(url, timeout=10)
            log(f"URL: {r.status_code} | {r.text[:100]}")
        except Exception as e:
            log(f"URL {url}: {e}")
    
    # Intercept: watch network requests
    intercepted = []
    
    def handle_request(request):
        if 'challenge' in request.url.lower() or 'turnstile' in request.url.lower():
            intercepted.append(request.url)
    
    page.on_request(lambda r: handle_request(r))
    
    # Fill form + trigger challenge
    page.fill('input[name="email"]', 'test@hilmal.store')
    page.fill('input[name="password"]', 'Test123!')
    time.sleep(2)
    
    # Check if any challenge requests were made
    log(f"Intercepted challenge URLs: {intercepted}")
    
    browser.close()

# Try calling the CF challenge platform API
log("=== Try CF challenge platform API ===")
try:
    # CF precursor challenge API
    r = requests.post(
        "https://dash.cloudflare.com/cdn-cgi/challenge-platform/",
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data={'sitekey': '0x4AAAAAAABlg1iaAR3mgkjp', 'pageurl': 'https://dash.cloudflare.com/sign-up'},
        timeout=10
    )
    log(f"Response: {r.status_code} | {r.text[:200]}")
except Exception as e:
    log(f"Challenge API error: {e}")

# Try the actual challenge endpoint
log("=== Try actual challenge endpoint ===")
try:
    r = requests.get(
        "https://dash.cloudflare.com/cdn-cgi/challenge/platform",
        params={'token': 'test'},
        timeout=10
    )
    log(f"Platform challenge: {r.status_code} | {r.headers}")
except Exception as e:
    log(f"Platform error: {e}")

# Try CF API v4 to get challenge token
log("=== Try CF API for challenge token ===")
try:
    r = requests.get(
        "https://dash.cloudflare.com/api/v4/challenge",
        timeout=10
    )
    log(f"API v4 challenge: {r.status_code} | {r.text[:200]}")
except Exception as e:
    log(f"API v4 error: {e}")

log("=== Done ===")