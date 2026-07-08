#!/usr/bin/env python3
"""
CF 500K Signup Automation v2 - Full Pipeline
Kamatera VPS: 91.202.171.64
IMAP: cfmail / CfMail2024! :993
Proxy: Geonode US residential
9router: local SQLite
"""
import sys, os, time, random, string, re, json, imaplib, email
from email.header import decode_header
from camoufox import Camoufox
import requests

# ============ CONFIG ============
TWOCAPTCHA_KEY = "3da28555894fd89bb569b748731e9400"
CF_PAGE = "https://dash.cloudflare.com/sign-up"
ACCOUNTS_FILE = "/tmp/accounts_500k.txt"
KV_FILE = "/tmp/kv_tokens.json"
PROGRESS_FILE = "/tmp/progress.json"
LOG_FILE = "/tmp/cf_signup_500k.log"

# Email - Kamatera local IMAP
IMAP_HOST = "localhost"
IMAP_PORT = 993
IMAP_USER = "cfmail"
IMAP_PASS = "CfMail2024!"
IMAP_MAILBOX = "INBOX"

# Domains (Spacemail catch-all → Kamatera MX)
EMAIL_DOMAINS = [
    "hilmal.store",
    "indoking.xyz",
    "hilmal.space",
    "tengke-core.shop"
]

# Geonode US Proxy
PROXY_SERVER = "http://148.72.141.11:9000"
PROXY_USER = "geonode_RTwCdAt5Br-type-residential-country-us"
PROXY_PASS = "34c063a6-055f-42e0-980d-57db761b8c46"

PROXIES = {
    'http': f"http://{PROXY_USER}:{PROXY_PASS}@148.72.141.11:9000",
    'https': f"http://{PROXY_USER}:{PROXY_PASS}@148.72.141.11:9000"
}

# 9router local SQLite
NINEROUTER_DB = "/tmp/9router.sqlite"

# ============ LOGGING ============
def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")

def log_ok(msg):
    log(f"✅ {msg}")

def log_err(msg):
    log(f"❌ {msg}")

