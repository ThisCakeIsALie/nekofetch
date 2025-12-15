from __future__ import annotations

import argparse
import base64
from io import BytesIO
import os
import sys
from typing import Tuple

from PIL import Image
import requests

API_RANDOM = "https://nekos.moe/api/v1/random/image"
IMAGE_URL = "https://nekos.moe/image/{image_id}"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

SUPPORTED_KITTY_TERMINALS = ("kitty", "wezterm", "ghostty", "contour")


def supports_kitty_graphics() -> bool:
    """Heuristically detect terminals that speak the Kitty graphics protocol."""
    term = os.environ.get("TERM", "").lower()
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    if any(marker in term for marker in SUPPORTED_KITTY_TERMINALS):
        return True
    if any(marker in term_program for marker in SUPPORTED_KITTY_TERMINALS):
        return True
    if os.environ.get("KITTY_WINDOW_ID") or os.environ.get("WEZTERM_PANE"):
        return True
    return False


def require_kitty_protocol() -> None:
    """Fail early if stdout is not a TTY or the terminal lacks graphics support."""
    if not sys.stdout.isatty():
        sys.stderr.write("nekofetch needs a TTY to render inline images.\n")
        raise SystemExit(1)

    if os.environ.get("NEKOFETCH_ASSUME_KITTY_PROTOCOL"):
        return

    if not supports_kitty_graphics():
        sys.stderr.write(
            "Terminal does not appear to support the Kitty graphics protocol. "
            "Try Kitty/WezTerm or set NEKOFETCH_ASSUME_KITTY_PROTOCOL=1 to force.\n"
        )
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


def display_with_kitty_protocol(image_bytes: bytes) -> None:
    """
    Send image bytes using Kitty's inline graphics protocol.

    The payload is base64 encoded and chunked to keep within the protocol limits.
    """
    encoded = base64.b64encode(image_bytes)
    chunk_size = 4096
    buf_write = sys.stdout.buffer.write

    for idx in range(0, len(encoded), chunk_size):
        chunk = encoded[idx : idx + chunk_size]
        more = idx + chunk_size < len(encoded)
        if idx == 0:
            header = f"a=T,f=100,m={int(more)}".encode("ascii")
        else:
            header = f"m={int(more)}".encode("ascii")

        buf_write(b"\x1b_G")
        buf_write(header)
        buf_write(b";")
        buf_write(chunk)
        buf_write(b"\x1b\\")

    buf_write(b"\n")
    sys.stdout.flush()


def ensure_png(image_bytes: bytes) -> bytes:
    """The Kitty protocol expects PNG data when f=100; convert if needed."""
    if image_bytes.startswith(PNG_SIGNATURE):
        return image_bytes

    try:
        with Image.open(BytesIO(image_bytes)) as img:
            buf = BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
    except Exception as exc:
        raise RuntimeError("Failed to decode image bytes for Kitty rendering") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch a random catgirl and display it via the Kitty graphics protocol."
    )
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
        require_kitty_protocol()
        image_bytes, _image_id = fetch_random_image(args.nsfw)
        png_bytes = ensure_png(image_bytes)
        display_with_kitty_protocol(png_bytes)
    except KeyboardInterrupt:
        sys.stderr.write("\nCancelled.\n")
        raise SystemExit(1)
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
