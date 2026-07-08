#!/usr/bin/env python3
"""
CF Signup - OAUTH FLOW v2 (debug + fix)
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

GOOGLE_EMAIL = f"cfautomation{int(time.time())}@gmail.com"
GOOGLE_PW = "CfSignup123!"

def signup():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROMIUM, args=CHROME_ARGS)
        ctx = browser.new_context(proxy=PROXY)
        page = ctx.new_page()
        
        page.goto("https://dash.cloudflare.com/sign-up", timeout=60000)
        time.sleep(8)
        
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
        
        google_btn = page.query_selector('button:has-text("Google")')
        if google_btn and google_btn.is_visible():
            google_btn.click()
            time.sleep(3)
        
        log(f"OAuth URL: {page.url}")
        
        # Fill email
        for attempt in range(10):
            email_inp = page.query_selector('input[type="email"], input[name="identifier"], input#identifier')
            if email_inp and email_inp.is_visible():
                email_inp.fill(GOOGLE_EMAIL)
                time.sleep(0.5)
                page.keyboard.press('Enter')
                log(f"Filled: {GOOGLE_EMAIL}")
                break
            time.sleep(1)
        else:
            log("No email input")
            browser.close()
            return
        
        # Wait after submit, then check what's on page
        time.sleep(3)
        log(f"After email: {page.url}")
        log(f"Title: {page.title()}")
        
        # Take screenshot to see the page
        page.screenshot(path='/tmp/oauth_after_email.png')
        
        # Debug: show all inputs visible
        inputs = page.query_selector_all('input')
        log(f"All inputs visible ({len(inputs)}):")
        for inp in inputs:
            try:
                t = inp.get_attribute('type') or 'text'
                n = inp.get_attribute('name') or ''
                i = inp.get_attribute('id') or ''
                ar = inp.get_attribute('aria-label') or ''
                vis = inp.is_visible()
                if vis:
                    log(f"  [{t}] name={n} id={i} aria={ar}")
            except:
                pass
        
        # Wait more for password
        for i in range(15):
            pw_inp = page.query_selector('input[type="password"]')
            if pw_inp and pw_inp.is_visible():
                log("Password field appeared!")
                pw_inp.fill(GOOGLE_PW)
                time.sleep(0.5)
                page.keyboard.press('Enter')
                break
            # Check for error messages
            body = page.inner_text('body')
            if 'couldn\'t find' in body.lower() or 'not a valid' in body.lower() or 'could not' in body.lower():
                log(f"ERROR on page: {body[:200]}")
                break
            time.sleep(1)
        
        # Final state
        time.sleep(5)
        log(f"Final: {page.title()} | {page.url}")
        page.screenshot(path='/tmp/oauth_final.png')
        browser.close()

if __name__ == '__main__':
    signup()