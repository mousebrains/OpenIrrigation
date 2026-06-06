import logging

from databaseMaintenance import POLICIES, prune_table


class FakeCursor:
    def __init__(self, rowcount, params):
        self.rowcount = rowcount
        self.params = params

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, _statement, params):
        self.params.append(params)


class FakeConnection:
    def __init__(self, counts):
        self.counts = iter(counts)
        self.commits = 0
        self.params = []

    def cursor(self):
        return FakeCursor(next(self.counts), self.params)

    def commit(self):
        self.commits += 1


def test_prune_table_commits_each_bounded_batch():
    conn = FakeConnection([5000, 5000, 12])

    count = prune_table(conn, "currentlog", "timestamp", 365, 5000, 100000, logging.getLogger())

    assert count == 10012
    assert conn.commits == 3


def test_nonpositive_retention_disables_pruning():
    conn = FakeConnection([])

    assert prune_table(conn, "currentlog", "timestamp", 0, 5000, 100000, logging.getLogger()) == 0
    assert conn.commits == 0


def test_prune_table_stops_at_per_run_limit():
    conn = FakeConnection([5000, 2000])

    count = prune_table(conn, "currentlog", "timestamp", 365, 5000, 7000, logging.getLogger())

    assert count == 7000
    assert conn.commits == 2
    assert conn.params == [(365, 5000), (365, 2000)]


def test_quoted_policy_identifiers_match_postgresql_catalog_names():
    assert all(table == table.lower() and column == column.lower() for table, column, _ in POLICIES)
