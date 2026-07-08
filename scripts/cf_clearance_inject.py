#!/usr/bin/env python3
"""CF signup - extract cf_clearance from server-side Bright Data + inject into Chrome"""
from playwright.sync_api import sync_playwright
import time, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

BRD = {
    'http': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335',
    'https': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335'
}

email = f"cfclear{int(time.time())}@hilmal.store"
pw = "Cfclear123!"
log(f"Email: {email}")

# Step 1: Get cf_clearance cookie via requests (server-side bypass)
log("=== Step 1: Get cf_clearance cookie ===")
session = requests.Session()
session.proxies = BRD
session.verify = False
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
})

# Visit CF main page first (to get challenge cookies)
r1 = session.get('https://cloudflare.com', timeout=30)
log(f"Cloudflare.com: {r1.status_code}")

# Now visit signup (Bright Data will bypass challenge server-side)
r2 = session.get('https://dash.cloudflare.com/sign-up', timeout=30)
log(f"CF signup page: {r2.status_code}, Size: {len(r2.content)}")

# Check for cf_clearance cookie
all_cookies = session.cookies.get_dict()
log(f"All cookies: {list(all_cookies.keys())}")

cf_clearance = all_cookies.get('cf_clearance')
__cf_bm = all_cookies.get('__cf_bm')
log(f"cf_clearance: {cf_clearance[:30] if cf_clearance else 'NONE'}")
log(f"__cf_bm: {__cf_bm[:30] if __cf_bm else 'NONE'}")

# Check if challenge params exist
import re
challenge_match = re.search(r'window\._\w+\s*=\s*\{[^}]+challenge[^}]+\}', r2.text, re.IGNORECASE)
if challenge_match:
    log(f"Challenge params: {challenge_match.group()[:50]}")

# Step 2: Chrome WITHOUT proxy + injected clearance cookie
log("=== Step 2: Chrome WITHOUT proxy + clearance cookie ===")
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path='/usr/bin/chromium-browser',
        args=['--no-sandbox', '--disable-setuid-sandbox', '--ignore-certificate-errors']
    )
    ctx = browser.new_context(
        ignore_https_errors=True,
        # Set timezone and locale to match real user
        timezone_id='America/Chicago',
        locale='en-US',
    )
    page = ctx.new_page()
    
    # Inject ALL cookies from requests (including cf_clearance if any)
    for name, value in all_cookies.items():
        ctx.add_cookies([{'name': name, 'value': value, 'domain': '.dash.cloudflare.com', 'path': '/'}])
        ctx.add_cookies([{'name': name, 'value': value, 'domain': '.cloudflare.com', 'path': '/'}])
    
    log(f"Injected {len(all_cookies)} cookies")
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
    time.sleep(5)
    
    title = page.title()
    url = page.url
    body_text = page.evaluate("() => document.body ? document.body.innerText.substring(0, 300) : ''")
    
    log(f"Title: {title}")
    log(f"URL: {url}")
    log(f"Body: '{body_text}'")
    
    if 'dashboard' in title.lower() and 'sign-up' not in url:
        log("SUCCESS! Logged in via clearance cookie!")
        page.screenshot(path='/tmp/cf_clearance_success.png')
    elif 'email' in body_text.lower() and 'password' in body_text.lower():
        log("Signup form - NOT logged in yet")
        page.screenshot(path='/tmp/cf_clearance_form.png')
        
        # Check if challenge is bypassed (no challenge shown)
        if 'let us know' not in body_text.lower():
            log("No challenge! Filling form...")
            page.fill('input[name="email"]', email)
            page.fill('input[name="password"]', pw)
            time.sleep(0.5)
            page.click('button[type="submit"]')
            log("Submitted!")
            time.sleep(10)
            
            if 'dashboard' in page.title().lower():
                log("SUCCESS! Account created!")
                page.screenshot(path='/tmp/cf_clearance_account.png')
            else:
                body2 = page.evaluate("() => document.body ? document.body.innerText.substring(0, 200) : ''")
                log(f"Result: {body2}")
        else:
            log("Challenge still shown despite cookies")
            page.screenshot(path='/tmp/cf_clearance_challenge.png')
    else:
        log("Other result")
        page.screenshot(path='/tmp/cf_clearance_other.png')
    
    browser.close()

log("=== Done ===")