# Command Line Interface

Binarycookies provides a command-line interface to easily read binary cookie files.

## Installation

The CLI is automatically installed when you install the package:

```bash
pip install binarycookies
```
## Usage

bcparser FILE_PATH [--output FORMAT]

### Arguments
- `FILE_PATH`: Path to the binary cookies file you want to read.
 
#### Options
- `--output FORMAT`: Specify the output format. Supported formats are `json` (default), `ascii` and `netscape`.

### Examples
**JSON Output (Default):**
```bash
bcparser /path/to/cookies.binarycookies
```
**ASCII Output:**
```bash
bcparser /path/to/cookies.binarycookies --output ascii
```
This will display cookies in a human-readable format with each cookie property on a separate line.

**Netscape Format Output:**
```bash
bcparser /path/to/cookies.binarycookies --output netscape
```
This will display cookies in the Netscape cookie file format.

### Adding to Your Scripts
The CLI functionality can be integrated into your Python scripts as follows:

```python
from binarycookies.__main__ import cli

# Read and output cookies in JSON format
cli("path/to/Cookies.binarycookies", output="json")

# Read and output cookies in ASCII format
cli("path/to/Cookies.binarycookies", output="ascii")

# Read and output cookies in ASCII format
cli("path/to/Cookies.binarycookies", output="netscape")
```
