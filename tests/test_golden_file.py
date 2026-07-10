"""Golden-file tests pinning the exact on-disk format.

The fixture was verified byte-by-byte against Apple's Cookies.binarycookies
layout (page headers, record offsets, checksum, footer magic, trailing plist).
Any writer or reader change that alters the format will fail here.
"""

from datetime import datetime, timezone
from pathlib import Path

from binarycookies import dumps, load

FIXTURE = Path(__file__).parent / "fixtures" / "golden.binarycookies"


def test_golden_file_parses_expected_cookies():
    with open(FIXTURE, "rb") as f:
        cookies = load(f)

    assert [(c.domain, c.name, c.value) for c in cookies] == [
        ("example.com", "session_id", "abc123"),
        ("example.com", "prefs", "λ=1"),
        (".other.org", "tracker", "xyz"),
    ]

    session = cookies[0]
    assert session.flag == "Secure; HttpOnly"
    assert session.raw_flags == 0x4000005
    assert session.comment == "session cookie"
    assert session.create_datetime == datetime(2023, 10, 1, 12, 34, 56, tzinfo=timezone.utc)
    assert session.expiry_datetime == datetime(2033, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    assert cookies[1].flag == "HttpOnly"
    assert cookies[1].comment is None
    assert cookies[2].flag == "Unknown"


def test_golden_file_round_trips_byte_identical():
    raw = FIXTURE.read_bytes()
    with open(FIXTURE, "rb") as f:
        cookies = load(f)

    assert dumps(cookies) == raw
