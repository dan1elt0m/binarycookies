#!/usr/bin/env python3
"""Test script to verify the version option works correctly."""

import subprocess
import sys

from binarycookies import __version__


def test_version_option():
    """Test the --version flag."""
    print("Testing --version flag...")
    result = subprocess.run(
        [sys.executable, "-m", "binarycookies", "--version"], capture_output=True, text=True, check=False
    )

    output = result.stdout + result.stderr
    print(f"Output: {output}")

    expected = f"binarycookies version {__version__}"

    assert expected in output


def test_short_version_option():
    """Test the -v flag."""
    print("\nTesting -v flag...")
    result = subprocess.run([sys.executable, "-m", "binarycookies", "-v"], capture_output=True, text=True, check=False)

    output = result.stdout + result.stderr
    print(f"Output: {output}")

    expected = f"binarycookies version {__version__}"
    assert expected in output


def test_help_includes_version():
    """Test that --help shows the version option."""
    print("\nTesting --help includes version option...")
    result = subprocess.run(
        [sys.executable, "-m", "binarycookies", "--help"], capture_output=True, text=True, check=False
    )

    output = result.stdout + result.stderr

    assert "--version" in output
    assert "Show version and exit" in output
