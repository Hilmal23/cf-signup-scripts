#!/usr/bin/env python3
import requests, time, re, imaplib, email as emaillib, random, string

EMAIL_DOMAIN = "hilmal.store"
IMAP_HOST = "91.202.171.64"
IMAP_USER = "cfmail"
IMAP_PASS = "CfMail2024!"

def log(msg):
    print("[" + time.strftime("%H:%M:%S") + "] " + msg, flush=True)

def gen_email():
    ts = int(time.time() * 1000) + random.randint(1000, 9999)
    return "cf" + str(ts) + "@" + EMAIL_DOMAIN

def gen_password():
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choices(chars, k=14))

def wait_email(timeout=90):
    for i in range(timeout // 5):
        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST, 993)
            mail.login(IMAP_USER, IMAP_PASS)
            mail.select('INBOX')
            status, msgs = mail.search(None, 'UNSEEN')
            ids = msgs[0].split()
            if ids:
                for msg_id in reversed(ids):
                    status, msg_data = mail.fetch(msg_id, '(RFC822)')
                    msg = emaillib.message_from_bytes(msg_data[0][1])
                    subj = msg.get('Subject', '')
                    body = ''
                    if msg.is_multipart():
                        for p in msg.walk():
                            if p.get_content_type() == 'text/plain':
                                raw = p.get_payload(decode=True)
                                body = raw.decode('utf-8', errors='ignore') if isinstance(raw, bytes) else raw
                                break
                    else:
                        raw = msg.get_payload(decode=True)
                        body = raw.decode('utf-8', errors='ignore') if isinstance(raw, bytes) else raw
                    subj_lower = subj.lower()
                    if any(x in subj_lower for x in ['verify', 'confirm', 'cloudflare']):
                        log("Email: " + subj)
                        mail.store(msg_id, '+FLAGS', '\\Deleted')
                        links = re.findall(r'https?://[^\s<>"\'<]+', body)
                        for link in links:
                            if any(x in link.lower() for x in ['verify', 'confirm', 'click']):
                                log("Link: " + link[:70])
                                mail.logout()
                                return link
                mail.logout()
            else:
                mail.logout()
        except Exception as e:
            log("IMAP: " + str(e))
        if i < timeout // 5 - 1:
            log("Tunggu email... (" + str(i+1) + "/" + str(timeout//5) + ")")
            time.sleep(5)
    return None

def main():
    email = gen_email()
    password = gen_password()
    log("=== CF Signup ===")
    log("Email: " + email)
    log("Signup...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/125.0.0.0 Mobile Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Origin': 'https://dash.cloudflare.com',
        'Referer': 'https://dash.cloudflare.com/sign-up',
    }
    try:
        r = requests.post('https://dash.cloudflare.com/api/v4/user/create',
            json={"email": email, "password": password},
            headers=headers, timeout=30)
        log("Status: " + str(r.status_code))
        if r.status_code == 200:
            log("=== ACCOUNT CREATED! ===")
            link = wait_email()
            if link:
                log("Verifikasi...")
                r2 = requests.get(link, timeout=20, allow_redirects=True)
                log("Verified: " + str(r2.status_code))
                return True
            else:
                log("Email tidak ketemu!")
                return False
        elif r.status_code == 400:
            log(str(r.json()))
            return False
        else:
            log(str(r.status_code) + ": " + r.text[:200])
            return False
    except Exception as e:
        log("Error: " + str(e))
        return False

if __name__ == "__main__":
    ok = main()
    exit(0 if ok else 1)
