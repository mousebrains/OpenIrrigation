import csv
import datetime
import gzip
import logging
import os

import pytest

import databaseMaintenance as dm
from databaseMaintenance import POLICIES, prune_table

T0 = datetime.datetime(2024, 9, 8, 12, 0, tzinfo=datetime.timezone.utc)


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, statement, params=None):
        self.conn.statements.append(statement)


class FakeConnection:
    """A table of (timestamp, value) rows behind next/copy/delete_batch"""

    def __init__(self, nrows):
        self.rows = [(T0 + datetime.timedelta(minutes=i), i) for i in range(nrows)]
        self.commits = 0
        self.rollbacks = 0
        self.deletes = 0
        self.statements = []

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def inRange(self, first, last):
        return [r for r in self.rows if first <= r[0] <= last]


@pytest.fixture
def fake(monkeypatch):
    """Replace the three SQL helpers with ones backed by a FakeConnection"""
    state = {"copyDrop": 0, "copyError": None, "deleteExtra": 0}

    def next_batch(cur, table, column, days, batch_size):
        rows = cur.conn.rows[:batch_size]
        if not rows:
            return None
        return rows[0][0], rows[-1][0], len(cur.conn.inRange(rows[0][0], rows[-1][0]))

    def copy_batch(cur, table, column, first, last, out):
        if state["copyError"]:
            raise state["copyError"]
        lines = ["timestamp,value\n"] + [f"{t.isoformat()},{v}\n" for t, v in cur.conn.inRange(first, last)]
        out.write("".join(lines[:len(lines) - state["copyDrop"]]).encode())

    def delete_batch(cur, table, column, first, last):
        cur.conn.deletes += 1
        n = len(cur.conn.inRange(first, last))
        cur.conn.rows = [r for r in cur.conn.rows if not first <= r[0] <= last]
        return n + state["deleteExtra"]

    monkeypatch.setattr(dm, "next_batch", next_batch)
    monkeypatch.setattr(dm, "copy_batch", copy_batch)
    monkeypatch.setattr(dm, "delete_batch", delete_batch)
    return state


def archived(path):
    with gzip.open(path, "rt", newline="") as fp:
        return list(csv.reader(fp))


def prune(conn, archive_dir, batch_size=5, max_rows=100000, days=365):
    return prune_table(conn, str(archive_dir), "currentlog", "timestamp", days, batch_size, max_rows,
                       logging.getLogger())


def test_prune_table_archives_then_commits_each_bounded_batch(fake, tmp_path):
    conn = FakeConnection(12)

    assert prune(conn, tmp_path) == 12

    assert conn.commits == 3
    assert conn.rows == []
    files = sorted(os.listdir(tmp_path))
    assert files == ["currentlog.20240908T120000Z.20240908T120400Z.csv.gz",
                     "currentlog.20240908T120500Z.20240908T120900Z.csv.gz",
                     "currentlog.20240908T121000Z.20240908T121100Z.csv.gz"]
    assert (os.stat(tmp_path / files[0]).st_mode & 0o777) == 0o640
    rows = archived(tmp_path / files[0])
    assert rows[0] == ["timestamp", "value"]
    assert [r[1] for r in rows[1:]] == ["0", "1", "2", "3", "4"]
    # each transaction pins one snapshot for the count, COPY and DELETE
    assert conn.statements.count("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ") == 3


def test_nonpositive_retention_disables_pruning(fake, tmp_path):
    conn = FakeConnection(3)

    assert prune(conn, tmp_path, days=0) == 0
    assert conn.commits == 0
    assert len(conn.rows) == 3


def test_prune_table_stops_at_per_run_limit(fake, tmp_path):
    conn = FakeConnection(12)

    assert prune(conn, tmp_path, max_rows=7) == 7
    assert conn.commits == 2
    assert len(conn.rows) == 5
    assert len(os.listdir(tmp_path)) == 2


def test_short_archive_never_deletes(fake, tmp_path):
    fake["copyDrop"] = 1  # the COPY loses a row
    conn = FakeConnection(3)

    with pytest.raises(dm.ArchiveError):
        prune(conn, tmp_path)
    assert conn.deletes == 0
    assert conn.commits == 0
    assert conn.rollbacks == 1
    assert os.listdir(tmp_path) == []  # no archive, not even a temporary file


def test_failed_copy_never_deletes(fake, tmp_path):
    fake["copyError"] = OSError("disk full")
    conn = FakeConnection(3)

    with pytest.raises(OSError):
        prune(conn, tmp_path)
    assert conn.deletes == 0
    assert conn.commits == 0
    assert os.listdir(tmp_path) == []


def test_delete_count_mismatch_rolls_back(fake, tmp_path):
    fake["deleteExtra"] = 1
    conn = FakeConnection(3)

    with pytest.raises(dm.ArchiveError):
        prune(conn, tmp_path)
    assert conn.commits == 0
    assert conn.rollbacks == 1


def test_archive_never_overwrites(tmp_path):
    name = dm.archive_name(str(tmp_path), "sensorlog", T0, T0)
    assert os.path.basename(name) == "sensorlog.20240908T120000Z.20240908T120000Z.csv.gz"
    open(name, "w").close()
    assert dm.archive_name(str(tmp_path), "sensorlog", T0, T0).endswith(
        "sensorlog.20240908T120000Z.20240908T120000Z.1.csv.gz")


def test_archive_dir_is_required(tmp_path, caplog):
    logger = logging.getLogger("test")
    with caplog.at_level(logging.WARNING):
        assert not dm.check_archive_dir("", logger)
        assert not dm.check_archive_dir(str(tmp_path / "missing"), logger)
    assert "refusing to delete" in caplog.text
    assert dm.check_archive_dir(str(tmp_path), logger)


def test_main_without_archive_dir_deletes_nothing(monkeypatch):
    monkeypatch.setattr("sys.argv", ["databaseMaintenance.py", "--db=x", "--archive-dir="])

    def connect(**kwargs):
        raise AssertionError("must not connect")

    monkeypatch.setattr(dm.psycopg, "connect", connect)
    with pytest.raises(SystemExit) as exc:
        dm.main()
    assert exc.value.code == 1


def test_quoted_policy_identifiers_match_postgresql_catalog_names():
    assert all(table == table.lower() and column == column.lower() for table, column, _ in POLICIES)
