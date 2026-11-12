"""Regression checks for non-blocking thumbnails and stable tile geometry."""

import os
import time
from pathlib import Path

import imagehash
from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication, QLabel

from visilens.core import ImageInfo
from visilens.desktop import ImageTile
from visilens.thumbnails import ThumbnailEvents, ThumbnailTask


def test_thumbnail_worker_decodes_off_gui_thread(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    path = tmp_path / "picture.png"
    Image.new("RGB", (120, 90), "#346caa").save(path)
    events = ThumbnailEvents()
    received = []
    events.loaded.connect(lambda filename, generation, image:
                          received.append((filename, generation, image)))
    pool = QThreadPool()
    pool.start(ThumbnailTask(str(path), 42, events))
    assert pool.waitForDone(3000)
    deadline = time.monotonic() + 2
    while not received and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert len(received) == 1
    filename, generation, image = received[0]
    assert filename == str(path)
    assert generation == 42
    assert not image.isNull()
    assert image.width() <= 126
    assert image.height() <= 106


def test_tile_reserves_photo_space_before_and_after_loading(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    info = ImageInfo(
        tmp_path / "one.png", 1600, 1100, 256,
        imagehash.hex_to_hash("0" * 16), bytes(64 * 64 * 3), bytes(64 * 64),
    )
    tile = ImageTile(info, lambda _path, _checked: None)
    tile.show()
    app.processEvents()
    labels = tile.findChildren(QLabel)
    assert tile.width() == 142
    assert tile.height() == 198
    assert labels
    assert all(label.geometry().top() >= tile.button.geometry().bottom()
               for label in labels)
    tile.close()
