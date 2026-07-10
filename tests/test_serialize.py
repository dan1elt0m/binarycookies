import plistlib
from datetime import datetime, timezone
from io import BytesIO
from struct import unpack
from typing import List

from binarycookies import dump, dumps, load
from binarycookies._serialize import calculate_checksum, date_to_mac_epoch
from binarycookies.models import Cookie

COOKIE = {
    "name": "session_id",
    "value": "abc123",
    "url": "example.com",
    "path": "/",
    "flag": "Secure",
    "create_datetime": "2023-10-01T12:34:56Z",
    "expiry_datetime": "2023-12-31T23:59:59Z",
}


def test_dump(tmp_path):
    data = [
        {
            "name": "name",
            "value": "value",
            "url": "example.com",
            "path": "/",
            "flag": "Secure",
            "create_datetime": "2032-01-02T00:00:00Z",
            "expiry_datetime": "2032-01-02T00:00:00Z",
        }
    ]

    # Define the file path
    file_path = tmp_path / "Cookies.binarycookies"

    with open(file_path, "wb") as f:
        # Call the dump method
        dump(data, f)

    # Read the file back and verify its contents
    with open(file_path, "rb") as f:
        # Call the load method
        cookies = load(f)
    assert len(cookies) == 1
    cookie = cookies[0]
    assert cookie.name == "name"
    assert cookie.value == "value"
    assert cookie.url == "example.com"
    assert cookie.path == "/"
    assert cookie.flag == "Secure"
    assert cookie.create_datetime == datetime(2032, 1, 2, 0, 0, tzinfo=timezone.utc)
    assert cookie.expiry_datetime == datetime(2032, 1, 2, 0, 0, tzinfo=timezone.utc)


def test_dump_multiple_cookies(tmp_path):
    data = [
        {
            "name": "name1",
            "value": "value1",
            "url": "example1.com",
            "path": "/",
            "flag": "Secure",
            "create_datetime": "2032-01-02T00:00:00Z",
            "expiry_datetime": "2032-01-02T00:00:00Z",
        },
        {
            "name": "name2",
            "value": "value2",
            "url": "example2.com",
            "path": "/",
            "flag": "HttpOnly",
            "create_datetime": "2033-01-02T00:00:00Z",
            "expiry_datetime": "2033-01-02T00:00:00Z",
        },
    ]

    # Define the file path
    file_path = tmp_path / "Cookies.binarycookies"

    with open(file_path, "wb") as f:
        # Call the dump method
        dump(data, f)

    # Read the file back and verify its contents
    with open(file_path, "rb") as f:
        # Call the load method
        cookies = load(f)

    assert len(cookies) == 2

    cookie1 = cookies[0]
    assert cookie1.name == "name1"
    assert cookie1.value == "value1"
    assert cookie1.url == "example1.com"
    assert cookie1.path == "/"
    assert cookie1.flag == "Secure"
    assert cookie1.create_datetime == datetime(2032, 1, 2, 0, 0, tzinfo=timezone.utc)
    assert cookie1.expiry_datetime == datetime(2032, 1, 2, 0, 0, tzinfo=timezone.utc)

    cookie2 = cookies[1]
    assert cookie2.name == "name2"
    assert cookie2.value == "value2"
    assert cookie2.url == "example2.com"
    assert cookie2.path == "/"
    assert cookie2.flag == "HttpOnly"
    assert cookie2.create_datetime == datetime(2033, 1, 2, 0, 0, tzinfo=timezone.utc)
    assert cookie2.expiry_datetime == datetime(2033, 1, 2, 0, 0, tzinfo=timezone.utc)


def test_dumps_file_structure_matches_apple_format():
    """The file header, page header, and file tail must match Safari's on-disk format."""
    data = dumps([COOKIE])

    # File header: magic + number of pages (big-endian) + page size (big-endian)
    assert data[0:4] == b"cook"
    num_pages = unpack(">i", data[4:8])[0]
    assert num_pages == 1
    page_size = unpack(">i", data[8:12])[0]

    # Page header must be 0x00 0x00 0x01 0x00 (not 0x00 0x01 0x00 0x00)
    page = data[12 : 12 + page_size]
    assert page[0:4] == b"\x00\x00\x01\x00"
    # Number of cookies in page (little-endian)
    assert unpack("<i", page[4:8])[0] == 1
    # Offset table is terminated by 4 zero bytes
    assert page[12:16] == b"\x00\x00\x00\x00"

    # File tail: 4-byte big-endian checksum, 8-byte footer magic, binary plist
    tail = data[12 + page_size :]
    assert unpack(">I", tail[0:4])[0] == calculate_checksum(page)
    assert tail[4:12] == b"\x07\x17\x20\x05\x00\x00\x00\x4b"
    plist = plistlib.loads(tail[12:])
    assert plist == {"NSHTTPCookieAcceptPolicy": 2}


def test_dumps_cookie_record_matches_apple_format():
    """Cookie records must use the 56-byte header with zeroed comment offsets."""
    data = dumps([COOKIE])
    page_size = unpack(">i", data[8:12])[0]
    page = data[12 : 12 + page_size]

    cookie_offset = unpack("<i", page[8:12])[0]
    record = page[cookie_offset:]
    record_size = unpack("<i", record[0:4])[0]
    record = record[:record_size]

    # Strings start immediately after the 56-byte header, domain first
    assert unpack("<i", record[16:20])[0] == 56  # domain offset
    assert unpack("<i", record[20:24])[0] == 56 + len(b"example.com") + 1  # name offset
    # Comment offset and comment URL offset must be 0 when there is no comment
    assert unpack("<i", record[32:36])[0] == 0
    assert unpack("<i", record[36:40])[0] == 0
    # Dates are little-endian doubles in seconds since 2001-01-01
    expiry = datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    assert unpack("<d", record[40:48])[0] == date_to_mac_epoch(expiry)
    # String block: domain, name, path, value - each null-terminated
    assert record[56:] == b"example.com\x00session_id\x00/\x00abc123\x00"


def test_dumps_writes_one_page_per_domain():
    """Safari groups cookies by domain, one page per domain."""
    cookie_a = {**COOKIE, "url": "example1.com"}
    cookie_b = {**COOKIE, "url": "example2.com", "name": "other"}
    cookie_c = {**COOKIE, "url": "example1.com", "name": "second"}

    data = dumps([cookie_a, cookie_b, cookie_c])

    assert unpack(">i", data[4:8])[0] == 2
    page_sizes = [unpack(">i", data[8 + i * 4 : 12 + i * 4])[0] for i in range(2)]
    first_page = data[16 : 16 + page_sizes[0]]
    # Cookies of the same domain share a page, in input order
    assert unpack("<i", first_page[4:8])[0] == 2

    cookies = {(c.url, c.name) for c in load_bytes(data)}
    assert cookies == {("example1.com", "session_id"), ("example2.com", "other"), ("example1.com", "second")}


def load_bytes(data: bytes) -> List[Cookie]:
    return load(BytesIO(data))


def test_dump_naive_datetime_assumed_utc(tmp_path):
    naive = {**COOKIE, "create_datetime": "2023-10-01T12:34:56", "expiry_datetime": "2023-12-31T23:59:59"}
    file_path = tmp_path / "Cookies.binarycookies"

    with open(file_path, "wb") as f:
        dump(naive, f)
    with open(file_path, "rb") as f:
        [cookie] = load(f)

    assert cookie.create_datetime == datetime(2023, 10, 1, 12, 34, 56, tzinfo=timezone.utc)
    assert cookie.expiry_datetime == datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
