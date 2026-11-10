from pathlib import Path

import imagehash

from visilens.core import ImageInfo
from visilens.selection import SelectionOptions, propose_selection


def picture(path: Path, width: int, height: int, size: int) -> ImageInfo:
    return ImageInfo(path, width, height, size, imagehash.hex_to_hash("0" * 16), b"", b"")


def test_prefers_unique_higher_resolution(tmp_path: Path) -> None:
    best = picture(tmp_path / "large.png", 2000, 1000, 400)
    worse = picture(tmp_path / "small.png", 1000, 500, 100)
    result = propose_selection([[worse, best]], SelectionOptions())
    assert result.trash_paths == {worse.path}
    assert result.kept_paths == {best.path}
    assert result.recoverable_bytes == 100


def test_ambiguous_same_resolution_is_skipped(tmp_path: Path) -> None:
    a = picture(tmp_path / "a.png", 1000, 1000, 100)
    b = picture(tmp_path / "b.png", 1000, 1000, 200)
    result = propose_selection([[a, b]], SelectionOptions())
    assert not result.trash_paths
    assert result.skipped_groups == 1


def test_explicit_size_tiebreaker(tmp_path: Path) -> None:
    a = picture(tmp_path / "a.png", 1000, 1000, 100)
    b = picture(tmp_path / "b.png", 1000, 1000, 200)
    result = propose_selection([[a, b]], SelectionOptions(prefer_file_size=True))
    assert result.trash_paths == {a.path}


def test_protected_folder_takes_precedence(tmp_path: Path) -> None:
    protected = tmp_path / "originals"
    original = picture(protected / "a.png", 800, 600, 200)
    download = picture(tmp_path / "downloads" / "a.png", 2000, 1000, 400)
    result = propose_selection([[original, download]],
                               SelectionOptions(protected_folders=(protected,)))
    assert result.kept_paths == {original.path}
    assert result.trash_paths == {download.path}


def test_protected_folder_boundary_is_respected(tmp_path: Path) -> None:
    protected = tmp_path / "photos"
    close_name = picture(tmp_path / "photos-extra" / "a.png", 800, 600, 100)
    outside = picture(tmp_path / "other" / "b.png", 1600, 1200, 200)
    result = propose_selection([[close_name, outside]],
                               SelectionOptions(protected_folders=(protected,)))
    assert result.kept_paths == {outside.path}


def test_no_criteria_does_not_select_anything(tmp_path: Path) -> None:
    a = picture(tmp_path / "a.png", 1000, 1000, 100)
    b = picture(tmp_path / "b.png", 2000, 2000, 200)
    result = propose_selection([[a, b]], SelectionOptions(prefer_resolution=False))
    assert not result.trash_paths
    assert result.skipped_groups == 1
