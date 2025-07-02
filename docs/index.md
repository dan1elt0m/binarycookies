# Binary Cookies

Python library and CLI tool for reading and writing binary cookies files.

## Requirements

- Python 3.9 or higher

## Installation
```bash 
pip install binarycookies
```
If you want to use the parser as CLI, it's recommended to use pipx to install the package in an isolated environment.
```bash 
pipx install binarycookies
```

## Basic Usage CLI
After installation, you can use the command-line interface to read a binary cookies file:

```bash
bcparser <path_to_binary_cookies_file>
```
Replace <path_to_binary_cookies_file> with the path to the binary cookie file you want to read.

### Basic Usage Python

#### Deserialization

```python
import binarycookies 

with open("path/to/cookies.binarycookies", "rb") as f:
    cookies = binarycookies.load(f)
```

#### Serialization

```python
import binarycookies 

cookie = {
    "name": "session_id",
    "value": "abc123",
    "url": "https://example.com",
    "path": "/",
    "create_datetime": "2023-10-01T12:34:56+00:00",
    "expiry_datetime": "2023-12-31T23:59:59+00:00",
    "flag": "Secure"
}

with open("path/to/cookies.binarycookies", "wb") as f:
    binarycookies.dump(cookie, f)
```

## Output Types

The `bcparser` CLI supports two output types: `json` (default) and `ascii`.

### JSON Output

The `json` output type formats the cookies as a JSON array, making it easy to parse and manipulate programmatically.

Example usage:
```sh
bcparser path/to/cookies.binarycookies --output json
```

Example output JSON:
```json
[
  {
    "name": "session_id",
    "value": "abc123",
    "url": "https://example.com",
    "path": "/",
    "create_datetime": "2023-10-01T12:34:56+00:00",
    "expiry_datetime": "2023-12-31T23:59:59+00:00",
    "flag": "Secure"
  },
  {
    "name": "user_token",
    "value": "xyz789",
    "url": "https://example.com",
    "path": "/account",
    "create_datetime": "2023-10-01T12:34:56+00:00",
    "expiry_datetime": "2023-12-31T23:59:59+00:00",
    "flag": "HttpOnly"
  }
]
```

### ASCII Output
The ascii output type formats the cookies in a simple, line-by-line text format, making it easy to read and pipe to other command-line tools.

Example usage:
```sh
bcparser path/to/cookies.binarycookies --output ascii
```

Example output ASCII:
```text
Name: session_id
Value: abc123
URL: https://example.com
Path: /
Created: 2023-10-01T12:34:56+00:00
Expires: 2023-12-31T23:59:59+00:00
Flag: Secure
----------------------------------------
Name: user_token
Value: xyz789
URL: https://example.com
Path: /account
Created: 2023-10-01T12:34:56+00:00
Expires: 2023-12-31T23:59:59+00:00
Flag: HttpOnly
----------------------------------------
```


### Netscape Output
For `netscape` output use the --output netscape flag.
Example usage:
```sh
bcparser path/to/cookies.binarycookies --output netscape
```

Example output Netscape:
```netscape 
# Netscape HTTP Cookie File
example.com	FALSE	/	TRUE	1704067199	session_id	abc123
example.com	FALSE	/account	FALSE	1704067199	user_token	xyz789
```