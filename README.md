# nekofetch

Fetch a random catgirl image from nekos.moe and display it inline using the Kitty graphics protocol (Kitty, WezTerm, Ghostty, etc.).

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

You need a terminal that understands the Kitty graphics protocol; no external `kitty +kitten icat` binary is required. If you're using a compatible terminal that isn't auto-detected, set `NEKOFETCH_ASSUME_KITTY_PROTOCOL=1`.
