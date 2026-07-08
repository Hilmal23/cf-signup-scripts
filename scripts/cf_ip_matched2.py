#!/usr/bin/env python3
"""
CF Signup - IP-MATCHED solving (CRITICAL!)
Solve Turnstile via 2Captcha ROUTED THROUGH SAME BD proxy.
Then browser uses same proxy → same IP → token valid!
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
    """Solve Turnstile routed through same BD proxy as browser"""
    log("Solving Turnstile via BD proxy...")
    
    proxies = {'http': PROXY_STR, 'https': PROXY_STR}
    
    r = requests.get(
        f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={PAGE_URL}&sitekey={SITEKEY}&json=1",
        timeout=15, proxies=proxies
    )
    result = r.json()
    if result.get('status') != 1:
        log(f"Failed: {result}")
        return None
    job_id = result['request']
    log(f"Job: {job_id}")
    
    for i in range(40):
        time.sleep(3)
        r2 = requests.get(
            f"http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={job_id}&json=1",
            timeout=10, proxies=proxies
        )
        res = r2.json()
        if res.get('status') == 1:
            log(f"Token: {res['request'][:50]}...")
            return res['request']
        if 'CAPCHA_NOT_READY' not in str(res):
            log(f"Error: {res}")
            return None
        log(f"Waiting... ({i+1}/40)")
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
        
        all_cookies = ctx.cookies()
        
        # ROUTE: intercept and abort, send modified request
        api_req_data = [None]
        route_intercepted = [False]
        
        def handle_route(route):
            req = route.request
            if 'user/create' in req.url:
                headers = dict(req.headers)
                try:
                    body_data = json.loads(req.post_data or '{}')
                except:
                    body_data = {}
                
                api_req_data[0] = {
                    'url': req.url,
                    'headers': headers,
                    'body': body_data,
                    'cookies': all_cookies
                }
                
                log(f"Route intercepted!")
                route_intercepted[0] = True
                route.abort()
            else:
                route.continue_()
        
        page.route('**/api/v4/user/create', handle_route)
        
        log("Submitting...")
        email_inp = page.query_selector('input[name="email"]')
        email_inp.fill(email)
        time.sleep(0.3)
        pw_inp = page.query_selector('input[name="password"]')
        pw_inp.fill(pw)
        time.sleep(0.3)
        pw_inp.press('Enter')
        
        for i in range(30):
            if route_intercepted[0]:
                break
            time.sleep(0.5)
        
        time.sleep(3)
        
        if api_req_data[0] and route_intercepted[0]:
            req_info = api_req_data[0]
            req_info['body']['cf_challenge_response'] = token
            log(f"Injecting token (IP-matched): {token[:50]}...")
            
            session = requests.Session()
            session.verify = False
            session.proxies = {'http': PROXY_STR, 'https': PROXY_STR}
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Content-Type': 'application/json',
                'Origin': 'https://dash.cloudflare.com',
                'Referer': 'https://dash.cloudflare.com/sign-up',
            }
            
            cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in req_info['cookies']])
            headers['Cookie'] = cookie_str
            
            r = session.post(req_info['url'], json=req_info['body'], headers=headers, timeout=30)
            log(f"Status: {r.status_code}")
            log(f"Response: {r.text[:500]}")
            
            try:
                resp = r.json()
                if resp.get('success'):
                    log("===== SUCCESS! =====")
                    log(f"Account: {email}")
                else:
                    code = resp.get('errors', [{}])[0].get('code')
                    msg = resp.get('errors', [{}])[0].get('message')
                    log(f"Error {code}: {msg}")
            except:
                pass
        
        log(f"\nPage: {page.title()} | {page.url}")
        page.screenshot(path='/tmp/cf_ip_matched.png')
        browser.close()

def main():
    log("=== CF Signup - IP-MATCHED Solving ===")
    token = solve_with_proxy()
    if token:
        signup(token)
    log("\nDone")

if __name__ == '__main__':
    main()