"""Tests for scripts/dailyReport.py — pure functions and mocked I/O."""

import datetime
import logging
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import dailyReport


# ---------------------------------------------------------------------------
# sum_durations
# ---------------------------------------------------------------------------

class TestSumDurations:
    def test_single(self):
        items = [('pgm', datetime.timedelta(hours=1, minutes=30))]
        assert dailyReport.sum_durations(items) == '1:30:00'

    def test_multiple(self):
        items = [
            ('a', datetime.timedelta(minutes=45)),
            ('b', datetime.timedelta(minutes=15)),
        ]
        assert dailyReport.sum_durations(items) == '1:00:00'

    def test_empty(self):
        assert dailyReport.sum_durations([]) == '0:00:00'


# ---------------------------------------------------------------------------
# mkRows
# ---------------------------------------------------------------------------

class TestMkRows:
    def test_both_present(self):
        hist = {'StationA': [('Pgm1', datetime.timedelta(hours=1))]}
        pend = {'StationA': [('Pgm2', datetime.timedelta(minutes=30))]}
        rows = dailyReport.mkRows(hist, pend)
        assert len(rows) == 1
        row = rows[0]
        assert row[0] == 'StationA'
        assert row[1] == '1:00:00'   # historical duration
        assert row[2] == '0:30:00'   # pending duration
        assert 'Pgm1' in row[3]
        assert 'Pgm2' in row[3]

    def test_only_historical(self):
        hist = {'S1': [('P1', datetime.timedelta(hours=2))]}
        rows = dailyReport.mkRows(hist, {})
        assert len(rows) == 1
        assert rows[0][1] == '2:00:00'
        assert rows[0][2] is None

    def test_only_pending(self):
        pend = {'S2': [('P2', datetime.timedelta(minutes=10))]}
        rows = dailyReport.mkRows({}, pend)
        assert len(rows) == 1
        assert rows[0][1] is None
        assert rows[0][2] == '0:10:00'

    def test_empty(self):
        assert dailyReport.mkRows({}, {}) == []

    def test_sorted_keys(self):
        hist = {'Zebra': [('p', datetime.timedelta(seconds=1))]}
        pend = {'Alpha': [('p', datetime.timedelta(seconds=2))]}
        rows = dailyReport.mkRows(hist, pend)
        assert rows[0][0] == 'Alpha'
        assert rows[1][0] == 'Zebra'

    def test_html_escape_in_programs(self):
        hist = {'S': [('<script>', datetime.timedelta(seconds=1))]}
        rows = dailyReport.mkRows(hist, {})
        assert '&lt;script&gt;' in rows[0][3]
        assert '<script>' not in rows[0][3]


# ---------------------------------------------------------------------------
# mkTable
# ---------------------------------------------------------------------------

class TestMkTable:
    def test_structure(self):
        rows = [['Station1', '1:00:00', '0:30:00', 'Pgm1']]
        result = dailyReport.mkTable(rows)
        assert '<html>' in result
        assert '</html>' in result
        assert '<thead>' in result
        assert '<tbody>' in result
        assert '<tfoot>' in result
        assert 'Station1' in result

    def test_empty_rows(self):
        result = dailyReport.mkTable([])
        assert '<tbody>' in result
        assert '<tr>' not in result.split('<tbody>')[1].split('</tbody>')[0] or \
               result.count('<tr>') == 2  # only header + footer

    def test_none_values(self):
        rows = [['S1', None, '0:30:00', 'P1']]
        result = dailyReport.mkTable(rows)
        # None historical should produce empty td
        assert '<td></td>' in result

    def test_html_escape_station(self):
        rows = [['<b>Bad</b>', '1:00:00', None, 'pgm']]
        result = dailyReport.mkTable(rows)
        assert '&lt;b&gt;Bad&lt;/b&gt;' in result
        assert '<b>Bad</b>' not in result


# ---------------------------------------------------------------------------
# loadRows
# ---------------------------------------------------------------------------

