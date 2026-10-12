"""dailyReport.addShortfalls: today's and tomorrow's scheduler shortfalls."""

import datetime
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import dailyReport  # noqa: E402
from helpers import FakeCursor  # noqa: E402

TODAY = datetime.date(2026, 10, 11)
TBL = '<html><body><table></table></body></html>'


class FakeDB:
    def __init__(self, cur):
        self.cur = cur
        self.rolledBack = False

    def cursor(self):
        cur = self.cur

        class Ctx:
            def __enter__(self):
                return cur

            def __exit__(self, *a):
                return False
        return Ctx()

    def rollback(self):
        self.rolledBack = True


def test_rows_are_added_before_body_end():
    cur = FakeCursor([('FROM shortfall', [
        (TODAY, 'Hierbas', 'Bebedero', 2.0, 0.0),
        (TODAY, 'Lawn <&>', 'Oeste', 75.0, 52.5)])])
    out = dailyReport.addShortfalls(TBL, FakeDB(cur), TODAY, logging.getLogger('t'))
    assert out.endswith('</table>\n</body></html>')
    assert 'Bebedero' in out and '52.5' in out
    assert 'Lawn &lt;&amp;&gt;' in out  # escaped
    assert cur.executed[0][1] == (TODAY, TODAY + datetime.timedelta(days=1))


def test_no_rows_leaves_report_alone():
    out = dailyReport.addShortfalls(TBL, FakeDB(FakeCursor()), TODAY, logging.getLogger('t'))
    assert out == TBL


def test_missing_table_never_blocks_the_report():
    db = FakeDB(FakeCursor([('FROM shortfall', RuntimeError('relation does not exist'))]))
    out = dailyReport.addShortfalls(TBL, db, TODAY, logging.getLogger('t'))
    assert out == TBL
    assert db.rolledBack
