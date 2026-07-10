import plistlib
from datetime import datetime, timezone
from io import BufferedWriter, BytesIO
from struct import pack
from typing import BinaryIO, Dict, List, Tuple, Union

from pydantic import __version__ as pydantic_version

from binarycookies._deserialize import FLAGS
from binarycookies.models import BcField, Cookie, CookieFields, FileFields, Format

IS_PYDANTIC_V1 = pydantic_version.startswith("1.")

CookiesCollection = Union[List[Dict], List[Cookie], Tuple[Dict], Tuple[Cookie], Cookie, Dict[str, str]]

# Every page starts with these 4 bytes (0x00000100 stored big-endian)
PAGE_HEADER = b"\x00\x00\x01\x00"
# 4 zero bytes terminate the page's cookie offset table
PAGE_FOOTER = b"\x00\x00\x00\x00"
# 8-byte magic that follows the checksum at the end of the file
FILE_FOOTER = b"\x07\x17\x20\x05\x00\x00\x00\x4b"
# Cookie records without comments have a 56-byte fixed header; strings follow
COOKIE_HEADER_SIZE = 56
# Value Safari stores in the trailing NSHTTPCookieAcceptPolicy plist
DEFAULT_COOKIE_ACCEPT_POLICY = 2


def date_to_mac_epoch(date: datetime) -> int:
    """Converts a datetime object to mac epoch time. Naive datetimes are assumed to be UTC."""
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    mac_epoch_start = datetime(2001, 1, 1, tzinfo=timezone.utc)
    return int((date - mac_epoch_start).total_seconds())


def write_string(data: BytesIO, value: str):
    """Writes a string to binary file."""
    data.write(value.encode() + b"\x00")


def write_field(data: BytesIO, field: BcField, value: Union[str, int]):
    """Writes a field to binary data."""
    data.seek(field.offset)
    if field.format == Format.string:
        write_string(data, value)
    else:
        data.write(pack(field.format, value))


def serialize_cookie(cookie: Cookie) -> bytes:
    """Serializes a cookie object to Apple's binary cookie record format."""
    cookie_fields = CookieFields()

    # Cookie record layout (matches Safari/CFNetwork):
    # 0-3: size, 4-7: unknownOne, 8-11: flags, 12-15: unknownTwo
    # 16-19: domainOffset, 20-23: nameOffset, 24-27: pathOffset, 28-31: valueOffset
    # 32-35: commentOffset (0 = no comment), 36-39: commentURLOffset (0 = none)
    # 40-47: expires (float64 LE), 48-55: creation (float64 LE)
    # 56+: null-terminated domain, name, path, value strings
    url_bytes = cookie.url.encode("utf-8")
    name_bytes = cookie.name.encode("utf-8")
    path_bytes = cookie.path.encode("utf-8")
    value_bytes = cookie.value.encode("utf-8")

    # Each string has a null terminator
    strings_size = len(url_bytes) + 1 + len(name_bytes) + 1 + len(path_bytes) + 1 + len(value_bytes) + 1
    total_size = COOKIE_HEADER_SIZE + strings_size

    # Pre-allocate buffer with zeros; comment offsets at 32/36 stay 0 (no comment)
    cookie_data = BytesIO(b"\x00" * total_size)

    # Write size and flag
    cookie_data.write(pack(Format.integer, total_size))
    write_field(cookie_data, cookie_fields.flag, list(FLAGS.keys())[list(FLAGS.values()).index(cookie.flag)])

    # Calculate offsets - strings start right after the fixed header
    domain_offset = COOKIE_HEADER_SIZE
    name_offset = domain_offset + len(url_bytes) + 1  # +1 for null terminator
    path_offset = name_offset + len(name_bytes) + 1
    value_offset = path_offset + len(path_bytes) + 1

    # Write offsets (note: spec calls it domain but code uses url)
    write_field(cookie_data, cookie_fields.url_offset, domain_offset)
    write_field(cookie_data, cookie_fields.name_offset, name_offset)
    write_field(cookie_data, cookie_fields.path_offset, path_offset)
    write_field(cookie_data, cookie_fields.value_offset, value_offset)

    write_field(cookie_data, cookie_fields.expiry_date, date_to_mac_epoch(cookie.expiry_datetime))
    write_field(cookie_data, cookie_fields.create_date, date_to_mac_epoch(cookie.create_datetime))

    # Write domain (url), name, path, value strings
    cookie_data.seek(COOKIE_HEADER_SIZE)
    write_string(cookie_data, cookie.url)
    write_string(cookie_data, cookie.name)
    write_string(cookie_data, cookie.path)
    write_string(cookie_data, cookie.value)

    return cookie_data.getvalue()


