#!/usr/bin/env python3
"""
CF Signup Automation v1 - 500K Scale
Pipeline: CF Signup → Spacemail Verify → API Token → 9router
"""
import sys, os, time, random, string, re, json, imaplib, email
from email.header import decode_header
from camoufox import Camoufox
import requests

# ============ CONFIG ============
TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
CF_PAGE = "https://dash.cloudflare.com/sign-up"
ACCOUNTS_FILE = "/tmp/accounts_500k.txt"
PROGRESS_FILE = "/tmp/progress_500k.json"
LOG_FILE = "/tmp/cf_signup.log"
KV_FILE = "/tmp/kv_tokens.json"

# Email domains (Spacemail catch-all)
EMAIL_DOMAINS = [
    "hilmal.store",
    "indoking.xyz", 
    "hilmal.space",
    "tengke-core.shop"
]
EMAIL_PASS = "@Ikmal230104"
EMAIL_USER = "tengkeikmal"

# 9router config
NINEROUTER_DB = "/tmp/9router.sqlite"
NINEROUTER_PORT = 20128

# ============ LOGGING ============
def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")

def log_error(msg):
    log(f"❌ ERROR: {msg}")

def log_ok(msg):
    log(f"✅ {msg}")

# ============ EMAIL (Spacemail webmail via proxy) ============
PROXY = {
    'http': 'http://geonode_RTwCdAt5Br-type-residential-country-us:34c063a6-055f-42e0-980d-57db761b8c46@148.72.141.11:9000',
    'https': 'http://geonode_RTwCdAt5Br-type-residential-country-us:34c063a6-055f-42e0-980d-57db761b8c46@148.72.141.11:9000'
}

def login_spacemail(email_addr, password):
    """Login to Spacemail webmail, return session cookies"""
    s = requests.Session()
    s.proxies = PROXY
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    
    # Get login page
    r = s.get('https://www.spacemail.com/login/', timeout=15)
    
    # Extract CSRF from page source
    csrf_match = re.search(r'csrf["\s:*"\']+\s*["\']([a-f0-9]{32,})', r.text)
    if not csrf_match:
        csrf_match = re.search(r'token["\s:*"\']+\s*["\']([a-f0-9]{32,})', r.text)
    csrf = csrf_match.group(1) if csrf_match else ""
    
    # Submit login
    login_data = {'username': email_addr, 'password': password}
    r2 = s.post('https://www.spacemail.com/login/', data=login_data, allow_redirects=True, timeout=15)
    
    if 'mail' in r2.url or r2.status_code == 200:
        log(f"Spacemail logged in: {email_addr}")
        return s
    return None

def get_verification_link(email_addr, password, timeout=120):
    """Poll Spacemail webmail for CF verification email, return verification link"""
    s = login_spacemail(email_addr, password)
    if not s:
        return None
    
    start = time.time()
    while time.time() - start < timeout:
        try:
            # Get inbox
            r = s.get('https://www.spacemail.com/mail/', timeout=15)
            if r.status_code != 200:
                time.sleep(5)
                continue
            
            body = r.text
            
            # Look for CF verification email in page
            if 'Cloudflare' in body or 'verify' in body.lower():
                # Extract email list items
                links = re.findall(r'href=["\']([^"\']*token[^"\']*)["\']', body, re.I)
                texts = re.findall(r'(https://dash\.cloudflare\.com/[^"<\s]+)', body)
                if texts:
                    link = texts[0]
                    log(f"Found verification link: {link[:80]}")
                    return link
            
            # Look for verify link patterns
            patterns = [
                r'https://dash\.cloudflare\.com[^"<\s]+',
                r'/verify/[^"<\s]+',
                r'token=([a-zA-Z0-9_-]+)',
            ]
            for pat in patterns:
                m = re.search(pat, body)
                if m:
                    link = m.group(0)
                    if not link.startswith('http'):
                        link = 'https://dash.cloudflare.com' + link
                    log(f"Found link: {link[:80]}")
                    return link
            
            time.sleep(10)
        except Exception as e:
            log(f"Polling error: {e}")
            time.sleep(10)
    
    log_error(f"Timeout waiting for verification email: {email_addr}")
    return None

# ============ 2CAPTCHA SOLVER ============
def solve_turnstile_captcha(sitekey, page_url):
    """Solve Turnstile via 2Captcha, return token"""
    import json as json_mod
    
    # Submit to 2Captcha
    submit_url = f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={page_url}&sitekey={sitekey}&json=1"
    r = requests.get(submit_url, timeout=10)
    result = r.json()
    
    if result.get('status') != 1:
        log_error(f"2Captcha submit failed: {result}")
        return None
    
    captcha_id = result.get('request')
    log(f"2Captcha job ID: {captcha_id}")
    
    # Poll for result
    for i in range(60):
        time.sleep(5)
        check_url = f"http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={captcha_id}&json=1"
        r = requests.get(check_url, timeout=10)
        result = r.json()
        
        if result.get('status') == 1:
            token = result.get('request')
            log_ok(f"Captcha solved: {token[:40]}...")
            return token
        elif result.get('request') == 'CAPCHA_NOT_READY':
            continue
        else:
            log_error(f"2Captcha error: {result}")
            return None
    
    log_error("Captcha timeout")
    return None

# ============ CF SIGNUP ============
def random_email(domain):
    """Generate random email alias"""
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
    return f"{name}@{domain}"

def random_password():
    """Generate random password"""
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choices(chars, k=16))

