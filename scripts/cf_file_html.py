#!/usr/bin/env python3
"""CF signup - save HTML + load via file:// with cookies"""
from camoufox import Camoufox
import time, re, requests, os

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

BRD = {
    'http': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335',
    'https': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335'
}

email = f"filetest{int(time.time())}@hilmal.store"
pw = "Filetest123!"
log(f"Email: {email}")

HTML_FILE = '/tmp/cf_signup_page.html'

# Step 1: Get HTML via Bright Data + save locally
log("=== Step 1: Save modified HTML ===")
session = requests.Session()
session.proxies = BRD
session.verify = False
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
})

r = session.get('https://dash.cloudflare.com/sign-up', timeout=30)
log(f"Status: {r.status_code}, Size: {len(r.content)}")

# Save HTML
with open(HTML_FILE, 'w') as f:
    f.write(r.text)
log(f"Saved to {HTML_FILE}")

# Get cookies
cookies = session.cookies.get_dict()
log(f"Cookies: {list(cookies.keys())}")

# Step 2: Load HTML via file:// with cookies
log("=== Step 2: Load HTML file with cookies ===")
with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    # Set all cookies from requests
    for name, value in cookies.items():
        for domain in ['.dash.cloudflare.com', '.cloudflare.com', 'dash.cloudflare.com']:
            try:
                ctx.add_cookies([{'name': name, 'value': value, 'domain': domain, 'path': '/'}])
            except Exception as e:
                pass
    
    # Load HTML file
    page.goto(f"file://{HTML_FILE}", timeout=30000)
    time.sleep(5)
    
    title = page.title()
    url = page.url
    body = page.inner_text('body')
    
    log(f"Title: {title}")
    log(f"URL: {url}")
    log(f"Body: {body[:200]}")
    
    if 'dashboard' in title.lower() and 'sign-up' not in url:
        log("SUCCESS - logged in!")
        page.screenshot(path='/tmp/cf_file_logged_in.png')
    elif 'email' in body.lower() and 'password' in body.lower():
        log("Signup form loaded")
        page.screenshot(path='/tmp/cf_file_form.png')
        
        # Fill and submit
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', pw)
        time.sleep(0.5)
        page.click('button[type="submit"]')
        log("Submitted!")
        time.sleep(10)
        
        if 'dashboard' in page.title().lower():
            log("SUCCESS! Account created!")
            page.screenshot(path='/tmp/cf_file_success.png')
        else:
            body2 = page.inner_text('body')
            log(f"Result: {body2[:200]}")
    else:
        log("Other result")
        page.screenshot(path='/tmp/cf_file_other.png')
    
    browser.close()

log("=== Done ===")