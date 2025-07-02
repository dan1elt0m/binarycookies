import json
from datetime import datetime
from enum import Enum
from sys import stdout
from typing import Callable, List, Type

from rich import print as rprint

from binarycookies._serialize import IS_PYDANTIC_V1
from binarycookies.models import Cookie


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj: Type) -> str:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class OutputType(str, Enum):
    json = "json"
    ascii = "ascii"
    netscape = "netscape"


def _output_json(cookies: List[Cookie]):
    """Outputs cookies in JSON format."""
    output = [cookie.dict() for cookie in cookies] if IS_PYDANTIC_V1 else [cookie.model_dump() for cookie in cookies]
    json.dump(output, indent=2, cls=DateTimeEncoder, fp=stdout)


def _output_ascii(cookies: List[Cookie]):
    """Outputs cookies in a human-readable ASCII format."""
    for cookie in cookies:
        rprint(f"Name: {cookie.name}")
        rprint(f"Value: {cookie.value}")
        rprint(f"URL: {cookie.url}")
        rprint(f"Path: {cookie.path}")
        rprint(f"Created: {cookie.create_datetime.isoformat()}")
        rprint(f"Expires: {cookie.expiry_datetime.isoformat()}")
        rprint(f"Flag: {cookie.flag.value}")
        rprint("-" * 40)


def _output_netscape(cookies: List[Cookie]):
    """Outputs cookies in Netscape cookie file format."""
    # http://www.cookiecentral.com/faq/#3.5
    print("# Netscape HTTP Cookie File")
    for cookie in cookies:
        expiry_ts = int(cookie.expiry_datetime.timestamp())
        domain = cookie.url
        print(
            "%(domain)s\t%(flag)s\t%(path)s\t%(secure)s\t%(expiry)d\t%(name)s\t%(value)s"
            % {
                "domain": domain,
                "flag": str(domain.startswith(".")).upper(),
                "path": cookie.path,
                "secure": str("Secure" in cookie.flag.value).upper(),
                "expiry": expiry_ts,
                "name": cookie.name,
                "value": cookie.value,
            }
        )


OUTPUT_HANDLERS: dict[str, Callable[[List[Cookie]], None]] = {
    OutputType.json: _output_json,
    OutputType.ascii: _output_ascii,
    OutputType.netscape: _output_netscape,
}
