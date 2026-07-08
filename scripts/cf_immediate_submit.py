#!/usr/bin/env python3
"""CF Signup - solve turnstile + immediate browser submit"""
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
    
    try:
        page.wait_for_selector('input[name="email"]', timeout=30000)
    except:
        log("Form not loaded!")
        browser.close()
        exit(1)
    
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    log("Form filled")
    
    log("Clicking submit to trigger challenge...")
    page.click('button[type="submit"]')
    time.sleep(8)
    
    log(f"Title: {page.title()}")
    body = page.evaluate("() => document.body ? document.body.innerText.substring(0,300) : ''")
    
    # Check for challenge page
    is_challenge = 'let us know' in body.lower() or 'human' in body.lower()
    log(f"Challenge: {is_challenge}")
    log(f"Body: {body[:150]}")
    
    # Get security_token from page
    sec = page.evaluate("() => document.querySelector('input[name=\"security_token\"]')?.value || ''")
    log(f"security_token: {sec[:40]}...")
    
    # Get ALL cookies  
    cookies = ctx.cookies()
    cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
    log(f"Cookies: {cookie_str[:100]}...")
    
    # Also get the exact body that will be submitted
    form_data = page.evaluate("""() => {
        const inputs = document.querySelectorAll('input');
        const data = {};
        inputs.forEach(el => {
            if (el.name) data[el.name] = el.value;
        });
        return data;
    }""")
    log(f"Form data: {json.dumps(form_data)}")
    
    # Solve via 2Captcha
    log("\\n=== Solving via 2Captcha ===")
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
                    log(f"GOT TOKEN: {token[:50]}...")
                    log(f"Token length: {len(token)}")
                    
                    # Build body exactly from browser form data + token
                    body_data = {
                        "email": form_data.get("email", email),
                        "password": form_data.get("password", pw),
                        "mrk_optin": form_data.get("mrk_optin", "true").lower() == "true",
                        "security_token": sec or form_data.get("security_token", ""),
                        "method": form_data.get("method", "Onboarding: New_v2"),
                        "locale": form_data.get("locale", "en-US"),
                        "legal_stamp": form_data.get("legal_stamp", ""),
                        "opt_ins": {},
                        "mrktCheckboxDisplayed": False,
                        "hCaptchaDisplayed": False,
                        "cf_challenge_response": token
                    }
                    
                    log("Submitting via browser fetch...")
                    result = page.evaluate(f"""
                        async () => {{
                            try {{
                                const resp = await fetch('https://dash.cloudflare.com/api/v4/user/create', {{
                                    method: 'POST',
                                    headers: {{
                                        'Content-Type': 'application/json',
                                        'Origin': 'https://dash.cloudflare.com',
                                        'Referer': 'https://dash.cloudflare.com/sign-up',
                                    }},
                                    body: JSON.stringify({json.dumps(body_data)}),
                                }});
                                const text = await resp.text();
                                return {{ status: resp.status, body: text.substring(0, 500) }};
                            }} catch(e) {{
                                return {{ error: e.message }};
                            }}
                        }}
                    """)
                    
                    log(f"Browser fetch result: {result}")
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