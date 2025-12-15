# nekofetch

Fetch a random catgirl image from nekos.moe and display it in a Kitty terminal using the inline graphics protocol.

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

Requires running inside a Kitty terminal (`TERM=xterm-kitty`) with the `kitty` binary available in `PATH`.
