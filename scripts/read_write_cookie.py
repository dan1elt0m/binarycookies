import sys

import binarycookies


def main(path: str) -> None:
    print(f"Processing file at: {path}")
    with open(path, "rb") as f:
        cookies = binarycookies.load(f)

    with open("output.binarycookies", "wb") as f:
        binarycookies.dump(cookies, f)


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0])
