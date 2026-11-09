from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from visilens.core import discover, group_similar, inspect, scan


def test_discover_deduplicates_overlapping_roots(tmp_path: Path) -> None:
    folder = tmp_path / "photos"
    folder.mkdir()
    image = folder / "a.PNG"
    Image.new("RGB", (40, 40), "red").save(image)
    (folder / "notes.txt").write_text("ignore me")
    assert discover([folder, image, folder]) == [image]


def test_same_image_in_different_formats_is_similar(tmp_path: Path) -> None:
    original = Image.new("RGB", (160, 120), "white")
    drawing = ImageDraw.Draw(original)
    drawing.rectangle((20, 20, 70, 90), fill="navy")
    drawing.ellipse((80, 15, 145, 85), fill="tomato")
    png, jpg = tmp_path / "a.png", tmp_path / "b.jpg"
    original.save(png)
    original.save(jpg, quality=96)
    images, errors = scan([tmp_path])
    assert not errors
    assert len(group_similar(images, "Basic")) == 1


def test_unreadable_file_is_reported(tmp_path: Path) -> None:
    (tmp_path / "broken.jpg").write_bytes(b"not an image")
    images, errors = scan([tmp_path])
    assert not images
    assert len(errors) == 1


def test_keeps_higher_resolution_first(tmp_path: Path) -> None:
    first, second = tmp_path / "small.png", tmp_path / "large.png"
    Image.new("RGB", (50, 50), "blue").save(first)
    Image.new("RGB", (100, 100), "blue").save(second)
    group = group_similar([inspect(first), inspect(second)], "Strict")[0]
    assert group[0].path == second


def test_invalid_mode() -> None:
    with pytest.raises(ValueError):
        group_similar([], "Unknown")


def test_cancel_stops_before_loading(tmp_path: Path) -> None:
    Image.new("RGB", (20, 20), "green").save(tmp_path / "a.png")
    images, errors = scan([tmp_path], cancelled=lambda: True)
    assert images == [] and errors == []
