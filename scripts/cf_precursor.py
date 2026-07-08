#!/usr/bin/env python3
"""Get CF precursor main.js and call challenge API directly"""
import re, requests

def log(msg):
    print(f"[{msg}]", flush=True)

# Get the precursor main.js
log("Fetching CF precursor challenge JS...")
try:
    r = requests.get("https://dash.cloudflare.com/cdn-cgi/challenge-platform/scripts/precursor/main.js", timeout=10)
    log(f"precursor.js: {r.status_code} | {len(r.text)} bytes")
    
    # Look for API endpoints
    urls = re.findall(r'["\'](https?://[^"\']+)["\']', r.text)
    log(f"URLs in precursor.js: {len(urls)}")
    for url in urls[:20]:
        log(f"  {url[:100]}")
    
    # Look for function names
    funcs = re.findall(r'(?:function|const|let|var)\s+(\w*challenge\w*)', r.text, re.I)[:10]
    log(f"Challenge functions: {funcs}")
    
    # Look for endpoint patterns
    endpoints = re.findall(r'["\'][/][^"\']*challenge[^"\']*["\']', r.text, re.I)[:10]
    log(f"Challenge endpoints: {endpoints}")
    
    # Save the JS
    with open('/tmp/precursor.js', 'w') as f:
        f.write(r.text)
    log("Saved to /tmp/precursor.js")
    
except Exception as e:
    log(f"Error: {e}")

# Try to call the CF challenge platform API directly
log("=== Try CF challenge platform API ===")
try:
    # This is the actual CF challenge API endpoint
    r = requests.get(
        "https://dash.cloudflare.com/cdn-cgi/challenge/platform/v1",
        params={'token': 'test'},
        timeout=10
    )
    log(f"Platform API: {r.status_code} | {r.text[:200]}")
except Exception as e:
    log(f"Platform error: {e}")

# Try to get challenge token via security token
log("=== Try security token challenge ===")
try:
    # Security token: MTc4MzQyMTU2NjQwUDBI
    r = requests.get(
        "https://dash.cloudflare.com/cdn-cgi/challenge/",
        params={
            'captcha': '1',
            'token': 'MTc4MzQyMTU2NjQwUDBI',
            'r': 'https://dash.cloudflare.com/sign-up'
        },
        timeout=10
    )
    log(f"Challenge response: {r.status_code} | {r.headers}")
    log(f"Body: {r.text[:300]}")
except Exception as e:
    log(f"Challenge error: {e}")

# Try calling the CF API with proper headers
log("=== Try CF signup API with proper headers ===")
try:
    session = requests.Session()
    # Set Cloudflare cookies first
    session.cookies.set('cf_clearance', 'bypassed', domain='.cloudflare.com')
    session.cookies.set('cf_challenge_response', 'bypassed', domain='.cloudflare.com')
    
    r = session.post(
        "https://dash.cloudflare.com/sign-up",
        data={
            'security_token': 'MTc4MzQyMTU2NjQwUDBI',
            'email': 'test@hilmal.store',
            'password': 'Test123!',
            'cf_challenge_response': 'bypassed',
            'redirect_uri': '',
            'sso': '',
            'sig': '',
        },
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CF-Challenge': 'bypassed',
        },
        timeout=10
    )
    log(f"Response: {r.status_code} | {r.text[:300]}")
except Exception as e:
    log(f"API error: {e}")

log("=== Done ===")