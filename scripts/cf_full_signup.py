#!/usr/bin/env python3
"""CF Signup Full Test - signup + find sitekey + screenshot"""
from playwright.sync_api import sync_playwright
import time, re, json

def main():
    email_val = f'test{round(time.time())}@hilmal.store'
    print(f'Email: {email_val}')
    
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
        page.set_viewport_size({'width': 1280, 'height': 900})
        
        page.goto('https://dash.cloudflare.com/sign-up', timeout=60000)
        time.sleep(8)
        
        print(f'Title: {page.title()}')
        print(f'URL: {page.url}')
        
        # Cookie consent - dismiss it
        for _ in range(3):
            btns = page.query_selector_all('button')
            for btn in btns:
                txt = btn.inner_text().strip()
                if 'allow all' in txt.lower():
                    btn.click()
                    time.sleep(1)
                    break
            time.sleep(1)
        
        # Find ALL inputs
        all_inputs = page.query_selector_all('input')
        print(f'\nTotal inputs: {len(all_inputs)}')
        for inp in all_inputs:
            name = inp.get_attribute('name') or ''
            type_ = inp.get_attribute('type') or 'text'
            ph = inp.get_attribute('placeholder') or ''
            vis = inp.is_visible()
            print(f'  name={name} type={type_} ph={ph[:20]} visible={vis}')
        
        # Screenshot
        page.screenshot(path='/tmp/cf_signup_page.png', full_page=False)
        print('\nScreenshot: /tmp/cf_signup_page.png')
        
        # Check for Turnstile widget
        ts_iframe = page.query_selector('iframe[src*="turnstile"]')
        print(f'\nTurnstile iframe: {ts_iframe is not None}')
        if ts_iframe:
            src = ts_iframe.get_attribute('src') or ''
            m = re.search(r'sitekey=([^&"]+)', src)
            print(f'Sitekey: {m.group(1) if m else "none"}')
        
        # Try to find email input with ANY method
        email_inp = page.query_selector('input[name="email"]')
        if email_inp:
            print(f'\nEmail input found! visible={email_inp.is_visible()}')
            email_inp.fill(email_val)
            time.sleep(0.5)
            
            pw_inp = page.query_selector('input[name="password"]')
            if pw_inp:
                pw_inp.fill('TestPass123!')
                time.sleep(0.5)
                
                # Get sec token
                sec = page.evaluate("() => document.querySelector('input[name=\"security_token\"]')?.value || ''")
                print(f'Sec token: {sec[:30]}...')
                
                # Submit
                btn = page.query_selector('button[type="submit"]')
                if btn:
                    print('Clicking submit...')
                    btn.click()
                    time.sleep(10)
                    
                    print(f'After - Title: {page.title()}')
                    print(f'After - URL: {page.url}')
                    
                    # Check URL for verification redirect
                    if 'verify' in page.url.lower():
                        print('VERIFICATION NEEDED - Email verification will be sent')
                        # Save screenshot
                        page.screenshot(path='/tmp/cf_verify_page.png')
                        print('Verify page screenshot saved')
        
        browser.close()
    print('\nDone!')

main()