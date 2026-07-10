import sys
from datetime import datetime, timedelta, timezone
from io import BytesIO
from struct import unpack
from typing import BinaryIO, List, Union

from binarycookies.models import (
    BcField,
    BinaryCookiesDecodeError,
    Cookie,
    CookieFields,
    FileFields,
    Flag,
    Format,
)

SECURE_BIT = 0x1
HTTP_ONLY_BIT = 0x4

# Kept for backwards compatibility; interpret_flag treats flags as a bitfield instead
FLAGS = {
    0: Flag.UNKNOWN,
    1: Flag.SECURE,
    4: Flag.HTTPONLY,
    5: Flag.SECURE_HTTPONLY,
}


def interpret_flag(flags: int) -> Flag:
    """Interprets the Secure/HttpOnly bits of the raw flags bitfield."""
    secure = bool(flags & SECURE_BIT)
    http_only = bool(flags & HTTP_ONLY_BIT)
    if secure and http_only:
        return Flag.SECURE_HTTPONLY
    if secure:
        return Flag.SECURE
    if http_only:
        return Flag.HTTPONLY
    return Flag.UNKNOWN


MAC_UNIX_OFFSET = 978307200  # Seconds from Unix epoch (1970) to Mac epoch (2001)
INT32_TIME_T_MAX = 2147483647  # Max signed 32-bit time_t (Unix timestamp)
INT32_CUTOFF_DT = datetime(2038, 1, 19, 3, 14, 7, tzinfo=timezone.utc)


def mac_epoch_to_date(epoch: int) -> datetime:
    """
    Convert Mac epoch seconds (since 2001-01-01 UTC) to an aware datetime.

    On 32-bit systems, clamp results that would overflow `time_t` to 2038-01-19T03:14:07Z.
    On 64-bit systems, only clamp if the value exceeds datetime's range (-> datetime.max).
    """
    base = datetime(2001, 1, 1, tzinfo=timezone.utc)
    # Fast path: pure Python arithmetic (independent of C time_t)
    try:
        dt = base + timedelta(seconds=epoch)
    except OverflowError:
        # Beyond datetime range: choose appropriate cap
        if sys.maxsize <= 2**31 - 1:
            return INT32_CUTOFF_DT
        return datetime.max.replace(tzinfo=timezone.utc)

    # 32-bit clamp logic
    if sys.maxsize <= 2**31 - 1:
        unix_ts = epoch + MAC_UNIX_OFFSET
        if unix_ts > INT32_TIME_T_MAX:
            return INT32_CUTOFF_DT
    return dt


def read_string(data: BytesIO, size: int) -> str:
    """Reads a null-terminated UTF-8 string of at most `size` bytes from binary data."""
    raw = data.read(size)
    end = raw.find(b"\x00")
    if end != -1:
        raw = raw[:end]
    return raw.decode("utf-8")


def read_field(data: BytesIO, field: BcField) -> Union[str, int]:
    """Reads a field from binary data."""
    data.seek(field.offset)
    if field.format == Format.string:
        return read_string(data, field.size)
    return unpack(field.format, data.read(field.size))[0]


