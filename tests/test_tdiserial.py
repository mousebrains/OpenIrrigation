"""Tests for TDIserial: Serial class, framing, checksum, ACK/NAK handling, reply matching."""

import pytest
import logging
import queue
import time
import TDIserial
from TDIconstants import (
    SYNC, ACK, NAK,
    compute_checksum, frame_message, verify_checksum,
)
from TDIserial import Serial, Reply, isReplyTo, PRIORITY_VALVE, PRIORITY_POLL
from tdi_fakes import FakeController


@pytest.fixture
def logger():
    return logging.getLogger('test_tdiserial')


# ── compute_checksum ─────────────────────────────────────────────────

class TestComputeChecksum:
    def test_empty(self):
        assert compute_checksum(b'') == 0

    def test_single_byte(self):
        assert compute_checksum(b'\x42') == 0x42

    def test_wraps_at_256(self):
        # 0xFF + 0x02 = 0x101, masked to 0x01
        assert compute_checksum(b'\xff\x02') == 0x01

    def test_known_values(self):
        # "0E" -> 0x30 + 0x45 = 0x75
        data = b'020E'  # length "02" + body "0E"
        assert compute_checksum(data) == (0x30 + 0x32 + 0x30 + 0x45) & 0xFF


# ── verify_checksum ──────────────────────────────────────────────────

class TestVerifyChecksum:
    def test_valid(self):
        length_hex = b'02'
        body = b'0E'
        chk = compute_checksum(length_hex + body)
        checksum_hex = '{:02X}'.format(chk).encode('ascii')
        assert verify_checksum(length_hex, body, checksum_hex) is True

    def test_invalid(self):
        assert verify_checksum(b'02', b'0E', b'00') is False

    def test_non_hex_checksum(self):
        assert verify_checksum(b'02', b'0E', b'ZZ') is False

    def test_non_ascii_checksum(self):
        assert verify_checksum(b'02', b'0E', b'\xff\xfe') is False


# ── frame_message ────────────────────────────────────────────────────

class TestFrameMessage:
    def test_structure(self):
        """frame_message returns SYNC + length_hex + body + checksum_hex."""
        body = b'0E'
        framed = frame_message(body)
        assert framed[0:1] == SYNC
        # Length is 2 hex chars for len(body)=2
        assert framed[1:3] == b'02'
        # Body follows
        assert framed[3:5] == b'0E'
        # Last 2 bytes are checksum
        payload = framed[1:5]
        expected_chk = compute_checksum(payload)
        assert framed[5:] == '{:02X}'.format(expected_chk).encode('ascii')

    def test_round_trip(self):
        """A framed message should have a valid checksum."""
        body = b'0A0A00'
        framed = frame_message(body)
        length_hex = framed[1:3]
        msg_body = framed[3:-2]
        checksum_hex = framed[-2:]
        assert verify_checksum(length_hex, msg_body, checksum_hex) is True

    def test_various_lengths(self):
        """Frame messages of different body lengths."""
        for n in (0, 1, 5, 16, 255):
            body = bytes(n)
            framed = frame_message(body)
            length_hex = framed[1:3]
            n_parsed = int(length_hex.decode('ascii'), 16)
            assert n_parsed == n



# ── isReplyTo ────────────────────────────────────────────────────────

