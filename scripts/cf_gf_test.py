#!/usr/bin/env python3
"""CF signup - test NEW Geonode GF residential proxies"""
from camoufox import Camoufox
import time, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# Test 1: Check exit IP of new proxy
log("=== Test 1: Check exit IP of new proxy ===")
proxy = 'http://geonode_RTwCdAt5Br-type-residential-country-gf-lifetime-10-session-F7RFUN:13ac90b0-84fa-48a4-9f15-6532ae4aa21c@92.204.164.15:10000'

try:
    r = requests.get('https://ifconfig.me', proxies={'http': proxy, 'https': proxy}, timeout=15)
    exit_ip = r.text.strip()
    log(f"Exit IP: {exit_ip}")
    log(f"Is datacenter? Checking...")
    r2 = requests.get(f'https://ipinfo.io/{exit_ip}/json', timeout=10)
    info = r2.json()
    log(f"IP Info: {info}")
except Exception as e:
    log(f"Proxy error: {e}")
    exit_ip = None

# Test 2: CF signup via new proxy
log("=== Test 2: CF signup via new Geonode GF proxy ===")
email = f"gftest{int(time.time())}@hilmal.store"
pw = "GfTest123!"

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context(
        proxy={'server': 'http://92.204.164.15:10000',
               'username': 'geonode_RTwCdAt5Br-type-residential-country-gf-lifetime-10-session-F7RFUN',
               'password': '13ac90b0-84fa-48a4-9f15-6532ae4aa21c'}
    )
    page = ctx.new_page()
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
    time.sleep(5)
    
    title = page.title()
    url = page.url
    body = page.inner_text('body')
    
    log(f"Page loaded: {title} | {url}")
    
    if 'let us know' in body.lower():
        log("CAPTCHA challenge on page load!")
        page.screenshot(path='/tmp/cf_gf_challenge.png')
    else:
        log("No challenge on load!")
        page.screenshot(path='/tmp/cf_gf_no_challenge.png')
        
        # Try signup
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', pw)
        time.sleep(0.5)
        page.click('button[type="submit"]')
        time.sleep(10)
        
        title2 = page.title()
        url2 = page.url
        body2 = page.inner_text('body')
        
        log(f"After submit: {title2} | {url2}")
        if 'dashboard' in title2.lower() and 'sign-up' not in url2:
            log("SUCCESS!")
        elif 'unable to sign up' in body2.lower():
            log("BLOCKED: Unable to sign up")
        else:
            log(f"Result: {body2[:200]}")
    
    browser.close()

# Test 3: Try multiple session proxies
log("=== Test 3: Try 3 different session proxies ===")
sessions = ['X4wtLe', 'D0o2du', '9nA6bH']
for session in sessions:
    log(f"  Trying session: {session}")
    try:
        proxy_cfg = {
            'server': 'http://92.204.164.15:10000',
            'username': f'geonode_RTwCdAt5Br-type-residential-country-gf-lifetime-10-session-{session}',
            'password': '13ac90b0-84fa-48a4-9f15-6532ae4aa21c'
        }
        
        with Camoufox(headless=True, geoip=False) as browser:
            ctx = browser.new_context(proxy=proxy_cfg)
            page = ctx.new_page()
            
            page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
            time.sleep(4)
            
            body = page.inner_text('body')
            if 'let us know' in body.lower() or 'verify' in body.lower():
                log(f"  Session {session}: CAPTCHA challenge shown")
            elif 'sign up' in body.lower():
                log(f"  Session {session}: Signup form loaded (NO challenge!)")
                
                # Try to signup
                email = f"session{session}{int(time.time())}@hilmal.store"
                pw = "SessionTest123!"
                page.fill('input[name="email"]', email)
                page.fill('input[name="password"]', pw)
                time.sleep(0.3)
                page.click('button[type="submit"]')
                time.sleep(8)
                
                if 'dashboard' in page.title().lower() and 'sign-up' not in page.url:
                    log(f"  Session {session}: SUCCESS!")
                    browser.close()
                    break
                else:
                    log(f"  Session {session}: {page.inner_text('body')[:100]}")
            else:
                log(f"  Session {session}: Unexpected page")
            
            browser.close()
    except Exception as e:
        log(f"  Session {session} error: {e}")
    time.sleep(3)

log("=== Done ===")