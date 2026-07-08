#!/usr/bin/env python3
"""CF signup - intercept page via route and inject bypass"""
from camoufox import Camoufox
import time, requests

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

BRD_PROXY = {
    'server': 'http://brd.superproxy.io:33335',
    'username': 'brd-customer-hl_c0f6789c-zone-web_unlocker1',
    'password': 'ds3ovbwhs69y'
}

email = f"routetest{int(time.time())}@hilmal.store"
pw = "RouteTest123!"
log(f"Email: {email}")

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context(proxy=BRD_PROXY)
    page = ctx.new_page()
    
    # Route interception - modify response headers to trust MITM cert
    # First, let's try to route through mitmdump on local port
    # But mitmdump doesn't work because of SSL verification
    
    # Alternative: use route to intercept and process the page
    async def handle_route(route):
        req_url = route.request.url
        
        if 'dash.cloudflare.com/sign-up' in req_url:
            log(f"Intercepted: {req_url}")
            
            # Try to fulfill the request
            try:
                response = await route.fetch(timeout=30000)
                log(f"Fetch status: {response.status}")
                
                # Get the HTML
                body = await response.body()
                log(f"Body size: {len(body)}")
                
                # Continue with the route (let browser handle it)
                await route.continue_()
                
            except Exception as e:
                log(f"Fetch error: {e}")
                await route.abort('failed')
        else:
            await route.continue_()
    
    ctx.on('route', handle_route)
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
    time.sleep(5)
    
    title = page.title()
    body = page.inner_text('body')
    
    log(f"Title: {title}")
    log(f"Body preview: {body[:150]}")
    
    if 'dashboard' in title.lower() and 'sign-up' not in page.url:
        log("SUCCESS!")
    elif 'email' in body.lower() and 'password' in body.lower():
        log("Signup form loaded!")
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', pw)
        time.sleep(0.5)
        page.click('button[type="submit"]')
        time.sleep(10)
        
        if 'dashboard' in page.title().lower():
            log("SUCCESS! Account created!")
        else:
            log(f"Result: {page.inner_text('body')[:200]}")
    else:
        log("Challenge or other result")
        page.screenshot(path='/tmp/cf_route.png')
    
    browser.close()

log("=== Done ===")