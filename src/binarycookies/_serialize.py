from datetime import datetime, timezone
from io import BufferedWriter, BytesIO
from struct import pack
from typing import BinaryIO, Dict, List, Tuple, Union

from pydantic import __version__ as pydantic_version

from binarycookies._deserialize import FLAGS
from binarycookies.models import BcField, Cookie, CookieFields, FileFields, Format

IS_PYDANTIC_V1 = pydantic_version.startswith("1.")

CookiesCollection = Union[List[Dict], List[Cookie], Tuple[Dict], Tuple[Cookie], Cookie, Dict[str, str]]


def date_to_mac_epoch(date: datetime) -> int:
    """Converts a datetime object to mac epoch time."""
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
    """Serializes a cookie object to binary format."""
    cookie_fields = CookieFields()

    # Pre-calculate the size to allocate buffer
    # Cookie header is 60 bytes according to spec:
    # 0-3: size, 4-7: unknownOne, 8-11: flags, 12-15: unknownTwo
    # 16-19: domainOffset, 20-23: nameOffset, 24-27: pathOffset, 28-31: valueOffset
    # 32-35: commentOffset, 36-39: endHeader
    # 40-47: expires, 48-55: creation
    # 56-59: comment (empty), 60+: domain, name, path, value strings
    url_bytes = cookie.url.encode("utf-8")
    name_bytes = cookie.name.encode("utf-8")
    path_bytes = cookie.path.encode("utf-8")
    value_bytes = cookie.value.encode("utf-8")
    comment_bytes = b""  # Empty comment

    # Each string has a null terminator
    header_size = 60
    strings_size = (
        len(comment_bytes) + 1 + len(url_bytes) + 1 + len(name_bytes) + 1 + len(path_bytes) + 1 + len(value_bytes) + 1
    )
    total_size = header_size + strings_size

    # Pre-allocate buffer with zeros
    cookie_data = BytesIO(b"\x00" * total_size)

    # Write flag
    write_field(cookie_data, cookie_fields.flag, list(FLAGS.keys())[list(FLAGS.values()).index(cookie.flag)])

    # Calculate offsets - strings start at byte 60 after header
    comment_offset = 60
    domain_offset = comment_offset + len(comment_bytes) + 1  # +1 for null terminator
    name_offset = domain_offset + len(url_bytes) + 1
    path_offset = name_offset + len(name_bytes) + 1
    value_offset = path_offset + len(path_bytes) + 1

    # Write offsets (note: spec calls it domain but code uses url)
    write_field(cookie_data, cookie_fields.url_offset, domain_offset)
    write_field(cookie_data, cookie_fields.name_offset, name_offset)
    write_field(cookie_data, cookie_fields.path_offset, path_offset)
    write_field(cookie_data, cookie_fields.value_offset, value_offset)

    # Write commentOffset at offset 32
    cookie_data.seek(32)
    cookie_data.write(pack(Format.integer, comment_offset))

    # Write endHeader marker at offset 36 (4 bytes of 0x00)
    cookie_data.seek(36)
    cookie_data.write(b"\x00\x00\x00\x00")

    write_field(cookie_data, cookie_fields.expiry_date, date_to_mac_epoch(cookie.expiry_datetime))
    write_field(cookie_data, cookie_fields.create_date, date_to_mac_epoch(cookie.create_datetime))

    # Write string data starting at offset 60
    cookie_data.seek(60)
    # Write comment (empty string with null terminator)
    write_string(cookie_data, "")
    # Write domain (url), name, path, value
    write_string(cookie_data, cookie.url)
    write_string(cookie_data, cookie.name)
    write_string(cookie_data, cookie.path)
    write_string(cookie_data, cookie.value)

    # Write size at the beginning
    size = len(cookie_data.getvalue())
    cookie_data.seek(0)
    cookie_data.write(pack(Format.integer, size))
    return cookie_data.getvalue()


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

    data = BytesIO()

    # Write file header (4 bytes: "cook")
    data.write(b"cook")

    # Number of pages (1 for simplicity, big-endian)
    write_field(data, file_fields.num_pages, 1)

    # Write page size pointer
    data.write(pack(Format.integer, 0))  # Placeholder, will be updated

    # Store the position where page data starts
    page_start_offset = data.tell()
    page_data = BytesIO()

    # Write pageStart marker (4 bytes) - Must be 0x00, 0x01, 0x00, 0x00
    page_data.write(b"\x00\x01\x00\x00")

    # Write number of cookies in the page
    page_data.write(pack(Format.integer, len(cookies)))

    cookie_data_list = []
    # Serialize cookies
    for cookie in cookies:
        cookie_data_list.append(serialize_cookie(cookie))

    # Calculate where cookie data will start:
    # current position + (num_cookies * 4 bytes for offsets) + 4 bytes for pageEnd marker
    initial_cookie_offset = page_data.tell() + (len(cookies) * 4) + 4
    initial_cookie = True
    previous_sizes = 0

    # Write cookie offsets
    for cookie_data in cookie_data_list:
        if initial_cookie:
            page_data.write(pack(Format.integer, initial_cookie_offset))
            initial_cookie = False
        else:
            page_data.write(pack(Format.integer, previous_sizes + initial_cookie_offset))

        previous_sizes += len(cookie_data)

    # Write pageEnd marker (4 bytes) - Must be 0x00, 0x00, 0x00, 0x00
    page_data.write(b"\x00\x00\x00\x00")

    # Write cookie data
    for cookie_data in cookie_data_list:
        page_data.write(cookie_data)

    # Get the complete page data
    page_bytes = page_data.getvalue()
    page_size = len(page_bytes)

    # Update page size in the file header (big-endian format for page sizes)
    data.seek(8)
    data.write(pack(Format.integer_be, page_size))

    # Write the page data
    data.seek(page_start_offset)
    data.write(page_bytes)

    # Calculate and write checksum after all pages
    # The checksum is the sum of every 4th byte of the page data
    # Specification says 8 bytes, so we write it as a 64-bit integer
    checksum = calculate_checksum(page_bytes)
    data.write(pack("<Q", checksum))  # LE_uint64 (8 bytes)

    return data.getvalue()
