"""Build the Windows icon from the checked-in official VisiLens artwork."""
from __future__ import annotations

import base64
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
source = ROOT / "src" / "visilens" / "assets" / "icon.png.b64"
target_dir = ROOT / "build"
target_dir.mkdir(parents=True, exist_ok=True)
image_bytes = base64.b64decode(source.read_text(encoding="ascii").strip())
png = target_dir / "visilens-icon.png"
png.write_bytes(image_bytes)
with Image.open(png) as image:
    image.convert("RGBA").save(
        target_dir / "visilens.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
               (64, 64), (96, 96), (128, 128), (256, 256)],
    )
print(f"Created {target_dir / 'visilens.ico'}")