class TestIsReplyTo:
    def test_valve_reply_must_match_the_address(self):
        """The 2026-10-07 failure: a late 1D2200 was taken as the reply to 0D23."""
        assert isReplyTo(b'0D23', b'1D2300')
        assert not isReplyTo(b'0D23', b'1D2200')
        assert not isReplyTo(b'0A23', b'1A2200001A02BC003D')
        assert isReplyTo(b'0A23', b'1A2300001A02BC003D')
        assert isReplyTo(b'0T05', b'1T05001A02BC003D')
        assert isReplyTo(b'0S00', b'1S00040064')
        assert not isReplyTo(b'0S01', b'1S00040064')

    def test_all_off_reply_is_its_own(self):
        assert isReplyTo(b'0DFF', b'1DFF00')
        assert not isReplyTo(b'0DFF', b'1D2200')
        assert not isReplyTo(b'0D22', b'1DFF00')

    def test_hex_case_is_ignored(self):
        assert isReplyTo(b'0D2A', b'1D2a00')

    def test_reply_code_must_match_the_command(self):
        """A 1S and a 1U reply are the same length; only the code tells them apart."""
        assert isReplyTo(b'0U', b'1U00F000C8')
        assert not isReplyTo(b'0U', b'1S00040064')
        assert isReplyTo(b'0E', b'1E00')
        assert not isReplyTo(b'0E', b'1D2200')
        assert isReplyTo(b'0V', b'1V3.0b4')

    def test_path_replies(self):
        assert isReplyTo(b'0P00FF', b'1200FFFF')
        assert isReplyTo(b'0P00FF', b'1P00FFFF')
        assert isReplyTo(b'0200FF', b'1200FF')

    def test_zee_for_the_same_command(self):
        assert isReplyTo(b'0A23', b'1ZA0100')
        assert not isReplyTo(b'0D23', b'1ZA0100')

    def test_nothing(self):
        assert not isReplyTo(b'0E', None)
        assert not isReplyTo(b'0E', b'')
        assert not isReplyTo(b'0E', b'1')


# ── Serial against a fake controller on a pty ────────────────────────

@pytest.fixture
def fast(monkeypatch):
    """Short waits so a missing reply doesn't take 15 seconds"""
    monkeypatch.setattr(TDIserial, 'ACK_WAIT', 0.5)
    monkeypatch.setattr(TDIserial, 'REPLY_WAIT', 1.0)
    # tests/conftest.py stubs pyserial; TDIserial raises its exception on EOF
    monkeypatch.setattr(TDIserial.serial, 'SerialException', OSError, raising=False)


@pytest.fixture
def controller(logger, fast):
    """Start a fake controller with a script; returns (fake, Serial)"""
    fakes = []

    def start(script):
        fake = FakeController(script)
        fake.start()
        fakes.append(fake)
        return (fake, Serial(fake.host, logger, queue.Queue()))
    yield start
    for fake in fakes:
        fake.stop()


class TestTransact:
    def test_slow_reply_after_ack_is_waited_for(self, controller, monkeypatch):
        """Under load the reply comes 4-6 s after the ACK; the old code gave up after 1 s."""
        monkeypatch.setattr(TDIserial, 'REPLY_WAIT', 3)
        (fake, ser) = controller(lambda body, n: [('ack',), ('sleep', 1.2), ('reply', b'1D2200')])
        (t, reply) = ser.transact(b'0D22')
        assert reply == b'1D2200'
        assert t is not None
        assert fake.sentences == [b'0D22'] # Not sent again while waiting
        assert fake.waitFor(lambda: fake.answers == ACK) # The reply was ACKed

    def test_late_reply_is_not_taken_for_the_next_commands(self, controller):
        """Reproduces the review's pty finding: 0D22's reply arrives during 0D23's wait."""
        def script(body, n):
            if body == b'0D22':
                return [('ack',)] # The reply is slow
            return [('ack',), ('reply', b'1D2200'), ('reply', b'1D2300')]
        (fake, ser) = controller(script)
        assert ser.transact(b'0D22') == (None, None)
        assert fake.sentences == [b'0D22'] # ACKed, so never resent
        (_t, reply) = ser.transact(b'0D23')
        assert reply == b'1D2300'
        # Both frames were ACKed, so the controller stops resending the stale one
        assert fake.waitFor(lambda: fake.answers == ACK + ACK)

    def test_nak_is_resent(self, controller):
        (fake, ser) = controller(lambda body, n: [('nak',)] if n == 1 else [('ack',), ('reply', b'1E00')])
        assert ser.transact(b'0E')[1] == b'1E00'
        assert fake.sentences == [b'0E', b'0E']

    def test_no_ack_is_resent_then_given_up(self, controller):
        (fake, ser) = controller(lambda body, n: [])
        assert ser.transact(b'0D22') == (None, None)
        assert fake.sentences == [b'0D22'] * TDIserial.SEND_TRIES

    def test_reply_without_an_ack(self, controller):
        """A lost ACK: the reply itself shows the controller has the command."""
        (fake, ser) = controller(lambda body, n: [('reply', b'1D2300')])
        assert ser.transact(b'0D23')[1] == b'1D2300'
        assert fake.sentences == [b'0D23']

    def test_zee_reply(self, controller):
        (fake, ser) = controller(lambda body, n: [('ack',), ('reply', b'1ZA0100')])
        assert ser.transact(b'0A2300')[1] == b'1ZA0100'

    def test_bad_reply_is_naked_and_its_resend_taken(self, controller):
        bad = b'\x1606' + b'1D2300' + b'00\r' # wrong checksum
        (fake, ser) = controller(lambda body, n: [('ack',), ('raw', bad), ('reply', b'1D2300')])
        assert ser.transact(b'0D23')[1] == b'1D2300'
        assert fake.waitFor(lambda: fake.answers == NAK + ACK)


