#!/usr/bin/env python3
"""CF signup via Bright Data Web Unlocker"""
from camoufox import Camoufox
import time

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

BRD_PROXY = {
    'server': 'http://brd.superproxy.io:33335',
    'username': 'brd-customer-hl_c0f6789c-zone-web_unlocker1',
    'password': 'ds3ovbwhs69y'
}

email = f"brdtest{int(time.time())}@hilmal.store"
pw = "BrdTest123!"
log(f"Email: {email}")

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context(proxy=BRD_PROXY, ignore_https_errors=True)
    page = ctx.new_page()
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    time.sleep(5)
    
    title = page.title()
    url = page.url
    body = page.inner_text('body')
    
    log(f"Page: {title} | {url}")
    log(f"Body preview: {body[:200]}")
    
    if 'let us know' in body.lower() or 'verify you are human' in body.lower():
        log("CAPTCHA challenge shown!")
        page.screenshot(path='/tmp/cf_brd_challenge.png')
    elif 'email' in body.lower() and 'password' in body.lower():
        log("Signup form loaded! No challenge!")
        page.screenshot(path='/tmp/cf_brd_form.png')
        
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', pw)
        time.sleep(0.5)
        page.click('button[type="submit"]')
        log("Clicked submit...")
        time.sleep(10)
        
        title2 = page.title()
        url2 = page.url
        body2 = page.inner_text('body')
        
        log(f"Result: {title2} | {url2}")
        if 'dashboard' in title2.lower() and 'sign-up' not in url2:
            log("SUCCESS! Account created!")
            page.screenshot(path='/tmp/cf_brd_success.png')
        elif 'verify' in body2.lower() or 'complete' in body2.lower():
            log(f"Needs verification: {body2[:200]}")
        else:
            log(f"Other: {body2[:200]}")
    else:
        log(f"Unexpected: {body[:100]}")
        page.screenshot(path='/tmp/cf_brd_other.png')
    
    browser.close()

log("=== Done ===")