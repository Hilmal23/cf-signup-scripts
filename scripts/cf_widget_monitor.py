#!/usr/bin/env python3
"""CF signup - monitor dynamic challenge widget + solve via 2Captcha"""
from camoufox import Camoufox
import time, re, requests

TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
CF_PAGE = "https://dash.cloudflare.com/sign-up"

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def solve_turnstile(sitekey, pageurl):
    log(f"Solving Turnstile: {sitekey[:30]}...")
    try:
        url = f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={pageurl}&sitekey={sitekey}&json=1"
        r = requests.get(url, timeout=10)
        result = r.json()
        
        if result.get('status') != 1:
            log(f"Submit failed: {result}")
            return None
        
        job_id = result.get('request')
        log(f"Job ID: {job_id}")
        
        for i in range(60):
            time.sleep(3)
            check = f"http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={job_id}&json=1"
            r = requests.get(check, timeout=10)
            res = r.json()
            
            if res.get('status') == 1:
                token = res.get('request')
                log(f"Solved! Token: {token[:40]}...")
                return token
            elif 'NOT_READY' in str(res):
                if i % 5 == 0:
                    log(f"  Waiting... {i*3}s")
                continue
            else:
                log(f"Error: {res}")
                return None
    except Exception as e:
        log(f"Solve error: {e}")
    return None

def get_sitekey_from_iframe_url(iframe_url):
    """Extract sitekey from Turnstile iframe URL"""
    m = re.search(r'sitekey=([^&"]+)', iframe_url)
    if m:
        return m.group(1)
    return None

log("=== Testing dynamic challenge widget monitoring ===")

email = f"widget{int(time.time())}@hilmal.store"
pw = "WidgetTest123!"
log(f"Email: {email}")

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    page.goto(CF_PAGE, timeout=30000)
    time.sleep(3)
    
    # Check initial state
    initial_iframes = page.query_selector_all('iframe')
    log(f"Initial iframes: {len(initial_iframes)}")
    for i, f in enumerate(initial_iframes):
        log(f"  [{i}] src={f.get_attribute('src')[:80]}")
    
    # Fill form first
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    time.sleep(2)
    
    # Check for new iframes after fill
    iframes_after_fill = page.query_selector_all('iframe')
    log(f"Iframes after fill: {len(iframes_after_fill)}")
    
    # Monitor for dynamically added iframes using JavaScript
    result = page.evaluate("""
        () => {
            // Get all iframes with their src
            var iframes = Array.from(document.querySelectorAll('iframe')).map(f => ({
                src: f.src || '(empty)',
                id: f.id || '',
                class: f.className || '',
                style: f.style.cssText || '',
                data_attr: Object.keys(f.dataset).join(',')
            }));
            
            // Check challenge widget container
            var widget = document.querySelector('[data-testid="challenge-widget-container"]');
            var widgetHTML = widget ? widget.innerHTML.slice(0, 200) : 'not found';
            
            // Check if there's a turnstile API loaded
            var turnstileAPI = typeof window.turnstile !== 'undefined' || 
                               typeof window.cfTurnstile !== 'undefined' ||
                               typeof window.__cfTurnstile !== 'undefined';
            
            // Check for any new script tags
            var scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
            var challengeScripts = scripts.filter(s => s.includes('challenge') || s.includes('turnstile'));
            
            return {
                iframes: iframes,
                widgetHTML: widgetHTML,
                turnstileAPI: turnstileAPI,
                challengeScripts: challengeScripts
            };
        }
    """)
    log(f"Dynamic state: iframes={len(result['iframes'])}, turnstile={result['turnstileAPI']}")
    for iframe in result['iframes']:
        log(f"  iframe: {iframe}")
    if result['challengeScripts']:
        log(f"  Challenge scripts: {result['challengeScripts']}")
    
    # Now wait and monitor - check every 2 seconds for 30 seconds
    log("Monitoring for dynamic iframe for 30s...")
    found_iframe = None
    for sec in range(0, 30, 2):
        current_iframes = page.query_selector_all('iframe')
        for f in current_iframes:
            src = f.get_attribute('src') or ''
            if 'challenge' in src.lower() or 'turnstile' in src.lower() or src.startswith('https://challenges'):
                found_iframe = src
                log(f"FOUND CHALLENGE IFRAME at {sec}s: {src}")
                break
        
        if found_iframe:
            break
        time.sleep(2)
    
    if found_iframe:
        sitekey = get_sitekey_from_iframe_url(found_iframe)
        log(f"Sitekey from iframe: {sitekey}")
        
        if sitekey:
            token = solve_turnstile(sitekey, CF_PAGE)
            if token:
                log("Token received! Injecting into challenge widget...")
                
                # Inject token
                page.evaluate(f"""
                    () => {{
                        var token = '{token}';
                        // Try to find the challenge response input
                        var inputs = document.querySelectorAll('input[name="cf_challenge_response"]');
                        if (inputs.length > 0) {{
                            inputs[0].value = token;
                            inputs[0].setAttribute('value', token);
                            console.log('Token injected into input');
                        }}
                        
                        // Also try to find turnstile API
                        if (window.turnstile) {{
                            console.log('Calling turnstile.callback...');
                            // Try to trigger callback
                        }}
                    }}
                """)
                time.sleep(2)
    
    # Check challenge response before submit
    challenge_val = page.evaluate("() => document.querySelector('input[name=\"cf_challenge_response\"]')?.value || 'empty'")
    log(f"Challenge response: {challenge_val[:30]}")
    
    # Try to submit
    page.click('button[type="submit"]')
    time.sleep(8)
    
    title = page.title()
    url = page.url
    body = page.inner_text('body')
    
    log(f"Result: {title} | {url}")
    if 'dashboard' in title.lower() and 'sign-up' not in url:
        log("SUCCESS!")
    elif 'unable to sign up' in body.lower():
        log("BLOCKED: Unable to sign up")
    else:
        log(f"Body: {body[:300]}")
    
    page.screenshot(path='/tmp/cf_widget_monitor.png')
    browser.close()

log("=== Done ===")