# Protocol constants for the TDI 2-wire controller communication

# Framing bytes
SYNC = b'\x16'  # Start of a message
ACK  = b'\x06'  # Acknowledge
NAK  = b'\x15'  # Not acknowledge

# Valve command types (used in the command table's cmd column)
CMD_ON   = 0
CMD_OFF  = 1
CMD_TEST = 2


def compute_checksum(data: bytes) -> int:
    """Compute TDI protocol checksum (sum of bytes, masked to 8 bits)."""
    return sum(data) & 0xff


def frame_message(body: bytes) -> bytes:
    """Frame a TDI message: SYNC + length(hex) + body + checksum(hex)."""
    length_hex = '{:02X}'.format(len(body)).encode('ascii')
    payload = length_hex + body
    chk = '{:02X}'.format(compute_checksum(payload)).encode('ascii')
    return SYNC + payload + chk


def verify_checksum(length_hex: bytes, body: bytes, checksum_hex: bytes) -> bool:
    """Verify a TDI message checksum. Returns True if valid."""
    expected = compute_checksum(length_hex + body)
    try:
        actual = int(checksum_hex.decode('ascii'), 16)
    except (ValueError, UnicodeDecodeError):
        return False
    return expected == actual
