#!/usr/bin/env python3
"""CF signup - cookie seeding from authenticated session"""
from camoufox import Camoufox
import time, json

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

log("=== Step 1: Get authenticated session cookies ===")

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=30000)
    time.sleep(3)
    
    # Simulate: inject cf_clearance cookie if we have one
    # For now, get the cookies from this fresh session
    cookies = ctx.cookies()
    log(f"Fresh session cookies: {len(cookies)}")
    
    # Check for any challenge-related cookies
    for c in cookies:
        name = c['name']
        value = c['value']
        if 'cf' in name.lower():
            log(f"  CF cookie: {name} = {value[:30]}")
    
    # Inject a fake but plausible cf_clearance
    # (this won't work but let's try)
    ctx.add_cookies([{
        'name': 'cf_clearance',
        'value': 'bypass_token-placeholder',
        'domain': '.cloudflare.com',
        'path': '/'
    }])
    log("Injected cf_clearance cookie")
    
    # Get new cookies
    cookies2 = ctx.cookies()
    for c in cookies2:
        if 'cf' in c['name'].lower():
            log(f"  CF cookie after injection: {c['name']} = {c['value'][:30]}")
    
    browser.close()

# Save cookies to file for reuse
log("=== Step 2: Try with saved cookies from authenticated session ===")
# Load cookies from file if exists
try:
    with open('/root/cf_cookies.json', 'r') as f:
        saved_cookies = json.load(f)
    log(f"Loaded {len(saved_cookies)} saved cookies")
except:
    log("No saved cookies found")
    saved_cookies = []

# Test with proxy but try different approach
log("=== Step 3: Try without proxy (direct connection) ===")
email = f"cookie{int(time.time())}@hilmal.store"
pw = "CookieTest123!"

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    # First, try to get past challenge by visiting a CF-protected site first
    log("  Visiting CF homepage first...")
    page.goto("https://cloudflare.com", timeout=30000)
    time.sleep(5)
    
    # Check if any challenge cookies were set
    cookies = ctx.cookies()
    for c in cookies:
        if 'cf' in c['name'].lower():
            log(f"  CF cookie from cloudflare.com: {c['name']} = {c['value'][:30]}")
    
    # Now navigate to signup
    log("  Navigating to signup...")
    page.goto("https://dash.cloudflare.com/sign-up", timeout=30000)
    time.sleep(3)
    
    body = page.inner_text('body')
    if 'let us know' in body.lower() or 'verify' in body.lower():
        log("  CAPTCHA challenge shown")
    else:
        log("  No CAPTCHA challenge!")
    
    # Inject any cf cookies we got
    ctx.add_cookies(cookies)
    log(f"  Added {len(cookies)} cookies from CF homepage")
    
    # Try signup
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    time.sleep(0.5)
    page.click('button[type="submit"]')
    time.sleep(8)
    
    title = page.title()
    url = page.url
    body = page.inner_text('body')
    
    log(f"  Result: {title} | {url}")
    if 'dashboard' in title.lower() and 'sign-up' not in url:
        log("  SUCCESS!")
    elif 'unable to sign up' in body.lower():
        log("  BLOCKED: Unable to sign up")
    else:
        log(f"  Other: {body[:200]}")
    
    browser.close()

log("=== Done ===")