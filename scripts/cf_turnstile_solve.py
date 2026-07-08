#!/usr/bin/env python3
"""CF Turnstile Solver - solve + inject + signup"""
from playwright.sync_api import sync_playwright
import time, requests, json

TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
SITEKEY = "8732e7fe-bf77-5ee5-bb3f-f2004f0769ae"
PAGE_URL = "https://dash.cloudflare.com/sign-up"

def solve_turnstile(sitekey, pageurl):
    url = f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={pageurl}&sitekey={sitekey}&json=1"
    r = requests.get(url, timeout=10)
    result = r.json()
    
    if result.get('status') != 1:
        print(f"Submit failed: {result}")
        return None
    
    job_id = result.get('request')
    print(f"Job submitted: {job_id}")
    
    for i in range(60):
        time.sleep(3)
        check = f"http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={job_id}&json=1"
        r = requests.get(check, timeout=10)
        res = r.json()
        
        if res.get('status') == 1:
            token = res.get('request')
            print(f"Solved! Token: {token[:40]}...")
            return token
        elif 'NOT_READY' in str(res):
            print(f"Waiting... ({i+1}/60)")
        else:
            print(f"Error: {res}")
            return None
    return None

def main():
    email_val = f'test{round(time.time())}@hilmal.store'
    print(f'Testing signup: {email_val}')
    
    # Step 1: Solve Turnstile
    token = solve_turnstile(SITEKEY, PAGE_URL)
    if not token:
        print("Solved failed!")
        return
    
    print(f"\nToken obtained: {token[:50]}...")
    
    # Step 2: Browser signup with token injected
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path='/snap/chromium/3483/usr/lib/chromium-browser/chrome',
            args=['--no-sandbox', '--disable-setuid-sandbox', '--ignore-certificate-errors',
                  '--allow-running-insecure-content', '--ignore-certificate-errors-spki-list=*']
        )
        ctx = browser.new_context(
            proxy={'server': 'http://brd.superproxy.io:33335',
                   'username': 'brd-customer-hl_c0f6789c-zone-web_unlocker1',
                   'password': 'ds3ovbwhs69y'}
        )
        page = ctx.new_page()
        page.goto(PAGE_URL, timeout=60000)
        time.sleep(8)
        
        # Screenshot before
        page.screenshot(path='/tmp/cf_before.png')
        
        # Inject token BEFORE filling form
        page.evaluate(f"""
            () => {{
                // Find and fill Turnstile token
                var turnstileInput = document.querySelector('input[name*="turnstile"], input[name*="cf-turnstile"], input[name*="challenge"]');
                if (turnstileInput) {{
                    turnstileInput.value = '{token}';
                    console.log('Token injected into input:', turnstileInput.name);
                }} else {{
                    console.log('No turnstile input found');
                }}
                // Also try to call turnstile API directly
                if (typeof window.turnstile !== 'undefined') {{
                    window.turnstile.callback = window.turnstile.callback || [];
                    window.turnstile.callback.push(function(e) {{ console.log('Callback', e); }});
                }}
            }}
        """)
        time.sleep(2)
        
        # Fill email + password
        email_inp = page.query_selector('input[name="email"]')
        if email_inp:
            email_inp.fill(email_val)
            time.sleep(0.5)
        else:
            print("NO EMAIL INPUT!")
            page.screenshot(path='/tmp/cf_no_email.png')
        
        pw_inp = page.query_selector('input[name="password"]')
        if pw_inp:
            pw_inp.fill('TestPass123!')
            time.sleep(0.5)
        
        # Submit
        btn = page.query_selector('button[type="submit"]')
        if btn:
            print("Submitting...")
            btn.click()
            time.sleep(10)
        
        print(f'\nAfter - Title: {page.title()}')
        print(f'After - URL: {page.url}')
        
        # Screenshot after
        page.screenshot(path='/tmp/cf_after.png')
        
        # Check for email verification
        if 'verify' in page.url.lower() or 'verify' in page.title().lower():
            print("VERIFICATION EMAIL NEEDED!")
        
        browser.close()

if __name__ == '__main__':
    main()