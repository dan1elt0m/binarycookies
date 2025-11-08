from importlib.metadata import PackageNotFoundError, version

from binarycookies._deserialize import load, loads
from binarycookies._serialize import dump, dumps

try:
    __version__ = version("binarycookies")
except PackageNotFoundError:
    # Package is not installed, fallback to a default
    __version__ = "0.0.0+unknown"

__all__ = ["dump", "dumps", "load", "loads"]
