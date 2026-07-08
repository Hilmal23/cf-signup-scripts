#!/usr/bin/env python3
"""Find EXACTLY where 'Please complete CAPTCHA' error appears"""
from camoufox import Camoufox
import time

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

email = f"errtest{int(time.time())}@hilmal.store"
pw = "ErrTest123!"
log(f"Email: {email}")

with Camoufox(headless=True, geoip=False) as browser:
    ctx = browser.new_context()
    page = ctx.new_page()
    
    page.goto("https://dash.cloudflare.com/sign-up", timeout=30000)
    time.sleep(3)
    
    # Fill form
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', pw)
    time.sleep(0.5)
    
    # Submit
    page.click('button[type="submit"]')
    time.sleep(8)
    
    # Find ALL elements containing "captcha" text
    result = page.evaluate("""
        () => {
            // Deep search for CAPTCHA text
            var results = [];
            
            // Search all text nodes
            var walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null
            );
            var node;
            while(node = walker.nextNode()) {
                if (node.textContent.includes('CAPTCHA') || 
                    node.textContent.includes('captcha') ||
                    node.textContent.includes('human')) {
                    results.push({
                        tag: node.parentElement?.tagName,
                        cls: node.parentElement?.className?.slice(0,50),
                        id: node.parentElement?.id,
                        text: node.textContent.trim().slice(0,100)
                    });
                }
            }
            
            // Also check aria-labels and data attributes
            var ariaElements = document.querySelectorAll('[aria-label*="captcha"], [aria-label*="CAPTCHA"], [aria-label*="human"]');
            ariaElements.forEach(el => {
                results.push({
                    tag: el.tagName,
                    cls: el.className?.slice(0,50),
                    id: el.id,
                    text: el.getAttribute('aria-label'),
                    type: 'aria'
                });
            });
            
            // Check for toasts
            var toasts = document.querySelectorAll('[class*="toast"], [role="alert"], [class*="message"]');
            toasts.forEach(el => {
                var text = el.textContent.trim();
                if (text && text.length > 5) {
                    results.push({
                        tag: el.tagName,
                        cls: el.className?.slice(0,50),
                        id: el.id,
                        text: text.slice(0, 100),
                        type: 'toast'
                    });
                }
            });
            
            // Check body text for error
            var body = document.body.innerText;
            var lines = body.split('\\n').filter(l => l.trim().length > 0);
            
            return {
                elements: results,
                linesWithError: lines.filter(l => /captcha|human|verify|challenge/i.test(l)).slice(0, 20),
                bodySnippet: body.slice(0, 1000)
            };
        }
    """)
    
    log("Error elements found:")
    for e in result['elements']:
        log(f"  [{e.get('type','default')}] <{e['tag']}> id={e['id']} class={e['cls']} text={e['text']}")
    
    log("\\nLines with error keywords:")
    for line in result['linesWithError']:
        log(f"  {line[:100]}")
    
    log(f"\\nBody snippet: {result['bodySnippet'][:500]}")
    
    page.screenshot(path='/tmp/cf_captcha_error.png')
    browser.close()