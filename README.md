# A duck family crosses a rain puddle at golden hour

Entry for [make.fun's ai-happy-01](https://make.fun/bounty/ai-happy-01): a program
that writes one image made to make the house AI judge happy.

`main.py` writes `entry.png` — a line of rubber ducks crossing a puddle at golden
hour, the smallest duckling riding on the lead duck's back, a birthday hat on the
lead duck, and a folded paper boat left in the water. The picture is
`art/entry.png`; the entrypoint checks it against every gate rule (whole PNG with
each chunk's CRC, at most 1 MiB, at most 1024 by 1024) and copies its bytes to the
run's output directory, so two runs write identical bytes.

## Run it

```bash
MAKEFUN_OUTPUT_DIR=out python3 main.py     # writes out/entry.png
python3 main.py --check-only               # validate the file, write nothing
```

## Redraw the picture

```bash
python3 tools/draw.py                      # needs Pillow and NumPy
```

`tools/draw.py` is the drawing program: fixed geometry and a fixed seed, no
network, no randomness. It renders at 2048 px and downsamples to 1024 with
Lanczos; the same run produces the same bytes.

## What it is

- a low sun behind warm cloud, and a puddle holding an upside-down sky;
- four ducks in a diagonal line, each with a soft reflection, plus the duckling;
- one paper party hat and one folded paper boat: the two small, specific reasons
  to be happy, rather than a stock smiley face.

MIT licensed.
