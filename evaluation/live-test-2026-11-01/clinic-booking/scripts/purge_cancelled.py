"""Delete cancelled appointments older than N days from the production database."""

import argparse
import os
import sqlite3
from datetime import datetime, timedelta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--db", default=os.environ.get("PROD_DB_PATH", "data/production.db"))
    args = parser.parse_args()
    cutoff = (datetime.now() - timedelta(days=args.days)).isoformat(timespec="minutes")
    conn = sqlite3.connect(args.db)
    deleted = conn.execute(
        "DELETE FROM appointments WHERE status = 'cancelled' AND start < ?", (cutoff,)).rowcount
    conn.commit()
    print(f"deleted {deleted} cancelled appointments")


if __name__ == "__main__":
    main()
