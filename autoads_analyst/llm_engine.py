import sqlite3
import os
import json
try:
    from openai import OpenAI
except ImportError:
    pass # Will be handled by requirements

DB_PATH = 'auto_ads.db'

# The core prompt that turns the LLM into our Forensic Auditor
SYSTEM_PROMPT = """
You are an elite Google Ads Forensic Auditor and Data Analyst.
Your job is to analyze the provided raw campaign metrics and identify issues, anomalies, or areas of wasted spend.

You will be given JSON data representing the daily performance of various campaigns for a specific account.
Pay special attention to:
1. Massive spikes in Cost/Spend without corresponding Conversions.
2. Drastic increases in CPA (Cost Per Acquisition).
3. Any sudden drops in Conversions which could indicate broken tags.

Output your analysis in beautiful GitHub-flavored Markdown. 
Structure your response as follows:
- **Executive Summary:** A 2-3 sentence overview of the account's health.
- **Key Anomalies:** Bullet points of any suspicious spikes or drops, including exact dates and numbers.
- **Actionable Recommendations:** What the account manager should do next (e.g. check change history, revert bid strategy, pause keywords).

Be direct, analytical, and professional.
"""

def get_account_data(account_name):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT date, campaign_name, SUM(cost) as cost, SUM(clicks) as clicks, SUM(conversions) as conversions
        FROM campaign_stats
        WHERE account_name = ?
        GROUP BY date, campaign_name
        ORDER BY date ASC
    ''', (account_name,))
    
    rows = cursor.fetchall()
    conn.close()
    
    data = []
    for r in rows:
        data.append(dict(r))
    return data

def generate_audit_report(account_name):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "Error: OPENAI_API_KEY environment variable is not set. Please set it to generate AI insights."
        
    client = OpenAI(api_key=api_key)
    
    # Get the raw data
    data = get_account_data(account_name)
    if not data:
        return f"No data found for account: {account_name}"
        
    # Summarize data slightly to avoid token limits if it's huge, but for now just pass as JSON
    data_str = json.dumps(data, indent=2)
    
    prompt = f"Here is the daily campaign performance data for the account '{account_name}':\n\n{data_str}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error communicating with OpenAI API: {e}"

if __name__ == "__main__":
    # Simple test for Kansai account (assuming no API key is set, it will return the error string safely)
    print(generate_audit_report('2_kansai'))
