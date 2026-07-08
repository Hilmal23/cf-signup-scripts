#!/usr/bin/env python3
"""CF Signup Test - find Turnstile sitekey"""
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
        page.goto('https://dash.cloudflare.com/sign-up', timeout=60000)
        time.sleep(8)
        
        # Check for Turnstile sitekey
        sitekey = None
        scripts = page.query_selector_all('script[src*="turnstile"]')
        for s in scripts:
            src = s.get_attribute('src')
            m = re.search(r'sitekey=([^&"]+)', src)
            if m:
                sitekey = m.group(1)
        
        ts_widget = page.query_selector('[data-sitekey]')
        if ts_widget and not sitekey:
            sitekey = ts_widget.get_attribute('data-sitekey')
        
        print(f'Sitekey: {sitekey}')
        
        # Check iframe
        ts_iframe = page.query_selector('iframe[src*="turnstile"]')
        if ts_iframe:
            src = ts_iframe.get_attribute('src')
            m = re.search(r'sitekey=([^&"]+)', src)
            if m:
                sitekey = m.group(1)
                print(f'Sitekey from iframe: {sitekey}')
        
        print(f'Title: {page.title()}')
        
        # All inputs
        inputs = page.query_selector_all('input')
        for inp in inputs:
            name = inp.get_attribute('name') or ''
            type_ = inp.get_attribute('type') or ''
            if type_ in ['email', 'password', 'text', 'hidden']:
                print(f'  input: name={name} type={type_}')
        
        # Check URL params for sitekey
        url = page.url
        m = re.search(r'sitekey=([^&]+)', url)
        if m:
            print(f'Sitekey from URL: {m.group(1)}')
        
        browser.close()

main()