#!/usr/bin/env python3
"""CF Signup - BD bypassed challenge, now fill+submit with clearance cookie"""
from playwright.sync_api import sync_playwright
import time

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

email = f"cf{int(time.time())}@hilmal.store"
pw = "CfSignup123!"
log(f"Email: {email}")

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path="/snap/chromium/current/usr/lib/chromium-browser/chrome",
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--ignore-certificate-errors",
            "--allow-running-insecure-content",
            "--ignore-certificate-errors-spki-list=*",
        ]
    )
    ctx = browser.new_context(
        proxy={"server": "http://brd.superproxy.io:33335", "username": "brd-customer-hl_c0f6789c-zone-web_unlocker1", "password": "ds3ovbwhs69y"},
    )
    page = ctx.new_page()
    
    log("Loading page via BD...")
    page.goto("https://dash.cloudflare.com/sign-up", timeout=90000)
    time.sleep(8)
    
    title = page.title()
    url = page.url
    log(f"Title: {title}")
    log(f"URL: {url}")
    
    # Get cookies
    cookies = ctx.cookies()
    cf_clearance = next((c['value'] for c in cookies if c['name'] == 'cf_clearance'), None)
    cf_v = next((c['value'] for c in cookies if c['name'] == 'cf_v'), None)
    log(f"cf_clearance: {cf_clearance[:30] if cf_clearance else 'NONE'}...")
    log(f"cf_v: {cf_v}")
    
    # Check page content via evaluate (try harder)
    page_text = page.evaluate("""
        () => {
            // Try multiple ways to get text
            let text = '';
            try { text = document.body.innerText; } catch(e) {}
            if (!text || text.length < 10) {
                try { text = document.documentElement.textContent; } catch(e) {}
            }
            if (!text || text.length < 10) {
                try { text = document.body.textContent; } catch(e) {}
            }
            return {
                text: text ? text.substring(0, 500) : 'EMPTY',
                inputs: Array.from(document.querySelectorAll('input')).map(i => ({
                    name: i.name, type: i.type, id: i.id, placeholder: i.placeholder, value: i.value
                })),
                buttons: Array.from(document.querySelectorAll('button')).map(b => ({
                    type: b.type, text: b.textContent ? b.textContent.trim() : ''
                })),
                hasEmail: !!document.querySelector('input[name="email"], input[type="email"]'),
                hasPassword: !!document.querySelector('input[name="password"], input[type="password"]'),
            };
        }
    """)
    
    log(f"Page text: {page_text['text'][:300]}")
    log(f"Inputs: {page_text['inputs']}")
    log(f"Buttons: {page_text['buttons']}")
    log(f"Has email: {page_text['hasEmail']}")
    log(f"Has password: {page_text['hasPassword']}")
    
    # Find and fill
    email_input = page.query_selector('input[name="email"], input[type="email"]')
    pw_input = page.query_selector('input[name="password"], input[type="password"]')
    submit_btn = page.query_selector('button[type="submit"]')
    
    if email_input:
        email_input.fill(email)
        log("Email filled!")
    else:
        # Try by placeholder
        all_inputs = page.query_selector_all('input')
        for inp in all_inputs:
            ph = inp.get_attribute('placeholder') or ''
            if 'email' in ph.lower() or 'e-mail' in ph.lower():
                inp.fill(email)
                log(f"Email filled via placeholder: {ph}")
                break
    
    if pw_input:
        pw_input.fill(pw)
        log("Password filled!")
    
    time.sleep(1)
    
    # Click submit
    if submit_btn:
        submit_btn.click()
        log("Submit clicked!")
    else:
        page.click('button[type="submit"]')
        log("Submit clicked via selector!")
    
    time.sleep(12)
    
    log(f"After - Title: {page.title()}")
    log(f"After - URL: {page.url}")
    body2 = page.evaluate("() => document.body ? document.body.innerText.substring(0, 300) : ''")
    log(f"After body: {body2[:300]}")
    
    if "dashboard" in page.title().lower():
        log("SUCCESS! Account created!")
        page.screenshot(path='/tmp/cf_success.png')
    elif "verify" in body2.lower():
        log("Email verification page!")
        page.screenshot(path='/tmp/cf_verify.png')
    else:
        page.screenshot(path='/tmp/cf_result.png')
        log("Check screenshot!")
    
    browser.close()

log("=== Done ===")