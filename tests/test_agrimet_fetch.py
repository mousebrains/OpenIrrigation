"""AgriMet.fetchPage() must not hang the oneshot unit on a stalled server."""

import datetime
import io
import logging
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import AgriMet


def test_fetch_has_a_timeout(monkeypatch):
    seen = {}

    def urlopen(url, timeout=None):
        seen.update(url=url, timeout=timeout)
        return io.BytesIO(b"BEGIN DATA\nEND DATA\n")
    monkeypatch.setattr(AgriMet.urllib.request, "urlopen", urlopen)
    args = types.SimpleNamespace(input=None, output=None)
    page = AgriMet.fetchPage(datetime.timedelta(days=3), {"URL": "https://example.org/?back="},
                             args, logging.getLogger("test"))
    assert page.startswith("BEGIN DATA")
    assert seen == {"url": "https://example.org/?back=3", "timeout": AgriMet.FETCH_TIMEOUT}
    assert 0 < AgriMet.FETCH_TIMEOUT <= 300
