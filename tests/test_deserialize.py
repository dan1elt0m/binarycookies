import sys
from datetime import datetime, timezone
from struct import pack
from unittest.mock import patch

import pytest

from binarycookies import dump
from binarycookies._deserialize import interpret_flag, load, mac_epoch_to_date, read_cookie
from binarycookies.models import BinaryCookiesDecodeError, Cookie, Flag


def test_interpret_flag():
    assert interpret_flag(0) == Flag.UNKNOWN
    assert interpret_flag(1) == Flag.SECURE
    assert interpret_flag(4) == Flag.HTTPONLY
    assert interpret_flag(5) == Flag.SECURE_HTTPONLY
    assert interpret_flag(6) == Flag.UNKNOWN


def test_mac_epoch_to_date():
    epoch = 0  # This corresponds to 2001-01-01 00:00:00
    expected_date = datetime(2001, 1, 1, 0, 0, tzinfo=timezone.utc)
    assert mac_epoch_to_date(epoch) == expected_date


def test_mac_epoch_to_date_with_max_value():
    """
    Tests that a very large epoch value correctly returns datetime.max
    instead of raising an OverflowError.
    """
    # A very large epoch value that would cause an overflow
    large_epoch = sys.maxsize

    # The expected result is datetime.max with UTC timezone
    expected_date = datetime.max.replace(tzinfo=timezone.utc)

    # Call the function and assert the result
    assert mac_epoch_to_date(large_epoch) == expected_date


MAC_UNIX_OFFSET = 978307200  # 1970->2001
INT32_TIME_T_MAX = 2147483647  # 32-bit signed max
INT32_CUTOFF_DT = datetime(2038, 1, 19, 3, 14, 7, tzinfo=timezone.utc)


def test_mac_epoch_to_date_32bit_clamp(monkeypatch):
    # Simulate 32-bit architecture
    monkeypatch.setattr("binarycookies._deserialize.sys.maxsize", 2**31 - 1)

    # Epoch that would overflow 32-bit time_t (Unix ts = INT32_TIME_T_MAX + 1)
    overflowing_epoch = (INT32_TIME_T_MAX - MAC_UNIX_OFFSET) + 1
    assert mac_epoch_to_date(overflowing_epoch) == INT32_CUTOFF_DT


def test_mac_epoch_to_date_32bit_boundary(monkeypatch):
    monkeypatch.setattr("binarycookies._deserialize.sys.maxsize", 2**31 - 1)

    # Just below the overflow threshold
    safe_epoch = (INT32_TIME_T_MAX - MAC_UNIX_OFFSET) - 1
    dt = mac_epoch_to_date(safe_epoch)
    assert dt < INT32_CUTOFF_DT
    assert dt == datetime.fromtimestamp(safe_epoch + MAC_UNIX_OFFSET, tz=timezone.utc)


def test_read_cookie():
    from io import BytesIO

    # Create a mock binary cookie data
    cookie_size = 81
    cookie_data = BytesIO()
    cookie_data.write(pack("<i", cookie_size))  # cookie size
    cookie_data.write(pack("<i", 0))  # unknown
    cookie_data.write(pack("<i", 1))  # flag (SECURE)
    cookie_data.write(pack("<i", 0))  # unknown
    cookie_data.write(pack("<i", 56))  # url offset
    cookie_data.write(pack("<i", 68))  # name offset
    cookie_data.write(pack("<i", 73))  # path offset
    cookie_data.write(pack("<i", 75))  # value offset
    cookie_data.write(b"\x00\x00\x00@\xe4'\xcdA")  # unknown (8 bytes)
    cookie_data.write(pack("<d", 978307200.0))  # expiry date offset = 56 - 8 bytes = 48
    cookie_data.write(pack("<d", 978307200.0))  # creation date
    cookie_data.write(b"example.com\0")  # url
    cookie_data.write(b"name\0")  # name
    cookie_data.write(b"/\0")  # path
    cookie_data.write(b"value\0")  # value
    cookie_data.seek(0)

    cookie = read_cookie(cookie_data, cookie_size)
    assert cookie.name == "name"
    assert cookie.value == "value"
    assert cookie.url == "example.com"
    assert cookie.path == "/"
    assert cookie.flag == Flag.SECURE
    assert cookie.create_datetime == datetime(2032, 1, 2, 0, 0, tzinfo=timezone.utc)
    assert cookie.expiry_datetime == datetime(2032, 1, 2, 0, 0, tzinfo=timezone.utc)


def test_read_binary_cookies_file(tmp_path):
    cookie = Cookie(
        name="name",
        value="value",
        url="example.com",
        path="/",
        flag=Flag.SECURE,
        create_datetime=datetime(2032, 1, 2, 0, 0, tzinfo=timezone.utc),
        expiry_datetime=datetime(2032, 1, 2, 0, 0, tzinfo=timezone.utc),
    )
    file_path = tmp_path / "Cookies.binarycookies"

    with open(file_path, "wb") as f:
        dump(cookie, f)
    with open(file_path, "rb") as f:
        [result_cookie] = load(f)
    assert result_cookie == cookie


def test_read_binary_cookies_file_multiple_pages(tmp_path):
    with patch("binarycookies._deserialize._deserialize_page") as mock_binary_cookies_reader:
        file_path = tmp_path / "Cookies.binarycookies"
        with open(file_path, "wb") as f:
            f.write(b"cook")  # File Magic String
            f.write(b"\x00\x00\x00\x02")  # number of pages
            f.write(b"\x00\x00\x00\x4d")  # page size for first page
            f.write(b"\x00\x00\x00\x4d")  # page size for second page
            f.write(b"\x01\x00\x00\x00\x04\x00\x00\x00\x4d\x00\x00\x00" + b"\x00" * 65)  # first page content
            f.write(b"\x01\x00\x00\x00\x04\x00\x00\x00\x4d\x00\x00\x00" + b"\x00" * 64)  # second page content

        with open(file_path, "rb") as f:
            load(f)
        assert mock_binary_cookies_reader.call_count == 2
        assert (
            mock_binary_cookies_reader.call_args_list[0][0][0].read()
            == b"\x01\x00\x00\x00\x04\x00\x00\x00\x4d\x00\x00\x00" + b"\x00" * 65
        )
        assert (
            mock_binary_cookies_reader.call_args_list[1][0][0].read()
            == b"\x01\x00\x00\x00\x04\x00\x00\x00\x4d\x00\x00\x00" + b"\x00" * 64
        )


def test_read_binary_cookies_file_not_a_cookie_file(tmp_path):
    with patch("binarycookies._deserialize._deserialize_page"):
        file_path = tmp_path / "Cookies.binarycookies"
        with open(file_path, "wb") as f:
            f.write(b"not a cookie file")

        with (
            pytest.raises(
                BinaryCookiesDecodeError,
                match="The file is not a valid binary cookies file. Missing magic String:cook.",
            ),
            open(file_path, "rb") as f,
        ):
            load(f)
