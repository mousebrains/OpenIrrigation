"""Tests for AgriMet.Fetcher.parsePage() — pure string parsing, no DB needed.

AgriMet.py has module-level argparse code, so we cannot import it directly.
Instead, we extract parsePage's source logic into a local helper for testing.
This validates the parsing algorithm without needing the full module.
"""

import datetime
import logging
import re


class _PageParser:
    """Minimal stand-in that replicates Fetcher.parsePage() logic for testing."""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger('test')

    def parsePage(self, page: str, codigoToIndex: dict) -> list:
        """break the page into data rows and return them"""
        state = 0
        stations = []
        codigos = []
        rows = []
        for line in page.splitlines():
            line = line.strip()
            if not line: continue
            if line == "BEGIN DATA":
                state = 1
                stations = []
                codigos = []
                continue
            if (state == 0) or (line == "END DATA"):
                state = 0
                continue
            if state == 0:
                line = line.strip()
                if line == "BEGIN DATA":
                    state += 1
            if state == 1:
                if not re.match(r'\s*DATE\s*,', line):
                    state = 0
                    rows = []
                    self.logger.warning('Expected a DATE header line, but got a %s line', line)
                    continue
                items = re.split(r'\s*,\s*', line)
                for i in range(1, len(items)):
                    parts = re.split(r'\s+', items[i])
                    if len(parts) != 2:
                        self.logger.warning('Field, %s, does not contain station code format',
                                items[i])
                        state = 0
                        rows = []
                        continue
                    stations.append(parts[0])
                    codigos.append(codigoToIndex[parts[1]] if parts[1] in codigoToIndex else None)
                state += 1
                continue
            items = re.split(r'\s*,\s*', line)
            try:
                t = datetime.datetime.strptime(items[0], '%m/%d/%Y').date()
                for i in range(1, len(items)):
                    if codigos[i-1] is None: continue
                    try:
                        val = float(items[i])
                        rows.append((t, stations[i-1], codigos[i-1], val))
                    except (ValueError, TypeError):
                        continue
            except (ValueError, IndexError):
                state = 0
                rows = []
                continue

        self.logger.info('Found %s rows', len(rows))
        return rows if len(rows) else None


SAMPLE_PAGE = """\
Some header junk
BEGIN DATA
 DATE       , ABEI ET ,  ABEI MN
07/01/2024  ,  0.29   ,  58
07/02/2024  ,  0.31   ,  62
END DATA
"""

CODIGOS = {'ET': 1, 'MN': 2}


class TestParsePageBasic:
    def test_returns_rows(self):
        parser = _PageParser()
        rows = parser.parsePage(SAMPLE_PAGE, CODIGOS)
        assert rows is not None
        assert len(rows) == 4  # 2 dates * 2 columns

    def test_row_structure(self):
        parser = _PageParser()
        rows = parser.parsePage(SAMPLE_PAGE, CODIGOS)
        # Each row is (date, station, codigo_id, value)
        (t, station, code, val) = rows[0]
        assert t == datetime.date(2024, 7, 1)
        assert station == 'ABEI'
        assert code == 1  # ET
        assert val == 0.29

    def test_second_column(self):
        parser = _PageParser()
        rows = parser.parsePage(SAMPLE_PAGE, CODIGOS)
        (t, station, code, val) = rows[1]
        assert t == datetime.date(2024, 7, 1)
        assert station == 'ABEI'
        assert code == 2  # MN
        assert val == 58.0

    def test_second_date(self):
        parser = _PageParser()
        rows = parser.parsePage(SAMPLE_PAGE, CODIGOS)
        (t, station, code, val) = rows[2]
        assert t == datetime.date(2024, 7, 2)
        assert val == 0.31


class TestParsePageEdgeCases:
    def test_empty_page(self):
        parser = _PageParser()
        result = parser.parsePage('', CODIGOS)
        assert result is None

    def test_no_begin_data(self):
        parser = _PageParser()
        result = parser.parsePage('just some text\nno data here\n', CODIGOS)
        assert result is None

    def test_missing_end_data(self):
        """If END DATA is missing, parser still returns rows collected so far."""
        page = """\
BEGIN DATA
 DATE       , ABEI ET
07/01/2024  ,  0.29
"""
        parser = _PageParser()
        rows = parser.parsePage(page, CODIGOS)
        assert rows is not None
        assert len(rows) == 1

    def test_malformed_header_resets(self):
        """If the header line after BEGIN DATA doesn't match DATE, state resets."""
        page = """\
BEGIN DATA
NOT A DATE HEADER
07/01/2024  ,  0.29
END DATA
"""
        parser = _PageParser()
        result = parser.parsePage(page, CODIGOS)
        assert result is None

    def test_unknown_codigo_skipped(self):
        """Columns with unknown codigos (not in codigoToIndex) are skipped."""
        page = """\
BEGIN DATA
 DATE       , ABEI ET , ABEI XX
07/01/2024  ,  0.29   ,  999
END DATA
"""
        parser = _PageParser()
        rows = parser.parsePage(page, CODIGOS)
        assert rows is not None
        # Only ET column parsed, XX is unknown
        assert len(rows) == 1
        assert rows[0][2] == 1  # ET

    def test_missing_value_skipped(self):
        """Non-numeric values are silently skipped."""
        page = """\
BEGIN DATA
 DATE       , ABEI ET
07/01/2024  ,  ---
END DATA
"""
        parser = _PageParser()
        result = parser.parsePage(page, CODIGOS)
        assert result is None  # No valid rows

    def test_multiple_data_blocks(self):
        """Both BEGIN DATA blocks accumulate rows."""
        page = """\
BEGIN DATA
 DATE       , ABEI ET
07/01/2024  ,  0.10
END DATA
BEGIN DATA
 DATE       , ABEI MN
07/02/2024  ,  55
END DATA
"""
        parser = _PageParser()
        rows = parser.parsePage(page, CODIGOS)
        assert rows is not None
        assert len(rows) == 2

    def test_blank_lines_skipped(self):
        page = """\

BEGIN DATA

 DATE       , ABEI ET

07/01/2024  ,  0.29

END DATA

"""
        parser = _PageParser()
        rows = parser.parsePage(page, CODIGOS)
        assert rows is not None
        assert len(rows) == 1
