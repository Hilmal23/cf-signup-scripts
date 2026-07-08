#!/usr/bin/env python3
"""
CF Signup - SUCCESS DETECTION via Page Navigation (not API status)
Key insight: API returns 400 but account IS created!
Detection: page URL changes to dashboard, OR email already exists message.
"""
from playwright.sync_api import sync_playwright
import time, json, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
SITEKEY = "0x4AAAAAAAJel0iaAR3mgkjp"
PAGE_URL = "https://dash.cloudflare.com/sign-up"
CHROMIUM = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
PROXY_USER = "brd-customer-hl_c0f6789c-zone-web_unlocker1"
PROXY_PASS = "ds3ovbwhs69y"
PROXY = {'server': 'http://brd.superproxy.io:33335', 'username': PROXY_USER, 'password': PROXY_PASS}
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

def signup():
    email = f"cf{int(time.time()*1000)}@hilmal.store"
    pw = "CfSignup123!"
    log(f"Email: {email}")
    
    token = solve()
    if not token:
        log("Solve failed!")
        return None
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROMIUM, args=CHROME_ARGS)
        ctx = browser.new_context(proxy=PROXY)
        page = ctx.new_page()
        
        # Track URL changes
        url_history = [None]
        def on_nav(url):
            url_history[0] = url
        page.on("navigation", on_nav)
        
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
        
        page.evaluate(f'''() => {{
            window.cf_challenge_response = "{token}";
            window._cf_challenge_response = "{token}";
        }}''')
        
        for i in range(10):
            cookies = {c["name"]: c["value"] for c in ctx.cookies()}
            if 'cf_clearance' in cookies:
                log(f"cf_clearance: YES ({i*2}s)")
                break
            time.sleep(2)
        
        email_inp = page.query_selector('input[name="email"]')
        if not email_inp or not email_inp.is_visible():
            log("No email input!")
            browser.close()
            return None
        
        email_inp.fill(email)
        time.sleep(0.3)
        pw_inp = page.query_selector('input[name="password"]')
        pw_inp.fill(pw)
        time.sleep(0.3)
        
        # Track responses
        captured_res = [None]
        def on_res(resp):
            if 'user/create' in resp.url:
                captured_res[0] = resp
        page.on("response", on_res)
        
        log("Submitting...")
        page.click('button[type="submit"]')
        
        # Wait for navigation or page change
        for i in range(20):
            time.sleep(1)
            url = page.url
            title = page.title()
            body = page.inner_text('body')
            
            # SUCCESS signals
            if 'dashboard' in url.lower() and 'sign-up' not in url:
                log(f"===== NAVIGATED TO DASHBOARD! =====")
                log(f"URL: {url}")
                page.screenshot(path='/tmp/cf_success.png')
                browser.close()
                return email
            
            if 'EMAIL ALREADY EXISTS' in body.upper():
                log(f"===== EMAIL ALREADY REGISTERED! =====")
                log(f"URL: {url}")
                log(f"Account likely created: {email}")
                page.screenshot(path='/tmp/cf_email_taken.png')
                browser.close()
                return email
            
            if 'VERIF' in body.upper() and 'EMAIL' in body.upper():
                log(f"===== VERIFY EMAIL PAGE! =====")
                page.screenshot(path='/tmp/cf_verify.png')
                browser.close()
                return email
            
            if i % 5 == 0:
                log(f"  [{i}s] {title[:40]}")
        
        # Check the captured API response
        if captured_res[0]:
            status = captured_res[0].status
            try:
                body = captured_res[0].json()
                if body.get('success'):
                    log("===== API SUCCESS! =====")
                    return email
                code = body.get('errors', [{}])[0].get('code')
                msg = body.get('errors', [{}])[0].get('message')
                log(f"API error {code}: {msg}")
            except:
                log(f"API ({status}): {captured_res[0].text[:200]}")
        
        page.screenshot(path='/tmp/cf_final.png')
        log(f"Final: {page.title()} | {page.url}")
        browser.close()
        return None

def main():
    log("=== CF Signup - SUCCESS Detection ===")
    result = signup()
    if result:
        log(f"\n===== POTENTIAL ACCOUNT: {result} =====")
    else:
        log("\nNo account detected")
    log("\nDone")

if __name__ == '__main__':
    main()