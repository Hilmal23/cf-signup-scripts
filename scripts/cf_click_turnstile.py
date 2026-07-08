#!/usr/bin/env python3
"""
CF Signup - CORRECT approach:
1. Solve Turnstile via 2Captcha (correct sitekey found!)
2. Click the Turnstile iframe checkbox WITHIN the browser
3. THEN submit the form (browser handles token automatically)
"""
from playwright.sync_api import sync_playwright
import time, json, requests, re

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
SITEKEY = "0x4AAAAAAAJel0iaAR3mgkjp"
PAGE_URL = "https://dash.cloudflare.com/sign-up"
CHROMIUM = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
PROXY = {'server': 'http://brd.superproxy.io:33335', 'username': 'brd-customer-hl_c0f6789c-zone-web_unlocker1', 'password': 'ds3ovbwhs69y'}
CHROME_ARGS = ["--no-sandbox","--disable-setuid-sandbox","--ignore-certificate-errors","--allow-running-insecure-content","--ignore-certificate-errors-spki-list=*"]

def solve_turnstile():
    """Solve Turnstile once via 2Captcha"""
    log("=== Solving Turnstile ===")
    r = requests.get(
        f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={PAGE_URL}&sitekey={SITEKEY}&json=1",
        timeout=10
    )
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

def find_and_click_turnstile(page):
    """Find Turnstile iframe and click its checkbox"""
    # Find the challenge/turnstile iframe
    for iframe in page.query_selector_all('iframe'):
        src = iframe.get_attribute('src') or ''
        id_ = iframe.get_attribute('id') or ''
        cls = iframe.get_attribute('class') or ''
        
        if 'challenge' in src.lower() or 'turnstile' in src.lower():
            log(f"Found challenge iframe: {src[:80]}")
            try:
                # Use frame_locator with the iframe
                fl = page.frame_locator(f'#{id_}') if id_ else page.frame_locator(f'[src="{src}"]')
                # Try to find checkbox
                cb = fl.query_selector('input[type="checkbox"]')
                if cb:
                    log(f"Found checkbox! Clicking...")
                    cb.click()
                    time.sleep(2)
                    return True
                # Try to find the iframe by src attribute
                log(f"No checkbox in this iframe")
            except Exception as e:
                log(f"Frame click error: {e}")
    
    # Alternative: find ALL iframes and check their content
    all_iframes = page.query_selector_all('iframe')
    log(f"Total iframes on page: {len(all_iframes)}")
    for i, iframe in enumerate(all_iframes):
        src = iframe.get_attribute('src') or ''
        id_ = iframe.get_attribute('id') or ''
        print(f"  [{i}] id={id_[:20]} src={src[:60]}")
    
    return False

def signup_with_challenge():
    """Full signup flow with Turnstile solve"""
    token = solve_turnstile()
    if not token:
        log("Solve failed!")
        return
    
    email = f"cf{int(time.time()*1000)}@hilmal.store"
    pw = "CfSignup123!"
    log(f"\nEmail: {email}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=CHROMIUM,
            args=CHROME_ARGS,
        )
        ctx = browser.new_context(proxy=PROXY)
        page = ctx.new_page()
        
        page.goto(PAGE_URL, timeout=60000)
        time.sleep(8)
        
        log(f"Title: {page.title()}")
        
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
        
        # Check for challenge
        body = page.inner_text('body')
        has_challenge = 'let us know' in body.lower()
        log(f"Challenge: {has_challenge}")
        
        if has_challenge:
            # Try to click Turnstile iframe checkbox
            found = find_and_click_turnstile(page)
            if not found:
                log("Could not find/click Turnstile checkbox!")
                # Try injecting token into every possible location
                page.evaluate(f"""
                    () => {{
                        window.cf_challenge_response = "{token}";
                        window._cf_challenge_response = "{token}";
                        // Dispatch custom event
                        document.dispatchEvent(new CustomEvent('turnstile-success', {{detail: "{token}"}}));
                        // Try Turnstile API
                        if (typeof Turnstile !== 'undefined') {{
                            Object.defineProperty(window, 'cf_challenge_response', {{value: "{token}", writable: true}});
                        }}
                    }}
                """)
            
            # Wait for challenge to clear
            for i in range(10):
                time.sleep(2)
                body = page.inner_text('body')
                if 'let us know' not in body.lower():
                    log(f"Challenge cleared after {i*2}s!")
                    break
                log(f"Still waiting... ({i+1}/10)")
        
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
        
        # Capture API
        captured_req = [None]
        captured_res = [None]
        def on_req(req):
            if 'user/create' in req.url:
                captured_req[0] = {'url': req.url, 'headers': dict(req.headers), 'body': req.post_data}
        def on_res(resp):
            if 'user/create' in resp.url:
                captured_res[0] = resp
        page.on("request", on_req)
        page.on("response", on_res)
        
        # Inject token JUST BEFORE clicking submit
        page.evaluate(f"""
            () => {{
                // Final attempt - set ALL possible token locations
                window.cf_challenge_response = "{token}";
                window._cf_challenge_response = "{token}";
                document.querySelectorAll('input').forEach(inp => {{
                    if (inp.name && (inp.name.includes('challenge') || inp.name.includes('cf_') || inp.name.includes('turnstile'))) {{
                        inp.value = "{token}";
                        inp.setAttribute('value', "{token}");
                    }}
                }});
            }}
        """)
        
        # Small delay to let injection take effect
        time.sleep(0.5)
        
        # Submit
        log("Submitting...")
        page.click('button[type="submit"]')
        time.sleep(10)
        
        log(f"After: {page.title()} | {page.url}")
        page.screenshot(path='/tmp/cf_result.png')
        
        if captured_req[0]:
            try:
                body = json.loads(captured_req[0]['body'])
                log(f"cf_challenge_response: '{body.get('cf_challenge_response', 'EMPTY')[:60] if body.get('cf_challenge_response') else 'EMPTY'}'")
            except:
                log(f"Body: {captured_req[0]['body'][:200]}")
        
        if captured_res[0]:
            log(f"API: {captured_res[0].status}")
            try:
                log(f"Response: {json.dumps(captured_res[0].json(), indent=2)}")
            except:
                log(f"Response: {captured_res[0].text[:200]}")
        
        browser.close()

def main():
    log("=== CF Signup - Turnstile Click Approach ===")
    signup_with_challenge()
    log("\n=== Done ===")

if __name__ == '__main__':
    main()