#!/usr/bin/env python3
"""CF Signup Main Pipeline - Orchestrates N workers, auto-backup to GitHub"""
import os, sys, json, time, subprocess, threading, requests
from pathlib import Path
from datetime import datetime

# ============ CONFIG ============
TARGET = int(os.environ.get('TARGET', '200000'))
WORKERS = int(os.environ.get('WORKERS', '3'))
BACKUP_EVERY = int(os.environ.get('BACKUP_EVERY', '100'))

WORKER_SCRIPT = '/root/cf-automation-suite/cf_worker_v1.py'
ACCOUNTS_FILE = Path('/root/cf-automation-suite/accounts_new.txt')
PROGRESS_FILE = Path('/root/cf-automation-suite/progress.json')
LOG_DIR = Path('/tmp/cf_workers_logs')
LOG_DIR.mkdir(exist_ok=True)

GITHUB_REPO = 'Hilnal23/cf-automation-suite'
GITHUB_USER = 'Hilmal23'

# ============ LOGGING ============
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

# ============ PROGRESS ============
def load_progress():
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {'count': 0, 'total_attempts': 0, 'backups': 0, 'start_time': datetime.now().isoformat()}

def save_progress(p):
    PROGRESS_FILE.write_text(json.dumps(p, indent=2))

def load_accounts():
    if not ACCOUNTS_FILE.exists():
        return []
    accounts = []
    for line in ACCOUNTS_FILE.read_text().strip().split('\n'):
        if line.strip():
            try:
                accounts.append(json.loads(line))
            except:
                pass
    return accounts

# ============ BACKUP TO GITHUB ============
def backup_to_github():
    """Backup accounts via file sharing (GitHub not available)"""
    accounts = load_accounts()
    count = len(accounts)
    log(f"BACKUP: {count} accounts saved")
    
    # Save to local backup with timestamp
    backup_file = Path(f'/root/cf-automation-suite/accounts_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
    backup_file.write_text(ACCOUNTS_FILE.read_text())
    log(f"Local backup: {backup_file}")
    return count

# ============ WORKER THREAD ============
def run_worker(worker_id):
    log_file = LOG_DIR / f'worker_{worker_id}.log'
    cmd = f'python3 {WORKER_SCRIPT} WORKER_ID={worker_id >> {log_file} 2>&1 &'
    
    proc = subprocess.Popen(
        ['python3', WORKER_SCRIPT],
        env={**os.environ, 'WORKER_ID': str(worker_id)},
        stdout=open(log_file, 'w'),
        stderr=subprocess.STDOUT,
    )
    return proc

# ============ MAIN LOOP ============
def main():
    log(f"=== CF Signup Pipeline ===")
    log(f"Target: {TARGET} accounts | Workers: {WORKERS}")
    
    p = load_progress()
    log(f"Resuming from {p['count']} accounts")
    
    # Start workers
    workers = []
    for i in range(WORKERS):
        t = threading.Thread(target=run_worker, args=(i,))
        t.start()
        workers.append(t)
        time.sleep(2)
    
    log(f"All {WORKERS} workers started")
    
    # Main loop - check progress every 30s
    while True:
        time.sleep(30)
        accounts = load_accounts()
        count = len(accounts)
        
        # Update progress
        p['count'] = count
        save_progress(p)
        
        log(f"Progress: {count}/{TARGET} accounts")
        
        # Auto-backup every BACKUP_EVERY
        if count > 0 and count % BACKUP_EVERY == 0 and count != p.get('last_backup', 0):
            p['last_backup'] = count
            backup_to_github()
        
        if count >= TARGET:
            log(f"TARGET REACHED: {count} accounts!")
            backup_to_github()
            break
        
        # Check if all workers died
        alive = sum(1 for w in workers if w.is_alive())
        log(f"Workers alive: {alive}/{WORKERS}")
        
        if alive == 0 and count < p['count']:
            log("All workers died - restart loop")
            workers = []
            for i in range(WORKERS):
                t = threading.Thread(target=run_worker, args=(i,))
                t.start()
                workers.append(t)
                time.sleep(2)

if __name__ == '__main__':
    main()
