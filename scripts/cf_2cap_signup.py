#!/usr/bin/env python3
"""CF signup with 2Captcha Turnstile solver"""
from camoufox import Camoufox
import time, re, requests

TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
CF_PAGE = "https://dash.cloudflare.com/sign-up"

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def get_sitekey(page):
    """Extract Turnstile sitekey"""
    iframe = page.query_selector('iframe[src*="turnstile"]')
    if iframe:
        src = iframe.get_attribute('src') or ''
        m = re.search(r'sitekey=([^&]+)', src)
        if m:
            return m.group(1)
    
    els = page.query_selector_all('[data-sitekey]')
    for el in els:
        sk = el.get_attribute('data-sitekey')
        if sk:
            return sk
    
    # Try from page source
    m = re.search(r'data-sitekey=["\']([^"\']+)["\']', page.content())
    if m:
        return m.group(1)
    
    m = re.search(r'sitekey=([^&"\']+)', page.content())
    if m:
        return m.group(1)
    
    return None

def solve_turnstile(sitekey, pageurl):
    log(f"Solving Turnstile sitekey={sitekey[:30]}...")
    
    # Submit to 2Captcha
    url = f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={pageurl}&sitekey={sitekey}&json=1"
    r = requests.get(url, timeout=10)
    result = r.json()
    
    if result.get('status') != 1:
        log(f"Submit failed: {result}")
        return None
    
    job_id = result.get('request')
    log(f"Job ID: {job_id}")
    
    # Poll
    for i in range(90):
        time.sleep(3)
        check = f"http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={job_id}&json=1"
        r = requests.get(check, timeout=10)
        res = r.json()
        
        if res.get('status') == 1:
            token = res.get('request')
            log(f"Solved! Token: {token[:40]}...")
            return token
        elif 'NOT_READY' in str(res):
            continue
        else:
            log(f"Error: {res}")
            return None
    
    log("Timeout")
    return None

email = f"captest{int(time.time())}@hilmal.store"
pw = "Captest123!"
log(f"Testing: {email}")

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    ctx.clear_cookies()
    page = ctx.new_page()
    
    page.goto(CF_PAGE, timeout=45000)
    time.sleep(5)
    
    # Check CAPTCHA
    body = page.inner_text('body')
    if 'human' in body.lower():
        log("CAPTCHA detected, getting sitekey...")
        sitekey = get_sitekey(page)
        log(f"Sitekey: {sitekey}")
        
        if sitekey:
            token = solve_turnstile(sitekey, CF_PAGE)
            if token:
                log("Injecting token...")
                page.evaluate(f"""
                    var cfToken = '{token}';
                    // Try to find Turnstile response field
                    var inputs = document.querySelectorAll('input[name*="turnstile"], input[name*="cf-turnstile"]');
                    inputs.forEach(i => i.value = cfToken);
                    
                    // Try challenge div
                    var div = document.querySelector('[data-sitekey]');
                    if (div) div.setAttribute('data-response', cfToken);
                    
                    // Try iframe
                    var iframe = document.querySelector('iframe[src*="turnstile"]');
                    if (iframe) {{
                        var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                        // Can't access due to CORS but browser might handle it
                    }}
                """)
                time.sleep(2)
            else:
                log("Captcha solve failed - need 2Captcha balance")
                page.screenshot(path='/tmp/cf_captcha_fail.png')
                ctx.close()
                browser.close()
                exit(1)
    
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
        log("SUCCESS! Account created!")
        # Save session state
        cookies = ctx.cookies()
        with open('/tmp/cf_auth_cookies.json', 'w') as f:
            import json
            json.dump(cookies, f)
        log(f"Saved {len(cookies)} cookies")
        page.screenshot(path='/tmp/cf_success.png')
    else:
        log(f"FAILED: {body[:200]}")
        page.screenshot(path='/tmp/cf_fail.png')
    
    browser.close()