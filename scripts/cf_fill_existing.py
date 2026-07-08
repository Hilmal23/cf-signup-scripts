#!/usr/bin/env python3
"""
CF Signup - Find and FILL existing hidden field (not create new one)
Key insight: CF creates a hidden input for cf_challenge_response but keeps it empty.
We must FILL the existing field, not create a new one.
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
        log(f"Failed: {result}")
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
    return None

def signup(token):
    email = f"cf{int(time.time()*1000)}@hilmal.store"
    pw = "CfSignup123!"
    log(f"Email: {email}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROMIUM, args=CHROME_ARGS)
        ctx = browser.new_context(proxy=PROXY)
        page = ctx.new_page()
        
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
        
        # STEP 1: Inspect ALL hidden inputs on the page
        all_inputs = page.query_selector_all('input')
        log(f"\nTotal inputs: {len(all_inputs)}")
        for inp in all_inputs:
            name = inp.get_attribute('name') or ''
            type_ = inp.get_attribute('type') or 'text'
            val = inp.get_attribute('value') or ''
            log(f"  type={type_:12} name={name:30} value={val[:30] if val else '(empty)'}")
        
        # STEP 2: Find existing cf_challenge_response hidden input
        existing = page.query_selector('input[name="cf_challenge_response"]')
        if existing:
            log(f"Existing cf_challenge_response field found!")
            type_ = existing.get_attribute('type')
            val = existing.get_attribute('value')
            log(f"  type={type_}, current value={val[:30] if val else '(empty)'}")
            existing.fill(token)
            time.sleep(0.5)
            val_after = existing.get_attribute('value')
            log(f"  After fill: {val_after[:50] if val_after else '(empty)'}")
        else:
            log("No existing cf_challenge_response field - creating...")
            page.evaluate(f'''() => {{
                var input = document.createElement('input');
                input.type = "hidden";
                input.name = "cf_challenge_response";
                input.value = "{token}";
                input.id = "cf_challenge_response";
                var form = document.querySelector('form');
                if (form) form.appendChild(input);
                else document.body.appendChild(input);
            }}''')
            time.sleep(0.5)
        
        # STEP 3: Verify the field now has the token
        hidden_val = page.evaluate('''() => {{
            var inp = document.querySelector('input[name="cf_challenge_response"]');
            return inp ? JSON.stringify({{name: inp.name, type: inp.type, value: inp.value, valueLen: inp.value.length}}) : "NOT FOUND";
        }}''')
        log(f"Hidden field state: {hidden_val}")
        
        # Wait for cf_clearance
        for i in range(10):
            cookies = {c["name"]: c["value"] for c in ctx.cookies()}
            if 'cf_clearance' in cookies:
                log(f"cf_clearance: {cookies['cf_clearance'][:40]}... (waited {i*2}s)")
                break
            time.sleep(2)
        
        # STEP 4: Fill form
        email_inp = page.query_selector('input[name="email"]')
        if not email_inp or not email_inp.is_visible():
            log("No email input!")
            browser.close()
            return
        
        # CRITICAL: FILL the token field AGAIN after filling email (it might get cleared)
        token_field = page.query_selector('input[name="cf_challenge_response"]')
        if token_field:
            token_field.fill(token)
            log(f"Token field refilled: {token_field.get_attribute('value')[:50] if token_field.get_attribute('value') else 'EMPTY'}")
        
        email_inp.fill(email)
        time.sleep(0.3)
        
        # REFILL token field AGAIN after email fill
        token_field2 = page.query_selector('input[name="cf_challenge_response"]')
        if token_field2:
            token_field2.fill(token)
        
        pw_inp = page.query_selector('input[name="password"]')
        pw_inp.fill(pw)
        time.sleep(0.3)
        
        # REFILL token field AGAIN after password fill (last chance)
        token_field3 = page.query_selector('input[name="cf_challenge_response"]')
        if token_field3:
            token_field3.fill(token)
            log(f"Token field (final): {token_field3.get_attribute('value')[:50] if token_field3.get_attribute('value') else 'EMPTY'}")
        
        captured_res = [None]
        captured_req = [None]
        def on_res(resp):
            if 'user/create' in resp.url:
                captured_res[0] = resp
        def on_req(req):
            if 'user/create' in req.url:
                captured_req[0] = req
        page.on("request", on_req)
        page.on("response", on_res)
        
        log("Submitting...")
        pw_inp.press('Enter')
        time.sleep(10)
        
        log(f"After: {page.title()} | {page.url}")
        
        if captured_req[0]:
            try:
                body = json.loads(captured_req[0].post_data or '{}')
                tval = body.get('cf_challenge_response', '')
                log(f"Token in API body: '{tval[:60] if tval else '(empty)'}' (len={len(tval)})")
            except:
                log(f"Body: {captured_req[0].post_data[:100]}")
        
        if captured_res[0]:
            log(f"API: {captured_res[0].status}")
            try:
                body = captured_res[0].json()
                if body.get('success'):
                    log("===== SUCCESS! =====")
                else:
                    code = body.get('errors', [{}])[0].get('code')
                    msg = body.get('errors', [{}])[0].get('message')
                    log(f"Error {code}: {msg}")
            except:
                log(f"Response: {captured_res[0].text[:300]}")
        
        page.screenshot(path='/tmp/cf_final.png')
        browser.close()

def main():
    log("=== CF Signup - Fill Existing Hidden Field ===")
    token = solve()
    if token:
        signup(token)
    log("\nDone")

if __name__ == '__main__':
    main()