#!/usr/bin/env python3
"""Add the historical completion-time index used by retention maintenance."""

import argparse
import sys

try:
    import psycopg
except ImportError:
    sys.exit("psycopg is required: pip install psycopg[binary]")


def migrate(db, dry_run: bool) -> bool:
    with db.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_catalog.pg_indexes WHERE indexname=%s;",
            ("historical_toff_index",),
        )
        if cur.fetchone() is not None:
            print("historical_toff_index already exists")
            return False
        cur.execute("CREATE INDEX historical_toff_index ON historical(toff);")

    if dry_run:
        db.rollback()
        print("DRY RUN - index creation rolled back")
    else:
        db.commit()
        print("Created historical_toff_index")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Database name")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        db = psycopg.connect(dbname=args.db)
    except Exception as exc:
        sys.exit(f"Cannot connect to database {args.db!r}: {exc}")

    try:
        migrate(db, args.dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    main()
