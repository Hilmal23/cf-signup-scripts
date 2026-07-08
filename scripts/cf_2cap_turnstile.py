#!/usr/bin/env python3
"""CF Signup - 2Captcha Turnstile solver approach"""
from playwright.sync_api import sync_playwright
import requests, time, json, re

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

email = f"cf{int(time.time())}@hilmal.store"
pw = "CfSignup123!"
log(f"Email: {email}")

BRD = 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335'
TWOCAPTCHA_KEY = '3da28555894fd89bb569b748731e9400'

SITEKEY = '0x4AAAAAAAJel0iaAR3mgkjp'
PAGE_URL = 'https://dash.cloudflare.com/sign-up'

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path="/snap/chromium/current/usr/lib/chromium-browser/chrome",
        args=[
            "--no-sandbox", "--disable-setuid-sandbox",
            "--ignore-certificate-errors",
            "--allow-running-insecure-content",
            "--ignore-certificate-errors-spki-list=*",
        ]
    )
    ctx = browser.new_context(
        proxy={"server": "http://brd.superproxy.io:33335", "username": "brd-customer-hl_c0f6789c-zone-web_unlocker1", "password": "ds3ovbwhs69y"},
    )
    page = ctx.new_page()
    
    log("Loading page via BD...")
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    time.sleep(8)
    
    cookies = ctx.cookies()
    cookie_dict = {c['name']: c['value'] for c in cookies}
    log(f"cf_clearance: {cookie_dict.get('cf_clearance', 'NONE')[:30]}...")
    
    # Fill form first
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    
    # Submit and capture the API call + response
    captured = [None, None]
    def on_request(request):
        if '/api/v4/user/create' in request.url:
            captured[0] = {'headers': dict(request.headers), 'body': request.post_data}
    def on_response(response):
        if 'user/create' in response.url:
            captured[1] = {'status': response.status, 'body_text': response.text()}
    page.on("request", on_request)
    page.on("response", on_response)
    page.click('button[type="submit"]')
    time.sleep(6)
    
    log(f"After - Title: {page.title()}")
    
    if not captured[0]:
        log("No create API!")
        browser.close()
        exit(1)
    
    req = captured[0]
    
    # Check the API response
    if captured[1]:
        log(f"API status: {captured[1]['status']}")
        try:
            data = json.loads(captured[1]['body_text'])
            log(f"API response: {json.dumps(data)}")
        except:
            log(f"API response: {captured[1]['body_text'][:200]}")
    
    # Now try 2Captcha solve
    log("\n=== Solving Turnstile via 2Captcha ===")
    
    # Get the sitekey from the Turnstile iframe
    turnstile_iframe = page.query_selector('iframe[src*="turnstile"]')
    if turnstile_iframe:
        src = turnstile_iframe.get_attribute('src')
        log(f"Turnstile iframe src: {src}")
        # Extract sitekey from URL
        match = re.search(r'rch/([^/]+)/', src)
        if match:
            SITEKEY = match.group(1)
            log(f"Extracted sitekey: {SITEKEY}")
    else:
        log("No Turnstile iframe found")
        # Check if there's a challenge widget
        challenge = page.query_selector('[data-sitekey]')
        if challenge:
            SITEKEY = challenge.get_attribute('data-sitekey')
            log(f"Found sitekey from attribute: {SITEKEY}")
    
    # Submit to 2Captcha
    log(f"Submitting to 2Captcha (sitekey: {SITEKEY[:20]}...)")
    r = requests.get(
        f'http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={PAGE_URL}&sitekey={SITEKEY}&json=1',
        timeout=15
    )
    log(f"2Captcha submit: {r.text}")
    
    try:
        result = r.json()
        if result.get('status') == 1:
            captcha_id = result['request']
            log(f"Captcha ID: {captcha_id}")
            
            # Wait for solve
            log("Waiting for solve...")
            for i in range(60):
                time.sleep(5)
                r2 = requests.get(
                    f'http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={captcha_id}&json=1',
                    timeout=15
                )
                resp = r2.json()
                log(f"Poll {i+1}: {resp}")
                if resp.get('status') == 1:
                    token = resp['request']
                    log(f"GOT TOKEN: {token[:30]}...")
                    
                    # Now inject token into the create API call
                    log("\n=== Re-submit with Turnstile token ===")
                    body = json.loads(req['body'])
                    body['cf_challenge_response'] = token
                    
                    headers = {k: v for k, v in req['headers'].items()}
                    headers['content-type'] = 'application/json'
                    
                    rs = requests.Session()
                    rs.proxies = {'http': BRD, 'https': BRD}
                    rs.verify = False
                    for name, value in cookie_dict.items():
                        rs.cookies.set(name, value, domain='.cloudflare.com', path='/')
                    
                    r3 = rs.post(
                        'https://dash.cloudflare.com/api/v4/user/create',
                        data=json.dumps(body),
                        headers=headers,
                        timeout=30
                    )
                    
                    log(f"Status: {r3.status_code}")
                    log(f"Response: {r3.text[:500]}")
                    
                    if r3.status_code == 200:
                        log("SUCCESS! Account created!")
                    else:
                        try:
                            err = r3.json()
                            log(f"Error: {json.dumps(err, indent=2)}")
                        except:
                            log(f"Response: {r3.text[:300]}")
                    break
                elif 'CAPCHA_NOT_READY' in str(resp):
                    continue
                else:
                    log(f"Error/captcha status: {resp}")
                    break
        else:
            log(f"2Captcha error: {result}")
    except Exception as e:
        log(f"Exception: {e}")
    
    browser.close()

log("=== Done ===")