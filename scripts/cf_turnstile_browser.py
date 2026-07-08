#!/usr/bin/env python3
"""CF Signup - intercept + resolve challenge in browser, then submit"""
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
    
    # Intercept the API request
    captured_req = [None]
    captured_res = [None]
    
    def on_request(req):
        if '/api/v4/user/create' in req.url:
            captured_req[0] = {'headers': dict(req.headers), 'body': req.post_data}
    
    def on_response(res):
        if 'user/create' in res.url:
            captured_res[0] = res
    
    page.on("request", on_request)
    page.on("response", on_response)
    
    log("Clicking submit...")
    page.click('button[type="submit"]')
    time.sleep(5)
    
    log(f"Title: {page.title()}")
    
    # Check if challenge page
    body = page.evaluate("() => document.body ? document.body.innerText.substring(0,200) : ''")
    is_challenge = 'let us know' in body.lower()
    log(f"Challenge shown: {is_challenge}")
    
    if captured_res[0]:
        log(f"API status: {captured_res[0].status}")
    
    if not captured_req[0]:
        log("No create API!")
        browser.close()
        exit(1)
    
    req = captured_req[0]
    
    # Wait for the challenge page to fully load
    if is_challenge:
        log("Waiting for challenge to fully load...")
        time.sleep(5)
    
    # Try to get Turnstile iframe
    turnstile_iframe = page.query_selector('iframe[src*="turnstile"]')
    log(f"Turnstile iframe: {turnstile_iframe is not None}")
    
    if turnstile_iframe:
        src = turnstile_iframe.get_attribute('src')
        log(f"Iframe src: {src}")
    
    # Try to solve via 2Captcha (pass iframe URL)
    log("\n=== Solving via 2Captcha ===")
    
    if turnstile_iframe:
        src = turnstile_iframe.get_attribute('src')
        r = requests.get(
            f'http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={PAGE_URL}&sitekey={SITEKEY}&json=1',
            timeout=15
        )
    else:
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
                    
                    # Try injecting into browser and clicking submit again
                    log("Injecting token into browser...")
                    
                    page.evaluate(f"""
                        window.cf_challenge_response = "{token}";
                        window._cf_challenge_response = "{token}";
                    """)
                    
                    # Also try to find and trigger submit
                    result = page.evaluate("""
                        () => {
                            // Try to find the Turnstile API
                            if (typeof ___cf_challenge_dispatch !== 'undefined') {
                                return 'found dispatch';
                            }
                            if (typeof _cf_challenge !== 'undefined') {
                                return 'found _cf_challenge';
                            }
                            return 'not found';
                        }
                    """)
                    log(f"Challenge API: {result}")
                    
                    # Get fresh security token
                    sec = page.evaluate("() => document.querySelector('input[name=\"security_token\"]')?.value || ''")
                    
                    # Build new body with token
                    body_data = json.loads(req['body'])
                    new_body = {
                        "email": email,
                        "password": pw,
                        "mrk_optin": True,
                        "security_token": sec or body_data.get("security_token", ""),
                        "method": "Onboarding: New_v2",
                        "locale": "en-US",
                        "legal_stamp": body_data.get("legal_stamp", ""),
                        "opt_ins": {},
                        "mrktCheckboxDisplayed": False,
                        "hCaptchaDisplayed": False,
                        "cf_challenge_response": token
                    }
                    
                    # Use browser to make the API call via fetch
                    api_result = page.evaluate(f"""
                        async () => {{
                            try {{
                                const response = await fetch('https://dash.cloudflare.com/api/v4/user/create', {{
                                    method: 'POST',
                                    headers: {{
                                        'Content-Type': 'application/json',
                                        'Origin': 'https://dash.cloudflare.com',
                                        'Referer': 'https://dash.cloudflare.com/sign-up',
                                        'User-Agent': navigator.userAgent,
                                    }},
                                    body: JSON.stringify({json.dumps(new_body)}),
                                }});
                                const text = await response.text();
                                return {{ status: response.status, body: text }};
                            }} catch(e) {{
                                return {{ error: e.message }};
                            }}
                        }}
                    """)
                    
                    log(f"Browser API result: {api_result}")
                    break
                elif 'CAPCHA_NOT_READY' in str(resp):
                    log(f"Poll {i+1}...")
                    continue
                else:
                    log(f"Error: {resp}")
                    break
    except Exception as e:
        log(f"Exception: {e}")
    
    browser.close()

log("=== Done ===")