# ============ EMAIL (Kamatera IMAP) ============
def read_verification_email(timeout=180):
    """Poll local IMAP for CF verification email, return verification URL"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            mc = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            mc.login(IMAP_USER, IMAP_PASS)
            mc.select(IMAP_MAILBOX)
            
            # Search for NEW Cloudflare emails
            typ, data = mc.search(None, 'UNSEEN')
            ids = data[0].split()
            
            if not ids:
                # Also check all recent
                typ, data = mc.search(None, 'ALL')
                ids = data[0].split()
            
            for mid in ids:
                typ, msg_data = mc.fetch(mid, '(RFC822)')
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                
                subject = msg['Subject'] or ''
                sender = msg['From'] or ''
                body = ""
                
                if msg.is_multipart():
                    for part in msg.walk():
                        ct = part.get_content_type()
                        if ct == 'text/plain':
                            try:
                                body = part.get_payload(decode=True).decode(errors='replace')
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode(errors='replace')
                    except:
                        pass
                
                # Check if this is a CF verification email
                if 'cloudflare' in sender.lower() or 'cloudflare' in subject.lower() or 'cloudflare' in body.lower():
                    # Extract verification link
                    links = re.findall(r'https://dash\.cloudflare\.com[^\s<>"\']+', body)
                    if links:
                        link = links[0]
                        log_ok(f"Found CF verification email! Link: {link[:70]}...")
                        # Mark as seen
                        mc.store(mid, '+FLAGS', '\\Seen')
                        mc.logout()
                        return link
                    
                    # Also check for verify token
                    tokens = re.findall(r'verify[/\?=&]([a-zA-Z0-9_-]+)', body, re.I)
                    if tokens:
                        link = f"https://dash.cloudflare.com/verify/{tokens[0]}"
                        log_ok(f"Found verify token: {link}")
                        mc.store(mid, '+FLAGS', '\\Seen')
                        mc.logout()
                        return link
                
                # Mark read to avoid reprocessing
                mc.store(mid, '+FLAGS', '\\Seen')
            
            mc.logout()
            time.sleep(5)
            
        except Exception as e:
            log_err(f"IMAP error: {e}")
            time.sleep(10)
    
    log_err(f"Timeout waiting for verification email ({timeout}s)")
    return None

def clear_inbox():
    """Clear IMAP inbox to avoid duplicates"""
    try:
        mc = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mc.login(IMAP_USER, IMAP_PASS)
        mc.select(IMAP_MAILBOX)
        typ, data = mc.search(None, 'ALL')
        ids = data[0].split()
        if ids:
            mc.store('1:' + str(len(ids)), '+FLAGS', '\\Deleted')
            mc.expunge()
        mc.logout()
        log("Inbox cleared")
    except Exception as e:
        log_err(f"Clear inbox error: {e}")

# ============ 2CAPTCHA SOLVER ============
def solve_turnstile(sitekey, page_url):
    """Solve Turnstile CAPTCHA via 2Captcha"""
    try:
        # Submit
        submit_url = f"http://2captcha.com/in.php?key={TWOCAPTCHA_KEY}&method=turnstile&pageurl={page_url}&sitekey={sitekey}&json=1"
        r = requests.get(submit_url, timeout=10)
        result = r.json()
        
        if result.get('status') != 1:
            log_err(f"2Captcha submit failed: {result}")
            return None
        
        job_id = result.get('request')
        log(f"2Captcha job: {job_id}")
        
        # Poll
        for i in range(60):
            time.sleep(5)
            check = f"http://2captcha.com/res.php?key={TWOCAPTCHA_KEY}&action=get&id={job_id}&json=1"
            r = requests.get(check, timeout=10)
            res = r.json()
            
            if res.get('status') == 1:
                token = res.get('request')
                log_ok(f"Captcha solved!")
                return token
            elif res.get('request') == 'CAPCHA_NOT_READY':
                continue
            else:
                log_err(f"2Captcha error: {res}")
                return None
        
        log_err("Captcha timeout")
        return None
    except Exception as e:
        log_err(f"Captcha solver error: {e}")
        return None

# ============ CF SIGNUP ============
def gen_email(domain):
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=14))
    return f"{name}@{domain}"

def gen_password():
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choices(chars, k=16))

def get_sitekey(page):
    """Extract Turnstile sitekey"""
    iframes = page.query_selector_all('iframe[src*="turnstile"]')
    for iframe in iframes:
        src = iframe.get_attribute('src')
        m = re.search(r'sitekey=([^&]+)', src)
        if m:
            return m.group(1)
    
    els = page.query_selector_all('[data-sitekey]')
    for el in els:
        sk = el.get_attribute('data-sitekey')
        if sk:
            return sk
    
    return None

def signup_one(domain):
    """Signup one CF account"""
    email_addr = gen_email(domain)
    password = gen_password()
    
    log(f"Signing up: {email_addr}")
    
    try:
        with Camoufox(headless=True, humanize=True, geoip=False) as browser:
            ctx = browser.new_context()
            page = ctx.new_page()
            
            # Go to signup page
            page.goto(CF_PAGE, timeout=45000)
            time.sleep(4)
            
            # Check for challenge page
            if "Just a moment" in page.title():
                log("Challenge page detected, waiting...")
                for _ in range(20):
                    time.sleep(3)
                    if "Just a moment" not in page.title():
                        break
            
            # Fill email
            email_input = page.query_selector('input[name="email"]') or page.query_selector('input[type="email"]')
            if email_input:
                email_input.fill(email_addr)
                time.sleep(0.5)
            
            # Fill password
            pw_input = page.query_selector('input[name="password"]') or page.query_selector('input[type="password"]')
            if pw_input:
                pw_input.fill(password)
                time.sleep(0.5)
            
            # Check for CAPTCHA
            sitekey = get_sitekey(page)
            if sitekey:
                log(f"CAPTCHA detected, sitekey: {sitekey[:25]}...")
                token = solve_turnstile(sitekey, CF_PAGE)
                if token:
                    page.evaluate(f"""
                        var inp = document.querySelector('input[name*="turnstile"], input[name*="cf-turnstile"]');
                        if (inp) inp.value = '{token}';
                        var div = document.querySelector('[data-sitekey]');
                        if (div) div.setAttribute('data-response', '{token}');
                    """)
                    time.sleep(2)
            
            # Submit
            submit_btn = page.query_selector('button[type="submit"]')
            if submit_btn:
                submit_btn.click()
            
            time.sleep(5)
            url = page.url
            title = page.title()
            
            log(f"After submit: {title[:50]} | {url[:60]}")
            
            # Check if verification needed
            if 'verify' in url or 'verify' in title.lower() or 'verification' in url:
                log(f"Email verification needed: {email_addr}")
                ctx.close()
                return {'email': email_addr, 'password': password, 'status': 'verify_needed', 'url': url}
            
            # Account created - already logged in (title = Dashboard)
            # Go directly to API tokens
            page.goto("https://dash.cloudflare.com/profile/api-tokens", timeout=60000)
            time.sleep(5)
            
            # Check for challenge
            for _ in range(15):
                if "Just a moment" not in page.title():
                    break
                time.sleep(3)
            
            api_token = None
            tokens = page.query_selector_all('code, [data-token], .token-value')
            for el in tokens:
                val = el.inner_text().strip()
                if len(val) > 20 and re.match(r'^[a-zA-Z0-9_-]+$', val):
                    api_token = val
                    break
            
            ctx.close()
            
            if api_token:
                log_ok(f"Account + API token: {email_addr}")
                return {
                    'email': email_addr,
                    'password': password,
                    'api_token': api_token,
                    'status': 'success'
                }
            else:
                log(f"Account created, no API token: {email_addr}")
                return {
                    'email': email_addr,
                    'password': password,
                    'status': 'created_no_token'
                }
                
    except Exception as e:
        log_err(f"Signup error: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============ KV STORAGE ============
def save_to_kv(email, token, domain):
    """Save token to KV JSON"""
    kv = {}
    if os.path.exists(KV_FILE):
        with open(KV_FILE) as f:
            kv = json.load(f)
    kv[email] = {
        'token': token,
        'domain': domain,
        'added': time.time()
    }
    with open(KV_FILE, "w") as f:
        json.dump(kv, f, indent=2)
    log(f"KV saved: {email[:30]} (total: {len(kv)})")

# ============ 9ROUTER ============
def add_to_9router(email, token):
    """Add API key to local 9router SQLite"""
    try:
        import sqlite3
        conn = sqlite3.connect(NINEROUTER_DB)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                provider TEXT,
                model TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                email TEXT,
                note TEXT
            )
        """)
        c.execute("""
            INSERT OR REPLACE INTO api_keys (key, provider, model, enabled, email, note)
            VALUES (?, 'cloudflare', 'glm-5.2', 1, ?, '500K scale')
        """, (token, email))
        conn.commit()
        conn.close()
        log_ok(f"9router: {email[:40]}")
        return True
    except Exception as e:
        log_err(f"9router add error: {e}")
        return False

