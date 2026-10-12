"""Tests for scripts/notifyFailure.py — the OnFailure= email: holdoff per
unit, and root when the database is down."""

import logging
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import notifyFailure as NF


class Cursor:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeDB:
    """DB.DB: cursor() raises NoConnection when the database is down."""
    def __init__(self, down):
        self.down = down

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self, qDict=False):
        if self.down:
            raise NF.DB.NoConnection("down")
        return Cursor()


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    env = types.SimpleNamespace(sent=[], down=False)
    monkeypatch.setattr(NF.DB, "DB", lambda db, logger: FakeDB(env.down))
    monkeypatch.setattr(NF, "unitStatus", lambda unit: f"* {unit} - failed\n")

    def sendReport(cur, key, subject, body, logger, mailFrom=None, fallback=True):
        env.sent.append((type(cur).__name__, key, subject))
        return ["root"]
    monkeypatch.setattr(NF.Notify, "sendReport", sendReport, raising=False)
    env.args = types.SimpleNamespace(db="x", unit="OISched.service", holdoff=6.0, mailFrom=None)
    return env


def test_reports_once_per_holdoff(env):
    log = logging.getLogger("test")
    NF.report(env.args, log)
    NF.report(env.args, log)
    assert [k for (_, k, _) in env.sent] == ["systemd"]
    assert env.sent[0][2].startswith("OISched.service failed on ")
    assert os.path.exists(NF.stampFile("OISched.service"))


def test_units_are_separate(env):
    NF.report(env.args, logging.getLogger("test"))
    env.args.unit = "OIFlowSensorWatch.service"
    NF.report(env.args, logging.getLogger("test"))
    assert len(env.sent) == 2


def test_database_down_goes_to_root(env):
    env.down = True
    NF.report(env.args, logging.getLogger("test"))
    assert env.sent[0][0] == "NoSubscribers"
    cur = NF.NoSubscribers()
    cur.execute("SELECT 1")
    assert cur.fetchall() == []


def test_holdoff_expired(env):
    NF.report(env.args, logging.getLogger("test"))
    stamp = NF.stampFile("OISched.service")
    old = os.path.getmtime(stamp) - 7 * 3600
    os.utime(stamp, (old, old))
    NF.report(env.args, logging.getLogger("test"))
    assert len(env.sent) == 2


def test_stamp_file_name_is_safe():
    assert NF.stampFile("../x y.service") == "OIFailure-.._x_y.service.stamp"
    assert "/" not in NF.stampFile("a/b")
