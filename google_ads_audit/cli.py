from __future__ import annotations

import argparse
import logging
from pathlib import Path

from google_ads_audit.ai import generate_ai_summary
from google_ads_audit.analysis import run_audit
from google_ads_audit.cleaning import read_google_ads_csv
from google_ads_audit.config import load_config
from google_ads_audit.reporting import export_excel, export_json, export_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Google Ads audit from exported CSV files.")
    parser.add_argument("csv_files", nargs="+", help="Google Ads CSV exports")
    parser.add_argument("--config", default="config/audit_config.yml", help="Audit config YAML")
    parser.add_argument("--output-dir", default="reports", help="Report output directory")
    parser.add_argument("--with-ai", action="store_true", help="Generate OpenAI narrative if OPENAI_API_KEY is set")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    config = load_config(args.config)
    imported = [read_google_ads_csv(path, source_name=Path(path).name) for path in args.csv_files]
    result = run_audit(imported, config)
    if args.with_ai:
        result.ai_summary = generate_ai_summary(result.metrics)

    output_dir = Path(args.output_dir)
    export_json(result, output_dir / "audit_metrics.json")
    export_excel(result, output_dir / "google_ads_audit.xlsx")
    export_pdf(result, output_dir / "google_ads_audit.pdf")
    print(f"Overall score: {result.scores.overall}/100")
    print(f"Findings: {len(result.findings)}")
    print(f"Reports written to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
