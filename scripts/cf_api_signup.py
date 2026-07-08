#!/usr/bin/env python3
"""CF signup via direct API + browser for CAPTCHA"""
from camoufox import Camoufox
import time, re, requests, json

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# Test direct API signup
log("=== Test CF API signup ===")
email = f"apitest{int(time.time())}@hilmal.store"
pw = "Apitest123!"

# First, get the security token from the page
with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=30000)
    time.sleep(3)
    
    # Extract all hidden form fields
    inputs = page.query_selector_all('input')
    form_data = {}
    for inp in inputs:
        name = inp.get_attribute('name') or ''
        type_ = inp.get_attribute('type') or 'text'
        value = inp.get_attribute('value') or ''
        if type_ == 'hidden' and name:
            form_data[name] = value
            log(f"Hidden: {name} = {value[:30]}")
    
    browser.close()

# Try POST to CF API
log("=== Try API signup ===")
api_url = "https://dash.cloudflare.com/api/v1/signup"
data = {
    'email': email,
    'password': pw,
    'username': email.split('@')[0],
}
log(f"POST to {api_url}")
log(f"Data: {data}")

try:
    r = requests.post(api_url, data=data, timeout=10)
    log(f"Response: {r.status_code} | {r.text[:300]}")
except Exception as e:
    log(f"API error: {e}")

# Try CF client API
log("=== Try CF client v4 API ===")
try:
    r = requests.post(
        "https://api.cloudflare.com/client/v4/signup",
        headers={'Content-Type': 'application/json'},
        json={'email': email, 'password': pw},
        timeout=10
    )
    log(f"Response: {r.status_code} | {r.text[:300]}")
except Exception as e:
    log(f"API v4 error: {e}")

# Try alternative signup URL
log("=== Try alternative URLs ===")
alt_urls = [
    "https://dash.cloudflare.com/sign-up/email",
    "https://cloudflare.com/signup",
    "https://dash.cloudflare.com/join",
]
for url in alt_urls:
    try:
        r = requests.get(url, timeout=10, allow_redirects=False)
        log(f"{url}: {r.status_code}")
    except Exception as e:
        log(f"{url}: ERROR {e}")

# The real approach: use browser to navigate, extract challenge params, solve, inject
log("=== Final: Extract challenge + solve ===")
with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=30000)
    time.sleep(3)
    
    # Try to access CF challenge iframe directly
    result = page.evaluate("""
        () => {
            // Check the challenge widget shadow DOM
            var widget = document.querySelector('[data-testid="challenge-widget-container"]');
            if (!widget) return 'No widget';
            
            // Shadow DOM check
            var shadow = widget.shadowRoot || widget;
            var innerHTML = shadow.innerHTML || widget.innerHTML;
            
            // Look for all iframes in shadow DOM
            var iframes = shadow.querySelectorAll ? shadow.querySelectorAll('iframe') : [];
            
            // Try to get the challenge API URL
            var scripts = Array.from(document.querySelectorAll('script[src*="challenge"]'));
            var challengeUrls = scripts.map(s => s.src);
            
            // Try to find the sitekey in page context
            var cfState = window.__cfState__ || window.__NEXT_DATA__ || {};
            
            return {
                innerHTML: innerHTML.slice(0, 300),
                iframeCount: iframes.length,
                challengeUrls: challengeUrls,
                widgetClass: widget.className,
                shadowRoot: !!widget.shadowRoot
            };
        }
    """)
    log(f"Challenge state: {result}")
    
    browser.close()