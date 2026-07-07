import os
import glob
import pandas as pd

DATA_DIR = r"c:\Users\Piyush Kulkarni\OneDrive\Documents\GoogleAds_scraper\data"

def check_account_data():
    accounts = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
    
    expected_files = [
        "Search terms report.csv",
        "Change history report.csv",
        "Auction insights report.csv",
        "Campaign performance.csv" # or Untitled report.csv
    ]
    
    print("=== Google Ads Multi-Account Data Status ===")
    all_ready = True
    for account in accounts:
        acc_path = os.path.join(DATA_DIR, account)
        files = os.listdir(acc_path)
        print(f"\n[{account}]")
        
        found_csvs = [f for f in files if f.endswith('.csv')]
        if not found_csvs:
            print("  -> STATUS: Empty. Waiting for CSV exports.")
            all_ready = False
            continue
            
        print(f"  -> Found {len(found_csvs)} CSV files.")
        for f in found_csvs:
            print(f"     - {f}")
            
    if all_ready and len(accounts) > 0:
        print("\nAll accounts have data! Ready to run deep analysis.")
    else:
        print("\nAction Required: Please export the required CSV reports from Google Ads and place them in their respective folders.")

if __name__ == "__main__":
    check_account_data()
