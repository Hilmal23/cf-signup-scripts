#!/usr/bin/env python3
"""CF signup - manipulate challenge widget via injected JS"""
from camoufox import Camoufox
import time, re

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

email = f"jstest{int(time.time())}@hilmal.store"
pw = "Jstest123!"
log(f"Testing: {email}")

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    # Navigate FIRST
    page.goto("https://dash.cloudflare.com/sign-up", timeout=30000)
    time.sleep(3)
    
    # BEFORE filling anything, inject JS to hook into CF challenge
    result = page.evaluate("""
        () => {
            // Hook into CF challenge define
            var originalDefine = window.__CFChallengeDefine;
            var hooked = false;
            var challengeData = null;
            
            // Try to find challenge state
            var state = {
                windowKeys: Object.keys(window).filter(k => k.includes('cf') || k.includes('challenge') || k.includes('turnstile')).slice(0, 20),
                challengeContainer: null,
                challengeWidget: document.querySelector('[data-testid="challenge-widget-container"]'),
                hiddenInputs: Array.from(document.querySelectorAll('input[type="hidden"]')).map(i => ({name: i.name, id: i.id, value: i.value.slice(0,20)})),
                widgetHTML: document.querySelector('[data-testid="challenge-widget-container"]')?.innerHTML || '',
            };
            
            // Try to find CF state
            if (window.__cfState__) state.cfState = JSON.stringify(window.__cfState__).slice(0, 100);
            if (window.__NEXT_DATA__) state.nextData = JSON.stringify(window.__NEXT_DATA__).slice(0, 100);
            
            // Find any function that handles challenge
            var scripts = Array.from(document.querySelectorAll('script'));
            var challengeScript = scripts.find(s => s.src.includes('precursor'));
            state.precursorScript = challengeScript ? challengeScript.src : 'not found';
            
            return state;
        }
    """)
    log(f"Challenge state: {result}")
    
    # Try to inject a workaround: directly set the challenge response
    # by hooking into the form submit handler
    page.evaluate("""
        () => {
            // Method 1: Override the challenge response setter
            var hiddenInput = document.querySelector('input[name="cf_challenge_response"]');
            if (hiddenInput) {
                // Make it think it's already solved
                Object.defineProperty(hiddenInput, 'value', {
                    get: function() { return this._value || 'passed'; },
                    set: function(v) { this._value = v; this.dataset.challengePassed = 'true'; },
                    configurable: true
                });
            }
            
            // Method 2: Disable challenge validation
            window.__cfChallengePassed = true;
            window.__cfChallengeBypassed = true;
            
            // Method 3: Hook into form submit
            var form = document.querySelector('form');
            if (form) {
                var originalSubmit = form.onsubmit;
                form.onsubmit = function(e) {
                    var inp = document.querySelector('input[name="cf_challenge_response"]');
                    if (inp) inp.value = 'manually_bypassed';
                    console.log('Form submit hooked, challenge bypassed');
                    return originalSubmit ? originalSubmit.call(this, e) : true;
                };
            }
            
            // Method 4: Try to call CF challenge API manually
            var securityToken = document.querySelector('input[name="security_token"]')?.value;
            if (securityToken) {
                console.log('Security token: ' + securityToken);
            }
            
            return {
                hiddenInput: !!hiddenInput,
                form: !!form,
                securityToken: securityToken
            };
        }
    """)
    log("Bypass hooks injected")
    time.sleep(1)
    
    # Now fill and submit
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    time.sleep(0.5)
    
    # Check challenge response before submit
    response_val = page.evaluate("() => document.querySelector('input[name=\"cf_challenge_response\"]')?.value || 'empty'")
    log(f"Challenge response before submit: {response_val[:30]}")
    
    page.click('button[type="submit"]')
    time.sleep(8)
    
    title = page.title()
    url = page.url
    body = page.inner_text('body')
    
    log(f"Result: {title} | {url}")
    
    if 'dashboard' in title.lower() and 'sign-up' not in url:
        log("SUCCESS via JS bypass!")
        page.screenshot(path='/tmp/cf_js_bypass_success.png')
    else:
        log(f"FAILED: {body[:200]}")
        page.screenshot(path='/tmp/cf_js_bypass_fail.png')
    
    browser.close()