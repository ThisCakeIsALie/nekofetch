from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from typing import Tuple

import requests

API_RANDOM = "https://nekos.moe/api/v1/random/image"
IMAGE_URL = "https://nekos.moe/image/{image_id}"


def require_kitty() -> None:
    """Fail early if we're not in a Kitty terminal or the binary is missing."""
    if not shutil.which("kitty"):
        sys.stderr.write("kitty executable not found in PATH; install Kitty to view images.\n")
        raise SystemExit(1)

    term = os.environ.get("TERM", "")
    kitty_id = os.environ.get("KITTY_WINDOW_ID")
    if "kitty" not in term and not kitty_id:
        sys.stderr.write("This script requires a Kitty terminal for inline graphics.\n")
        raise SystemExit(1)


def fetch_random_image(nsfw: bool) -> Tuple[bytes, str]:
    resp = requests.get(API_RANDOM, params={"nsfw": str(nsfw).lower(), "count": 1}, timeout=10)
    resp.raise_for_status()

    try:
        payload = resp.json()
        image_id = payload["images"][0]["id"]
    except Exception as exc:  # pragma: no cover - defensive parsing
        raise RuntimeError(f"Unexpected response from nekos.moe: {resp.text}") from exc

    img_resp = requests.get(IMAGE_URL.format(image_id=image_id), timeout=20)
    img_resp.raise_for_status()
    return img_resp.content, image_id


def display_with_kitty(image_bytes: bytes) -> None:
    # kitty icat can read from stdin; avoids temp files.
    result = subprocess.run(
        ["kitty", "+kitten", "icat", "--align", "left", "--stdin", "yes"],
        input=image_bytes,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"kitty icat failed with exit code {result.returncode}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch a random catgirl and display it with Kitty.")
    try:
        boolean_action = argparse.BooleanOptionalAction  # type: ignore[attr-defined]
    except AttributeError:
        parser.add_argument(
            "--nsfw",
            dest="nsfw",
            action="store_true",
            default=False,
            help="Allow NSFW catgirls instead of the default SFW images.",
        )
        parser.add_argument(
            "--no-nsfw",
            dest="nsfw",
            action="store_false",
            help="Force SFW catgirls (default).",
        )
    else:
        parser.add_argument(
            "--nsfw",
            action=boolean_action,
            default=False,
            help="Allow NSFW catgirls instead of the default SFW images.",
        )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        require_kitty()
        image_bytes, image_id = fetch_random_image(args.nsfw)
        display_with_kitty(image_bytes)
    except KeyboardInterrupt:
        sys.stderr.write("\nCancelled.\n")
        raise SystemExit(1)
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
