#!/usr/bin/env python3
"""CF Signup - minimal, runs on ANY machine"""
import subprocess, sys

def log(msg):
    print(f"[+] {msg}", flush=True)

def run(cmd):
    log(f"Running: {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(r.stdout, r.stderr)
    return r.returncode == 0

log("Checking Python...")
if not run("python3 --version"): exit(1)

log("Installing Playwright...")
run("pip install playwright requests 2>&1 | tail -3")
run("python3 -m playwright install chromium 2>&1 | tail -3")

log("Ready! Run the signup script now.")
log("Usage: python3 cf_signup_simple.py")