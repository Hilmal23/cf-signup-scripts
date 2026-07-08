#!/usr/bin/env python3
"""
CF Signup - MONITOR full page state after submit
Track every URL change, every response, every console message.
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

def signup(token):
    email = f"cf{int(time.time()*1000)}@hilmal.store"
    pw = "CfSignup123!"
    log(f"Email: {email}")
    
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
        
        all_cookies = {c["name"]: c["value"] for c in ctx.cookies()}
        security_token = page.evaluate('''() => {{
            var inp = document.querySelector('input[name="security_token"]');
            return inp ? inp.value : "";
        }}''')
        log(f"Security token: {security_token[:30]}...")
        
        # Track ALL requests and responses
        events = []
        def on_req(req):
            if 'cloudflare' in req.url or 'cf' in req.url.lower():
                events.append(f"REQ: {req.method} {req.url[:80]}")
        def on_res(resp):
            if 'cloudflare' in resp.url or 'cf' in resp.url.lower():
                events.append(f"RES: {resp.status} {resp.url[:80]}")
        def on_nav(url):
            events.append(f"NAV: {url[:80]}")
        page.on("request", on_req)
        page.on("response", on_res)
        page.on("navigation", on_nav)
        
        # Also listen for console messages
        console_msgs = []
        def on_console(msg):
            console_msgs.append(f"{msg.type}: {msg.text[:100]}")
        page.on("console", on_console)
        
        # Fill form and submit
        email_inp = page.query_selector('input[name="email"]')
        if not email_inp or not email_inp.is_visible():
            log("No email input!")
            browser.close()
            return
        
        email_inp.fill(email)
        time.sleep(0.3)
        pw_inp = page.query_selector('input[name="password"]')
        pw_inp.fill(pw)
        time.sleep(0.3)
        
        log("Submitting via click...")
        page.click('button[type="submit"]')
        
        # Wait and monitor
        log("Monitoring for 20 seconds...")
        for i in range(20):
            time.sleep(1)
            url = page.url
            title = page.title()
            body_preview = page.inner_text('body')[:100].replace('\n', ' ')
            if i % 5 == 0:
                log(f"  [{i}s] {title[:40]} | {url[:60]}")
        
        log(f"\n=== All events ({len(events)}) ===")
        for e in events:
            log(f"  {e}")
        
        log(f"\n=== Console messages ({len(console_msgs)}) ===")
        for c in console_msgs[:20]:
            log(f"  {c}")
        
        # Check final state
        log(f"\nFinal: {page.title()} | {page.url}")
        page.screenshot(path='/tmp/cf_monitor.png')
        
        # Check for specific elements on the page
        body = page.inner_text('body')
        
        # Look for error messages
        if 'verify' in body.lower():
            log(">>> VERIFY EMAIL PAGE! <<<")
        if 'already' in body.lower():
            log(">>> EMAIL ALREADY EXISTS! <<<")
        if 'taken' in body.lower():
            log(">>> EMAIL TAKEN! <<<")
        if 'error' in body.lower():
            log(">>> ERROR ON PAGE! <<<")
        
        # Check specific response
        for e in events:
            if 'user/create' in e:
                log(f"API event: {e}")
        
        browser.close()

def main():
    log("=== CF Signup - Full Monitor ===")
    token = solve()
    if token:
        signup(token)
    log("\nDone")

if __name__ == '__main__':
    main()