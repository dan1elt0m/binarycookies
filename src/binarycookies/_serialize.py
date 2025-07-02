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
    cookie_data = BytesIO()
    cookie_fields = CookieFields()
    # Write flag
    write_field(cookie_data, cookie_fields.flag, list(FLAGS.keys())[list(FLAGS.values()).index(cookie.flag)])

    # Calculate offsets
    url_offset = 56  # The actual cookies content always starts at byte 56
    name_offset = 1 + url_offset + len(cookie.url.encode("utf-8"))
    path_offset = 1 + name_offset + len(cookie.name.encode("utf-8"))
    value_offset = 1 + path_offset + len(cookie.path.encode("utf-8"))

    write_field(cookie_data, cookie_fields.url_offset, url_offset)
    write_field(cookie_data, cookie_fields.name_offset, name_offset)
    write_field(cookie_data, cookie_fields.path_offset, path_offset)
    write_field(cookie_data, cookie_fields.value_offset, value_offset)

    write_field(cookie_data, cookie_fields.expiry_date, date_to_mac_epoch(cookie.expiry_datetime))
    write_field(cookie_data, cookie_fields.create_date, date_to_mac_epoch(cookie.create_datetime))

    # Write cookie data
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
    """Dumps a Binary Cookies object to create a binary cookies file.k

    Args:
        cookies: A Binary Cookies object to be serialized.
        f: The file-like object to write the binary cookies data to.
    """
    binary = dumps(cookies)
    f.write(binary)


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

    # Write file header
    write_field(data, file_fields.header, "cook")

    # Number of pages (1 for simplicity)
    write_field(data, file_fields.num_pages, 1)

    # Write number of cookies
    data.write(pack(Format.integer, len(cookies)))

    # Placeholder for page size
    page_size_offset = data.tell()
    data.write(b"\x00\x00\x00\x00")

    # Write number of cookies
    data.write(pack(Format.integer, len(cookies)))
    cookie_data_list = []
    # Write cookies
    for cookie in cookies:
        cookie_data_list.append(serialize_cookie(cookie))

    initial_cookie_offset = data.tell() + (len(cookies) * 4)
    initial_cookie = True
    previous_sizes = 0
    for cookie_data in cookie_data_list:
        if initial_cookie:
            data.write(pack(Format.integer, initial_cookie_offset))
            initial_cookie = False
        else:
            data.write(pack(Format.integer, previous_sizes + initial_cookie_offset))

        previous_sizes += len(cookie_data)

    # Unknown data
    data.write(b"\x00\x00\x00\x00")
    data.write(b"\x00\x00\x00\x00")
    data.write(b"\x00\x00\x00\x00")

    for cookie_data in cookie_data_list:
        data.write(cookie_data)

    # Update page size
    page_size = data.tell()
    data.seek(page_size_offset)
    data.write(pack(Format.integer, page_size))

    return data.getvalue()
