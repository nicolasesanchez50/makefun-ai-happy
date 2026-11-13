#!/usr/bin/env python3
"""Draw the entry for make.fun's ai-happy-01: a rubber-duck family crossing a
rain puddle at golden hour, the smallest duckling riding on the big one's back.

Everything is generated from fixed geometry and a fixed seed, so the program
is reproducible byte for byte. Nothing is downloaded, nothing is random.

The scene: warm low sun, a wide puddle holding an upside-down sky, five ducks
in a diagonal line with their reflections, one bright leaf, soft ripples.
"""

import math
import os
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output")

FINAL = 1024          # the size the competition sees
SS = 2                # supersampling factor used while drawing
W = H = FINAL * SS

# Palette: one warm mood, violet dusk at the top of the sky down to gold at
# the water, ducks in egg-yolk yellow with pumpkin beaks.
SKY_STOPS = [
    (0.00, (58, 42, 92)),
    (0.28, (122, 62, 110)),
    (0.52, (198, 92, 108)),
    (0.72, (247, 146, 96)),
    (0.88, (255, 198, 122)),
    (1.00, (255, 227, 170)),
]
ASPHALT = (74, 64, 82)
PUDDLE_EDGE = (255, 214, 158)
DUCK_BODY = (255, 208, 64)
DUCK_LIGHT = (255, 236, 150)
DUCK_SHADE = (233, 160, 44)
DUCK_BEAK = (240, 106, 38)
DUCK_EYE = (48, 32, 24)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def sky_gradient(width, height):
    """Vertical gradient through SKY_STOPS as a float array."""
    ys = np.linspace(0.0, 1.0, height, dtype=np.float32)
    arr = np.zeros((height, width, 3), dtype=np.float32)
    for i in range(len(SKY_STOPS) - 1):
        p0, c0 = SKY_STOPS[i]
        p1, c1 = SKY_STOPS[i + 1]
        band = (ys >= p0) & (ys <= p1)
        t = (ys[band] - p0) / max(p1 - p0, 1e-6)
        for ch in range(3):
            arr[band, :, ch] = np.array(c0[ch], dtype=np.float32) + t[:, None] * (
                float(c1[ch]) - float(c0[ch])
            )
    return arr


def radial_glow(width, height, cx, cy, radius, color, strength=1.0, power=2.2):
    """Additive light falloff, as float RGB."""
    yy, xx = np.mgrid[0:height, 0:width]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(radius, 1)
    fall = np.clip(1.0 - d, 0.0, 1.0) ** power
    out = np.zeros((height, width, 3), dtype=np.float32)
    for ch in range(3):
        out[:, :, ch] = fall * float(color[ch]) * strength
    return out


def add_glow(base, glow):
    return np.clip(base + glow, 0, 255)


def ellipse_mask(width, height, cx, cy, rx, ry, feather=2.0):
    """Soft-edged filled ellipse as a 0..1 float mask."""
    yy, xx = np.mgrid[0:height, 0:width]
    nx = (xx - cx) / max(rx, 1.0)
    ny = (yy - cy) / max(ry, 1.0)
    d = np.sqrt(nx * nx + ny * ny)
    edge = feather / max(min(rx, ry), 1.0)
    return np.clip((1.0 - d) / edge, 0.0, 1.0)


