#!/usr/bin/env python3
"""
CF Signup Script - Jalankan di HP (Termux)
Bypass CF challenge pake IP residential HP lu
"""
import requests, time, json, re, imaplib, email as emaillib
from email.mime.text import MIMEText
import random
import string

# ============ KONFIGURASI ============
EMAIL_DOMAIN = "hilmal.store"  # Ganti kalo mau domain lain
# Domains: hilmal.store, indoking.xyz, hilmal.space, tengke-core.shop

IMAP_HOST = "91.202.171.64"   # Kamatera VPS
IMAP_USER = "cfmail"
IMAP_PASS = "CfMail2024!"

KAMATERA_HOST = "91.202.171.64"
KAMATERA_USER = "root"
KAMATERA_PASS = "Hilmal#Server2026"

MAX_WAIT_EMAIL = 60  # Detik tunggu email verifikasi
# ======================================

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def gen_email():
    ts = int(time.time() * 1000)
    return f"cf{ts}@{EMAIL_DOMAIN}"

def gen_password():
    chars = string.ascii_letters + string.digits + "!@#$"
    return ''.join(random.choices(chars, k=16))

def gen_name():
    adj = ["dark", "swift", "bold", "iron", "blue", "neon", "zero", "prime"]
    noun = ["fox", "hawk", "wolf", "bear", "lion", "byte", "node", "flux"]
    n = random.choice(adj) + random.choice(noun)
    num = random.randint(10, 99)
    return f"{n.capitalize()} {num}"

def wait_for_verification_email(timeout=MAX_WAIT_EMAIL):
    """Baca email verifikasi dari Kamatera IMAP"""
    for i in range(timeout // 5):
        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST, 993)
            mail.login(IMAP_USER, IMAP_PASS)
            mail.select('INBOX')
            status, msgs = mail.search(None, 'ALL')
            ids = msgs[0].split()
            
            if ids:
                # Check newest email
                for msg_id in reversed(ids[-5:]):
                    status, msg_data = mail.fetch(msg_id, '(RFC822)')
                    msg = emaillib.message_from_bytes(msg_data[0][1])
                    subj = msg.get('Subject', '')
                    body = ''
                    if msg.is_multipart():
                        for p in msg.walk():
                            if p.get_content_type() == 'text/plain':
                                body = p.get_payload(decode=True)
                                if isinstance(body, bytes):
                                    body = body.decode('utf-8', errors='ignore')
                                break
                    else:
                        body = msg.get_payload(decode=True)
                        if isinstance(body, bytes):
                            body = body.decode('utf-8', errors='ignore')
                    
                    subj_lower = subj.lower()
                    body_lower = body.lower()
                    
                    # Check for verification email
                    if any(x in subj_lower for x in ['verify', 'verification', 'confirm', 'email', 'cloudflare', 'sign']):
                        log(f"Email ditemukan: {subj}")
                        # Delete after read
                        mail.store(msg_id, '+FLAGS', '\\Deleted')
                        
                        # Extract verification link
                        links = re.findall(r'https?://[^\s<>"\']+', body)
                        verify_links = [l for l in links if 'verify' in l.lower() or 'confirm' in l.lower() or 'email' in l.lower() or 'click' in l.lower()]
                        
                        if verify_links:
                            log(f"Link verifikasi: {verify_links[0][:80]}...")
                            mail.logout()
                            return verify_links[0]
                        elif links:
                            log(f"Link found: {links[0][:80]}...")
                            mail.logout()
                            return links[0]
            
            mail.logout()
        except Exception as e:
            log(f"IMAP error: {e}")
        
        if i < timeout // 5 - 1:
            log(f"Menunggu email... ({i+1}/{timeout//5})")
            time.sleep(5)
    
    return None

def verify_email_link(link):
    """Klik link verifikasi"""
    try:
        r = requests.get(link, timeout=20, allow_redirects=True)
        log(f"Verification status: {r.status_code}")
        if r.status_code in (200, 302, 303):
            log("Email terverifikasi!")
            return True
    except Exception as e:
        log(f"Verify error: {e}")
    return False

def signup(email, password, name):
    """Signup CF via API"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json',
            'Origin': 'https://dash.cloudflare.com',
            'Referer': 'https://dash.cloudflare.com/sign-up',
        }
        
        data = {
            "email": email,
            "password": password,
        }
        
        r = requests.post(
            'https://dash.cloudflare.com/api/v4/user/create',
            json=data,
            headers=headers,
            timeout=30
        )
        
        log(f"Signup status: {r.status_code}")
        
        if r.status_code == 200:
            try:
                resp = r.json()
                log(f"Response: {json.dumps(resp, indent=2)}")
            except:
                log(f"Response: {r.text[:300]}")
            return r.status_code == 200, r
        
        elif r.status_code == 400:
            try:
                err = r.json()
                log(f"Error: {json.dumps(err, indent=2)}")
            except:
                log(f"Response: {r.text[:300]}")
            return False, r
        
        else:
            log(f"Unexpected: {r.status_code} - {r.text[:200]}")
            return False, r
            
    except Exception as e:
        log(f"Signup error: {e}")
        return False, None

def main():
    email = gen_email()
    password = gen_password()
    name = gen_name()
    
    log(f"=== CF Signup ===")
    log(f"Email: {email}")
    log(f"Password: {password[:8]}...")
    log(f"Name: {name}")
    log(f"IP: residential (HP lu)")
    
    # Signup
    log("\nSignup...")
    success, resp = signup(email, password, name)
    
    if not success:
        log("Signup failed!")
        return False
    
    # Wait for verification email
    log("\nMenunggu email verifikasi...")
    link = wait_for_verification_email()
    
    if link:
        log(f"Link ditemukan: {link[:60]}...")
        if verify_email_link(link):
            log("=== Account berhasil dibuat! ===")
            return True
        else:
            log("Verify failed!")
            return False
    else:
        log("Email verifikasi tidak ditemukan!")
        return False

if __name__ == "__main__":
    ok = main()
    exit(0 if ok else 1)