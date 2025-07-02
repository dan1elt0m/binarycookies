[![Github Actions Status](https://github.com/dan1elt0m/binary-cookies-reader/workflows/test/badge.svg)](https://github.com/dan1elt0m/binary-cookies-reader/actions/workflows/test.yml)
<h1>
  <img src="docs/bincook.png" width="30" style="vertical-align: middle; margin-right: 10px;">
  Binary Cookies
</h1>

CLI tool and Python library for reading and writing Binary Cookies.

### Requirements

- Python >= 3.9

### Installation
```bash 
pip install binarycookies
```

### CLI example:
```sh
bcparser path/to/cookies.binarycookies
```

Output:
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

`ascii` output is also possible with the --output ascii flag.

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

### License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

### Contributing
Contributions are welcome! If you find a bug or have a feature request, please open an issue on GitHub. Pull requests are also welcome.