def serialize_page(cookies: List[Cookie]) -> bytes:
    """Serializes a list of cookies into a single page in Apple's binary cookies format."""
    cookie_data_list = [serialize_cookie(cookie) for cookie in cookies]

    page = BytesIO()
    page.write(PAGE_HEADER)
    page.write(pack(Format.integer, len(cookie_data_list)))

    # Cookie offsets are relative to the page start:
    # 8-byte page header + 4 bytes per offset + 4-byte page footer
    cookie_offset = 8 + (len(cookie_data_list) * 4) + 4
    for cookie_data in cookie_data_list:
        page.write(pack(Format.integer, cookie_offset))
        cookie_offset += len(cookie_data)

    page.write(PAGE_FOOTER)

    for cookie_data in cookie_data_list:
        page.write(cookie_data)

    return page.getvalue()


def dump(cookies: CookiesCollection, f: Union[BufferedWriter, BytesIO, BinaryIO]):
    """Dumps a Binary Cookies object to create a binary cookies file.

    Args:
        cookies: A Binary Cookies object to be serialized.
        f: The file-like object to write the binary cookies data to.
    """
    binary = dumps(cookies)
    f.write(binary)


def calculate_checksum(page_data: bytes) -> int:
    """Calculates the checksum by summing every 4th byte of the page data.

    Args:
        page_data: The raw bytes of a page.
    Returns:
        int: The checksum value.
    """
    checksum = 0
    # Sum every 4th byte (bytes at positions 0, 4, 8, 12, ...)
    for i in range(0, len(page_data), 4):
        checksum += page_data[i]
    return checksum


def dumps(cookies: CookiesCollection) -> bytes:
    """Dumps a Binary Cookies object to a byte string.

    Args:
        cookies: A Binary Cookies object to be serialized.
    Returns:
        bytes: The serialized binary cookies data.
    """
    if isinstance(cookies, dict):
        cookies = [Cookie.parse_obj(cookies)] if IS_PYDANTIC_V1 else [Cookie.model_validate(cookies)]
    elif isinstance(cookies, (list, tuple)):
        if IS_PYDANTIC_V1:
            cookies = [Cookie.parse_obj(cookie) for cookie in cookies]
        else:
            cookies = [Cookie.model_validate(cookie) for cookie in cookies]
    elif isinstance(cookies, Cookie):
        cookies = [cookies]
    else:
        raise TypeError("Invalid type for cookies. Expected dict, list, tuple, or Cookie.")

    file_fields = FileFields()

    # Safari stores one page per domain, in first-seen order
    cookies_by_domain: Dict[str, List[Cookie]] = {}
    for cookie in cookies:
        cookies_by_domain.setdefault(cookie.url, []).append(cookie)
    pages = [serialize_page(domain_cookies) for domain_cookies in cookies_by_domain.values()]

    data = BytesIO()

    # Write file header (4 bytes: "cook")
    data.write(b"cook")

    # Number of pages (big-endian)
    write_field(data, file_fields.num_pages, len(pages))

    # Page sizes (big-endian), followed by the page data itself
    for page in pages:
        data.write(pack(Format.integer_be, len(page)))
    for page in pages:
        data.write(page)

    # File tail: 4-byte big-endian checksum over every 4th byte of each page,
    # the 8-byte footer magic, and a binary plist with the cookie accept policy
    checksum = sum(calculate_checksum(page) for page in pages)
    data.write(pack(">I", checksum & 0xFFFFFFFF))
    data.write(FILE_FOOTER)
    data.write(plistlib.dumps({"NSHTTPCookieAcceptPolicy": DEFAULT_COOKIE_ACCEPT_POLICY}, fmt=plistlib.FMT_BINARY))

    return data.getvalue()
