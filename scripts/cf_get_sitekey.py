#!/usr/bin/env python3
import requests, re

r = requests.get('https://dash.cloudflare.com/assets/cf-TurnstileWidget.Ct3Nawi5.js', timeout=15)
text = r.text
print(f'JS size: {len(text)}')

# Find ALL potential sitekeys (20+ char alphanumeric strings)
potential = re.findall(r'["\'][\da-zA-Z_-]{20,50}["\']', text)
print(f'Potential keys (20+ chars): {len(potential)}')
for p in potential[:20]:
    print(f'  {p}')

# Try render parameter
renders = re.findall(r'render["\s:]*["\']([a-zA-Z0-9_-]{10,})["\']', text)
print(f'\nRender tokens: {renders[:5]}')

# Look for sitekey specifically
for pattern in [
    r'sitekey["\s:]*["\']([a-zA-Z0-9_-]{20,})',
    r'challenge["\s:].*?["\']([a-zA-Z0-9_-]{20,})',
    r'token.*?["\']([a-zA-Z0-9_-]{30,})',
]:
    found = re.findall(pattern, text)
    if found:
        print(f'Pattern {pattern[:30]}: {found[:3]}')

# Also check the oneshot challenge URL we captured
oneshot_url = 'https://dash.cloudflare.com/cdn-cgi/challenge-platform/h/b/jsd/oneshot/80a697ecdece/0.89070798149694'
r2 = requests.get(oneshot_url, timeout=15)
print(f'\nOneshot JS size: {len(r2.text)}')
sk = re.findall(r'sitekey["\s:]*["\']([a-zA-Z0-9_-]{20,})', r2.text)
print(f'Sitekey from oneshot: {sk[:3]}')