"""
SQL-level tests against a real PostgreSQL.

These run only when OI_TEST_PG is set; the server comes from the libpq
environment (PGHOST, PGPORT, PGUSER, PGPASSWORD) and the user must be able to
create roles and databases.  Locally, for example:

    OI_TEST_PG=1 PGHOST=127.0.0.1 PGPORT=54317 PGUSER=postgres python -m pytest tests_sql

Keep this directory separate from tests/: tests/conftest.py replaces psycopg
with a stub for the whole session, so run the two suites in separate pytest
invocations (as CI does).
"""

import os
import sys
import uuid

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

if not os.environ.get("OI_TEST_PG"):
    pytest.skip("OI_TEST_PG not set: no PostgreSQL for the SQL tests", allow_module_level=True)

import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

import load_schema  # noqa: E402


@pytest.fixture(scope="session")
def dbName():
    """A freshly built database for this test session, dropped afterwards."""
    name = "oi_test_" + uuid.uuid4().hex[:10]
    load_schema.createDB(name)
    load_schema.loadSchema(name)
    yield name
    load_schema.dropDB(name)


@pytest.fixture
def db(dbName):
    """A connection whose work is rolled back after each test."""
    with psycopg.connect(dbname=dbName, row_factory=dict_row) as conn:
        yield conn
        conn.rollback()


@pytest.fixture
def freshDB():
    """A private database for tests that must commit (e.g. migrations)."""
    name = "oi_test_" + uuid.uuid4().hex[:10]
    load_schema.createDB(name)
    load_schema.loadSchema(name)
    yield name
    load_schema.dropDB(name)
