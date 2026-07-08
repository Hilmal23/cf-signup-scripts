#!/usr/bin/env python3
"""
CF Signup - Set value via JS (bypasses hidden input restriction)
Playwright's fill() can't fill type=hidden inputs.
Use page.evaluate() JS to set the value directly.
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
        
        # Wait for cf_clearance
        for i in range(10):
            cookies = {c["name"]: c["value"] for c in ctx.cookies()}
            if 'cf_clearance' in cookies:
                log(f"cf_clearance: YES (waited {i*2}s)")
                break
            time.sleep(2)
        
        # STEP 1: Set token via JS (THIS IS THE KEY FIX!)
        result = page.evaluate(f'''() => {{
            var inp = document.querySelector('input[name="cf_challenge_response"]');
            if (inp) {{
                inp.value = "{token}";
                inp.setAttribute('value', "{token}");
                // Dispatch input event so React/JS picks it up
                inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return "SUCCESS: value set to " + inp.value.length + " chars";
            }}
            return "NOT FOUND";
        }}''')
        log(f"JS set result: {result}")
        
        # STEP 2: Verify value was set
        val_check = page.evaluate('''() => {{
            var inp = document.querySelector('input[name="cf_challenge_response"]');
            return inp ? inp.value.slice(0, 50) : "NOT FOUND";
        }}''')
        log(f"Value check: {val_check}...")
        
        # STEP 3: Fill form fields
        email_inp = page.query_selector('input[name="email"]')
        if not email_inp or not email_inp.is_visible():
            log("No email input!")
            browser.close()
            return
        
        email_inp.fill(email)
        time.sleep(0.3)
        
        # STEP 4: SET TOKEN AGAIN after filling email (in case it was cleared)
        page.evaluate(f'''() => {{
            var inp = document.querySelector('input[name="cf_challenge_response"]');
            if (inp) {{
                inp.value = "{token}";
                inp.setAttribute('value', "{token}");
                inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }}''')
        
        pw_inp = page.query_selector('input[name="password"]')
        pw_inp.fill(pw)
        time.sleep(0.3)
        
        # STEP 5: SET TOKEN AGAIN after filling password (final)
        page.evaluate(f'''() => {{
            var inp = document.querySelector('input[name="cf_challenge_response"]');
            if (inp) {{
                inp.value = "{token}";
                inp.setAttribute('value', "{token}");
                inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }}''')
        
        val_final = page.evaluate('''() => {{
            var inp = document.querySelector('input[name="cf_challenge_response"]');
            return inp ? inp.value.slice(0, 60) : "NOT FOUND";
        }}''')
        log(f"Final token value: {val_final}...")
        
        # Intercept request
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
        
        log("Submitting...")
        pw_inp.press('Enter')
        time.sleep(10)
        
        log(f"After: {page.title()} | {page.url}")
        
        if captured_req[0]:
            try:
                body = json.loads(captured_req[0].post_data or '{}')
                tval = body.get('cf_challenge_response', '')
                log(f"Token in body: '{tval[:60] if tval else '(empty)'}' (len={len(tval)})")
            except:
                pass
        
        if captured_res[0]:
            log(f"API: {captured_res[0].status}")
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
        
        page.screenshot(path='/tmp/cf_final.png')
        browser.close()

def main():
    log("=== CF Signup - JS Set Value (No Hidden Fill) ===")
    token = solve()
    if token:
        signup(token)
    log("\nDone")

if __name__ == '__main__':
    main()