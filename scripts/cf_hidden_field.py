#!/usr/bin/env python3
"""
CF Signup - INJECT TOKEN INTO HIDDEN FORM FIELD (CRITICAL FIX!)
The API requires cf_challenge_response in the REQUEST BODY.
Inject it as a hidden input field so browser includes it in form serialization.
"""
from playwright.sync_api import sync_playwright
import time, json, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
SITEKEY = "0x4AAAAAAAJel0iaAR3mgkjp"
PAGE_URL = "https://dash.cloudflare.com/sign-up"
CHROMIUM = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
PROXY = {'server': 'http://brd.superproxy.io:33335', 'username': 'brd-customer-hl_c0f6789c-zone-web_unlocker1', 'password': 'ds3ovbwhs69y'}
CHROME_ARGS = ["--no-sandbox","--disable-setuid-sandbox","--ignore-certificate-errors","--allow-running-insecure-content","--ignore-certificate-errors-spki-list=*"]

def solve():
    log("Solving Turnstile...")
    r = requests.get(f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={PAGE_URL}&sitekey={SITEKEY}&json=1", timeout=15)
    result = r.json()
    if result.get('status') != 1:
        log(f"Submit failed: {result}")
        return None
    job_id = result['request']
    for i in range(40):
        time.sleep(3)
        r2 = requests.get(f"http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={job_id}&json=1", timeout=10)
        res = r2.json()
        if res.get('status') == 1:
            log(f"Token: {res['request'][:50]}...")
            return res['request']
        if 'CAPCHA_NOT_READY' not in str(res):
            log(f"Error: {res}")
            return None
        log(f"Waiting... ({i+1}/40)")
    return None

def signup():
    token = solve()
    if not token:
        log("Solve failed!")
        return
    
    email = f"cf{int(time.time()*1000)}@hilmal.store"
    pw = "CfSignup123!"
    log(f"\nEmail: {email}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROMIUM, args=CHROME_ARGS)
        ctx = browser.new_context(proxy=PROXY)
        page = ctx.new_page()
        
        log("Loading signup page...")
        page.goto(PAGE_URL, timeout=60000)
        time.sleep(10)
        
        for _ in range(5):
            try:
                allow = page.query_selector('button:has-text("Allow All")')
                if allow and allow.is_visible():
                    allow.click()
                    time.sleep(1)
                    break
            except:
                pass
            time.sleep(1)
        
        # CRITICAL: Inject token into a HIDDEN FORM FIELD so it gets serialized in POST body!
        log("Injecting token into hidden form field...")
        page.evaluate(f'''() => {{
            // Create hidden input for cf_challenge_response
            var existing = document.querySelector('input[name="cf_challenge_response"]');
            if (existing) {{
                existing.value = "{token}";
                existing.setAttribute('value', "{token}");
            }} else {{
                var input = document.createElement('input');
                input.type = "hidden";
                input.name = "cf_challenge_response";
                input.value = "{token}";
                // Find the form and append
                var form = document.querySelector('form');
                if (form) {{
                    form.appendChild(input);
                    console.log("Hidden cf_challenge_response field added to form");
                }} else {{
                    document.body.appendChild(input);
                    console.log("Form not found, added to body");
                }}
            }}
            // Also set window vars
            window.cf_challenge_response = "{token}";
            window._cf_challenge_response = "{token}";
        }}''')
        
        # Wait for challenge
        body = page.inner_text('body')
        has_challenge = 'let us know' in body.lower()
        log(f"Challenge: {has_challenge}")
        
        if has_challenge:
            for i in range(8):
                time.sleep(2)
                body = page.inner_text('body')
                if 'let us know' not in body.lower():
                    log(f"Challenge cleared! ({i*2}s)")
                    break
                # Check if cf_clearance cookie appeared
                cookies = {c["name"]: c["value"] for c in ctx.cookies()}
                if 'cf_clearance' in cookies:
                    log(f"cf_clearance appeared: {cookies['cf_clearance'][:30]}...")
                log(f"Waiting... ({i+1}/8)")
        
        # Check cf_clearance
        cookies = {c["name"]: c["value"] for c in ctx.cookies()}
        if 'cf_clearance' in cookies:
            log(f"cf_clearance: YES ({cookies['cf_clearance'][:40]}...)")
        else:
            log("cf_clearance: NO")
        
        # Verify hidden field exists
        hidden_val = page.evaluate('''() => {{
            var inp = document.querySelector('input[name="cf_challenge_response"]');
            return inp ? inp.value : "NOT FOUND";
        }}''')
        log(f"Hidden field value: {hidden_val[:60]}...")
        
        # Fill form
        email_inp = page.query_selector('input[name="email"]')
        if not email_inp or not email_inp.is_visible():
            log("No email input!")
            page.screenshot(path='/tmp/cf_nofield.png')
            browser.close()
            return
        
        email_inp.fill(email)
        time.sleep(0.3)
        pw_inp = page.query_selector('input[name="password"]')
        pw_inp.fill(pw)
        time.sleep(0.3)
        
        # Double check hidden field still there after fill
        hidden_val2 = page.evaluate('''() => {{
            var inp = document.querySelector('input[name="cf_challenge_response"]');
            return inp ? inp.value : "NOT FOUND";
        }}''')
        log(f"Hidden field after fill: {hidden_val2[:60]}...")
        
        # Intercept API request
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
        
        # SUBMIT via keyboard (bypasses some JS event handlers)
        log("Submitting (pressing Enter)...")
        pw_inp.press('Enter')
        time.sleep(10)
        
        log(f"After: {page.title()} | {page.url}")
        page.screenshot(path='/tmp/cf_result.png')
        
        if captured_req[0]:
            try:
                body = json.loads(captured_req[0].post_data or '{}')
                has_token = bool(body.get('cf_challenge_response'))
                log(f"API body has token: {has_token}")
                log(f"Body keys: {list(body.keys())}")
                if has_token:
                    log(f"Token value: {body['cf_challenge_response'][:60]}...")
            except Exception as e:
                log(f"Body parse error: {e}")
                log(f"Raw body: {captured_req[0].post_data[:200]}")
        
        if captured_res[0]:
            log(f"API status: {captured_res[0].status}")
            try:
                body = captured_res[0].json()
                if body.get('success'):
                    log("===== SUCCESS! =====")
                    log(f"Account: {email}")
                else:
                    code = body.get('errors', [{}])[0].get('code')
                    msg = body.get('errors', [{}])[0].get('message')
                    log(f"Error {code}: {msg}")
            except:
                log(f"Response: {captured_res[0].text[:300]}")
        
        browser.close()

def main():
    log("=== CF Signup - Hidden Field Method ===")
    signup()
    log("\n=== Done ===")

if __name__ == '__main__':
    main()