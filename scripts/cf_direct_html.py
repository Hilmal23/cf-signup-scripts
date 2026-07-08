#!/usr/bin/env python3
"""CF signup - load modified HTML directly into browser"""
from camoufox import Camoufox
import time, re, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

BRD = {
    'http': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335',
    'https': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335'
}

email = f"directtest{int(time.time())}@hilmal.store"
pw = "DirectTest123!"
log(f"Email: {email}")

# Step 1: Get modified HTML via requests (via Bright Data)
log("=== Step 1: Get modified HTML via Bright Data ===")
session = requests.Session()
session.proxies = BRD
session.verify = False
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
})

r = session.get('https://dash.cloudflare.com/sign-up', timeout=30)
log(f"Page status: {r.status_code}")
log(f"Content length: {len(r.content)}")

# Get cookies
cookies = session.cookies.get_dict()
log(f"Cookies: {list(cookies.keys())}")

# Check for challenge
if 'challenge' in r.text.lower() or 'verify' in r.text.lower():
    log("Challenge present in page content")
    # Check challenge type
    if '__CF$cv$params' in r.text:
        log("CF Cloudflare challenge (precursor.js)")
    if 'turnstile' in r.text.lower():
        log("Turnstile CAPTCHA")
else:
    log("NO challenge in page!")

# Step 2: Load modified HTML directly into browser (bypass navigation MITM issue)
log("=== Step 2: Load modified HTML directly into browser ===")
with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    # Set cookies first
    for name, value in cookies.items():
        try:
            ctx.add_cookies([{'name': name, 'value': value, 'domain': '.dash.cloudflare.com', 'path': '/'}])
            ctx.add_cookies([{'name': name, 'value': value, 'domain': '.cloudflare.com', 'path': '/'}])
        except:
            pass
    
    # Set the modified HTML directly - bypasses navigation cert issue
    page.set_content(r.text, timeout=30000)
    time.sleep(5)
    
    title = page.title()
    body = page.inner_text('body')
    
    log(f"Page title: {title}")
    log(f"Body preview: {body[:150]}")
    
    if 'dashboard' in title.lower():
        log("SUCCESS - dashboard loaded!")
        # We're logged in!
    elif 'email' in body.lower() and 'password' in body.lower():
        log("Signup form loaded!")
        
        # Try to fill and submit
        try:
            page.fill('input[name="email"]', email)
            page.fill('input[name="password"]', pw)
            time.sleep(0.5)
            page.click('button[type="submit"]')
            log("Clicked submit...")
            time.sleep(10)
            
            if 'dashboard' in page.title().lower():
                log("SUCCESS! Account created!")
                page.screenshot(path='/tmp/cf_direct_success.png')
            else:
                body2 = page.inner_text('body')
                log(f"Result: {body2[:200]}")
        except Exception as e:
            log(f"Fill error: {e}")
    elif 'let us know' in body.lower():
        log("Challenge shown")
        page.screenshot(path='/tmp/cf_direct_challenge.png')
    else:
        log("Other result")
        page.screenshot(path='/tmp/cf_direct_other.png')
    
    browser.close()

log("=== Done ===")