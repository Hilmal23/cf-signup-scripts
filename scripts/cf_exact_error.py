#!/usr/bin/env python3
"""CF signup - capture exact error on failed submit"""
from camoufox import Camoufox
import time, json

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

email = f"exacttest{int(time.time())}@hilmal.store"
pw = "ExactTest123!"
log(f"Email: {email}")

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=30000)
    time.sleep(3)
    
    # Fill form
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    
    # Intercept ALL responses via CDP
    responses = []
    failed_reqs = []
    
    # Intercept via route
    async def handle_route(route):
        url = route.request.url
        log(f"ROUTE: {route.request.method} {url[:80]}")
        await route.continue_()
    
    ctx.on('route', handle_route)
    
    # Monitor network failures
    def on_request_failed(request):
        if 'cloudflare' in request.url:
            failed_reqs.append(request.url)
            log(f"FAILED: {request.url[:80]}")
    
    # Submit
    page.click('button[type="submit"]')
    time.sleep(8)
    
    # Get error messages on page
    error_elements = page.query_selector_all('[role="alert"], .error, .text-red, [class*="error"], [class*="warning"], [class*="invalid"]')
    for el in error_elements:
        text = el.inner_text().strip()
        if text:
            log(f"ERROR element: {text[:100]}")
    
    # Check all form fields for error states
    inputs = page.query_selector_all('input')
    for inp in inputs:
        cls = inp.get_attribute('class') or ''
        aria = inp.get_attribute('aria-invalid') or ''
        aria_msg = inp.get_attribute('aria-errormessage') or ''
        if 'error' in cls.lower() or aria == 'true' or aria_msg:
            log(f"Input error: class={cls} aria-invalid={aria} msg={aria_msg}")
    
    # Check page content for error text
    body = page.inner_text('body')
    # Look for error-related text
    import re
    error_patterns = [
        r'unable to sign up',
        r'cannot sign up',
        r'verify you are human',
        r'challenge',
        r'complete the verification',
        r'captcha',
        r'blocked',
        r'denied',
    ]
    for pat in error_patterns:
        matches = re.findall(rf'.{{0,50}}{pat}.{{0,50}}', body, re.I)
        if matches:
            for m in matches:
                log(f"MATCH [{pat}]: {m.strip()}")
    
    # Also check for any toasts/notifications
    toasts = page.query_selector_all('[class*="toast"], [class*="notification"], [class*="alert"]')
    for t in toasts:
        log(f"Toast: {t.inner_text()[:100]}")
    
    page.screenshot(path='/tmp/cf_exact_error.png')
    log("Screenshot saved!")
    
    browser.close()