"""Conservative, non-destructive proposals for duplicate-image selection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .core import ImageInfo


@dataclass(frozen=True)
class SelectionOptions:
    prefer_resolution: bool = True
    prefer_file_size: bool = True
    protected_folders: tuple[Path, ...] = ()
    resolve_ties: bool = True


@dataclass(frozen=True)
class SelectionProposal:
    trash_paths: frozenset[Path]
    kept_paths: frozenset[Path]
    skipped_groups: int
    recoverable_bytes: int
    tied_groups: int = 0


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

    Protected folders, resolution and optionally file size establish priorities.
    By default, remaining ties use a stable path ordering. The resulting choice
    is a proposal for manual review, NOT a claim of superior image quality.
    """
    trash: set[Path] = set()
    kept: set[Path] = set()
    skipped = 0
    tied = 0
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
            if not options.resolve_ties:
                skipped += 1
                continue
            tied += 1
            candidates.sort(key=lambda image: str(image.path).casefold())
        winner = candidates[0]
        kept.add(winner.path)
        for image in group:
            if image.path != winner.path:
                trash.add(image.path)
                bytes_saved += image.bytes
    return SelectionProposal(frozenset(trash), frozenset(kept), skipped, bytes_saved, tied)
