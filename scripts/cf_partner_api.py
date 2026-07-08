#!/usr/bin/env python3
"""CF signup via Partner/Enterprise path + direct API"""
from camoufox import Camoufox
import time, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

email = f"partnertest{int(time.time())}@hilmal.store"
pw = "PartnerTest123!"

# Test 1: CF Partner API signup
log("=== Test 1: CF Partner API ===")
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json',
    'Origin': 'https://dash.cloudflare.com',
    'Referer': 'https://dash.cloudflare.com/',
})

# Try CF API signup
api_urls = [
    'https://api.cloudflare.com/client/v4/signup',
    'https://dash.cloudflare.com/api/v1/signup',
    'https://dash.cloudflare.com/api/v2/signup',
]
for url in api_urls:
    try:
        r = session.post(url, json={'email': email, 'password': pw}, timeout=10)
        log(f"POST {url}: {r.status_code} | {r.text[:100]}")
    except Exception as e:
        log(f"POST {url}: {e}")

# Test 2: /cdn-cgi/challenge bypass
log("=== Test 2: CF challenge bypass ===")
bypass_urls = [
    'https://dash.cloudflare.com/cdn-cgi/challenge-platform/headers',
    'https://dash.cloudflare.com/cdn-cgi/challenge/cloudflare-primary',
]
for url in bypass_urls:
    try:
        r = session.get(url, timeout=10)
        log(f"GET {url}: {r.status_code} | {r.text[:100]}")
    except Exception as e:
        log(f"GET {url}: {e}")

# Test 3: Partner portal
log("=== Test 3: CF Partner portal ===")
with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    # Try partner signup
    partner_urls = [
        'https://partners.cloudflare.com/sign-up',
        'https://www.cloudflare.com/enterprise/signup',
        'https://dash.cloudflare.com/join',
        'https://www.cloudflare.com/partners/',
    ]
    for url in partner_urls:
        try:
            page.goto(url, timeout=15000)
            time.sleep(2)
            title = page.title()
            url2 = page.url
            log(f"{url}: {title} | {url2}")
            if 'signup' in title.lower() or 'sign up' in title.lower():
                break
        except Exception as e:
            log(f"{url}: Error {e}")
    
    browser.close()

# Test 4: Direct DNS signup (no browser challenge)
log("=== Test 4: CF Workers API ===")
try:
    # Get a clearance token via CF challenge endpoint
    r = requests.get(
        'https://dash.cloudflare.com/cdn-cgi/challenge-platform/headers',
        headers={'User-Agent': 'Mozilla/5.0 Chrome/120'},
        timeout=10
    )
    log(f"Challenge headers: {r.status_code} | {dict(r.headers)}")
except Exception as e:
    log(f"Challenge error: {e}")

# Test 5: Try browser with extended timeout + no challenge detection
log("=== Test 5: Browser test with extended wait ===")
with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    # Visit cloudflare.com first to warm up
    page.goto("https://cloudflare.com", timeout=60000)
    time.sleep(5)
    
    # Get cookies
    cookies_before = {c['name']: c['value'] for c in ctx.cookies()}
    log(f"Warm cookies: {len(cookies_before)}")
    for k, v in cookies_before.items():
        if 'cf' in k.lower():
            log(f"  CF: {k} = {v[:20]}")
    
    # Now go to signup
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    time.sleep(8)
    
    title = page.title()
    url = page.url
    body = page.inner_text('body')
    
    log(f"Result: {title} | {url}")
    
    if 'let us know' in body.lower():
        log("Challenge shown - need cf_clearance cookie")
    else:
        log("No challenge on warmup visit!")
        # Add warm cookies and try again
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', pw)
        time.sleep(0.5)
        page.click('button[type="submit"]')
        time.sleep(8)
        
        if 'dashboard' in page.title().lower():
            log("SUCCESS!")
        else:
            log(f"Result: {body[:200]}")
    
    browser.close()

log("=== Done ===")