#!/usr/bin/env python3
"""CF signup - pure Python requests approach"""
import requests, re, time, json

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

BRD = {
    'http': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335',
    'https': 'http://brd-customer-hl_c0f6789c-zone-web_unlocker1:ds3ovbwhs69y@brd.superproxy.io:33335'
}

email = f"apitest{int(time.time())}@hilmal.store"
pw = "Apitest123!"

log(f"Email: {email}")

s = requests.Session()
s.proxies = BRD
s.verify = False
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Origin': 'https://dash.cloudflare.com',
    'Referer': 'https://dash.cloudflare.com/sign-up',
})

# Step 1: Get signup page
log("=== Step 1: Get signup page ===")
r = s.get('https://dash.cloudflare.com/sign-up', timeout=30)
log(f"Page: {r.status_code}, Size: {len(r.content)}")

# Extract hidden fields
security_token = re.search(r'name="security_token"\s+value="([^"]+)"', r.text)
cf_token = re.search(r'name="cf_challenge_response"\s+id="([^"]+)"\s+type="hidden"\s+value="([^"]+)"', r.text)
redirect_uri = re.search(r'name="redirect_uri"\s+value="([^"]+)"', r.text)
sso = re.search(r'name="sso"\s+value="([^"]+)"', r.text)
sig = re.search(r'name="sig"\s+value="([^"]+)"', r.text)

log(f"security_token: {security_token.group(1)[:20] if security_token else 'None'}")
log(f"cf_challenge_response: {cf_token.group(2)[:20] if cf_token else 'None'}")
log(f"redirect_uri: {redirect_uri.group(1)[:20] if redirect_uri else 'None'}")

# Step 2: Submit form via POST
log("=== Step 2: Submit signup form ===")
form_data = {
    'email': email,
    'password': pw,
}
if security_token:
    form_data['security_token'] = security_token.group(1)
if redirect_uri:
    form_data['redirect_uri'] = redirect_uri.group(1)
if sso:
    form_data['sso'] = sso.group(1)
if sig:
    form_data['sig'] = sig.group(1)
# Leave cf_challenge_response empty - Bright Data bypasses challenge server-side

log(f"Form data: {list(form_data.keys())}")

try:
    r2 = s.post('https://dash.cloudflare.com/sign-up', data=form_data, timeout=30, allow_redirects=True)
    log(f"POST result: {r2.status_code}")
    log(f"Final URL: {r2.url}")
    log(f"Response size: {len(r2.content)}")
    
    if 'dashboard' in r2.url.lower():
        log("SUCCESS! Account created!")
        log(f"Redirected to: {r2.url}")
    else:
        # Check what we got
        log(f"Response preview: {r2.text[:500]}")
        
        # Try JSON API instead
        log("=== Try JSON API ===")
        s.headers.update({'Content-Type': 'application/json', 'Accept': 'application/json'})
        r3 = s.post('https://dash.cloudflare.com/api/v4/signup', json={'email': email, 'password': pw}, timeout=20)
        log(f"JSON API: {r3.status_code} | {r3.text[:200]}")
        
except Exception as e:
    log(f"POST error: {e}")

# Step 3: Try OAuth flow instead
log("=== Step 3: Try Google OAuth ===")
try:
    # Get OAuth URL
    oauth_url = 'https://dash.cloudflare.com/oauth2/sign-in/google'
    r4 = s.get(oauth_url, timeout=20, allow_redirects=True)
    log(f"Google OAuth: {r4.status_code} | {r4.url}")
except Exception as e:
    log(f"OAuth error: {e}")

log("=== Done ===")