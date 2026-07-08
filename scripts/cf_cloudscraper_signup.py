#!/usr/bin/env python3
"""CF Signup via cloudscraper - try to bypass CF challenge + API signup"""
import cloudscraper, time, re

def main():
    # Create scraper with CF challenge bypass
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    scraper.proxies = {
        'http': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335',
        'https': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335'
    }
    
    # Step 1: Get signup page + security token
    print("Fetching signup page...")
    r = scraper.get('https://dash.cloudflare.com/sign-up', timeout=30)
    print(f"Status: {r.status_code}")
    print(f"URL after: {r.url[:80]}")
    
    # Find security token
    sec_token = re.search(r'name="security_token"\s+value="([^"]+)"', r.text)
    if sec_token:
        print(f"Security token: {sec_token.group(1)[:30]}...")
    else:
        print("No security token found")
    
    # Find all form inputs
    inputs = re.findall(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"[^>]*>', r.text)
    print(f"Form inputs: {inputs}")
    
    # Step 2: Try direct POST with security token
    email_val = f'test{int(time.time())}@hilmal.store'
    data = {
        'security_token': sec_token.group(1) if sec_token else '',
        'email': email_val,
        'password': 'TestPass123!',
        'redirect_uri': '',
    }
    
    print(f"\nTrying POST signup: {email_val}")
    r2 = scraper.post('https://dash.cloudflare.com/sign-up', data=data, timeout=30)
    print(f"POST Status: {r2.status_code}")
    print(f"POST URL: {r2.url[:80]}")
    print(f"POST Headers: {dict(r2.headers)}")
    print(f"POST Body: {r2.text[:500]}")
    
    # Check for cookies
    print(f"\nCookies: {[c.name for c in scraper.cookies]}")
    
    # Step 3: Check for verification redirect
    if 'verify' in r2.url.lower():
        print("VERIFICATION NEEDED!")
    
    # Save cookies for next request
    print("\nDone!")

if __name__ == '__main__':
    main()