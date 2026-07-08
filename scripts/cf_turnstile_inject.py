#!/usr/bin/env python3
"""CF Signup - inject Turnstile token + re-submit"""
from playwright.sync_api import sync_playwright
import requests, time, json

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
    
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    
    captured = [None]
    def on_request(req):
        if '/api/v4/user/create' in req.url:
            captured[0] = {'headers': dict(req.headers), 'body': req.post_data}
    page.on("request", on_request)
    page.click('button[type="submit"]')
    time.sleep(6)
    
    log(f"After - Title: {page.title()}")
    if not captured[0]:
        log("No create API!")
        browser.close()
        exit(1)
    
    req = captured[0]
    body = json.loads(req['body'])
    log(f"cf_challenge_response: '{body.get('cf_challenge_response', '')}' (empty!)")
    
    cookies = ctx.cookies()
    cookie_dict = {c['name']: c['value'] for c in cookies}
    
    # Solve via 2Captcha
    log("\n=== Solving Turnstile ===")
    r = requests.get(
        f'http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={PAGE_URL}&sitekey={SITEKEY}&json=1',
        timeout=15
    )
    log(f"Submit: {r.text}")
    
    try:
        result = r.json()
        if result.get('status') == 1:
            captcha_id = result['request']
            for i in range(40):
                time.sleep(5)
                r2 = requests.get(
                    f'http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={captcha_id}&json=1',
                    timeout=15
                )
                resp = r2.json()
                if resp.get('status') == 1:
                    token = resp['request']
                    log(f"GOT TOKEN: {token[:30]}...")
                    
                    # Get fresh security_token
                    sec = page.evaluate("() => document.querySelector('input[name=\"security_token\"]')?.value || ''")
                    
                    # Build new body with token
                    new_body = {
                        "email": email,
                        "password": pw,
                        "mrk_optin": True,
                        "security_token": sec or body.get("security_token", ""),
                        "method": "Onboarding: New_v2",
                        "locale": "en-US",
                        "legal_stamp": body.get("legal_stamp", ""),
                        "opt_ins": {},
                        "mrktCheckboxDisplayed": False,
                        "hCaptchaDisplayed": False,
                        "cf_challenge_response": token
                    }
                    
                    # Inject token into browser too
                    page.evaluate(f"""
                        window.cf_challenge_response = "{token}";
                        window.__cf_challenge_response = "{token}";
                    """)
                    log("Token injected into browser")
                    
                    # Submit via Python API
                    headers = {k: v for k, v in req['headers'].items()}
                    headers['content-type'] = 'application/json'
                    
                    rs = requests.Session()
                    rs.proxies = {'http': BRD, 'https': BRD}
                    rs.verify = False
                    for name, value in cookie_dict.items():
                        rs.cookies.set(name, value, domain='.cloudflare.com', path='/')
                    
                    log("Submitting with token...")
                    r3 = rs.post(
                        'https://dash.cloudflare.com/api/v4/user/create',
                        data=json.dumps(new_body),
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
                    log(f"Poll {i+1}: not ready...")
                    continue
                else:
                    log(f"Error: {resp}")
                    break
    except Exception as e:
        log(f"Exception: {e}")
    
    browser.close()

log("=== Done ===")