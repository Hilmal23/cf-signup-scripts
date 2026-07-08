#!/usr/bin/env python3
"""CF signup - extract sitekey, solve via 2Captcha, inject token"""
from camoufox import Camoufox
import time, re, requests

TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
CF_PAGE = "https://dash.cloudflare.com/sign-up"

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def get_sitekey_from_api_js(html):
    """Extract sitekey from the Turnstile API script URL in page"""
    m = re.search(r'src="(https://challenges\.cloudflare\.com/turnstile/v\d+/api\.js\?render=[^"]+)"', html)
    if m:
        url = m.group(1)
        m2 = re.search(r'render=([^&"]+)', url)
        if m2:
            return m2.group(1)
    return None

def solve_turnstile(sitekey, pageurl):
    log(f"Solving: sitekey={sitekey[:30]}...")
    url = f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={pageurl}&sitekey={sitekey}&json=1"
    r = requests.get(url, timeout=10)
    result = r.json()
    
    if result.get('status') != 1:
        log(f"Submit failed: {result}")
        return None
    
    job_id = result.get('request')
    log(f"Job: {job_id}")
    
    for i in range(60):
        time.sleep(3)
        check = f"http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={job_id}&json=1"
        r = requests.get(check, timeout=10)
        res = r.json()
        
        if res.get('status') == 1:
            token = res.get('request')
            log(f"Solved! {token[:40]}...")
            return token
        elif 'NOT_READY' in str(res):
            continue
        else:
            log(f"Error: {res}")
            return None
    return None

# Test 1: Check sitekey extraction
log("=== Testing sitekey extraction ===")
with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    page.goto(CF_PAGE, timeout=30000)
    time.sleep(3)
    
    html = page.content()
    sitekey = get_sitekey_from_api_js(html)
    log(f"Sitekey: {sitekey}")
    
    # Also check challenge widget
    widget = page.query_selector('[data-testid="challenge-widget-container"]')
    if widget:
        log(f"Widget found: {widget.get_attribute('class')}")
        # Get inner HTML
        inner = page.evaluate("() => document.querySelector('[data-testid=\"challenge-widget-container\"]').innerHTML")
        log(f"Widget inner: {inner[:300]}")
    
    # Check hidden input
    hidden = page.query_selector('input[name="cf_challenge_response"]')
    if hidden:
        id_ = hidden.get_attribute('id') or ''
        val = hidden.get_attribute('value') or ''
        log(f"Hidden input: id={id_} value={val[:30]}")
    
    page.screenshot(path='/tmp/cf_widget.png')
    browser.close()

# Test 2: Try to invoke CF Turnstile JS directly
log("=== Testing CF Turnstile JS ===")
with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    page.goto(CF_PAGE, timeout=30000)
    time.sleep(3)
    
    result = page.evaluate("""
        () => {
            var result = {
                cfTurnstile: typeof window.cfTurnstile !== 'undefined',
                turnstileObject: typeof window.turnstile !== 'undefined',
                challengeWidget: typeof window.__CFChallengeDefine !== 'undefined',
                rendered: false,
                token: null
            };
            
            // Try to find if Turnstile rendered
            var container = document.querySelector('[data-testid="challenge-widget-container"]');
            var iframe = container ? container.querySelector('iframe') : null;
            if (iframe) {
                result.rendered = true;
                result.iframeSrc = iframe.src;
                result.iframeClass = iframe.className;
            }
            
            // Try calling turnstile.render directly
            try {
                if (window.turnstile) {
                    var sitekey = window.turnstile.sitekey || 'not found';
                    result.turnstileSitekey = sitekey;
                }
            } catch(e) {
                result.turnstileError = e.message;
            }
            
            return result;
        }
    """)
    log(f"Turnstile JS: {result}")
    
    browser.close()

# Test 3: Full flow with 2Captcha
log("=== Full signup with 2Captcha ===")
email = f"solve{int(time.time())}@hilmal.store"
pw = "SolveTest123!"
log(f"Email: {email}")

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    page.goto(CF_PAGE, timeout=30000)
    time.sleep(3)
    
    # Get sitekey
    html = page.content()
    sitekey = get_sitekey_from_api_js(html)
    log(f"Sitekey: {sitekey}")
    
    if sitekey:
        token = solve_turnstile(sitekey, CF_PAGE)
        if token:
            # Inject token into hidden field
            page.fill('input[name="cf_challenge_response"]', token)
            log("Token injected!")
            time.sleep(1)
    
    # Fill form
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    
    # Submit
    page.click('button[type="submit"]')
    time.sleep(8)
    
    title = page.title()
    url = page.url
    body = page.inner_text('body')
    
    log(f"Result: {title} | {url}")
    
    if 'dashboard' in title.lower() and 'sign-up' not in url:
        log("SUCCESS!")
        page.screenshot(path='/tmp/cf_solved.png')
    else:
        log(f"FAILED: {body[:200]}")
        page.screenshot(path='/tmp/cf_not_solved.png')
    
    browser.close()