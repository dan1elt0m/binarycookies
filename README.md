[![Github Actions Status](https://github.com/dan1elt0m/binary-cookies-reader/workflows/test/badge.svg)](https://github.com/dan1elt0m/binary-cookies-reader/actions/workflows/test.yml)
<h1>
  <img src="docs/bincook.png" width="30" style="vertical-align: middle; margin-right: 10px;">
  Binary Cookies
</h1>

CLI tool and Python library for reading and writing Binary Cookies.

### Documentation
For detailed documentation, please visit the [Binary Cookies Documentation](https://dan1elt0m.github.io/binarycookies/)

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
    "flag": "Secure",
    "raw_flags": 1,
    "comment": null
  },
  {
    "name": "user_token",
    "value": "xyz789",
    "url": "https://example.com",
    "path": "/account",
    "create_datetime": "2023-10-01T12:34:56+00:00",
    "expiry_datetime": "2023-12-31T23:59:59+00:00",
    "flag": "HttpOnly",
    "raw_flags": 4,
    "comment": null
  }
]
```
#### Output formats
The CLI supports multiple output formats using the --output flag.
- `json` (default): Outputs cookies in JSON format.
- `ascii`: Outputs cookies in a human-readable ASCII format with each cookie property on a separate line.
- `netscape`: Outputs cookies in the Netscape cookie file format.

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
    "url": "https://example.com",  # "domain" is accepted as an alias for "url"
    "path": "/",
    "create_datetime": "2023-10-01T12:34:56+00:00",
    "expiry_datetime": "2023-12-31T23:59:59+00:00",
    "flag": "Secure"
}

with open("path/to/cookies.binarycookies", "wb") as f:
    binarycookies.dump(cookie, f)
```

Optional fields:
- `comment`: cookie comment string stored in the file (default: no comment)
- `raw_flags`: the raw flags bitfield written to disk. When omitted, it is derived
  from `flag` (`Secure` = 1, `HttpOnly` = 4, `Secure; HttpOnly` = 5). Cookies read
  with `load`/`loads` always carry `raw_flags`, so unknown flag bits survive a
  read-modify-write round trip.

### Ethical Use & Responsible Handling
This project is intended for lawful, ethical use only. Typical, appropriate uses include:
- Inspecting Binary Cookies from your own devices or data you are authorized to access
- DFIR, QA, and security testing performed with explicit, written permission
- Educational/research work on datasets that are owned by you, anonymized, or publicly released for that purpose

You must not use this tool to:
- Access, extract, modify, or distribute cookies from systems or accounts you do not own or have permission to analyze
- Bypass authentication, session management, DRM, or other technical controls
- Enable tracking, stalking, doxxing, fraud, or other privacy-invasive or harmful activities


### License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

### Contributing
Contributions are welcome! If you find a bug or have a feature request, please open an issue on GitHub. Pull requests are also welcome.
