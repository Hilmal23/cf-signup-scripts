#!/usr/bin/env python3
"""
CF Signup Turnstile FREE bypass - NO 2Captcha, NO paid solver.
Test multiple free approaches:
1. Kamatera clean IP direct (no proxy) 
2. Residential proxy (free tier or alternative providers)
3. VPN tunnel to residential exit
4. Camoufox fingerprint reuse (skip challenge if fingerprint known)
5. Intercept + inject Turnstile from working browser context
"""
from playwright.sync_api import sync_playwright
import time, json, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

EMAIL = f"cf{int(time.time())}@hilmal.store"
PW = "CfSignup123!"

PROXY_ALTERNATIVES = [
    # Bright Data Web Unlocker (works for page load)
    {'server': 'http://brd.superproxy.io:33335', 'username': 'brd-customer-hl_c0f6789c-zone-web_unlocker1', 'password': 'ds3ovbwhs69y'},
    # No proxy (clean Kamatera IP)
    None,
    # Alternative free/cheap proxies
    # {'server': 'http://85.214.32.52:80'},  # test only
]

CHROMIUM_PATH = "/snap/chromium/current/usr/lib/chromium-browser/chrome"

CHROME_ARGS = [
    "--no-sandbox", "--disable-setuid-sandbox",
    "--ignore-certificate-errors",
    "--allow-running-insecure-content",
    "--ignore-certificate-errors-spki-list=*",
]

def test_signup_no_proxy():
    """Test signup from CLEAN Kamatera IP - no proxy at all"""
    log("\n=== TEST 1: No Proxy (Clean Kamatera IP) ===")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                executable_path=CHROMIUM_PATH,
                args=CHROME_ARGS,
            )
            ctx = browser.new_context()
            page = ctx.new_page()
            
            log("Loading signup page (no proxy)...")
            page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
            time.sleep(10)
            
            log(f"Title: {page.title()}")
            log(f"URL: {page.url[:80]}")
            
            # Check for challenge
            body = page.evaluate("() => document.body?.innerText?.slice(0, 200) || ''")
            if 'let us know' in body.lower():
                log("Challenge shown from clean IP!")
                # Still try to fill + submit
                page.screenshot(path='/tmp/cf_clean_ip.png')
            else:
                log("No challenge from clean IP!")
            
            # Try to find form
            email_inp = page.query_selector('input[name="email"]')
            if email_inp:
                log("Email input found!")
                email_inp.fill(EMAIL)
                pw_inp = page.query_selector('input[name="password"]')
                pw_inp.fill(PW)
                
                # Capture requests
                captured_req = [None]
                def on_req(req):
                    if '/api/v4/user/create' in req.url:
                        captured_req[0] = req
                page.on("request", on_req)
                
                log("Submitting...")
                page.click('button[type="submit"]')
                time.sleep(10)
                
                log(f"After submit - Title: {page.title()}")
                log(f"After submit - URL: {page.url[:80]}")
                
                if captured_req[0]:
                    body_data = captured_req[0].post_data
                    if body_data:
                        data = json.loads(body_data)
                        log(f"cf_challenge_response: '{data.get('cf_challenge_response', 'EMPTY')[:50] if data.get('cf_challenge_response') else 'EMPTY'}'")
                
                page.screenshot(path='/tmp/cf_clean_submit.png')
            else:
                log("NO email input visible!")
                page.screenshot(path='/tmp/cf_clean_nofill.png')
            
            browser.close()
    except Exception as e:
        log(f"Error: {e}")

def test_signup_bd_proxy():
    """Test with BD Web Unlocker proxy"""
    log("\n=== TEST 2: Bright Data Web Unlocker Proxy ===")
    proxy = PROXY_ALTERNATIVES[0]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                executable_path=CHROMIUM_PATH,
                args=CHROME_ARGS,
            )
            ctx = browser.new_context(proxy=proxy)
            page = ctx.new_page()
            
            log("Loading via BD...")
            page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
            time.sleep(10)
            
            log(f"Title: {page.title()}")
            log(f"URL: {page.url[:80]}")
            
            body = page.evaluate("() => document.body?.innerText?.slice(0, 200) || ''")
            has_challenge = 'let us know' in body.lower()
            log(f"Challenge shown: {has_challenge}")
            
            # Find email input
            email_inp = page.query_selector('input[name="email"]')
            if email_inp and email_inp.is_visible():
                log("Email input visible!")
                email_inp.fill(EMAIL)
                pw_inp = page.query_selector('input[name="password"]')
                pw_inp.fill(PW)
                time.sleep(0.5)
                
                # Get ALL security tokens
                sec_token = page.evaluate("() => document.querySelector('input[name=\"security_token\"]')?.value || ''")
                sig = page.evaluate("() => document.querySelector('input[name=\"sig\"]')?.value || ''")
                log(f"Security token: {sec_token[:30]}...")
                log(f"Sig: {sig[:30]}...")
                
                # Check for Turnstile iframe
                ts_iframe = page.query_selector('iframe[src*="challenge"]')
                log(f"Turnstile iframe: {ts_iframe is not None}")
                if ts_iframe:
                    src = ts_iframe.get_attribute('src')
                    log(f"Iframe src: {src[:100]}")
                
                # Capture request
                captured_req = [None]
                def on_req(req):
                    if '/api/v4/user/create' in req.url:
                        captured_req[0] = {
                            'url': req.url,
                            'headers': dict(req.headers),
                            'body': req.post_data,
                            'cookies': dict(ctx.cookies())
                        }
                page.on("request", on_req)
                
                # Dismiss cookie consent if present
                for _ in range(2):
                    allow = page.query_selector('button:has-text("Allow All")')
                    if allow and allow.is_visible():
                        allow.click()
                        time.sleep(1)
                
                log("Clicking submit...")
                page.click('button[type="submit"]')
                time.sleep(10)
                
                log(f"After - Title: {page.title()}")
                log(f"After - URL: {page.url[:80]}")
                
                if captured_req[0]:
                    try:
                        body_data = json.loads(captured_req[0]['body'])
                        log(f"API body cf_challenge_response: '{body_data.get('cf_challenge_response', 'EMPTY')[:50] if body_data.get('cf_challenge_response') else 'EMPTY'}'")
                    except:
                        log(f"API body: {captured_req[0]['body'][:200]}")
                else:
                    log("No create API captured!")
                
                page.screenshot(path='/tmp/cf_bd_submit.png')
            else:
                log("No email input!")
                page.screenshot(path='/tmp/cf_bd_nofill.png')
            
            browser.close()
    except Exception as e:
        log(f"Error: {e}")

