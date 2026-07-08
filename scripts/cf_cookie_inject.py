#!/usr/bin/env python3
"""CF signup - requests page load + browser cookie injection (no proxy needed)"""
from camoufox import Camoufox
import time, re, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

BRD = {
    'http': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335',
    'https': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335'
}

email = f"cookietest{int(time.time())}@hilmal.store"
pw = "Cookietest123!"
log(f"Email: {email}")

# Step 1: Get page + cookies via requests (via Bright Data)
log("=== Step 1: Get CF page + cookies via requests ===")
session = requests.Session()
session.proxies = BRD
session.verify = False
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
})

r = session.get('https://dash.cloudflare.com/sign-up', timeout=30)
log(f"Page status: {r.status_code}")

# Extract ALL cookies from session
raw_cookies = []
for name, value in session.cookies.get_dict().items():
    raw_cookies.append({
        'name': name,
        'value': value,
        'domain': '.dash.cloudflare.com',
        'path': '/'
    })
    # Also set for cloudflare.com
    raw_cookies.append({
        'name': name,
        'value': value,
        'domain': '.cloudflare.com',
        'path': '/'
    })

log(f"Extracted {len(raw_cookies)} cookies")

# Extract page content hash to detect challenge
page_hash = hash(r.text[:500])
log(f"Page hash: {page_hash}")

# Check for challenge widget
if 'challenge' in r.text.lower():
    log("Challenge JS detected in page")
    # Try to find challenge data
    challenge_data = re.search(r'challengeToken\w*["\x27]\s*[:=]\s*["\x27]([A-Za-z0-9+/=]+)', r.text)
    if challenge_data:
        log(f"Challenge token: {challenge_data.group(1)[:30]}")
else:
    log("No challenge detected in requests page")

# Step 2: Use browser with injected cookies (NO proxy needed)
log("=== Step 2: Browser with injected cookies (no proxy) ===")
with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    # Inject cookies from requests
    for c in raw_cookies:
        try:
            ctx.add_cookies([c])
        except:
            pass
    
    log(f"Injected {len(raw_cookies)} cookies")
    
    # Navigate to CF signup
    page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
    time.sleep(5)
    
    title = page.title()
    url = page.url
    body = page.inner_text('body')
    
    log(f"Page: {title} | {url}")
    log(f"Body preview: {body[:150]}")
    
    if 'dashboard' in title.lower() and 'sign-up' not in url:
        log("SUCCESS - logged in via cookies!")
    elif 'let us know' in body.lower() or 'verify you are human' in body.lower():
        log("CAPTCHA challenge shown")
        page.screenshot(path='/tmp/cf_cookie_challenge.png')
    elif 'email' in body.lower() and 'password' in body.lower():
        log("Signup form - cookies not logged in, try submit")
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', pw)
        time.sleep(0.5)
        page.click('button[type="submit"]')
        time.sleep(10)
        
        if 'dashboard' in page.title().lower():
            log("SUCCESS!")
            page.screenshot(path='/tmp/cf_cookie_success.png')
        else:
            body2 = page.inner_text('body')
            log(f"Result: {body2[:200]}")
    else:
        log(f"Other result")
        page.screenshot(path='/tmp/cf_cookie_other.png')
    
    browser.close()

log("=== Done ===")