# nekofetch

Fetch a random catgirl image from nekos.moe and display it inline using the Kitty graphics protocol (Kitty, WezTerm, Ghostty, etc.), sixel, Chafa, or a terminal-safe ANSI/Unicode fallback.

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

Rendering defaults to `--protocol auto`. Kitty-compatible terminals use the Kitty graphics protocol. Other terminals use Chafa's symbol renderer when `chafa` is installed, otherwise nekofetch falls back to a built-in true-color Unicode half-block renderer that works in ordinary terminals such as Termius.

You can force a renderer with:

```bash
nekofetch --protocol kitty
nekofetch --protocol sixel
nekofetch --protocol chafa
nekofetch --protocol ansi
```

Sixel output requires `img2sixel` (libsixel), and Chafa output requires `chafa`. The ANSI fallback has no extra dependency beyond nekofetch itself.

If you're using a Kitty-compatible terminal that isn't auto-detected, set `NEKOFETCH_ASSUME_KITTY_PROTOCOL=1`. To explicitly opt into sixel auto-selection, set `NEKOFETCH_ASSUME_SIXEL_PROTOCOL=1`.
