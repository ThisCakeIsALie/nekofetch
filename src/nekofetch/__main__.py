from __future__ import annotations

import argparse
import base64
from io import BytesIO
import os
import shutil
import subprocess
import sys
from typing import Tuple

from PIL import Image
import requests

API_RANDOM = "https://nekos.moe/api/v1/random/image"
IMAGE_URL = "https://nekos.moe/image/{image_id}"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

SUPPORTED_KITTY_TERMINALS = ("kitty", "wezterm", "ghostty", "contour")
SIXEL_TOOL = "img2sixel"
CHAFA_TOOL = "chafa"


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


def choose_graphics_protocol(requested: str = "auto") -> str:
    """Pick the best available graphics protocol for the current terminal."""
    if not sys.stdout.isatty():
        sys.stderr.write("nekofetch needs a TTY to render inline images.\n")
        raise SystemExit(1)

    if requested != "auto":
        if requested == "sixel" and not shutil.which(SIXEL_TOOL):
            raise RuntimeError(f"{SIXEL_TOOL} is required for sixel output")
        if requested == "chafa" and not shutil.which(CHAFA_TOOL):
            raise RuntimeError(f"{CHAFA_TOOL} is required for chafa output")
        return requested

    if supports_kitty_graphics():
        return "kitty"

    # For an unknown terminal, do not blindly emit sixel merely because an
    # encoder happens to be installed. Chafa's symbols mode and the native ANSI
    # renderer only use ordinary text/color escape sequences, so they are safe
    # fallbacks for SSH clients such as Termius.
    if shutil.which(CHAFA_TOOL):
        return "chafa"

    return "ansi"


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


def display_with_sixel(image_bytes: bytes) -> None:
    try:
        subprocess.run(
            [SIXEL_TOOL],
            input=image_bytes,
            stdout=sys.stdout.buffer,
            check=True,
        )
    except FileNotFoundError:
        raise RuntimeError(f"{SIXEL_TOOL} is required for sixel output") from None
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"{SIXEL_TOOL} failed to render the image") from exc
    sys.stdout.flush()


def display_with_chafa(image_bytes: bytes) -> None:
    """Render through Chafa using only Unicode symbols and ANSI colors."""
    try:
        subprocess.run(
            [CHAFA_TOOL, "--format=symbols", "--size=60x30", "-"],
            input=image_bytes,
            stdout=sys.stdout.buffer,
            check=True,
        )
    except FileNotFoundError:
        raise RuntimeError(f"{CHAFA_TOOL} is required for chafa output") from None
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"{CHAFA_TOOL} failed to render the image") from exc
    sys.stdout.flush()


def display_with_ansi(image_bytes: bytes) -> None:
    """Render an image as true-color Unicode half blocks; works in plain terminals."""
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            img = source.convert("RGB")
    except Exception as exc:
        raise RuntimeError("Failed to decode image bytes for ANSI rendering") from exc

    terminal_width = shutil.get_terminal_size((80, 24)).columns
    target_width = max(1, min(60, terminal_width, img.width))
    target_height = max(1, round(img.height * target_width / img.width))
    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

    pixels = img.load()
    lines = []
    for y in range(0, target_height, 2):
        parts = []
        lower_y = min(y + 1, target_height - 1)
        for x in range(target_width):
            upper = pixels[x, y]
            lower = pixels[x, lower_y]
            parts.append(
                f"\x1b[38;2;{upper[0]};{upper[1]};{upper[2]}m"
                f"\x1b[48;2;{lower[0]};{lower[1]};{lower[2]}m▀"
            )
        parts.append("\x1b[0m")
        lines.append("".join(parts))

    sys.stdout.write("\n".join(lines) + "\n")
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
        raise RuntimeError("Failed to decode image bytes for rendering") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch a random catgirl and display it via Kitty, sixel, Chafa, "
            "or a terminal-safe ANSI fallback."
        )
    )
    parser.add_argument(
        "--protocol",
        choices=("auto", "kitty", "sixel", "chafa", "ansi"),
        default="auto",
        help="Rendering protocol to use (default: auto).",
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
        protocol = choose_graphics_protocol(args.protocol)
        image_bytes, _image_id = fetch_random_image(args.nsfw)
        png_bytes = ensure_png(image_bytes)
        if protocol == "kitty":
            display_with_kitty_protocol(png_bytes)
        elif protocol == "sixel":
            display_with_sixel(png_bytes)
        elif protocol == "chafa":
            display_with_chafa(png_bytes)
        else:
            display_with_ansi(png_bytes)
    except KeyboardInterrupt:
        sys.stderr.write("\nCancelled.\n")
        raise SystemExit(1)
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
