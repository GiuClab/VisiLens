"""Small headless GUI regression checks for multi-image groups."""

import os
from pathlib import Path

import imagehash

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from visilens.app import MainWindow
from visilens.core import ImageInfo


def test_four_copies_visible_thumbnail_previews_checkbox_selects() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    images = [
        ImageInfo(Path(f"image-{n}.png"), 100, 100, 100 + n,
                  imagehash.hex_to_hash("0" * 16), bytes(64 * 64 * 3),
                  bytes([255]) * (64 * 64))
        for n in range(4)
    ]
    window.images = images
    window.refresh_groups()
    window.resize(1180, 720)
    window.show()
    app.processEvents()
    assert len(window.tiles) == 4
    assert len(window.group_labels) == 1
    path = window.groups[0][2].path
    window.tiles[path].button.click()
    assert path not in window.selected_paths
    assert window.preview_path == path
    assert window.tiles[path].property("active") is True
    window.tiles[path].checkbox.click()
    assert path in window.selected_paths
    assert window.preview_path == path
    window.tiles[path].checkbox.click()
    assert path not in window.selected_paths
    assert window.preview_path == path
    window.mode_slider.setValue(2)
    assert window.MODES[window.mode_slider.value()] == "Strict"
    window.auto_select()
    assert len(window.selected_paths) == 3
    assert sum(tile.checkbox.isChecked() for tile in window.tiles.values()) == 3
    assert "3 per il cestino" in window.group_labels[0].text()
    window.close()


def test_folder_tree_has_shortcuts_and_mode_colors() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    window = MainWindow()
    root = window.tree.topLevelItem(0)
    labels = {root.child(i).text(0) for i in range(root.childCount())}
    assert "Download" in labels
    assert "Documenti" in labels
    assert window.MODES == ("Loose", "Basic", "Strict")
    for index, color in enumerate(window.MODE_COLORS):
        window.mode_slider.setValue(index)
        assert color in window.mode_slider.styleSheet()
    window.close()