def read_cookie(cookie: BytesIO, cookie_size: int) -> Cookie:
    """Reads a cookie from the given offset in the page."""

    cookie_fields = CookieFields()
    raw_flags = read_field(cookie, cookie_fields.flag)
    flag = interpret_flag(raw_flags)

    # Read comment offset at offset 32 (0 means the cookie has no comment)
    cookie.seek(32)
    comment_offset = unpack(Format.integer, cookie.read(4))[0]

    url_offset = read_field(cookie, cookie_fields.url_offset)
    name_offset = read_field(cookie, cookie_fields.name_offset)
    path_offset = read_field(cookie, cookie_fields.path_offset)
    value_offset = read_field(cookie, cookie_fields.value_offset)

    expiry_datetime = mac_epoch_to_date(read_field(cookie, cookie_fields.expiry_date))
    create_datetime = mac_epoch_to_date(read_field(cookie, cookie_fields.create_date))

    # Read strings - the comment (if any) comes first, then domain (url)
    comment = None
    if comment_offset > 0:
        comment_end = url_offset if comment_offset <= url_offset else cookie_size
        comment = read_field(
            cookie, BcField(offset=comment_offset, size=comment_end - comment_offset, format=Format.string)
        )
    url = read_field(cookie, BcField(offset=url_offset, size=name_offset - url_offset, format=Format.string))
    name = read_field(cookie, BcField(offset=name_offset, size=path_offset - name_offset, format=Format.string))
    path = read_field(cookie, BcField(offset=path_offset, size=value_offset - path_offset, format=Format.string))
    value = read_field(cookie, BcField(offset=value_offset, size=cookie_size - value_offset, format=Format.string))

    return Cookie(
        name=name,
        value=value,
        url=url,
        path=path,
        create_datetime=create_datetime,
        expiry_datetime=expiry_datetime,
        flag=flag,
        raw_flags=raw_flags,
        comment=comment,
    )


def get_cookie_offsets(page: BytesIO, num_cookies: int) -> List[int]:
    """Reads the offsets of the cookies in the page."""
    return [read_field(page, BcField(offset=8 + (4 * i), size=4, format=Format.integer)) for i in range(num_cookies)]


def get_file_pages(binary_file: BytesIO, num_pages: int) -> List[int]:
    """Reads the sizes of the pages in the binary file."""
    return [
        read_field(binary_file, BcField(offset=8 + (i * 4), size=4, format=Format.integer_be)) for i in range(num_pages)
    ]


def _deserialize_page(page: BytesIO) -> List[Cookie]:
    """Reads a binary cookie file and returns a list of cookies."""
    num_cookies = read_field(page, BcField(offset=4, size=4, format=Format.integer))
    cookie_offsets = get_cookie_offsets(page, num_cookies)
    cookies = []
    for offset in cookie_offsets:
        cookie_size = read_field(page, BcField(offset=offset, size=4, format=Format.integer))
        page.seek(offset)
        cookie = page.read(cookie_size)
        cookies.append(read_cookie(BytesIO(cookie), cookie_size))
    return cookies


def load(bf: BinaryIO) -> List[Cookie]:
    """Deserializes a binary cookie file and returns a list of Cookie objects.

    Args:
        bf (BinaryIO): A binary file object containing the binary cookie data.
    Returns:
        List[Cookie]: A list of Cookie objects.
    """
    # Check if the file is empty
    if bf.readable() and bf.read(1) == b"":
        raise BinaryCookiesDecodeError("The file is empty.")
    # Reset the file pointer to the beginning
    bf.seek(0)
    # Check if the file is a valid binary cookies file
    if bf.readable() and bf.read(4) != b"cook":
        raise BinaryCookiesDecodeError("The file is not a valid binary cookies file. Missing magic String:cook.")
    # Reset the file pointer to the beginning
    bf.seek(0)
    # Deserialize the binary cookies file
    return loads(BytesIO(bf.read()))


def loads(b: BytesIO) -> List[Cookie]:
    """Deserializes a binary cookie file and returns a list of Cookie objects.

    Args:
        b (BytesIO): A BytesIO object containing the binary cookie data.
    Returns:
        List[Cookie]: A list of Cookie objects.
    """
    all_cookies = []
    file_fields = FileFields()

    # Number of pages in the binary file: 4 bytes
    num_pages = read_field(b, field=file_fields.num_pages)
    page_sizes = get_file_pages(b, num_pages)

    pages = []
    b.seek(8 + (num_pages * 4))
    for ps in page_sizes:
        # Grab individual pages and each page will contain >= one cookie
        pages.append(b.read(ps))

    for page in pages:
        cookies = _deserialize_page(BytesIO(page))
        all_cookies.extend(cookies)

    return all_cookies
