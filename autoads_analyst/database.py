import sqlite3
import os
import codecs
import csv
import glob

DB_PATH = 'auto_ads.db'
DATA_DIR = '../data'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Campaigns Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS campaign_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_name TEXT,
        date TEXT,
        campaign_name TEXT,
        cost REAL,
        clicks INTEGER,
        conversions REAL,
        UNIQUE(account_name, date, campaign_name)
    )
    ''')
    
    conn.commit()
    return conn

def clean_currency(val):
    if not val: return 0.0
    val = val.replace('£', '').replace('JP¥', '').replace(',', '').strip()
    try:
        return float(val)
    except:
        return 0.0

def clean_int(val):
    if not val: return 0
    val = val.replace(',', '').strip()
    try:
        return int(float(val))
    except:
        return 0

def clean_float(val):
    if not val: return 0.0
    val = val.replace(',', '').strip()
    try:
        return float(val)
    except:
        return 0.0

def process_campaign_report(filepath, account_name, conn):
    cursor = conn.cursor()
    
    try:
        with codecs.open(filepath, 'r', encoding='utf-16') as f:
            content = f.read()
    except:
        with codecs.open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
    lines = content.split('\n')
    header_idx = -1
    for i, l in enumerate(lines):
        if 'Day' in l and 'Campaign' in l:
            header_idx = i
            break
            
    if header_idx == -1:
        print(f"Skipping {filepath}, no header found.")
        return

    reader = csv.reader(lines[header_idx:], delimiter='\t')
    headers = next(reader)
    
    # Map column indices
    col_map = {h.lower(): i for i, h in enumerate(headers)}
    if 'day' not in col_map or 'campaign' not in col_map: return
    
    for row in reader:
        if len(row) < 3: continue
        
        day = row[col_map.get('day')]
        campaign = row[col_map.get('campaign')]
        
        # Skip totals and junk
        if 'Total' in day or '--' in day or 'Total' in campaign: continue
        if not day.strip(): continue
        
        cost_idx = col_map.get('cost')
        clicks_idx = col_map.get('clicks')
        conv_idx = col_map.get('conversions')
        
        cost = clean_currency(row[cost_idx]) if cost_idx is not None else 0.0
        clicks = clean_int(row[clicks_idx]) if clicks_idx is not None else 0
        conversions = clean_float(row[conv_idx]) if conv_idx is not None else 0.0
        
        # Insert or ignore duplicate
        cursor.execute('''
            INSERT OR IGNORE INTO campaign_stats (account_name, date, campaign_name, cost, clicks, conversions)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (account_name, day, campaign, cost, clicks, conversions))
        
    conn.commit()

def sync_data():
    conn = init_db()
    
    # Scan all directories in data/
    if not os.path.exists(DATA_DIR):
        print(f"Data directory {DATA_DIR} not found.")
        return
        
    for account_dir in os.listdir(DATA_DIR):
        full_dir = os.path.join(DATA_DIR, account_dir)
        if os.path.isdir(full_dir):
            account_name = account_dir.replace('account_', '').strip()
            # Look for campaign reports
            for f in os.listdir(full_dir):
                if 'campaign report' in f.lower() and f.endswith('.csv'):
                    filepath = os.path.join(full_dir, f)
                    print(f"Processing {filepath}...")
                    process_campaign_report(filepath, account_name, conn)
                    
    print("Database sync complete!")
    conn.close()

if __name__ == "__main__":
    sync_data()
