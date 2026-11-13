#!/usr/bin/env python3
"""make.fun ai-happy-01 entry: a duck family crossing a rain puddle at golden hour.

The picture is ``art/entry.png``, drawn by ``tools/draw.py`` and committed with
this repository. This entrypoint copies those bytes to the run's output
directory, so the judge sees exactly the file the repository holds and two runs
write identical bytes.

It uses the standard library only, and it re-checks every rule the gate checks
before writing anything: whole PNG (each chunk's CRC, the stream ending at
IEND), at most 1 MiB, at most 1024 by 1024 pixels. A broken file is refused
here rather than silently entering as a blank.
"""

import binascii
import hashlib
import os
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE = HERE / "art" / "entry.png"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 1024 * 1024
MAX_SIDE = 1024


def output_dir() -> Path:
    """Where the harness wants the image: $MAKEFUN_OUTPUT_DIR, else /output."""
    return Path(os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output")


def read_image(path: Path) -> bytes:
    data = path.read_bytes()
    if not data.startswith(PNG_MAGIC):
        raise SystemExit(f"{path.name}: not a PNG (magic bytes are wrong)")
    return data


def image_size(data: bytes) -> tuple:
    if len(data) < 24 or data[12:16] != b"IHDR":
        raise SystemExit("entry.png: the header is missing its IHDR chunk")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def check_whole(data: bytes) -> None:
    """Walk every chunk, verify its CRC, and insist the stream ends at IEND."""
    pos = len(PNG_MAGIC)
    while pos + 12 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        crc_bytes = data[pos + 8 + length:pos + 12 + length]
        if len(crc_bytes) != 4:
            raise SystemExit("entry.png: a chunk is cut short")
        want = binascii.crc32(kind + body) & 0xFFFFFFFF
        if want != struct.unpack(">I", crc_bytes)[0]:
            raise SystemExit(f"entry.png: chunk {kind!r} fails its checksum")
        pos += 12 + length
        if kind == b"IEND":
            break
    else:
        raise SystemExit("entry.png: the stream never reaches IEND")
    if pos != len(data):
        raise SystemExit("entry.png: trailing bytes after IEND")


def main() -> int:
    check_only = "--check-only" in sys.argv[1:]
    data = read_image(IMAGE)
    if len(data) > MAX_BYTES:
        raise SystemExit(f"entry.png: {len(data)} bytes is over the {MAX_BYTES}-byte cap")
    width, height = image_size(data)
    if not (0 < width <= MAX_SIDE and 0 < height <= MAX_SIDE):
        raise SystemExit(f"entry.png: {width}x{height} is outside the {MAX_SIDE}px cap")
    check_whole(data)

    digest = hashlib.sha256(data).hexdigest()
    if check_only:
        print(f"ok {width}x{height} {len(data)} bytes sha256={digest}")
        return 0

    target = output_dir() / "entry.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    print(f"wrote {target} ({width}x{height}, {len(data)} bytes, sha256={digest})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
