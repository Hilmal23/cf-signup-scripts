#!/usr/bin/env python3
"""Extract Turnstile sitekey from CF page JS context"""
from playwright.sync_api import sync_playwright
import time, re

def main():
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
        time.sleep(10)
        
        # Screenshot
        page.screenshot(path='/tmp/cf_challenge.png')
        print('Screenshot: /tmp/cf_challenge.png')
        
        # Extract ALL sitekeys from page context
        sitekeys = page.evaluate("""
            () => {
                const results = [];
                // Check window objects
                for (const [k, v] of Object.entries(window)) {
                    if (k.toLowerCase().includes('turnstile') || k.toLowerCase().includes('cf_challenge')) {
                        results.push(`window.${k}: ${JSON.stringify(v)}`);
                    }
                }
                // Check data attributes
                document.querySelectorAll('[data-sitekey]').forEach(el => {
                    results.push(`data-sitekey: ${el.getAttribute('data-sitekey')}`);
                });
                // Check iframe src attributes
                document.querySelectorAll('iframe[src*="turnstile"]').forEach(el => {
                    results.push(`turnstile iframe: ${el.getAttribute('src')}`);
                });
                // Check meta tags
                document.querySelectorAll('meta[name*="cf"], meta[name*="turnstile"], meta[name*="challenge"]').forEach(el => {
                    results.push(`meta: ${el.getAttribute('name')}: ${el.getAttribute('content')}`);
                });
                // Check script tags for sitekey
                document.querySelectorAll('script').forEach(s => {
                    const src = s.src || '';
                    if (src.includes('api.js') || src.includes('turnstile')) {
                        results.push(`script: ${src}`);
                    }
                });
                // Check for Turnstile global
                if (typeof window.turnstile !== 'undefined') {
                    results.push(`turnstile object: ${JSON.stringify(window.turnstile)}`);
                }
                if (typeof window.cfTurnstile !== 'undefined') {
                    results.push(`cfTurnstile: ${JSON.stringify(window.cfTurnstile)}`);
                }
                return results;
            }
        """)
        
        print(f'\nFound {len(sitekeys)} items:')
        for item in sitekeys:
            print(f'  {item[:150]}')
        
        # Try to find the sitekey by searching network responses
        def on_response(resp):
            if 'turnstile' in resp.url.lower() or 'challenge' in resp.url.lower():
                print(f'Challenge URL: {resp.url[:100]}')
                if resp.status == 200 and 'javascript' in resp.headers.get('content-type', ''):
                    try:
                        body = resp.text()
                        sk = re.findall(r'["\']sitekey["\'][:\s]+["\']([a-zA-Z0-9_-]{20,})["\']', body)
                        if sk:
                            print(f'  SITEKEY FOUND: {sk[0]}')
                    except:
                        pass
        
        page.on('response', on_response)
        
        # Reload to capture network
        page.reload()
        time.sleep(8)
        
        # Try JS evaluation for challenge container
        challenge_div = page.query_selector('[data-testid="challenge-widget-container"]')
        if challenge_div:
            print(f'\nChallenge container: {challenge_div.get_attribute("class")}')
            inner = page.evaluate("() => document.querySelector('[data-testid=\"challenge-widget-container\"]')?.innerHTML?.slice(0, 200)")
            print(f'Inner: {inner}')
        
        # Try to find the Turnstile widget iframe
        ts_iframe = page.query_selector('iframe[src*="challenge"]')
        if ts_iframe:
            src = ts_iframe.get_attribute('src')
            print(f'\nChallenge iframe: {src[:120]}')
            m = re.search(r'sitekey=([^&"]+)', src)
            if m:
                print(f'SITEKEY: {m.group(1)}')
        
        # Try looking for the widget in the HTML near "Let us know you are human"
        human_text = page.evaluate("""
            () => {
                const all = document.querySelectorAll('*');
                for (const el of all) {
                    if (el.textContent.includes('Let us know you are human')) {
                        const parent = el.closest('[class]');
                        if (parent) {
                            return parent.innerHTML.slice(0, 500);
                        }
                    }
                }
                return 'not found';
            }
        """)
        print(f'\nHuman text container: {human_text[:300]}')
        
        browser.close()

main()