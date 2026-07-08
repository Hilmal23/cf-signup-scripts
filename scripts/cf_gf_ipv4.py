#!/usr/bin/env python3
"""CF signup - force IPv4 on Geonode GF proxy"""
from camoufox import Camoufox
import time, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# Test IPv4 exit
log("=== Test IPv4 forcing ===")
proxy = 'http://geonode_RTwCdAt5Br-type-residential-country-gf-lifetime-10-session-F7RFUN:13ac90b0-84fa-48a4-9f15-6532ae4aa21c@92.204.164.15:10000'

# Try forcing IPv4 via DNS
try:
    r = requests.get('https://api.ipify.org?format=json', proxies={'http': proxy, 'https': proxy}, timeout=15)
    log(f"IPv4: {r.text}")
except Exception as e:
    log(f"IPv4 check error: {e}")

# Test CF via new proxy format
log("=== Test CF signup via new proxy format ===")
email = f"ipv4test{int(time.time())}@hilmal.store"
pw = "Ipv4Test123!"

# Try with username:password in server URL
try:
    proxy_url = 'http://geonode_RTwCdAt5Br-type-residential-country-gf-lifetime-10-session-F7RFUN:13ac90b0-84fa-48a4-9f15-6532ae4aa21c@92.204.164.15:10000'
    
    with Camoufox(headless=True, geoip=False) as browser:
        ctx = browser.new_context(
            proxy={'server': proxy_url}
        )
        page = ctx.new_page()
        
        page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
        time.sleep(5)
        
        title = page.title()
        url = page.url
        body = page.inner_text('body')
        
        log(f"Result: {title} | {url}")
        
        if 'let us know' in body.lower():
            log("Challenge on load")
            page.screenshot(path='/tmp/cf_gf_challenge.png')
        else:
            log("No challenge!")
            page.fill('input[name="email"]', email)
            page.fill('input[name="password"]', pw)
            time.sleep(0.5)
            page.click('button[type="submit"]')
            time.sleep(8)
            
            if 'dashboard' in page.title().lower():
                log("SUCCESS!")
            else:
                log(f"Failed: {page.inner_text('body')[:200]}")
        
        browser.close()
except Exception as e:
    log(f"Browser error: {e}")

# Test 3: Try with different proxy URL format
log("=== Test: proxy URL with explicit credentials ===")
try:
    # Playwright expects separate server/user/pass
    with Camoufox(headless=True, geoip=False) as browser:
        ctx = browser.new_context(
            proxy={
                'server': 'http://92.204.164.15:10000',
                'username': 'geonode_RTwCdAt5Br-type-residential-country-gf-lifetime-10-session-X4wtLe',
                'password': '13ac90b0-84fa-48a4-9f15-6532ae4aa21c'
            }
        )
        page = ctx.new_page()
        
        page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
        time.sleep(5)
        
        body = page.inner_text('body')
        if 'let us know' in body.lower():
            log("Challenge shown via separate creds")
        else:
            log("NO challenge via separate creds!")
            
            email = f"sep{int(time.time())}@hilmal.store"
            pw = "SepTest123!"
            page.fill('input[name="email"]', email)
            page.fill('input[name="password"]', pw)
            time.sleep(0.5)
            page.click('button[type="submit"]')
            time.sleep(8)
            
            if 'dashboard' in page.title().lower():
                log("SUCCESS!")
            else:
                log(f"Failed: {page.inner_text('body')[:200]}")
        
        browser.close()
except Exception as e:
    log(f"Error with separate creds: {e}")

log("=== Done ===")