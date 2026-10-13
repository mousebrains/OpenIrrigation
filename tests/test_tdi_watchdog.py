"""TDIserver's watchdog: thread heartbeats and the systemd notify socket."""

import logging
import os
import queue
import shutil
import socket
import tempfile
import threading
import time

import pytest

import MyBaseThread


class Worker(MyBaseThread.MyBaseThread):
    HEARTBEAT_LIMIT = 60

    def __init__(self):
        super().__init__('Worker', logging.getLogger('test'), queue.Queue())

    def runMain(self):
        while not self.wait_for_shutdown(0.01):
            pass


class TestStalled:
    def test_not_started(self):
        assert Worker().stalled() == 'not running'

    def test_healthy_then_hung(self):
        w = Worker()
        w.start()
        try:
            assert w.stalled() is None
            w.heartbeat = time.monotonic() - 61 # no beat for over a minute
            assert 'no progress' in w.stalled()
            w.beat()
            assert w.stalled() is None
        finally:
            w.shutdown()
            w.join(timeout=1)
        assert w.stalled() == 'not running'

    def test_no_limit_only_checks_running(self):
        w = Worker()
        w.HEARTBEAT_LIMIT = None
        w.start()
        try:
            w.heartbeat = 0
            assert w.stalled() is None
        finally:
            w.shutdown()
            w.join(timeout=1)

    def test_valve_and_serial_threads_are_watched(self):
        import TDIserial
        import TDIvalve
        import DB
        assert TDIserial.Serial.HEARTBEAT_LIMIT > TDIserial.SEND_TRIES * TDIserial.ACK_WAIT + TDIserial.REPLY_WAIT
        assert TDIvalve.ValveOps.HEARTBEAT_LIMIT > TDIvalve.REPLY_TIMEOUT
        assert DB.DBout.HEARTBEAT_LIMIT is not None


class TestSdNotify:
    def test_without_systemd(self, monkeypatch):
        monkeypatch.delenv('NOTIFY_SOCKET', raising=False)
        assert MyBaseThread.sdNotify('READY=1') is False

    def test_sends_to_the_socket(self, monkeypatch):
        d = tempfile.mkdtemp(prefix='oi') # short: AF_UNIX paths are limited to ~100 bytes
        path = os.path.join(d, 'n')
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
                s.bind(path)
                monkeypatch.setenv('NOTIFY_SOCKET', path)
                assert MyBaseThread.sdNotify('WATCHDOG=1') is True
                s.settimeout(1)
                assert s.recv(100) == b'WATCHDOG=1'
        finally:
            shutil.rmtree(d)

    @pytest.mark.skipif(not hasattr(socket, 'AF_UNIX') or os.uname().sysname != 'Linux',
                        reason='abstract sockets are Linux only')
    def test_abstract_socket(self, monkeypatch):
        name = 'oi-test-{}'.format(threading.get_ident())
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
            s.bind('\0' + name)
            monkeypatch.setenv('NOTIFY_SOCKET', '@' + name)
            assert MyBaseThread.sdNotify('READY=1') is True
            s.settimeout(1)
            assert s.recv(100) == b'READY=1'
