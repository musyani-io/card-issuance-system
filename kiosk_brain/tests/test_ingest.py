"""
Live ingestion smoke test for the kiosk Pi workflow.

This script exercises the real ingest path:
- calls the university API through modules.database.ingest_card()
- generates OTP / temp PIN when required
- sends SMS and email through modules.sms_client
- writes the kiosk_db records and audit log entries

Usage:
    cd kiosk_brain
    python tests/test_ingest.py --reg-number 2022-04-09050

Optional:
    python tests/test_ingest.py --reg-number 2022-04-09050 --db-path /path/to/kiosk.db

Warning:
    Running this script may send real SMS and email messages to the student
    contact details stored in the local kiosk database.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a live card ingestion smoke test")
    parser.add_argument(
        "--reg-number",
        help="Registration number to ingest",
    )
    parser.add_argument(
        "--db-path",
        help="Optional SQLite database path override",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    reg_number = args.reg_number or input("Enter registration number: ").strip()
    if not reg_number:
        print("Registration number is required.")
        return 1

    db_path = args.db_path or os.getenv("KIOSK_DB_PATH")
    if db_path:
        os.environ["KIOSK_DB_PATH"] = db_path

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    )

    print("Starting live ingestion test...")
    print(f"Registration number: {reg_number}")
    if db_path:
        print(f"Database path: {db_path}")
    print("This will call the real API and may send real SMS/email messages.")

    try:
        from modules.database import ingest_card, get_student_from_db

        result = ingest_card(reg_number)
        print("\nIngest result:")
        print(result)

        if result.get("success"):
            lookup = get_student_from_db(reg_number)
            print("\nLocal kiosk_db lookup after ingest:")
            print(lookup)
            print("\nStatus: ingest completed successfully.")
            if result.get("credentials_sent"):
                print("Credentials were sent successfully.")
            else:
                print("Ingest succeeded, but credential delivery reported failure.")
            return 0

        print("\nStatus: ingest failed.")
        print(f"Failed step: {result.get('step')}")
        print(f"Error: {result.get('error')}")
        return 2
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    except Exception as exc:
        print("\nUnexpected error during live ingestion test:")
        print(exc)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())