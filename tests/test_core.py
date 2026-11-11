import os
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from visilens.core import discover, group_similar, inspect, is_duplicate, scan


def test_hidden_files_and_folders_are_opt_in(tmp_path: Path) -> None:
    visible = tmp_path / "visible.jpg"
    hidden = tmp_path / ".hidden.jpg"
    directory = tmp_path / ".private"
    directory.mkdir()
    nested = directory / "nested.jpg"
    for path in (visible, hidden, nested):
        Image.new("RGB", (48, 48), "blue").save(path, format="JPEG")
    assert discover([tmp_path]) == [visible]
    assert set(discover([tmp_path], include_hidden=True)) == {visible, hidden, nested}
    images, errors = scan([tmp_path])
    assert not errors
    assert [info.path for info in images] == [visible]
    all_images, errors = scan([tmp_path], include_hidden=True)
    assert not errors
    assert len(all_images) == 3


def test_discover_deduplicates_overlapping_roots(tmp_path: Path) -> None:
    folder = tmp_path / "photos"
    folder.mkdir()
    image = folder / "a.PNG"
    Image.new("RGB", (40, 40), "red").save(image)
    (folder / "notes.txt").write_text("ignore me")
    assert discover([folder, image, folder]) == [image]


@pytest.mark.parametrize("suffix", [".jfif", ".jfi", ".jif", ".JFIF"])
def test_jfif_family_is_discovered_and_decoded(tmp_path: Path, suffix: str) -> None:
    """JPEG bytes are valid under every supported JFIF-family extension."""
    path = tmp_path / f"photo{suffix}"
    Image.new("RGB", (64, 48), "orange").save(path, format="JPEG")
    assert discover([tmp_path]) == [path]
    image, errors = scan([tmp_path])
    assert not errors
    assert len(image) == 1
    assert (image[0].width, image[0].height) == (64, 48)


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


@pytest.mark.parametrize("change", ["shirt", "background"])
def test_strict_rejects_small_local_changes(tmp_path: Path, change: str) -> None:
    """Even small edits may be meaningful; Strict must not group them."""
    original = Image.new("RGB", (300, 300), "#e6e7e9")
    draw = ImageDraw.Draw(original)
    draw.ellipse((70, 45, 230, 205), fill="#ad7650")
    draw.rectangle((100, 205, 200, 265), fill="#303030")
    altered = original.copy()
    redraw = ImageDraw.Draw(altered)
    if change == "shirt":
        redraw.rectangle((125, 220, 174, 250), fill="#6a82bd")
    else:
        redraw.rectangle((10, 10, 58, 40), fill="#6a82bd")
    a, b = tmp_path / "original.png", tmp_path / "changed.png"
    original.save(a)
    altered.save(b)
    assert not is_duplicate(inspect(a), inspect(b), "Strict")


def test_cache_reuses_unchanged_files_and_invalidates_edits(tmp_path: Path, monkeypatch) -> None:
    from visilens import core

    source = tmp_path / "picture.png"
    cache = tmp_path / "fingerprints.sqlite3"
    Image.new("RGB", (80, 80), "red").save(source)
    real_inspect = core.inspect
    calls = []

    def counted(path):
        calls.append(path)
        return real_inspect(path)

    monkeypatch.setattr(core, "inspect", counted)
    first, errors = scan([source], cache_path=cache)
    second, errors_again = scan([source], cache_path=cache)
    assert not errors and not errors_again
    assert first == second
    assert len(calls) == 1
    Image.new("RGB", (80, 80), "blue").save(source)
    stat = source.stat()
    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))
    third, errors_last = scan([source], cache_path=cache)
    assert not errors_last
    assert len(calls) == 2
    assert third[0].rgb_sample != first[0].rgb_sample


def test_strict_distinguishes_transparency_from_black_background(tmp_path: Path) -> None:
    """Same logo pixels, different background alpha: distinct assets in Strict."""
    transparent = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(transparent).ellipse((30, 30, 170, 170), fill=(230, 176, 34, 255))
    opaque = Image.alpha_composite(Image.new("RGBA", transparent.size, "black"), transparent)
    a, b = tmp_path / "logo-transparent.png", tmp_path / "logo-black.png"
    transparent.save(a)
    opaque.save(b)
    first, second = inspect(a), inspect(b)
    assert first.phash == second.phash
    assert first.rgb_sample == second.rgb_sample
    assert first.alpha_sample != second.alpha_sample
    assert not is_duplicate(first, second, "Strict")


def test_transparent_resized_copy_still_matches(tmp_path: Path) -> None:
    transparent = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(transparent).rectangle((50, 50, 150, 150), fill=(200, 30, 30, 255))
    first, second = tmp_path / "a.png", tmp_path / "b.png"
    transparent.save(first)
    transparent.resize((400, 400), Image.Resampling.NEAREST).save(second)
    assert is_duplicate(inspect(first), inspect(second), "Strict")
