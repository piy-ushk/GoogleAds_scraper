# Google Ads Audit System

A professional CSV-based Google Ads audit system for diagnosing account performance declines without using the Google Ads API yet.

The architecture is intentionally split into import, cleaning, analysis, scoring, visualization, reporting, and optional AI narration. Later, a Google Ads API collector can replace the CSV importer without changing the analysis engine.

## What It Does

- Accepts exported Google Ads CSV files in any combination:
  - Campaigns
  - Ad Groups
  - Keywords
  - Search Terms
  - Ads
  - Devices
  - Locations
  - Auction Insights
  - Change History
  - Conversions
  - Landing Pages
- Auto-detects report type from column names.
- Cleans currency, percentages, dates, missing values, duplicate rows, and summary rows.
- Normalizes metrics into canonical columns like `cost`, `clicks`, `impressions`, `conversions`, `ctr`, `conversion_rate`, and `cost_per_conversion`.
- Generates consultant-style findings with:
  - Reason
  - Evidence
  - Impact
  - Specific recommendation
  - Priority
  - Structured metrics
- Produces:
  - Streamlit dashboard
  - PDF audit report
  - Excel workbook
  - Structured JSON metrics
  - Optional OpenAI-generated narrative from computed metrics only

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run Dashboard

```powershell
streamlit run app.py
```

Upload any Google Ads CSV exports. The app will detect report types and run all compatible audit modules.

## Run CLI

```powershell
python -m google_ads_audit.cli exports\campaigns.csv exports\keywords.csv exports\search_terms.csv --output-dir reports
```

With optional AI explanation:

```powershell
$env:OPENAI_API_KEY="your_api_key"
python -m google_ads_audit.cli exports\campaigns.csv exports\keywords.csv --with-ai
```

AI receives only computed structured metrics JSON, not raw CSV rows.

## Recommended Google Ads Exports

For the locksmith audit, export at least:

1. Campaigns by day from January to July
2. Keywords by day
3. Search Terms by day
4. Devices by day
5. Locations by day
6. Auction Insights by month
7. Change History from April to June
8. Landing Pages with conversion metrics

The most important diagnostic comparison is January-April vs May-July, plus change history around May.

## Folder Structure

```text
google_ads_audit/
  analysis/
    campaign_audit.py
    keyword_audit.py
    search_term_audit.py
    conversion_audit.py
    segment_audits.py
    auction_audit.py
    change_history_audit.py
    landing_page_audit.py
    engine.py
  ai.py
  cleaning.py
  columns.py
  config.py
  models.py
  reporting.py
  scoring.py
  visualization.py
app.py
config/audit_config.yml
```

## Notes

The system does not claim certainty from thin data. It identifies likely performance drivers backed by computed evidence. For example:

- A campaign spent a high share of budget but contributed a low share of conversions.
- A keyword spent meaningful budget with zero conversions.
- CPA rose in the later half of the uploaded date range.
- A bid strategy or budget change appears in the change history near a performance drop.

This is the right foundation for a defensible paid audit.
