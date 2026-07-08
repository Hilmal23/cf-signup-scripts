#!/usr/bin/env python3
"""
CF Signup - FREE Turnstile Bypass via Camoufox
Key insight: disable_coop=True allows clicking Turnstile cross-origin iframe elements!
This means we can potentially bypass Turnstile WITHOUT any solver.
"""
from camoufox import Camoufox
import time, re, json, os

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

EMAIL = f"cf{int(time.time()*1000)}@hilmal.store"
PW = "CfSignup123!"

def get_security_token(page):
    el = page.query_selector('input[name="security_token"]')
    return el.get_attribute('value') or '' if el else ''

def signup():
    log(f"Email: {EMAIL}")
    log("Browser: Camoufox Firefox (with disable_coop=True)")
    
    with Camoufox(
        headless=True,
        geoip=True,  # Auto-detect IP-based geolocation
        disable_coop=True,  # KEY: allows clicking Turnstile iframe checkbox!
        i_know_what_im_doing=True,  # Allow all configs
        debug=False,
    ) as browser:
        ctx = browser.new_context()
        page = ctx.new_page()
        
        log("Loading CF signup...")
        page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
        time.sleep(8)
        
        log(f"Title: {page.title()}")
        log(f"URL: {page.url}")
        
        # Dismiss cookie consent
        for _ in range(5):
            try:
                allow = page.query_selector('button:has-text("Allow All")')
                if allow and allow.is_visible():
                    allow.click()
                    time.sleep(1)
                    log("Cookie dismissed")
            except:
                pass
            time.sleep(1)
        
        # Check for Turnstile challenge
        body = page.inner_text('body')
        has_challenge = 'let us know' in body.lower()
        log(f"Turnstile challenge: {has_challenge}")
        
        if has_challenge:
            # Try to find and click Turnstile iframe checkbox
            log("Looking for Turnstile iframe...")
            
            # The Turnstile iframe has src with "challenge" or "turnstile"
            ts_iframe = None
            for iframe in page.query_selector_all('iframe'):
                src = iframe.get_attribute('src') or ''
                if 'challenge' in src.lower() or 'turnstile' in src.lower():
                    ts_iframe = iframe
                    log(f"Found Turnstile iframe: {src[:100]}")
                    break
            
            if ts_iframe:
                try:
                    # Try to click the iframe checkbox directly
                    # With disable_coop=True, cross-origin iframe clicks should work
                    frame = page.frame_locator(iframe.get_attribute('id') or src)
                    checkbox = frame.query_selector('input[type="checkbox"]')
                    if checkbox:
                        log("Clicking Turnstile checkbox...")
                        checkbox.click()
                        time.sleep(3)
                        log("Checkbox clicked!")
                    else:
                        log("No checkbox found in iframe")
                except Exception as e:
                    log(f"Iframe click error: {e}")
            
            # Also check for the "Verify" button or challenge UI
            for btn_txt in ['Verify', 'Verify now', 'Next', 'Check']:
                btn = page.query_selector(f'button:has-text("{btn_txt}")')
                if btn and btn.is_visible():
                    log(f"Found '{btn_txt}' button, clicking...")
                    btn.click()
                    time.sleep(3)
                    break
            
            # Wait for challenge to clear
            for i in range(10):
                body = page.inner_text('body')
                if 'let us know' not in body.lower():
                    log(f"Challenge resolved after {i*2}s!")
                    break
                time.sleep(2)
                log(f"Waiting... ({i+1}/10)")
        
        # Check for email input
        email_inp = page.query_selector('input[name="email"]')
        if not email_inp or not email_inp.is_visible():
            log("NO email input!")
            page.screenshot(path='/tmp/cf_cf_challenge.png')
            browser.close()
            return
        
        log("Form found, filling...")
        email_inp.fill(EMAIL)
        time.sleep(0.3)
        
        pw_inp = page.query_selector('input[name="password"]')
        pw_inp.fill(PW)
        time.sleep(0.3)
        
        sec = get_security_token(page)
        log(f"Security token: {sec[:30]}...")
        
        # Capture API request
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
        
        log(f"After submit: {page.title()} | {page.url}")
        
        if captured_req[0]:
            try:
                body = json.loads(captured_req[0].post_data or '{}')
                log(f"cf_challenge_response: '{body.get('cf_challenge_response', 'EMPTY')[:60] if body.get('cf_challenge_response') else 'EMPTY'}'")
            except:
                log(f"Body: {captured_req[0].post_data[:200]}")
        
        if captured_res[0]:
            log(f"API status: {captured_res[0].status}")
            try:
                log(f"Response: {json.dumps(captured_res[0].json(), indent=2)}")
            except:
                log(f"Response: {captured_res[0].text[:300]}")
        
        page.screenshot(path='/tmp/cf_final.png')
        log("Screenshot: /tmp/cf_final.png")
        
        browser.close()

def main():
    log("=== CF Signup FREE Bypass (Camoufox + disable_coop) ===")
    signup()
    log("\n=== Done ===")

if __name__ == '__main__':
    main()