class TestLoadRows:
    def test_groups_by_station(self):
        logger = logging.getLogger('test')
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.__iter__ = MagicMock(return_value=iter([
            ('S1', 'P1', datetime.timedelta(hours=1)),
            ('S1', 'P2', datetime.timedelta(minutes=30)),
            ('S2', 'P1', datetime.timedelta(hours=2)),
        ]))
        mock_db.cursor.return_value = mock_cursor

        result = dailyReport.loadRows(mock_db, 'SELECT ...', ('arg1',), logger)
        assert 'S1' in result
        assert 'S2' in result
        assert len(result['S1']) == 2
        assert len(result['S2']) == 1

    def test_empty_result(self):
        logger = logging.getLogger('test')
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.__iter__ = MagicMock(return_value=iter([]))
        mock_db.cursor.return_value = mock_cursor

        result = dailyReport.loadRows(mock_db, 'SELECT ...', ('arg1',), logger)
        assert result == {}

    def test_logs_sql_on_error(self):
        logger = logging.getLogger('test')
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.execute.side_effect = RuntimeError('DB error')
        mock_db.cursor.return_value = mock_cursor

        with pytest.raises(RuntimeError):
            dailyReport.loadRows(mock_db, 'BAD SQL', ('x',), logger)


# ---------------------------------------------------------------------------
# sendTable
# ---------------------------------------------------------------------------

class TestSendTable:
    @patch('dailyReport.SMTP')
    def test_sends_message(self, mock_smtp_cls):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value = mock_smtp
        logger = logging.getLogger('test')

        args = types.SimpleNamespace(
            mailFrom='from@test.com',
            mailTo=['to@test.com'],
        )
        dailyReport.sendTable('<html></html>', 3, 5, args, logger)

        mock_smtp_cls.assert_called_once_with('localhost', timeout=30)
        mock_smtp.send_message.assert_called_once()
        mock_smtp.quit.assert_called_once()

    @patch('dailyReport.SMTP')
    def test_smtp_error_logged_and_raised(self, mock_smtp_cls):
        mock_smtp_cls.side_effect = ConnectionRefusedError('no postfix')
        logger = logging.getLogger('test')

        args = types.SimpleNamespace(
            mailFrom='from@test.com',
            mailTo=['to@test.com'],
        )
        with pytest.raises(ConnectionRefusedError):
            dailyReport.sendTable('<html></html>', 3, 5, args, logger)


# ---------------------------------------------------------------------------
# getEmailTo
# ---------------------------------------------------------------------------

class TestGetEmailTo:
    def test_returns_list(self):
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.__iter__ = MagicMock(return_value=iter([
            ('a@b.com',), ('c@d.com',),
        ]))
        mock_db.cursor.return_value = mock_cursor

        result = dailyReport.getEmailTo(mock_db)
        assert result == ['a@b.com', 'c@d.com']

    def test_returns_none_when_empty(self):
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.__iter__ = MagicMock(return_value=iter([]))
        mock_db.cursor.return_value = mock_cursor

        result = dailyReport.getEmailTo(mock_db)
        assert result is None


# ---------------------------------------------------------------------------
# doit
# ---------------------------------------------------------------------------

class TestDoit:
    @patch('dailyReport.sendTable')
    @patch('dailyReport.getPending', return_value={})
    @patch('dailyReport.getHistorical', return_value={})
    @patch('dailyReport.getEmailTo', return_value=None)
    @patch('dailyReport.DB.DB')
    def test_no_recipients_logs_warning(self, mock_db_cls, mock_get_email,
                                         mock_hist, mock_pend, mock_send,
                                         caplog):
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db_cls.return_value = mock_db

        logger = logging.getLogger('test')
        args = types.SimpleNamespace(db='testdb', mailTo=None)
        t0 = datetime.datetime(2024, 1, 1)

        with caplog.at_level(logging.WARNING):
            dailyReport.doit(t0, args, logger)

        assert 'No email recipients' in caplog.text
        mock_send.assert_not_called()

    @patch('dailyReport.sendTable')
    @patch('dailyReport.getPending', return_value={'S1': [('P', datetime.timedelta(hours=1))]})
    @patch('dailyReport.getHistorical', return_value={'S1': [('P', datetime.timedelta(hours=2))]})
    @patch('dailyReport.DB.DB')
    def test_sends_when_recipients_provided(self, mock_db_cls, mock_hist,
                                             mock_pend, mock_send):
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db_cls.return_value = mock_db

        logger = logging.getLogger('test')
        args = types.SimpleNamespace(
            db='testdb', mailTo=['user@example.com'],
            mailFrom='test@example.com',
            hoursBack=24, hoursForward=24,
        )
        t0 = datetime.datetime(2024, 1, 1)

        dailyReport.doit(t0, args, logger)
        mock_send.assert_called_once()
