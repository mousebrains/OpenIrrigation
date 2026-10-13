#!/usr/bin/env python3
"""
Build a fresh OpenIrrigation database the way 'make -C database freshdb'
does, without psql or sudo, for the SQL-level tests and the CI migration job.

The connection comes from the libpq environment (PGHOST, PGPORT, PGUSER,
PGPASSWORD) and must be able to CREATE ROLE and CREATE DATABASE.  As in
production, everything is owned by the parent role (irrparent): the schema
is loaded under SET ROLE instead of database/Makefile's trailing
'REASSIGN OWNED BY CURRENT_USER', which a superuser cannot be the source of.

Usage:
    python3 tests_sql/load_schema.py --db oi_ci
"""

import argparse
import os

import psycopg
from psycopg import sql

DBDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database")

# Same files, same order, as SQL in database/Makefile
FILES = (
    "db.schema.sql", "db.site.sql", "db.funcs.sql", "db.list.sql", "db.params.sql",
    "db.ET.sql", "db.soil.sql", "db.crop.sql", "db.changelog.sql",
)

PARENT = "irrparent"


def readSQL(fn: str) -> str:
    """File contents minus psql meta-commands (e.g. db.funcs.sql's \\o)."""
    with open(os.path.join(DBDIR, fn)) as fp:
        return "".join(ln for ln in fp if not ln.lstrip().startswith("\\"))


def createDB(dbName: str) -> None:
    with psycopg.connect(dbname="postgres", autocommit=True) as db:
        if not db.execute("SELECT 1 FROM pg_roles WHERE rolname=%s;", (PARENT,)).fetchone():
            db.execute(sql.SQL("CREATE ROLE {} NOSUPERUSER CREATEDB NOLOGIN;")
                       .format(sql.Identifier(PARENT)))
        db.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE);").format(sql.Identifier(dbName)))
        db.execute(sql.SQL("CREATE DATABASE {} OWNER {};")
                   .format(sql.Identifier(dbName), sql.Identifier(PARENT)))


def loadSchema(dbName: str) -> None:
    with psycopg.connect(dbname=dbName) as db:
        db.execute("SET client_min_messages=WARNING;")
        db.execute(sql.SQL("SET ROLE {};").format(sql.Identifier(PARENT)))
        for fn in FILES:
            db.execute(readSQL(fn))
        db.execute("RESET ROLE;")
        db.commit()


def dropDB(dbName: str) -> None:
    with psycopg.connect(dbname="postgres", autocommit=True) as db:
        db.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE);").format(sql.Identifier(dbName)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a fresh OpenIrrigation database")
    parser.add_argument("--db", required=True, help="Database to (re)create")
    args = parser.parse_args()
    createDB(args.db)
    loadSchema(args.db)
    print(f"Created {args.db} from {', '.join(FILES)}")


if __name__ == "__main__":
    main()
