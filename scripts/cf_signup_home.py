#!/usr/bin/env python3
"""CF Signup Test - Run from YOUR machine (home IP)"""
import sys
import os
import time
import random

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed")
        print("Run: pip install playwright && playwright install chromium")
        return

    log("Starting CF signup test from YOUR network...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Show browser
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = context.new_page()
        
        log("Navigating to CF signup...")
        page.goto('https://dash.cloudflare.com/sign-up', timeout=60000)
        
        # Wait for potential challenge
        log(f"Page title: {page.title()}")
        log(f"Page URL: {page.url}")
        
        # Check for challenge
        title = page.title()
        if title == "Just a moment...":
            log("Challenge detected! Waiting for resolution...")
            try:
                page.wait_for_url(lambda u: 'sign-up' in u and 'cloudflare' in u, timeout=120)
                log(f"Challenge passed! URL: {page.url}")
            except:
                log("Challenge did NOT resolve in 120s")
                browser.close()
                return
        
        # Wait for form
        time.sleep(5)
        log(f"Title after wait: {page.title()}")
        log(f"URL: {page.url}")
        
        browser.close()
        log("Test complete!")

if __name__ == '__main__':
    main()