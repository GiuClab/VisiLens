"""Small headless GUI regression checks for multi-image groups."""

import os
import time
from pathlib import Path

import imagehash

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect, QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from visilens import desktop
from visilens.app import MainWindow
from visilens.core import ImageInfo


def wait_for(app: QApplication, condition, timeout: float = 3) -> None:
    deadline = time.monotonic() + timeout
    while not condition() and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(15)
    assert condition()


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
    wait_for(app, lambda: len(window.tiles) == 4)
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
    wait_for(app, lambda: len(window.tiles) == 4 and window.group_thread is None)
    window.auto_select()
    assert len(window.selected_paths) == 3
    assert sum(tile.checkbox.isChecked() for tile in window.tiles.values()) == 3
    assert "3 per il cestino" in window.group_labels[0].text()
    assert sum(tile.property("trash") is True for tile in window.tiles.values()) == 3
    marked = next(iter(window.selected_paths))
    window.show_preview(marked)
    assert window.tiles[marked].property("trash") is True
    assert window.tiles[marked].property("active") is False
    assert "href=" in window.preview_link.text()
    window.confirm_close = lambda: True
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


def test_cached_groups_return_without_starting_another_thread() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    digest = imagehash.hex_to_hash("0" * 16)
    window.images = [ImageInfo(Path(f"cached-{n}.jpg"), 120, 120, 200, digest,
                               bytes(64 * 64 * 3), bytes([255]) * (64 * 64))
                     for n in range(3)]
    window.refresh_groups()
    wait_for(app, lambda: "Loose" in window.group_cache and window.group_thread is None)
    window.mode_slider.setValue(2)
    wait_for(app, lambda: "Strict" in window.group_cache and window.group_thread is None)
    cached = window.group_cache["Loose"]
    window.mode_slider.setValue(0)
    window.request_groups()
    assert window.groups is cached
    assert window.group_thread is None
    wait_for(app, lambda: len(window.tiles) == 3)
    window.confirm_close = lambda: True
    window.close()


def test_clickable_path_reveals_photo_in_windows_explorer(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    window = MainWindow()
    filename = Path(r"D:\Pictures\Album\foto.jpg")
    window.preview_path = filename
    called = []
    monkeypatch.setattr(desktop.sys, "platform", "win32")
    monkeypatch.setattr(desktop.subprocess, "Popen", lambda args: called.append(args))
    window.reveal_preview_file()
    assert called == [["explorer.exe", "/select,", str(filename)]]
    window.close()


def test_stat_cards_have_three_colored_vector_icons() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    window = MainWindow()
    icons = window.findChildren(desktop.StatIcon)
    assert {icon.kind for icon in icons} == {"photo", "copies", "storage"}
    assert len({desktop.StatIcon.COLORS[icon.kind][0] for icon in icons}) == 3
    window.close()


def test_first_launch_maximized_and_restored_window_stays_onscreen(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "window.ini"), QSettings.Format.IniFormat)
    first = MainWindow(settings=settings)
    first.open_initial_window()
    app.processEvents()
    assert first.isMaximized()
    first.close()

    available = app.primaryScreen().availableGeometry()
    settings.setValue("window/maximized", False)
    settings.setValue("window/normal_geometry", QRect(-2000, -2000, 2000, 1400))
    second = MainWindow(settings=settings)
    second.open_initial_window()
    app.processEvents()
    assert not second.isMaximized()
    assert available.contains(second.geometry())
    second.close()


def test_close_confirmation_only_when_duplicate_groups_exist(monkeypatch, tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    settings = QSettings(str(tmp_path / "close.ini"), QSettings.Format.IniFormat)
    empty = MainWindow(settings=settings)
    empty.show()

    def unexpected_prompt() -> bool:
        raise AssertionError("Non chiedere conferma senza gruppi")

    monkeypatch.setattr(empty, "confirm_close", unexpected_prompt)
    assert empty.close()

    window = MainWindow(settings=settings)
    window.groups = [[object(), object()]]
    window.show()
    monkeypatch.setattr(window, "confirm_close", lambda: False)
    assert not window.close()
    assert window.isVisible()
    assert window.groups
    monkeypatch.setattr(window, "confirm_close", lambda: True)
    assert window.close()
