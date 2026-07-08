#!/usr/bin/env python3
"""
CF Signup - IP-MATCHED solving (CRITICAL FIX!)
Key insight: cf_clearance cookie is bound to the solving IP.
If 2Captcha solves from datacenter IP, cookie fails.
Solution: Route 2Captcha API call through SAME proxy as browser.
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
PROXY_STR = f"http://{PROXY_USER}:{PROXY_PASS}@brd.superproxy.io:33335"
CHROME_ARGS = ["--no-sandbox","--disable-setuid-sandbox","--ignore-certificate-errors","--allow-running-insecure-content","--ignore-certificate-errors-spki-list=*"]

def solve_with_proxy():
    """
    Solve Turnstile via 2Captcha, routing request through SAME proxy as browser.
    This ensures the cf_clearance cookie is bound to the residential proxy IP.
    """
    log("=== Solving Turnstile (via SAME proxy as browser) ===")
    
    # Route 2Captcha through BD proxy
    proxies = {
        'http': PROXY_STR,
        'https': PROXY_STR,
    }
    
    url = f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={PAGE_URL}&sitekey={SITEKEY}&json=1"
    r = requests.get(url, timeout=15, proxies=proxies)
    result = r.json()
    if result.get('status') != 1:
        log(f"Submit failed: {result}")
        return None
    job_id = result['request']
    log(f"Job: {job_id}")
    
    for i in range(40):
        time.sleep(3)
        r2 = requests.get(f"http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={job_id}&json=1",
                         timeout=10, proxies=proxies)
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

def signup_flow(token):
    """Complete signup with the IP-matched token"""
    email = f"cf{int(time.time()*1000)}@hilmal.store"
    pw = "CfSignup123!"
    log(f"\nEmail: {email}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROMIUM, args=CHROME_ARGS)
        ctx = browser.new_context(proxy=PROXY)
        page = ctx.new_page()
        
        # Step 1: Load signup page (gets challenge context from residential proxy)
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
        
        body = page.inner_text('body')
        has_challenge = 'let us know' in body.lower()
        log(f"Challenge: {has_challenge}")
        
        if has_challenge:
            log("Injecting token...")
            result = page.evaluate(f"""
                () => {{
                    window.cf_challenge_response = "{token}";
                    window._cf_challenge_response = "{token}";
                    
                    if (typeof Turnstile !== 'undefined') {{
                        try {{
                            Object.defineProperty(window, 'cf_challenge_response', {{
                                value: "{token}", writable: true, configurable: true
                            }});
                            return 'Turnstile obj + token set';
                        }} catch(e) {{ return 'Turnstile error: ' + e.message; }}
                    }}
                    
                    var inputs = document.querySelectorAll('input');
                    for (var i = 0; i < inputs.length; i++) {{
                        var n = inputs[i].name || '';
                        if (n.includes('challenge') || n.includes('cf_')) {{
                            inputs[i].value = "{token}";
                            return 'Set input: ' + n;
                        }}
                    }}
                    return 'No input found';
                }}
            """)
            log(f"Injection: {result}")
            
            for i in range(8):
                time.sleep(2)
                body = page.inner_text('body')
                if 'let us know' not in body.lower():
                    log(f"Challenge cleared! ({i*2}s)")
                    break
                log(f"Waiting... ({i+1}/8)")
        
        # Check cookies
        cookies = ctx.cookies()
        cf_clearance = None
        for c in cookies:
            if c['name'] == 'cf_clearance':
                cf_clearance = c['value']
                log(f"cf_clearance: {c['value'][:50]}...")
            elif c['name'] in ['__cf_bm', '__cf_ob', '__cflb']:
                log(f"  {c['name']}: {c['value'][:30]}...")
        
        if not cf_clearance:
            log("No cf_clearance cookie!")
            page.screenshot(path='/tmp/cf_no_clearance.png')
        
        # Fill + submit
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
        page.click('button[type="submit"]')
        time.sleep(10)
        
        log(f"After: {page.title()} | {page.url}")
        page.screenshot(path='/tmp/cf_result.png')
        
        if captured_req[0]:
            try:
                body = json.loads(captured_req[0].post_data or '{}')
                log(f"cf_challenge_response: '{body.get('cf_challenge_response', 'EMPTY')[:60] if body.get('cf_challenge_response') else 'EMPTY'}'")
            except:
                log(f"Body: {captured_req[0].post_data[:100]}")
        
        if captured_res[0]:
            log(f"API status: {captured_res[0].status}")
            try:
                log(f"Response: {json.dumps(captured_res[0].json(), indent=2)}")
            except:
                log(f"Response: {captured_res[0].text[:300]}")
        
        browser.close()

def main():
    log("=== CF Signup - IP-MATCHED Solving ===")
    log(f"Balance: ${requests.get('http://2captcha.com/res.php?key=3da28555894fd89bb569b748731e9400&action=getbalance', timeout=10).json().get('request', 0)}")
    
    token = solve_with_proxy()
    if not token:
        log("Solve failed!")
        return
    
    signup_flow(token)
    log("\n=== Done ===")

if __name__ == '__main__':
    main()