"""Tests for MyLogger: addArgs and mkLogger."""

import sys
import argparse
import logging
import logging.handlers

# Remove the conftest stub so we can test the real module
sys.modules.pop('MyLogger', None)
import MyLogger  # noqa: E402


class TestAddArgs:
    def test_adds_logfile_arg(self):
        parser = argparse.ArgumentParser()
        MyLogger.addArgs(parser)
        args = parser.parse_args([])
        assert hasattr(args, 'logfile')
        assert args.logfile is None

    def test_adds_verbose_arg(self):
        parser = argparse.ArgumentParser()
        MyLogger.addArgs(parser)
        args = parser.parse_args(['--verbose'])
        assert args.verbose is True

    def test_adds_maxlogsize_arg(self):
        parser = argparse.ArgumentParser()
        MyLogger.addArgs(parser)
        args = parser.parse_args([])
        assert args.maxlogsize == 10000000

    def test_adds_backupcount_arg(self):
        parser = argparse.ArgumentParser()
        MyLogger.addArgs(parser)
        args = parser.parse_args(['--backupcount', '3'])
        assert args.backupcount == 3


class TestMkLogger:
    def test_stream_handler_default(self):
        parser = argparse.ArgumentParser()
        MyLogger.addArgs(parser)
        args = parser.parse_args([])
        logger = MyLogger.mkLogger(args, 'test_stream')
        handlers = [h for h in logger.handlers
                    if isinstance(h, logging.StreamHandler)
                    and not isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(handlers) >= 1

    def test_verbose_sets_debug(self):
        parser = argparse.ArgumentParser()
        MyLogger.addArgs(parser)
        args = parser.parse_args(['--verbose'])
        logger = MyLogger.mkLogger(args, 'test_verbose')
        assert any(h.level == logging.DEBUG for h in logger.handlers)

    def test_non_verbose_sets_info(self):
        parser = argparse.ArgumentParser()
        MyLogger.addArgs(parser)
        args = parser.parse_args([])
        logger = MyLogger.mkLogger(args, 'test_info')
        assert any(h.level == logging.INFO for h in logger.handlers)

    def test_file_handler(self, tmp_path):
        logfile = str(tmp_path / 'test.log')
        parser = argparse.ArgumentParser()
        MyLogger.addArgs(parser)
        args = parser.parse_args(['--logfile', logfile])
        logger = MyLogger.mkLogger(args, 'test_file')
        handlers = [h for h in logger.handlers
                    if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert len(handlers) >= 1

    def test_custom_format(self):
        parser = argparse.ArgumentParser()
        MyLogger.addArgs(parser)
        args = parser.parse_args([])
        fmt = '%(message)s'
        logger = MyLogger.mkLogger(args, 'test_fmt', fmt=fmt)
        assert any(h.formatter._fmt == fmt for h in logger.handlers)

    def test_returns_logger(self):
        parser = argparse.ArgumentParser()
        MyLogger.addArgs(parser)
        args = parser.parse_args([])
        result = MyLogger.mkLogger(args, 'test_return')
        assert isinstance(result, logging.Logger)
