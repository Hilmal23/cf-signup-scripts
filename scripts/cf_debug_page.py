#!/usr/bin/env python3
"""CF Signup - debug page content"""
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
        
        # Save screenshot first thing
        page.screenshot(path='/tmp/cf_debug.png', full_page=False)
        print('Screenshot: /tmp/cf_debug.png')
        
        # Check title vs actual content
        body_text = page.evaluate("() => document.body.innerText.slice(0, 500)")
        print(f'Body text: {body_text[:300]}')
        
        # Get ALL interactive elements
        all_btns = page.query_selector_all('button')
        all_inps = page.query_selector_all('input')
        all_links = page.query_selector_all('a')
        all_forms = page.query_selector_all('form')
        
        print(f'\nElements: {len(all_btns)} buttons, {len(all_inps)} inputs, {len(all_links)} links, {len(all_forms)} forms')
        
        print('\nButtons:')
        for b in all_btns:
            txt = b.inner_text().strip()
            if txt:
                print(f'  [{txt[:50]}]')
        
        print('\nForms:')
        for f in all_forms:
            action = f.get_attribute('action') or 'no-action'
            method = f.get_attribute('method') or 'no-method'
            print(f'  action={action} method={method}')
            ins = f.query_selector_all('input')
            for inp in ins:
                n = inp.get_attribute('name') or ''
                t = inp.get_attribute('type') or 'text'
                p = inp.get_attribute('placeholder') or ''
                print(f'    input: name={n} type={t} ph={p[:20]}')
        
        print(f'\nURL: {page.url}')
        print(f'Title: {page.title()}')
        
        # Check for any visible form
        visible_inputs = [i for i in all_inps if i.is_visible()]
        print(f'Visible inputs: {len(visible_inputs)}')
        
        # Check if page has body at all
        body_html = page.evaluate("() => document.body.innerHTML.slice(0, 300)")
        print(f'Body HTML: {body_html[:200]}')
        
        browser.close()

main()