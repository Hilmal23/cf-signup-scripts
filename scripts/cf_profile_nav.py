#!/usr/bin/env python3
"""Find profile menu and click through to API tokens"""
from camoufox import Camoufox
import time

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

with Camoufox(headless=True, humanize=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    email = f"test{time.time()}@hilmal.store"
    pw = "TestPass123!"
    
    # Signup
    page.goto("https://dash.cloudflare.com/sign-up", timeout=45000)
    time.sleep(4)
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    page.click('button[type="submit"]')
    time.sleep(5)
    log(f"After signup: {page.url} | {page.title()}")
    
    # Look for header/nav links
    nav_links = page.query_selector_all('a[href*="profile"], a[href*="account"], a[href*="user"], a[href*="setting"]')
    log(f"Nav links found: {len(nav_links)}")
    for link in nav_links:
        href = link.get_attribute('href') or ''
        text = link.inner_text()[:30]
        log(f"  {text} -> {href}")
    
    # Look for button with account/settings text
    buttons = page.query_selector_all('button')
    log(f"Buttons found: {len(buttons)}")
    for btn in buttons:
        text = btn.inner_text()[:30]
        attrs = btn.get_attribute('class') or ''
        if any(x in text.lower() + attrs.lower() for x in ['account', 'profile', 'user', 'setting']):
            log(f"  [MATCH] {text} | {attrs[:50]}")
    
    # Look for any clickable div in header
    header = page.query_selector('header')
    if header:
        header_links = header.query_selector_all('a, button')
        log(f"Header elements: {len(header_links)}")
        for el in header_links[:20]:
            text = el.inner_text()[:30]
            href = el.get_attribute('href') or ''
            log(f"  {text} -> {href}")
    
    # Look for avatar/icon in header
    avatar = page.query_selector('[class*="avatar"], [class*="user"], [class*="account"]')
    if avatar:
        log(f"Avatar found: {avatar.get_attribute('class')}")
        # Click it
        try:
            avatar.click()
            time.sleep(3)
            log(f"Avatar clicked: {page.url} | {page.title()}")
            dropdown = page.inner_text('body')[:1000]
            log(f"Dropdown: {dropdown}")
        except Exception as e:
            log(f"Avatar click failed: {e}")
    
    # Get ALL clickable elements
    all_clickable = page.query_selector_all('a, button, [role="button"], [onclick], [class*="clickable"]')
    log(f"Total clickable: {len(all_clickable)}")
    
    # Look for the API tokens link pattern
    api_patterns = ['api-tokens', 'api_token', 'api token', 'tokens', 'token']
    for el in all_clickable:
        text = el.inner_text().lower()
        href = (el.get_attribute('href') or '').lower()
        if any(p in text or p in href for p in api_patterns):
            log(f"[API LINK] {el.inner_text()[:30]} -> {el.get_attribute('href')}")
    
    page.screenshot(path='/tmp/cf_dashboard.png')
    log("Screenshot!")
    
    browser.close()