import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from database import DB_PATH, sync_data
from llm_engine import generate_audit_report

st.set_page_config(page_title="AutoAds Analyst", layout="wide")

st.title("🚀 AutoAds Forensic Analyst")
st.markdown("Automated Google Ads Data Scraping, Auditing, and AI Analysis.")

# Initialize DB connection to get accounts
def get_accounts():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT account_name FROM campaign_stats ORDER BY account_name")
        accounts = [row[0] for row in cursor.fetchall()]
        conn.close()
        return accounts
    except:
        return []

def get_dataframe(account_name):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, SUM(cost) as cost, SUM(conversions) as conversions FROM campaign_stats WHERE account_name = ? GROUP BY date ORDER BY date",
        conn, params=(account_name,)
    )
    conn.close()
    
    # Calculate daily CPA safely
    df['cpa'] = df.apply(lambda row: row['cost'] / row['conversions'] if row['conversions'] > 0 else 0, axis=1)
    return df

# Sidebar
st.sidebar.header("Controls")
if st.sidebar.button("🔄 Sync Local CSVs to DB"):
    with st.spinner("Parsing CSVs..."):
        sync_data()
    st.sidebar.success("Database synced successfully!")
    st.rerun()

accounts = get_accounts()

if not accounts:
    st.warning("No data found in the database. Please click 'Sync Local CSVs to DB' in the sidebar.")
else:
    selected_account = st.sidebar.selectbox("Select Account to Analyze:", accounts)
    
    st.header(f"Account Overview: {selected_account.upper()}")
    
    df = get_dataframe(selected_account)
    
    if df.empty:
        st.info("No data available for this account.")
    else:
        # Metrics
        total_cost = df['cost'].sum()
        total_conv = df['conversions'].sum()
        avg_cpa = total_cost / total_conv if total_conv > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Spend", f"¥{total_cost:,.0f}")
        col2.metric("Total Conversions", f"{total_conv:,.0f}")
        col3.metric("Avg CPA", f"¥{avg_cpa:,.0f}")
        
        # Charts
        st.subheader("Performance Trends")
        fig1 = px.line(df, x='date', y=['cost', 'conversions'], title='Daily Spend & Conversions')
        st.plotly_chart(fig1, use_container_width=True)
        
        fig2 = px.bar(df, x='date', y='cpa', title='Daily CPA (Cost Per Acquisition)')
        st.plotly_chart(fig2, use_container_width=True)
        
        # AI Analyst Brain
        st.divider()
        st.subheader("🧠 AutoAds AI Brain Analysis")
        
        api_key = st.text_input("Enter OpenAI API Key (optional, for AI Analysis):", type="password")
        
        if st.button("Generate AI Forensic Audit"):
            if not api_key:
                st.error("Please enter an API Key to run the Brain.")
            else:
                import os
                os.environ["OPENAI_API_KEY"] = api_key
                
                with st.spinner("Analyzing gigabytes of metrics and simulating forensic audit..."):
                    report = generate_audit_report(selected_account)
                
                st.markdown("### AI Report Output")
                st.markdown(report)
