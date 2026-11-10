from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from visilens.core import discover, group_similar, inspect, is_duplicate, scan


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


@pytest.mark.parametrize("mode", ["Strict", "Basic", "Loose"])
def test_recolored_logo_is_not_a_duplicate(tmp_path: Path, mode: str) -> None:
    """Identical shapes with inverted colors are a design variant, not a duplicate."""
    dark = Image.new("RGB", (200, 200), "black")
    light = Image.new("RGB", (200, 200), "white")
    ImageDraw.Draw(dark).ellipse((35, 35, 165, 165), fill="gold")
    ImageDraw.Draw(light).ellipse((35, 35, 165, 165), fill="darkorange")
    a, b = tmp_path / "dark.png", tmp_path / "light.png"
    dark.save(a)
    light.save(b)
    assert not is_duplicate(inspect(a), inspect(b), mode)


@pytest.mark.parametrize("mode", ["Strict", "Basic", "Loose"])
def test_changed_clothing_is_not_a_duplicate(tmp_path: Path, mode: str) -> None:
    """A repeated character silhouette with altered outfit is a distinct image."""
    coat = Image.new("RGB", (160, 240), "#eeeeee")
    shirt = coat.copy()
    for image, outfit in ((coat, "#65402c"), (shirt, "#101010")):
        draw = ImageDraw.Draw(image)
        draw.ellipse((45, 15, 115, 85), fill="#b47b4c")
        draw.rectangle((42, 85, 118, 175), fill=outfit)
        draw.rectangle((48, 175, 71, 225), fill="#444444")
        draw.rectangle((89, 175, 112, 225), fill="#444444")
    a, b = tmp_path / "coat.png", tmp_path / "shirt.png"
    coat.save(a)
    shirt.save(b)
    assert not is_duplicate(inspect(a), inspect(b), mode)


def test_no_transitive_matches(tmp_path: Path) -> None:
    """A single group must not silently link unrelated endpoints through B."""
    base = Image.new("RGB", (160, 160), "white")
    ImageDraw.Draw(base).rectangle((30, 30, 130, 130), fill="#353535")
    variants = []
    for index, box in enumerate(((0, 0, 20, 20), (0, 0, 20, 20), (135, 135, 155, 155))):
        image = base.copy()
        if index >= 1:
            ImageDraw.Draw(image).rectangle((0, 0, 20, 20), fill="#777777")
        if index == 2:
            ImageDraw.Draw(image).rectangle(box, fill="#777777")
        path = tmp_path / f"variant-{index}.png"
        image.save(path)
        variants.append(inspect(path))
    groups = group_similar(variants, "Loose")
    assert all(all(is_duplicate(a, b, "Loose") for a in group for b in group)
               for group in groups)
