"""Conservative, non-destructive proposals for duplicate-image selection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .core import ImageInfo


@dataclass(frozen=True)
class SelectionOptions:
    prefer_resolution: bool = True
    prefer_file_size: bool = False
    protected_folders: tuple[Path, ...] = ()


@dataclass(frozen=True)
class SelectionProposal:
    trash_paths: frozenset[Path]
    kept_paths: frozenset[Path]
    skipped_groups: int
    recoverable_bytes: int


def _inside(path: Path, folder: Path) -> bool:
    try:
        path.resolve().relative_to(folder.resolve())
        return True
    except (ValueError, OSError, RuntimeError):
        return False


def propose_selection(
    groups: list[list[ImageInfo]], options: SelectionOptions
) -> SelectionProposal:
    """Recommend files to select, never delete anything.

    Each group needs one unambiguous winner. Protected folders always win over
    other locations, but a tie among protected candidates is skipped unless
    another enabled criterion resolves it. File size is not a quality estimate.
    """
    trash: set[Path] = set()
    kept: set[Path] = set()
    skipped = 0
    bytes_saved = 0
    for group in groups:
        if len(group) < 2:
            continue
        candidates = list(group)
        preferred = [image for image in candidates
                     if any(_inside(image.path, folder) for folder in options.protected_folders)]
        if preferred:
            candidates = preferred
        if options.prefer_resolution:
            max_pixels = max(image.pixels for image in candidates)
            candidates = [image for image in candidates if image.pixels == max_pixels]
        if options.prefer_file_size and len(candidates) > 1:
            max_bytes = max(image.bytes for image in candidates)
            candidates = [image for image in candidates if image.bytes == max_bytes]
        if len(candidates) != 1:
            skipped += 1
            continue
        winner = candidates[0]
        kept.add(winner.path)
        for image in group:
            if image.path != winner.path:
                trash.add(image.path)
                bytes_saved += image.bytes
    return SelectionProposal(frozenset(trash), frozenset(kept), skipped, bytes_saved)
