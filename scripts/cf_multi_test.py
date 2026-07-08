#!/usr/bin/env python3
"""CF signup - test multiple Geonode residential configs"""
from camoufox import Camoufox
import time, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# Test 1: Geonode US with session rotation (new session each time)
log("=== Test 1: Geonode US with session-per-request ===")
for attempt in range(3):
    log(f"  Attempt {attempt+1}...")
    
    proxy_config = {
        'http': 'http://geonode_RTwCdAt5Br-type-residential-country-us:34c063a6-055f-42e0-980d-57db761b8c46@148.72.141.11:9000',
        'https': 'http://geonode_RTwCdAt5Br-type-residential-country-us:34c063a6-055f-42e0-980d-57db761b8c46@148.72.141.11:9000'
    }
    
    try:
        r = requests.get('https://ifconfig.me', proxies=proxy_config, timeout=10)
        ip = r.text.strip()
        log(f"  Exit IP: {ip}")
    except Exception as e:
        log(f"  Proxy error: {e}")
        continue
    
    with Camoufox(headless=True, geoip=False) as browser:
        ctx = browser.new_context(
            proxy={'server': 'http://148.72.141.11:9000',
                   'username': 'geonode_RTwCdAt5Br-type-residential-country-us',
                   'password': '34c063a6-055f-42e0-980d-57db761b8c46'},
            color_scheme='light'
        )
        page = ctx.new_page()
        
        page.goto("https://dash.cloudflare.com/sign-up", timeout=30000)
        time.sleep(3)
        
        email = f"rotatest{attempt}{int(time.time())}@hilmal.store"
        pw = "Rotatest123!"
        
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', pw)
        time.sleep(0.5)
        page.click('button[type="submit"]')
        time.sleep(8)
        
        body = page.inner_text('body')
        if 'dashboard' in page.title().lower() and 'sign-up' not in page.url:
            log(f"  SUCCESS! Dashboard reached!")
            browser.close()
            break
        elif 'unable to sign up' in body.lower() or 'captcha' in body.lower():
            log(f"  BLOCKED: {body[:100]}")
        else:
            log(f"  Result: {page.title()} | {page.url}")
        
        browser.close()

# Test 2: Geonode FR (France) - might have different exit IP pool
log("=== Test 2: Geonode FR proxy ===")
fr_proxy = 'http://geonode_RTwCdAt5Br-type-residential-country-fr:34c063a6-055f-42e0-980d-57db761b8c46@148.72.141.11:9000'
try:
    r = requests.get('https://ifconfig.me', proxies={'http': fr_proxy, 'https': fr_proxy}, timeout=10)
    log(f"FR Exit IP: {r.text.strip()}")
except Exception as e:
    log(f"FR Proxy error: {e}")

# Test 3: Try with different fingerprint configs
log("=== Test 3: Different browser configs ===")
configs = [
    {'color_scheme': 'dark', 'timezone_id': 'America/New_York'},
    {'color_scheme': 'light', 'timezone_id': 'Europe/London'},
    {'color_scheme': 'no-preference', 'locale': 'en-GB'},
]

for cfg in configs:
    log(f"  Config: {cfg}")
    with Camoufox(headless=True, geoip=False) as browser:
        ctx = browser.new_context(
            proxy={'server': 'http://148.72.141.11:9000',
                   'username': 'geonode_RTwCdAt5Br-type-residential-country-us',
                   'password': '34c063a6-055f-42e0-980d-57db761b8c46'},
            **cfg
        )
        page = ctx.new_page()
        page.goto("https://dash.cloudflare.com/sign-up", timeout=30000)
        time.sleep(3)
        body = page.inner_text('body')
        
        # Check for CAPTCHA on page load
        if 'let us know' in body.lower() or 'verify you' in body.lower():
            log(f"  CAPTCHA challenge shown on load!")
        else:
            log(f"  Page loaded OK (no challenge on load)")
        
        browser.close()
        time.sleep(2)

# Test 4: Check what ifconfig.me shows through Camoufox proxy
log("=== Test 4: Check Camoufox proxy exit IP ===")
with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context(
        proxy={'server': 'http://148.72.141.11:9000',
               'username': 'geonode_RTwCdAt5Br-type-residential-country-us',
               'password': '34c063a6-055f-42e0-980d-57db761b8c46'}
    )
    page = ctx.new_page()
    page.goto("https://ifconfig.me", timeout=15000)
    time.sleep(3)
    ip = page.inner_text('body').strip()
    log(f"Camoufox via Geonode exit IP: {ip}")
    browser.close()

log("=== Done ===")