# ============ MAIN LOOP ============
def main_loop(target=100, batch_size=10):
    log(f"=== CF 500K Automation Started ===")
    log(f"Target: {target} accounts, batch size: {batch_size}")
    
    clear_inbox()
    
    total_success = 0
    total_verify = 0
    total_fail = 0
    
    # Load progress
    progress = {'success': 0, 'verify': 0, 'fail': 0}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            progress = json.load(f)
    
    total_success = progress.get('success', 0)
    total_verify = progress.get('verify', 0)
    total_fail = progress.get('fail', 0)
    
    i = 0
    while total_success + total_verify < target and i < target * 2:
        domain = EMAIL_DOMAINS[i % len(EMAIL_DOMAINS)]
        
        result = signup_one(domain)
        
        if result is None:
            total_fail += 1
            i += 1
            continue
        
        status = result.get('status')
        
        if status == 'success':
            # Save API token
            with open(ACCOUNTS_FILE, "a") as f:
                f.write(f"{result['email']}:{result['password']}|{result['api_token']}\n")
            
            save_to_kv(result['email'], result['api_token'], domain)
            add_to_9router(result['email'], result['api_token'])
            
            total_success += 1
            progress['success'] = total_success
            with open(PROGRESS_FILE, "w") as f:
                json.dump(progress, f)
            log_ok(f"Progress: {total_success}/{target} success")
            
        elif status == 'verify_needed':
            # Save for later verification
            with open(ACCOUNTS_FILE, "a") as f:
                f.write(f"{result['email']}:{result['password']}|verify_needed\n")
            
            total_verify += 1
            progress['verify'] = total_verify
            with open(PROGRESS_FILE, "w") as f:
                json.dump(progress, f)
            log(f"Verify needed: {total_verify} pending")
        
        else:
            total_fail += 1
            i += 1
            continue
        
        i += 1
        
        # Brief pause between signups
        time.sleep(random.uniform(3, 8))
        
        # Save checkpoint every 10
        if total_success % 10 == 0 and total_success > 0:
            log(f"Checkpoint: {total_success} accounts saved to KV + 9router")
    
    log(f"=== DONE! Success: {total_success} | Verify pending: {total_verify} | Fail: {total_fail} ===")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--batch", type=int, default=1)
    args = parser.parse_args()
    
    main_loop(target=args.count, batch_size=args.batch)