def get_sitekey_from_page(page):
    """Extract Turnstile sitekey from page"""
    # Method 1: from iframe src
    iframes = page.query_selector_all('iframe[src*="turnstile"]')
    for iframe in iframes:
        src = iframe.get_attribute('src')
        m = re.search(r'sitekey=([^&]+)', src)
        if m:
            return m.group(1)
    
    # Method 2: from data-sitekey attribute
    elements = page.query_selector_all('[data-sitekey]')
    for el in elements:
        sk = el.get_attribute('data-sitekey')
        if sk:
            return sk
    
    # Method 3: from challenge response input
    inputs = page.query_selector_all('input[name="cf-chl-widget-81dq1_response"]')
    for inp in inputs:
        val = inp.get_attribute('value') or ''
        if val:
            return val[:40]
    
    return None

def cf_signup_batch(start_idx=0, count=10):
    """Signup batch of CF accounts"""
    log(f"Starting batch: {count} accounts from index {start_idx}")
    
    with Camoufox(headless=True, humanize=True, geoip=False) as browser:
        for i in range(count):
            idx = start_idx + i
            domain = EMAIL_DOMAINS[idx % len(EMAIL_DOMAINS)]
            email_addr = random_email(domain)
            password = random_password()
            
            log(f"[{idx}] Signing up: {email_addr}")
            
            try:
                ctx = browser.new_context()
                page = ctx.new_page()
                
                # Navigate
                page.goto(CF_PAGE, timeout=45000)
                time.sleep(5)
                
                # Fill form
                email_input = page.query_selector('input[name="email"], input[type="email"], input#email')
                if email_input:
                    email_input.fill(email_addr)
                    time.sleep(0.5)
                
                pw_input = page.query_selector('input[name="password"], input[type="password"], input#password')
                if pw_input:
                    pw_input.fill(password)
                    time.sleep(0.5)
                
                # Check for CAPTCHA
                sitekey = get_sitekey_from_page(page)
                if sitekey and 'turnstile' in page.content().lower():
                    log(f"CAPTCHA detected, sitekey: {sitekey[:30]}...")
                    token = solve_turnstile_captcha(sitekey, CF_PAGE)
                    if token:
                        # Inject token
                        page.evaluate(f"""
                            document.querySelector('input[name="cf-turnstile-response"]').value = '{token}';
                        """)
                    else:
                        log_error("Captcha failed, skipping this account")
                        ctx.close()
                        continue
                
                # Submit
                submit_btn = page.query_selector('button[type="submit"], button:has-text("Sign up")')
                if submit_btn:
                    submit_btn.click()
                
                time.sleep(5)
                url = page.url
                
                # Check for verification requirement
                if 'verify' in url or 'verification' in page.title().lower():
                    log(f"Verification needed for {email_addr}")
                    
                    # Get verification link from Spacemail
                    # For now, save to file and skip (manual verify)
                    with open(ACCOUNTS_FILE, "a") as f:
                        f.write(f"{email_addr}:{password}|needs_verify\n")
                    ctx.close()
                    continue
                
                # Success - extract API token
                page.goto("https://dash.cloudflare.com/profile/api-tokens", timeout=15000)
                time.sleep(3)
                
                api_token = None
                # Try to find API token in page
                token_elements = page.query_selector_all('.token-value, [data-token], code')
                for el in token_elements:
                    val = el.inner_text()
                    if len(val) > 20 and re.match(r'^[a-zA-Z0-9_-]+$', val):
                        api_token = val
                        break
                
                if api_token:
                    log_ok(f"Account {email_addr} - API token: {api_token[:20]}...")
                    
                    # Save to accounts file
                    with open(ACCOUNTS_FILE, "a") as f:
                        f.write(f"{email_addr}:{password}|{api_token}\n")
                    
                    # Save to KV file
                    save_to_kv(email_addr, api_token)
                    
                    # Add to 9router
                    add_to_9router(email_addr, api_token)
                else:
                    log(f"Account created but API token not extracted: {email_addr}")
                    with open(ACCOUNTS_FILE, "a") as f:
                        f.write(f"{email_addr}:{password}|created_no_token\n")
                
                ctx.close()
                
            except Exception as e:
                log_error(f"Signup failed: {e}")
                with open(LOG_FILE, "a") as f:
                    f.write(f"EXCEPTION: {email_addr} - {e}\n")
                continue
    
    log_ok(f"Batch complete! {count} accounts processed")
    return count

# ============ KV STORAGE ============
def save_to_kv(email, token):
    """Save token to KV JSON file"""
    kv = {}
    if os.path.exists(KV_FILE):
        with open(KV_FILE) as f:
            kv = json.load(f)
    kv[email] = {"token": token, "added": time.time()}
    with open(KV_FILE, "w") as f:
        json.dump(kv, f, indent=2)

# ============ 9ROUTER ============
def add_to_9router(email, token):
    """Add account to 9router database"""
    try:
        import sqlite3
        db = NINEROUTER_DB
        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO api_keys (key, provider, model, enabled, created_at, email)
            VALUES (?, ?, ?, 1, datetime('now'), ?)
        """, (token, 'cloudflare', 'glm-5.2', email))
        conn.commit()
        conn.close()
        log_ok(f"Added to 9router: {email[:30]}")
    except Exception as e:
        log_error(f"9router add failed: {e}")

# ============ MAIN ============
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()
    
    log(f"=== CF Signup 500K Automation Started ===")
    log(f"Target: {args.count} accounts from index {args.start}")
    
    cf_signup_batch(start_idx=args.start, count=args.count)
    
    log(f"=== DONE ===")