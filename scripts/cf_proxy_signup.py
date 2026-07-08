#!/usr/bin/env python3
"""CF signup via Geonode US residential proxy"""
from camoufox import Camoufox
import time, requests

PROXY = {'server': 'http://148.72.141.11:9000',
          'username': 'geonode_RTwCdAt5Br-type-residential-country-us',
          'password': '34c063a6-055f-42e0-980d-57db761b8c46'}

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

email = f"prox{int(time.time())}@hilmal.store"
pw = "Proxytest123!"
log(f"Testing via proxy: {email}")

with Camoufox(headless=True, geoip=False, proxy=PROXY) as browser:
    ctx = browser.new_context()
    ctx.clear_cookies()
    page = ctx.new_page()
    
    log("Navigating to CF signup via US proxy...")
    page.goto("https://dash.cloudflare.com/sign-up", timeout=45000)
    time.sleep(5)
    
    log(f"Page: {page.title()}")
    
    # Fill form
    page.fill('input[name="email"]', email)
    time.sleep(0.5)
    page.fill('input[name="password"]', pw)
    time.sleep(0.5)
    
    # Submit
    page.click('button[type="submit"]')
    time.sleep(8)
    
    title = page.title()
    url = page.url
    body = page.inner_text('body')
    
    log(f"Result: {title} | {url}")
    
    if 'dashboard' in title.lower() and 'sign-up' not in url:
        log("SUCCESS via US proxy! Account created!")
        page.screenshot(path='/tmp/cf_proxy_success.png')
    else:
        log(f"FAILED: {body[:200]}")
        page.screenshot(path='/tmp/cf_proxy_fail.png')
    
    browser.close()