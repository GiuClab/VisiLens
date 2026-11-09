"""Image discovery, perceptual hashing and similarity grouping (no GUI dependencies)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import imagehash
from PIL import Image, ImageOps, UnidentifiedImageError

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
THRESHOLDS = {"Strict": 2, "Basic": 7, "Loose": 13}


@dataclass(frozen=True)
class ImageInfo:
    path: Path
    width: int
    height: int
    bytes: int
    phash: imagehash.ImageHash

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
        digest = imagehash.phash(oriented.convert("RGB"))
    return ImageInfo(path=path, width=width, height=height, bytes=path.stat().st_size,
                     phash=digest)


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


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, index: int) -> int:
        while self.parent[index] != index:
            self.parent[index] = self.parent[self.parent[index]]
            index = self.parent[index]
        return index

    def union(self, a: int, b: int) -> None:
        self.parent[self.find(a)] = self.find(b)


def group_similar(images: list[ImageInfo], mode: str = "Basic") -> list[list[ImageInfo]]:
    """Connected components of hash-neighbor graph; groups may contain transitive matches."""
    if mode not in THRESHOLDS:
        raise ValueError(f"Unknown similarity mode: {mode}")
    threshold = THRESHOLDS[mode]
    uf = _UnionFind(len(images))
    for i, first in enumerate(images):
        for j in range(i + 1, len(images)):
            if first.phash - images[j].phash <= threshold:
                uf.union(i, j)
    groups: dict[int, list[ImageInfo]] = {}
    for i, item in enumerate(images):
        groups.setdefault(uf.find(i), []).append(item)
    result = [sorted(group, key=lambda x: (-x.pixels, -x.bytes, str(x.path)))
              for group in groups.values() if len(group) > 1]
    return sorted(result, key=lambda group: str(group[0].path).casefold())