class TestUnsolicited:
    def test_unsolicited_frames_are_acked(self, controller):
        """Unanswered, the controller resends a reply over and over."""
        (fake, ser) = controller(lambda body, n: [])
        fake.do(('reply', b'1D2202'))
        ser.readPending(0.5)
        assert fake.waitFor(lambda: fake.answers == ACK)

    def test_garbage_is_dropped(self, controller):
        (fake, ser) = controller(lambda body, n: [])
        fake.do(('raw', b'xyz\r'))
        fake.do(('reply', b'1E00'))
        ser.readPending(0.5)
        assert fake.waitFor(lambda: fake.answers == ACK)


class TestQueue:
    def test_valve_commands_go_first(self, logger, controller):
        (fake, ser) = controller(lambda body, n: [('ack',), ('reply', b'1' + body[1:])])
        polls = [Reply() for _ in range(3)]
        for r in polls:
            ser.put(b'0E', r)
        valve = Reply()
        ser.put(b'0D22', valve, PRIORITY_VALVE)
        ser.start()
        try:
            assert valve.get(timeout=3)[1] == b'1D22'
            for r in polls:
                assert r.get(timeout=3)[1] == b'1E'
        finally:
            ser.shutdown()
            ser.join(timeout=2)
        assert fake.sentences[0] == b'0D22'

    def test_abandoned_requests_are_not_sent(self, logger, controller):
        (fake, ser) = controller(lambda body, n: [('ack',), ('reply', b'1E00')])
        gone = Reply()
        gone.abandon()
        ser.put(b'0E', gone)
        wanted = Reply()
        ser.put(b'0U', wanted)
        ser.start()
        try:
            wanted.get(timeout=3)
        finally:
            ser.shutdown()
            ser.join(timeout=2)
        assert fake.sentences == [b'0U']

    def test_nothing_after_the_final_request(self, logger):
        ser = Serial(None, logger, queue.Queue())
        ser.put(b'0DFF', Reply(), PRIORITY_VALVE, final=True)
        late = Reply()
        ser.put(b'0A2200', late, PRIORITY_VALVE)
        assert late.get(timeout=0) == (None, None) # Refused at once
        assert ser.queue.qsize() == 1
        ser.put(b'0DFF', Reply(), PRIORITY_VALVE, final=True) # Another try at the all-off
        assert ser.queue.qsize() == 2

    def test_request_times_out_and_abandons(self, logger):
        ser = Serial(None, logger, queue.Queue()) # Not started, so nothing answers
        t0 = time.time()
        assert ser.request(b'0DFF', 0.1) == (None, None)
        assert time.time() - t0 < 1
        (_p, _n, _msg, reply) = ser.queue.get_nowait()
        assert reply.abandoned

    def test_poll_priority_default(self, logger):
        ser = Serial(None, logger, queue.Queue())
        ser.put(b'0E', Reply())
        assert ser.queue.get_nowait()[0] == PRIORITY_POLL
