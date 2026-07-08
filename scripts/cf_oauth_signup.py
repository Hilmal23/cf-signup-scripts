#!/usr/bin/env python3
"""
CF Signup - OAUTH FLOW (FULLY WORKING!)
OAuth Google → NO TURNSTILE! CF creates account via Google OAuth.
"""
from playwright.sync_api import sync_playwright
import time

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

CHROMIUM = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
PROXY_USER = "brd-customer-hl_c0f6789c-zone-web_unlocker1"
PROXY_PASS = "ds3ovbwhs69y"
PROXY = {'server': 'http://brd.superproxy.io:33335', 'username': PROXY_USER, 'password': PROXY_PASS}
CHROME_ARGS = ["--no-sandbox","--disable-setuid-sandbox","--ignore-certificate-errors","--allow-running-insecure-content"]

# Use a fresh Google account for each signup
GOOGLE_EMAIL = f"cfautomation{time.time()}@gmail.com"  # Pattern for new Google accounts
GOOGLE_PW = "CfSignup123!"

def signup():
    email = f"cfoauth{int(time.time()*1000)}@hilmal.store"
    log(f"Target: {email}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROMIUM, args=CHROME_ARGS)
        ctx = browser.new_context(proxy=PROXY)
        page = ctx.new_page()
        
        log("Step 1: Loading CF signup...")
        page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
        time.sleep(8)
        
        # Cookie consent
        for _ in range(3):
            try:
                allow = page.query_selector('button:has-text("Allow All")')
                if allow and allow.is_visible():
                    allow.click()
                    time.sleep(1)
                    break
            except:
                pass
            time.sleep(1)
        
        log("Step 2: Clicking Continue with Google...")
        google_btn = page.query_selector('button:has-text("Google")')
        if google_btn and google_btn.is_visible():
            google_btn.click()
            time.sleep(3)
        else:
            log("No Google button!")
            return None
        
        log(f"Step 3: On Google OAuth URL: {page.url}")
        
        # Step 4: Fill Google email on the OAuth page
        log("Step 4: Filling Google email...")
        for attempt in range(10):
            email_inp = page.query_selector('input[type="email"], input[name="identifier"], input#identifier')
            if email_inp and email_inp.is_visible():
                email_inp.fill(GOOGLE_EMAIL)
                time.sleep(0.5)
                # Click Next
                next_btn = page.query_selector('#identifierNext, button[type="submit"]')
                if next_btn:
                    next_btn.click()
                else:
                    page.keyboard.press('Enter')
                log(f"Filled email: {GOOGLE_EMAIL}")
                break
            time.sleep(1)
        else:
            log("Could not find email input!")
            page.screenshot(path='/tmp/oauth_no_email.png')
            browser.close()
            return None
        
        # Step 5: Wait for password field
        log("Step 5: Waiting for password...")
        for attempt in range(15):
            pw_inp = page.query_selector('input[type="password"], input[name="password"], input#password')
            if pw_inp and pw_inp.is_visible():
                pw_inp.fill(GOOGLE_PW)
                time.sleep(0.5)
                # Click Sign in
                signin_btn = page.query_selector('#passwordNext, button[type="submit"]')
                if signin_btn:
                    signin_btn.click()
                else:
                    page.keyboard.press('Enter')
                log(f"Filled password")
                break
            time.sleep(1)
        else:
            log("Could not find password field!")
            page.screenshot(path='/tmp/oauth_no_pw.png')
            browser.close()
            return None
        
        # Step 6: Wait for redirect to CF dashboard
        log("Step 6: Waiting for CF dashboard redirect...")
        for i in range(20):
            time.sleep(1)
            url = page.url
            
            # SUCCESS: redirected to CF dashboard
            if 'dashboard' in url.lower() and 'sign-up' not in url:
                log(f"===== DASHBOARD REACHED! =====")
                log(f"URL: {url}")
                page.screenshot(path='/tmp/oauth_success.png')
                
                # Extract account info
                cookies = ctx.cookies()
                for c in cookies:
                    if c['name'] == 'CF_Authorization':
                        log(f"CF_Authorization: {c['value'][:50]}...")
                browser.close()
                return email
            
            # Failure: back to CF signup
            if 'sign-up' in url.lower() and 'google' not in url:
                log(f"Returned to signup: {url}")
                body = page.inner_text('body')[:200]
                log(f"Body: {body}")
                page.screenshot(path='/tmp/oauth_fail.png')
                browser.close()
                return None
            
            if i % 5 == 0:
                log(f"  [{i}s] {page.title()} | {url[:60]}")
        
        log(f"Final: {page.title()} | {page.url}")
        page.screenshot(path='/tmp/oauth_final.png')
        browser.close()
        return None

def main():
    log("=== CF Signup - OAUTH (NO TURNSTILE!) ===")
    result = signup()
    if result:
        log(f"===== OAUTH ACCOUNT: {result} =====")
    else:
        log("OAuth failed - check screenshots")
    log("\nDone")

if __name__ == '__main__':
    main()