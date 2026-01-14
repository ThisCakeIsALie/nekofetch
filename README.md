# nekofetch

Fetch a random catgirl image from nekos.moe and display it inline using the Kitty graphics protocol (Kitty, WezTerm, Ghostty, etc.) or sixel (via img2sixel).

## Install

```bash
uv tool install .
```

## Usage

```bash
nekofetch
nekofetch --nsfw     # allow NSFW catgirls
nekofetch --no-nsfw  # force SFW (default)
```

If the terminal does not support Kitty, nekofetch falls back to sixel output via `img2sixel` (installable with libsixel). If you're using a compatible terminal that isn't auto-detected, set `NEKOFETCH_ASSUME_KITTY_PROTOCOL=1`.
