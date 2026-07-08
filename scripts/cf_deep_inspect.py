#!/usr/bin/env python3
"""Deep inspect CF signup CAPTCHA form"""
from camoufox import Camoufox
import time

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=30000)
    time.sleep(2)
    
    # Fill form
    page.fill('input[name="email"]', 'deep@test.com')
    page.fill('input[name="password"]', 'DeepTest123!')
    
    # Get EVERY iframe
    iframes = page.query_selector_all('iframe')
    log(f"Iframes: {len(iframes)}")
    for i, iframe in enumerate(iframes):
        src = iframe.get_attribute('src') or ''
        id_ = iframe.get_attribute('id') or ''
        cls = iframe.get_attribute('class') or ''
        log(f"  [{i}] id={id_} class={cls[:50]}")
        log(f"      src={src[:100]}")
    
    # Get ALL inputs
    inputs = page.query_selector_all('input')
    log(f"Inputs: {len(inputs)}")
    for inp in inputs:
        type_ = inp.get_attribute('type') or 'text'
        name = inp.get_attribute('name') or ''
        id_ = inp.get_attribute('id') or ''
        placeholder = inp.get_attribute('placeholder') or ''
        cls = inp.get_attribute('class') or ''
        value = inp.get_attribute('value') or ''
        aria = inp.get_attribute('aria-label') or ''
        log(f"  {name}/{type_} id={id_} placeholder={placeholder} class={cls[:30]} value={value[:20]} aria={aria}")
    
    # Get form
    forms = page.query_selector_all('form')
    log(f"Forms: {len(forms)}")
    for form in forms:
        id_ = form.get_attribute('id') or ''
        action = form.get_attribute('action') or ''
        log(f"  id={id_} action={action}")
    
    # Get ALL divs and look for challenge/check
    divs = page.query_selector_all('div')
    log(f"Divs: {len(divs)}")
    for div in divs:
        cls = div.get_attribute('class') or ''
        id_ = div.get_attribute('id') or ''
        text = div.inner_text()[:50].strip()
        if any(x in cls.lower() + text.lower() for x in ['turnstile', 'challenge', 'captcha', 'human', 'verify', 'checkbox', 'cf-']):
            log(f"  [MATCH] id={id_} class={cls[:60]}")
            log(f"          text={text}")
    
    # Get body HTML
    html = page.content()
    import re
    # Find any element with challenge/captcha
    challenge = re.findall(r'<[^>]*(?:turnstile|challenge|captcha|human|verify|cf-turnstile)[^>]*>', html, re.I)
    log(f"Challenge elements: {len(challenge)}")
    for c in challenge[:5]:
        log(f"  {c[:150]}")
    
    # Check if there's a checked checkbox
    checkboxes = page.query_selector_all('input[type="checkbox"]')
    log(f"Checkboxes: {len(checkboxes)}")
    
    # Try to evaluate JS to find all challenge widgets
    widgets = page.evaluate("""
        () => {
            // Find all Turnstile widgets
            var widgets = [];
            var iframes = document.querySelectorAll('iframe');
            iframes.forEach((f, i) => {
                widgets.push({
                    index: i,
                    src: f.src,
                    id: f.id,
                    class: f.className
                });
            });
            
            // Find all __cfUIChallenge__ or similar
            var challengeElements = document.querySelectorAll('[id*="challenge"], [class*="challenge"], [id*="turnstile"]');
            challengeElements.forEach(e => {
                widgets.push({
                    id: e.id,
                    class: e.className,
                    tag: e.tagName
                });
            });
            
            // Try to find Cloudflare challenge API
            var result = {
                hasChallenge: typeof window._cf_check_answer !== 'undefined',
                hasTurnstile: typeof window.cfTurnstile !== 'undefined',
                hasCaptcha: typeof window.captcha !== 'undefined',
                challengeDef: typeof window.__CFChallengeDefine !== 'undefined'
            };
            
            return JSON.stringify(result);
        }
    """)
    log(f"JS Challenge API: {widgets}")
    
    page.screenshot(path='/tmp/cf_deep_inspect.png')
    log("Screenshot saved!")
    
    browser.close()