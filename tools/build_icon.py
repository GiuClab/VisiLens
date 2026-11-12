"""Generate and validate a multi-resolution Windows icon from VisiLens artwork."""

from __future__ import annotations

import base64
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src" / "visilens" / "assets" / "icon.png.b64"
BUILD = ROOT / "build"
ICON_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48),
              (64, 64), (96, 96), (128, 128), (256, 256)]


def build() -> Path:
    BUILD.mkdir(parents=True, exist_ok=True)
    source_bytes = base64.b64decode(SOURCE.read_text(encoding="ascii").strip(),
                                    validate=True)
    png = BUILD / "visilens-icon.png"
    png.write_bytes(source_bytes)

    with Image.open(png) as image:
        # Pillow omits requested ICO sizes larger than the source image.
        # Ensure the master is large enough for all Windows icon resolutions.
        master = image.convert("RGBA")
        if master.width < 256 or master.height < 256:
            master = master.resize((256, 256), Image.Resampling.LANCZOS)
        target = BUILD / "visilens.ico"
        master.save(target, format="ICO", sizes=ICON_SIZES)

    with Image.open(target) as ico:
        available = ico.info.get("sizes", set())
        missing = set(ICON_SIZES) - set(available)
        if missing:
            raise RuntimeError(f"ICO is missing Windows icon sizes: {sorted(missing)}")
    print(f"Created and verified {target}")
    return target


if __name__ == "__main__":
    build()
