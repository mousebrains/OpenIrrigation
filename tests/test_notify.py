"""Tests for Notify traceback rendering.

Regression coverage for the 19-Aug-2026 OITDI alert email, which contained the
literal string 'NoneType: None' instead of a traceback: TDIserver reports the
failure after its except block has exited, where traceback.format_exc() has
nothing to format.
"""

import importlib.util
import pathlib
import sys

import pytest

# conftest installs a stub 'Notify' in sys.modules for the other test modules;
# load the real one under a private name so that stub is left alone.
_path = pathlib.Path(__file__).resolve().parent.parent / 'scripts' / 'Notify.py'
_spec = importlib.util.spec_from_file_location('_real_notify', _path)
Notify = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Notify)


def mkException():
    """Return a raised-and-caught exception, with its traceback attached."""
    try:
        raise ZeroDivisionError('cannot divide by zero')
    except ZeroDivisionError as e:
        return e


class TestFormatException:
    def test_exception_object_outside_except_block(self):
        """The failing case: report the error after the handler has exited."""
        exc = mkException()
        assert sys.exc_info()[0] is None, 'must be outside an except block'

        out = Notify.formatException(exc)

        assert 'ZeroDivisionError' in out
        assert 'cannot divide by zero' in out
        assert 'Traceback' in out
        assert 'mkException' in out          # the frame where it was raised
        assert 'NoneType: None' not in out

    def test_no_argument_inside_except_block(self):
        """Existing callers report from inside the handler; keep that working."""
        try:
            raise ValueError('boom')
        except ValueError:
            out = Notify.formatException()

        assert 'ValueError' in out
        assert 'boom' in out
        assert 'NoneType: None' not in out

    def test_no_argument_outside_except_block(self):
        """Nothing to format: say so rather than emitting 'NoneType: None'."""
        assert sys.exc_info()[0] is None

        out = Notify.formatException()

        assert 'NoneType: None' not in out
        assert 'No exception information available' in out

    def test_exception_argument_wins_over_ambient(self):
        """An explicit exception is reported even inside an unrelated handler."""
        exc = mkException()
        try:
            raise KeyError('unrelated')
        except KeyError:
            out = Notify.formatException(exc)

        assert 'ZeroDivisionError' in out
        assert 'unrelated' not in out


class TestOnExceptionSignature:
    def test_accepts_exception_argument(self):
        import inspect
        params = list(inspect.signature(Notify.onException).parameters)
        assert params == ['args', 'logger', 'exc']

    def test_exception_argument_is_optional(self):
        import inspect
        sig = inspect.signature(Notify.onException)
        assert sig.parameters['exc'].default is None


class TestEmailBody:
    def test_body_carries_the_traceback(self, monkeypatch):
        """End to end: the message handed to SMTP contains the real traceback."""
        sent = []

        class FakeSMTP:
            def __init__(self, host, timeout=None):
                pass

            def send_message(self, msg):
                sent.append(msg)

            def quit(self):
                pass

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute(self, sql, args=None):
                pass

            def __iter__(self):
                return iter([['pat@example.com']])

        class FakeDB:
            def __init__(self, dbName, logger):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def cursor(self):
                return FakeCursor()

        monkeypatch.setattr(Notify.smtplib, 'SMTP', FakeSMTP)
        monkeypatch.setattr(Notify.DB, 'DB', FakeDB)

        exc = mkException()
        args = type('Args', (), {'db': 'testdb'})()
        assert sys.exc_info()[0] is None  # the reporting-after-the-fact case

        Notify.onException(args, _NullLogger(), exc)

        assert len(sent) == 1
        body = sent[0].get_payload()
        assert 'ZeroDivisionError' in body
        assert 'NoneType: None' not in body
        assert 'command line:' in body


class _NullLogger:
    def exception(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass


if __name__ == '__main__':
    pytest.main([__file__])
