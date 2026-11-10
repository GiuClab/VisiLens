"""Image discovery, perceptual hashing and similarity grouping (no GUI dependencies)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import imagehash
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
# pHash is only a candidate filter. The RGB checks below reject visually
# different variants that share the same shape/composition.
THRESHOLDS = {
    "Strict": (2, 0.025, 0.055),
    "Basic": (7, 0.045, 0.095),
    "Loose": (13, 0.065, 0.14),
}
SAMPLE_SIZE = (64, 64)


@dataclass(frozen=True)
class ImageInfo:
    path: Path
    width: int
    height: int
    bytes: int
    phash: imagehash.ImageHash
    rgb_sample: bytes

    @property
    def pixels(self) -> int:
        return self.width * self.height


def discover(paths: Iterable[Path]) -> list[Path]:
    """Find supported files, deduplicating overlapping roots and symlink aliases."""
    found: dict[Path, Path] = {}
    for root in paths:
        root = Path(root).expanduser()
        if root.is_file():
            candidates = [root]
        elif root.is_dir():
            candidates = (p for p in root.rglob("*") if p.is_file())
        else:
            continue
        for path in candidates:
            if path.suffix.lower() in EXTENSIONS:
                try:
                    canonical = path.resolve(strict=True)
                except (OSError, RuntimeError):
                    continue
                found.setdefault(canonical, path)
    return sorted(found.values(), key=lambda p: str(p).casefold())


def inspect(path: Path) -> ImageInfo:
    """Read first frame, honor EXIF orientation and calculate 64-bit perceptual hash."""
    with Image.open(path) as image:
        image.seek(0)
        oriented = ImageOps.exif_transpose(image)
        width, height = oriented.size
        rgb = oriented.convert("RGB")
        digest = imagehash.phash(rgb)
        sample = rgb.resize(SAMPLE_SIZE, Image.Resampling.LANCZOS).tobytes()
    return ImageInfo(path=path, width=width, height=height, bytes=path.stat().st_size,
                     phash=digest, rgb_sample=sample)


def scan(paths: Iterable[Path], progress: Callable[[int, int], None] | None = None,
         cancelled: Callable[[], bool] | None = None) -> tuple[list[ImageInfo], list[str]]:
    candidates = discover(paths)
    images: list[ImageInfo] = []
    errors: list[str] = []
    for index, path in enumerate(candidates, 1):
        if cancelled and cancelled():
            break
        try:
            images.append(inspect(path))
        except (OSError, ValueError, UnidentifiedImageError) as exc:
            errors.append(f"{path}: {exc}")
        if progress:
            progress(index, len(candidates))
    return images, errors


def is_duplicate(first: ImageInfo, second: ImageInfo, mode: str = "Basic") -> bool:
    """Conservative matching: composition, color and changed-area must agree.

    Large recolorings, new clothing and alternate backgrounds are deliberately
    excluded, even when the pHash distance is zero. This is not crop matching.
    """
    if mode not in THRESHOLDS:
        raise ValueError(f"Unknown similarity mode: {mode}")
    phash_max, average_max, changed_max = THRESHOLDS[mode]
    if abs(first.width / first.height - second.width / second.height) > 0.025:
        return False
    if first.phash - second.phash > phash_max:
        return False
    a = np.frombuffer(first.rgb_sample, dtype=np.uint8).astype(np.int16)
    b = np.frombuffer(second.rgb_sample, dtype=np.uint8).astype(np.int16)
    difference = np.abs(a - b).reshape((*SAMPLE_SIZE, 3))
    average = float(difference.mean()) / 255
    changed_fraction = float(np.mean(np.max(difference, axis=2) > 32))
    return average <= average_max and changed_fraction <= changed_max


def group_similar(images: list[ImageInfo], mode: str = "Basic") -> list[list[ImageInfo]]:
    """Conservative complete-link groups, with no indirect A-B-C matches."""
    if mode not in THRESHOLDS:
        raise ValueError(f"Unknown similarity mode: {mode}")
    ranked = sorted(images, key=lambda x: (-x.pixels, -x.bytes, str(x.path)))
    groups: list[list[ImageInfo]] = []
    for image in ranked:
        for group in groups:
            if all(is_duplicate(image, other, mode) for other in group):
                group.append(image)
                break
        else:
            groups.append([image])
    result = [group for group in groups if len(group) > 1]
    return sorted(result, key=lambda group: str(group[0].path).casefold())
