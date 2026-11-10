"""Image discovery, perceptual hashing and similarity grouping (no GUI dependencies)."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import imagehash
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

EXTENSIONS = {
    ".jpg", ".jpeg", ".jfif", ".jfi", ".jif", ".png", ".webp",
    ".bmp", ".gif", ".tif", ".tiff",
}
# pHash is only a candidate filter. The RGB checks below reject visually
# different variants that share the same shape/composition.
THRESHOLDS = {
    # Strict intentionally behaves as a near-identical image detector, not a
    # "same subject" detector. Small outfit/background changes must not match.
    "Strict": (2, 0.006, 0.005, 12),
    "Basic": (7, 0.045, 0.095, 32),
    "Loose": (13, 0.065, 0.14, 32),
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
    alpha_sample: bytes

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
        rgba = oriented.convert("RGBA")
        rgb = rgba.convert("RGB")
        digest = imagehash.phash(rgb)
        sample = rgb.resize(SAMPLE_SIZE, Image.Resampling.LANCZOS).tobytes()
        alpha = rgba.getchannel("A").resize(SAMPLE_SIZE, Image.Resampling.LANCZOS).tobytes()
    return ImageInfo(path=path, width=width, height=height, bytes=path.stat().st_size,
                     phash=digest, rgb_sample=sample, alpha_sample=alpha)


class ScanCache:
    """Optional persistent image fingerprints. The original files are never modified."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS fingerprints_v4 (
                path TEXT PRIMARY KEY, size INTEGER, mtime_ns INTEGER,
                width INTEGER, height INTEGER, phash TEXT,
                rgb_sample BLOB, alpha_sample BLOB
            )
        """)

    def get(self, path: Path) -> ImageInfo | None:
        stat = path.stat()
        row = self.connection.execute(
            "SELECT width, height, phash, rgb_sample, alpha_sample FROM fingerprints_v4 "
            "WHERE path=? AND size=? AND mtime_ns=?",
            (str(path.resolve()), stat.st_size, stat.st_mtime_ns),
        ).fetchone()
        if (row is None or len(row[3]) != SAMPLE_SIZE[0] * SAMPLE_SIZE[1] * 3
                or len(row[4]) != SAMPLE_SIZE[0] * SAMPLE_SIZE[1]):
            return None
        return ImageInfo(path, row[0], row[1], stat.st_size,
                         imagehash.hex_to_hash(row[2]), row[3], row[4])

    def put(self, image: ImageInfo) -> None:
        stat = image.path.stat()
        self.connection.execute(
            "INSERT OR REPLACE INTO fingerprints_v4 VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (str(image.path.resolve()), stat.st_size, stat.st_mtime_ns,
             image.width, image.height, str(image.phash), image.rgb_sample,
             image.alpha_sample),
        )

    def close(self) -> None:
        self.connection.commit()
        self.connection.close()


def scan(paths: Iterable[Path], progress: Callable[[int, int], None] | None = None,
         cancelled: Callable[[], bool] | None = None,
         cache_path: Path | None = None) -> tuple[list[ImageInfo], list[str]]:
    candidates = discover(paths)
    images: list[ImageInfo] = []
    errors: list[str] = []
    cache: ScanCache | None = None
    try:
        if cache_path is not None:
            try:
                cache = ScanCache(cache_path)
            except (OSError, sqlite3.DatabaseError) as exc:
                errors.append(f"Cache non disponibile: {exc}")
        for index, path in enumerate(candidates, 1):
            if cancelled and cancelled():
                break
            try:
                info = cache.get(path) if cache is not None else None
                if info is None:
                    info = inspect(path)
                    if cache is not None:
                        cache.put(info)
                images.append(info)
            except (OSError, ValueError, UnidentifiedImageError, sqlite3.DatabaseError) as exc:
                errors.append(f"{path}: {exc}")
            if progress:
                progress(index, len(candidates))
    finally:
        if cache is not None:
            cache.close()
    return images, errors


def is_duplicate(first: ImageInfo, second: ImageInfo, mode: str = "Basic") -> bool:
    """Conservative matching: composition, color and changed-area must agree.

    Large recolorings, new clothing and alternate backgrounds are deliberately
    excluded, even when the pHash distance is zero. This is not crop matching.
    """
    if mode not in THRESHOLDS:
        raise ValueError(f"Unknown similarity mode: {mode}")
    phash_max, average_max, changed_max, pixel_tolerance = THRESHOLDS[mode]
    if abs(first.width / first.height - second.width / second.height) > 0.025:
        return False
    if first.phash - second.phash > phash_max:
        return False
    if mode == "Strict":
        alpha_a = np.frombuffer(first.alpha_sample, dtype=np.uint8).astype(np.int16)
        alpha_b = np.frombuffer(second.alpha_sample, dtype=np.uint8).astype(np.int16)
        # Transparent backgrounds and fully opaque backgrounds are distinct
        # assets even if their flattened RGB data happens to match.
        if float(np.mean(np.abs(alpha_a - alpha_b) > 8)) > 0.005:
            return False
    a = np.frombuffer(first.rgb_sample, dtype=np.uint8).astype(np.int16)
    b = np.frombuffer(second.rgb_sample, dtype=np.uint8).astype(np.int16)
    difference = np.abs(a - b).reshape((*SAMPLE_SIZE, 3))
    average = float(difference.mean()) / 255
    changed_fraction = float(np.mean(np.max(difference, axis=2) > pixel_tolerance))
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