def test_turnstile_iframe_detection():
    """Try to find Turnstile sitekey + iframe dynamically"""
    log("\n=== TEST 3: Dynamic Turnstile Detection ===")
    proxy = PROXY_ALTERNATIVES[0]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                executable_path=CHROMIUM_PATH,
                args=CHROME_ARGS,
            )
            ctx = browser.new_context(proxy=proxy)
            page = ctx.new_page()
            
            # Capture ALL network responses to find sitekey
            challenge_responses = []
            
            def on_resp(resp):
                url = resp.url
                if 'challenge' in url.lower() or 'turnstile' in url.lower():
                    challenge_responses.append({
                        'url': url,
                        'status': resp.status,
                        'headers': dict(resp.headers)
                    })
            
            page.on("response", on_resp)
            page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
            time.sleep(10)
            
            log("Challenge responses found:")
            for cr in challenge_responses:
                log(f"  [{cr['status']}] {cr['url'][:100]}")
            
            # Find ALL iframes
            iframes = page.query_selector_all('iframe')
            log(f"\nTotal iframes: {len(iframes)}")
            for iframe in iframes:
                src = iframe.get_attribute('src') or ''
                cls = iframe.get_attribute('class') or ''
                log(f"  src={src[:80]} class={cls[:40]}")
                if 'turnstile' in src.lower() or 'challenge' in src.lower():
                    log(f"  *** MATCH: {src}")
            
            browser.close()
    except Exception as e:
        log(f"Error: {e}")

def test_api_direct_no_challenge():
    """Try direct API call - bypass browser challenge entirely"""
    log("\n=== TEST 4: Direct API Call (bypass browser) ===")
    proxy = PROXY_ALTERNATIVES[0]
    
    session = requests.Session()
    session.proxies = {
        'http': f'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@{proxy["server"].replace("http://", "")}',
        'https': f'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@{proxy["server"].replace("http://", "")}'
    }
    session.verify = False
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    
    # Step 1: Get security token + cookies
    log("Fetching signup page for tokens...")
    try:
        r = session.get('https://dash.cloudflare.com/sign-up', timeout=30)
        log(f"Page status: {r.status_code}")
        log(f"Page URL: {r.url[:80]}")
        
        # Extract security token from HTML
        import re
        sec_token_match = re.search(r'name="security_token"\s+value="([^"]+)"', r.text)
        sig_match = re.search(r'name="sig"\s+value="([^"]+)"', r.text)
        
        sec_token = sec_token_match.group(1) if sec_token_match else ''
        sig = sig_match.group(1) if sig_match else ''
        
        log(f"Security token: {sec_token[:30] if sec_token else 'NONE'}...")
        log(f"Sig: {sig[:30] if sig else 'NONE'}...")
        
        # Step 2: Try creating account with cf_challenge_response=""
        log("Trying direct API POST (no challenge token)...")
        data = {
            "email": EMAIL,
            "password": PW,
            "mrk_optin": True,
            "security_token": sec_token,
            "method": "Onboarding: New_v2",
            "locale": "en-US",
            "legal_stamp": "",
            "opt_ins": {},
            "mrktCheckboxDisplayed": False,
            "hCaptchaDisplayed": False,
            "cf_challenge_response": ""
        }
        
        r2 = session.post(
            'https://dash.cloudflare.com/api/v4/user/create',
            json=data,
            timeout=30,
            allow_redirects=False
        )
        log(f"API Status: {r2.status_code}")
        log(f"API Response: {r2.text[:500]}")
        
        # Try without cookies (fresh)
        log("\nTrying fresh session (no cookies)...")
        session2 = requests.Session()
        session2.proxies = session.proxies
        session2.verify = False
        session2.headers.update(session.headers)
        
        r3 = session2.post(
            'https://dash.cloudflare.com/api/v4/user/create',
            json=data,
            timeout=30
        )
        log(f"Fresh API Status: {r3.status_code}")
        log(f"Fresh Response: {r3.text[:500]}")
        
    except Exception as e:
        log(f"Error: {e}")

def main():
    log("=== CF Signup FREE Bypass Tests ===")
    log(f"Email: {EMAIL}")
    log(f"Target: https://dash.cloudflare.com/sign-up")
    
    # Run tests
    test_signup_no_proxy()
    test_signup_bd_proxy()
    test_turnstile_iframe_detection()
    test_api_direct_no_challenge()
    
    log("\n=== All tests complete ===")

if __name__ == '__main__':
    main()