def to_image(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def draw_cloud(img, cx, cy, w, h, color, alpha=60, rim=None):
    """A flat, soft cloud bank made of overlapping ellipses, lit along the top."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    puffs = [(-0.34, 0.0, 0.40, 0.62), (-0.02, -0.16, 0.50, 0.80),
             (0.30, 0.02, 0.38, 0.58), (0.06, 0.10, 0.46, 0.56)]
    for px, py, pw, ph in puffs:
        x = cx + px * w
        y = cy + py * h
        d.ellipse([x - pw * w / 2, y - ph * h / 2, x + pw * w / 2, y + ph * h / 2],
                  fill=color + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius=6 * SS))
    img.alpha_composite(layer)
    if rim:
        light = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(light)
        for px, py, pw, ph in puffs[:2]:
            x = cx + px * w
            y = cy + py * h
            ld.arc([x - pw * w / 2, y - ph * h / 2, x + pw * w / 2, y + ph * h / 2],
                   start=196, end=344, fill=rim + (alpha + 35,), width=max(2, int(0.012 * h)))
        light = light.filter(ImageFilter.GaussianBlur(radius=3 * SS))
        img.alpha_composite(light)


def duck_sprite(size, flip=False):
    """One duck drawn on a transparent sprite, waterline at the sprite's bottom.

    size is the body length in supersampled pixels; the sprite is 0.9 * size
    tall and 1.6 * size wide, with the waterline sitting 0.18 * size above
    the sprite's bottom edge.
    """
    w = int(size * 1.7)
    h = int(size * 1.15)
    sprite = Image.new("RGBA", (max(w, 8), max(h, 8)), (0, 0, 0, 0))
    d = ImageDraw.Draw(sprite)
    cx = w / 2
    water = h - 0.16 * size

    body_cy = water - 0.30 * size
    body_rx = 0.50 * size
    body_ry = 0.31 * size
    head_c = (cx + 0.34 * size, water - 0.66 * size)
    head_r = 0.20 * size

    # tail: a small wedge flicked up at the back
    d.polygon([(cx - 0.46 * size, body_cy - 0.02 * size),
               (cx - 0.70 * size, body_cy - 0.26 * size),
               (cx - 0.40 * size, body_cy - 0.20 * size)], fill=DUCK_BODY)

    # body
    d.ellipse([cx - body_rx, body_cy - body_ry, cx + body_rx, body_cy + body_ry],
              fill=DUCK_BODY)
    # lit top of the body
    d.ellipse([cx - body_rx * 0.92, body_cy - body_ry * 1.02,
               cx + body_rx * 0.55, body_cy + body_ry * 0.18], fill=DUCK_LIGHT)
    # shaded underside
    d.arc([cx - body_rx, body_cy - body_ry, cx + body_rx, body_cy + body_ry],
          start=18, end=162, fill=DUCK_SHADE, width=max(2, int(0.035 * size)))

    # neck and head
    d.polygon([(cx + 0.10 * size, body_cy - 0.16 * size),
               (cx + 0.30 * size, body_cy - 0.16 * size),
               (cx + 0.44 * size, head_c[1] + 0.10 * size),
               (cx + 0.28 * size, head_c[1] + 0.12 * size)], fill=DUCK_BODY)
    d.ellipse([head_c[0] - head_r, head_c[1] - head_r,
               head_c[0] + head_r, head_c[1] + head_r], fill=DUCK_BODY)
    d.ellipse([head_c[0] - head_r * 0.92, head_c[1] - head_r * 1.02,
               head_c[0] + head_r * 0.30, head_c[1] + head_r * 0.05], fill=DUCK_LIGHT)

    # beak: a rounded wedge pointing forward
    beak_y = head_c[1] + 0.02 * size
    d.polygon([(head_c[0] + head_r * 0.70, beak_y - 0.055 * size),
               (head_c[0] + head_r * 1.72, beak_y + 0.005 * size),
               (head_c[0] + head_r * 0.70, beak_y + 0.075 * size)], fill=DUCK_BEAK)

    # eye, high and forward: a glad, wide-open dot with a catchlight
    ex, ey = head_c[0] + head_r * 0.30, head_c[1] - head_r * 0.22
    d.ellipse([ex - 0.045 * size, ey - 0.045 * size,
               ex + 0.045 * size, ey + 0.045 * size], fill=DUCK_EYE)
    d.ellipse([ex - 0.016 * size, ey - 0.030 * size,
               ex + 0.008 * size, ey - 0.006 * size], fill=(255, 255, 255, 255))

    if flip:
        sprite = sprite.transpose(Image.FLIP_LEFT_RIGHT)
    return sprite


def paste_duck(canvas, size, x, water_y, flip=False, reflection=True):
    """Place a duck with its waterline at (x, water_y), plus its reflection."""
    sprite = duck_sprite(size, flip=flip)
    sw, sh = sprite.size
    left = int(x - sw / 2)
    top = int(water_y - (sh - 0.16 * size))
    if reflection:
        refl = sprite.transpose(Image.FLIP_TOP_BOTTOM)
        refl = refl.filter(ImageFilter.GaussianBlur(radius=2.4 * SS))
        alpha = refl.split()[3].point(lambda v: int(v * 0.38))
        refl.putalpha(alpha)
        canvas.alpha_composite(refl, (left, int(water_y + 0.03 * size)))
    canvas.alpha_composite(sprite, (left, top))


def main():
    random.seed(20261113)

    sky = sky_gradient(W, H)
    # the low sun sits right of centre, just above the water
    sun = radial_glow(W, H, 0.70 * W, 0.47 * H, 0.62 * W, (255, 196, 120), 0.85, 2.0)
    sky = add_glow(sky, sun)
    sky = add_glow(sky, radial_glow(W, H, 0.70 * W, 0.47 * H, 0.20 * W, (255, 238, 186), 0.85, 1.9))
    img = to_image(sky).convert("RGBA")

    # ground: wet asphalt at dusk, warm where it meets the sky and deep plum
    # toward the viewer, so the horizon is a soft mist rather than a hard cut
    base = np.array(img.convert("RGB"), dtype=np.float32)
    horizon = 0.545 * H
    ys = np.arange(H, dtype=np.float32)[:, None]
    t = np.clip((ys - horizon) / max(H - horizon, 1.0), 0.0, 1.0)
    top_col = np.array([212, 146, 118], dtype=np.float32)
    bot_col = np.array([52, 36, 62], dtype=np.float32)
    gcol = (top_col[None, :] + (bot_col - top_col)[None, :] * t)[:, None, :]
    alpha = np.clip((ys - horizon) / (5.0 * SS), 0.0, 1.0)
    base = base * (1.0 - alpha[:, :, None]) + gcol[:, :, :] * alpha[:, :, None]
    mist = np.exp(-((ys - horizon) ** 2) / (2.0 * (0.055 * H) ** 2))
    base = np.clip(base + mist[:, :, None] * np.array([255, 214, 168], dtype=np.float32) * 0.22, 0, 255)
    img = to_image(base).convert("RGBA")

    # wet ground picks up the sky: a soft sheen above the puddle
    sheen = radial_glow(W, H, 0.60 * W, 0.72 * H, 0.55 * W, (255, 176, 120), 0.35, 2.4)
    base = np.array(img.convert("RGB"), dtype=np.float32)
    sheen_mask = ellipse_mask(W, H, 0.60 * W, 0.75 * H, 0.52 * W, 0.30 * H, feather=40 * SS)
    base = base + sheen * sheen_mask[:, :, None]
    img = to_image(base).convert("RGBA")

    # the puddle: an upside-down sky in a shallow ellipse
    puddle_cx, puddle_cy = 0.50 * W, 0.795 * H
    puddle_rx, puddle_ry = 0.475 * W, 0.235 * H
    mask = ellipse_mask(W, H, puddle_cx, puddle_cy, puddle_rx, puddle_ry, feather=3.0)
    flipped = np.flipud(base) * 0.92
    water = Image.fromarray(np.clip(flipped, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    img.paste(water, (0, 0), Image.fromarray((mask * 255).astype(np.uint8), "L"))

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # puddle rim: a thin bright edge where the water meets the wet ground
    d.ellipse([puddle_cx - puddle_rx, puddle_cy - puddle_ry,
               puddle_cx + puddle_rx, puddle_cy + puddle_ry],
              outline=PUDDLE_EDGE + (95,), width=max(2, int(0.004 * W)))

    # ripples, a few thin rings spreading where the ducks stand
    for rx, ry, a in ((0.30, 0.075, 70), (0.34, 0.086, 45), (0.22, 0.055, 55)):
        d.ellipse([0.50 * W - rx * W, 0.86 * H - ry * H,
                   0.50 * W + rx * W, 0.86 * H + ry * H],
                  outline=(255, 232, 190, a), width=max(1, int(0.0028 * W)))

    img.alpha_composite(layer)

    # cloud banks, low and warm, kept away from the sun
    draw_cloud(img, 0.20 * W, 0.36 * H, 0.42 * W, 0.13 * H, (255, 190, 170), 55, rim=(255, 232, 198))
    draw_cloud(img, 0.88 * W, 0.30 * H, 0.34 * W, 0.10 * H, (255, 206, 170), 45, rim=(255, 238, 206))
    draw_cloud(img, 0.42 * W, 0.20 * H, 0.36 * W, 0.09 * H, (196, 150, 190), 40)

    # the parade: big duck on the right, smaller ones behind it to the left
    line_y = 0.845 * H
    ducks = [
        (0.155 * W, 0.150 * W, line_y - 0.010 * H),
        (0.305 * W, 0.200 * W, line_y - 0.004 * H),
        (0.505 * W, 0.265 * W, line_y + 0.002 * H),
        (0.760 * W, 0.360 * W, line_y + 0.010 * H),
    ]
    for x, size, y in ducks:
        paste_duck(img, size, x, y)

    # the duckling riding on the big duck's back
    bx, bsize, by = ducks[-1]
    paste_duck(img, bsize * 0.34, bx + 0.055 * bsize, by - 0.345 * bsize,
               reflection=False)

    # the lead duck wears a paper party hat: one specific reason to be happy
    hat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hat)
    hx = bx + 0.34 * bsize
    base_y = by - 0.845 * bsize
    half = 0.115 * bsize
    apex = (hx + 0.075 * bsize, base_y - 0.30 * bsize)
    hd.polygon([(hx - half, base_y), (hx + half, base_y), apex], fill=(236, 92, 96, 245))
    hd.polygon([(hx - half * 0.72, base_y - 0.10 * bsize),
                (hx + half * 0.80, base_y - 0.10 * bsize),
                (hx + half * 0.50, base_y - 0.185 * bsize),
                (hx - half * 0.42, base_y - 0.185 * bsize)], fill=(255, 240, 214, 230))
    hd.line([(hx - half, base_y), (hx + half, base_y)], fill=(214, 74, 82, 240),
            width=max(2, int(0.018 * bsize)))
    pom = 0.030 * bsize
    hd.ellipse([apex[0] - pom, apex[1] - pom, apex[0] + pom, apex[1] + pom],
               fill=(255, 232, 160, 245))
    hat = hat.filter(ImageFilter.GaussianBlur(radius=0.5 * SS))
    img.alpha_composite(hat)

    # a paper boat, folded and left in the puddle: the second small happiness
    boat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(boat)
    bx, by, bs = 0.335 * W, 0.900 * H, 0.050 * W
    bd.polygon([(bx - bs, by), (bx + bs, by), (bx + bs * 0.68, by + bs * 0.42),
                (bx - bs * 0.68, by + bs * 0.42)], fill=(255, 246, 226, 240))
    bd.polygon([(bx - bs * 0.62, by + bs * 0.36),
                (bx + bs * 0.62, by + bs * 0.36),
                (bx + bs * 0.40, by + bs * 0.52),
                (bx - bs * 0.40, by + bs * 0.52)], fill=(238, 214, 178, 235))
    bd.polygon([(bx, by - bs * 0.92), (bx + bs * 0.62, by - bs * 0.04),
                (bx - bs * 0.55, by - bs * 0.04)], fill=(255, 252, 240, 245))
    bd.line([(bx, by - bs * 0.86), (bx, by - bs * 0.06)],
            fill=(226, 196, 160, 220), width=max(1, int(bs * 0.05)))
    boat = boat.filter(ImageFilter.GaussianBlur(radius=0.5 * SS))
    img.alpha_composite(boat)

    # a little sparkle on the water, painted last so it sits on top
    sparkle = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sparkle)
    for sx, sy, sr in ((0.615, 0.905, 0.010), (0.648, 0.878, 0.006),
                       (0.596, 0.862, 0.005)):
        d_x, d_y, r = sx * W, sy * H, sr * W
        sd.polygon([(d_x, d_y - r), (d_x + r * 0.28, d_y - r * 0.28),
                    (d_x + r, d_y), (d_x + r * 0.28, d_y + r * 0.28),
                    (d_x, d_y + r), (d_x - r * 0.28, d_y + r * 0.28),
                    (d_x - r, d_y), (d_x - r * 0.28, d_y - r * 0.28)],
                   fill=(255, 250, 226, 220))
    sparkle = sparkle.filter(ImageFilter.GaussianBlur(radius=0.7 * SS))
    img.alpha_composite(sparkle)

    # gentle vignette so the eye stays on the parade
    vign = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vign)
    vd.ellipse([-0.18 * W, -0.18 * H, 1.18 * W, 1.18 * H], fill=255)
    vign = vign.filter(ImageFilter.GaussianBlur(radius=0.10 * W))
    dark = Image.new("RGBA", (W, H), (34, 20, 44, 70))
    img = Image.composite(img, Image.alpha_composite(img, dark), vign)

    out = img.convert("RGB").resize((FINAL, FINAL), Image.LANCZOS)
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "entry.png"
    out.save(target, format="PNG", optimize=True)
    print(f"wrote {target} {out.size[0]}x{out.size[1]} {target.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
