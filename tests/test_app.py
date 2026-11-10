"""Small headless GUI regression checks for multi-image groups."""

import os
from pathlib import Path

import imagehash

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from visilens.app import MainWindow
from visilens.core import ImageInfo


def test_four_copies_are_all_visible_and_comparable() -> None:
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
    app.processEvents()
    assert window.preview_layout.count() == 4
    assert window.compare_a.count() == 4
    assert window.compare_b.count() == 4
    window.compare_a.setCurrentIndex(2)
    window.compare_b.setCurrentIndex(3)
    assert window.comparison_images() == (window.groups[0][2], window.groups[0][3])
    window.auto_select()
    assert len(window.selected_paths) == 3
    assert sum(checkbox.isChecked() for _, checkbox in window.checks) == 3
    window.close()
