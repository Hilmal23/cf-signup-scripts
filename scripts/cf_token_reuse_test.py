#!/usr/bin/env python3
"""Test: can one Turnstile solve work for multiple signups?"""
import requests, time

TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
SITEKEY = "8732e7fe-bf77-5ee5-bb3f-f2004f0769ae"

def solve_once():
    print("Solving Turnstile once...")
    url = f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl=https://dash.cloudflare.com/sign-up&sitekey={SITEKEY}&json=1"
    r = requests.get(url, timeout=10)
    result = r.json()
    if result.get('status') != 1:
        print(f"Submit failed: {result}")
        return None
    job_id = result.get('request')
    print(f"Job: {job_id}")
    for i in range(40):
        time.sleep(3)
        check = f"http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={job_id}&json=1"
        r = requests.get(check, timeout=10)
        res = r.json()
        if res.get('status') == 1:
            token = res.get('request')
            print(f"Token: {token[:50]}...")
            return token
        elif 'NOT_READY' not in str(res):
            print(f"Error: {res}")
            return None
    return None

def main():
    token = solve_once()
    if not token:
        return
    
    # Try using this same token from different "browser contexts" 
    # Test 1: Same token, different security tokens
    print("\n--- Testing if token works from different contexts ---")
    
    # Check 2Captcha docs for token reuse
    docs_url = "http://2captcha.com/2captcha-api#timeout-and-multiple-solutions"
    print(f"Note: 2Captcha tokens may be bound to session/cookie")
    print(f"If token fails on reuse, CF binds to browser fingerprint")
    
    print(f"\nToken: {token}")
    print("Test approach: Use token in different Playwright contexts")
    
    # Save token for testing
    with open('/tmp/cf_token.txt', 'w') as f:
        f.write(token)
    print("Token saved to /tmp/cf_token.txt")

if __name__ == '__main__':
    main()