"""Qt desktop interface for VisiLens."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, QSize, Qt, QThread, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from send2trash import send2trash

from .core import ImageInfo, group_similar, scan
from .selection import SelectionOptions, propose_selection

STYLE = """
QMainWindow, QWidget#root { background: #f4f5fa; }
QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; color: #252733; }
QFrame#card { background: white; border: 1px solid #e0e4ed; border-radius: 14px; }
QFrame#sidebar { background: #e9edf8; border: none; border-radius: 16px; }
QLabel#heading { font-size: 27px; font-weight: 750; }
QLabel#subtitle { color: #606779; font-size: 13px; }
QLabel#section { font-size: 17px; font-weight: 700; }
QLabel#metric { font-size: 27px; font-weight: 750; }
QLabel#tag { color: #3154ac; background: #e5ecff; border-radius: 8px;
             padding: 4px 8px; font-weight: 650; }
QPushButton { background: white; border: 1px solid #d5dbe8; border-radius: 9px;
              padding: 9px 13px; font-weight: 600; }
QPushButton:hover { background: #ecf1ff; border-color: #9aacdf; }
QPushButton#primary { background: #3858c9; color: white; border: none; padding: 12px 16px; }
QPushButton#primary:hover { background: #2e49af; }
QPushButton#danger { background: #fff3f3; color: #a52323; border-color: #efc0c0; }
QPushButton#nav { background: transparent; border: none; text-align: left; padding: 12px; }
QPushButton#nav:hover { background: #d6e0f8; }
QComboBox { background: white; border: 1px solid #d5dbe8; border-radius: 8px; padding: 8px; }
QListWidget { border: none; background: white; border-radius: 10px; outline: none; }
QListWidget::item { padding: 8px; border-bottom: 1px solid #eef0f5; }
QListWidget::item:selected { background: #dce6ff; color: #203d96; border-radius: 8px; }
QScrollArea { border: none; background: transparent; }
QSlider::groove:horizontal { background: #dfe5f2; height: 6px; border-radius: 3px; }
QSlider::handle:horizontal { background: #4166d5; width: 15px; margin: -5px 0;
                            border-radius: 7px; }
QProgressBar { background: #e1e5ef; border: none; border-radius: 5px; height: 8px; }
QProgressBar::chunk { background: #4c6de2; border-radius: 5px; }
"""


def titled(text: str, kind: str) -> QLabel:
    widget = QLabel(text)
    widget.setObjectName(kind)
    return widget


def card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    return frame, layout


def thumbnail(path: Path, width: int, height: int) -> QLabel:
    preview = QLabel()
    preview.setFixedSize(width, height)
    preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
    preview.setStyleSheet("background: #edf0f6; border-radius: 8px;")
    pixmap = QPixmap(str(path))
    if not pixmap.isNull():
        preview.setPixmap(pixmap.scaled(width - 6, height - 6,
                                        Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation))
    return preview


class ScanWorker(QObject):
    progress = Signal(int, int)
    complete = Signal(object, object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, folders: list[Path]) -> None:
        super().__init__()
        self.folders = folders
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        try:
            base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".cache")))
            cache_path = base / "VisiLens" / "scan-cache.sqlite3"
            images, errors = scan(self.folders, lambda n, total: self.progress.emit(n, total),
                                  lambda: self._cancelled, cache_path=cache_path)
            self.complete.emit(images, errors)
        except Exception as exc:  # noqa: BLE001 — report unexpected worker errors to GUI
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VisiLens — Trova le foto duplicate")
        self.resize(1420, 850)
        self.setMinimumSize(1150, 720)
        self.setStyleSheet(STYLE)
        self.folders: list[Path] = []
        self.images: list[ImageInfo] = []
        self.groups: list[list[ImageInfo]] = []
        self.selected_paths: set[Path] = set()
        self.group_badges: list[QLabel] = []
        self.settings = QSettings("GiuClab", "VisiLens")
        self.thread: QThread | None = None
        self.worker: ScanWorker | None = None

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(16)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(190)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(12, 24, 12, 15)
        nav.addWidget(titled("◈  VisiLens", "section"))
        nav.addSpacing(22)
        for caption, action in (("▱   Cartelle", self.add_folder),
                                ("◷   Scansioni", self.start_scan),
                                ("▢   Duplicati", lambda: self.group_list.setFocus()),
                                ("⚙   Impostazioni", lambda: self.mode.setFocus())):
            button = QPushButton(caption)
            button.setObjectName("nav")
            button.clicked.connect(action)
            nav.addWidget(button)
        nav.addStretch()
        nav.addWidget(titled("0.5.1 · Anteprima", "subtitle"))
        outer.addWidget(sidebar)

        layout = QVBoxLayout()
        layout.setSpacing(14)
        outer.addLayout(layout, 1)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.addWidget(titled("Trova le foto duplicate", "heading"))
        heading.addWidget(titled("Scansiona le cartelle, confronta le immagini e scegli cosa conservare.",
                                 "subtitle"))
        header.addLayout(heading, 1)
        add = QPushButton("＋  Aggiungi cartella")
        add.setObjectName("primary")
        add.clicked.connect(self.add_folder)
        header.addWidget(add)
        layout.addLayout(header)

        controls, toolbar_layout = card()
        toolbar = QHBoxLayout()
        toolbar_layout.addLayout(toolbar)
        self.folder_list = QListWidget()
        self.folder_list.setMinimumWidth(240)
        self.folder_list.setMaximumHeight(82)
        toolbar.addWidget(self.folder_list, 3)
        remove = QPushButton("Rimuovi cartella")
        remove.clicked.connect(self.remove_folder)
        toolbar.addWidget(remove)
        toolbar.addWidget(titled("Somiglianza", "subtitle"))
        self.mode = QComboBox()
        self.mode.addItems(["Strict", "Basic", "Loose"])
        self.mode.setCurrentText("Strict")
        self.mode.currentTextChanged.connect(self.refresh_groups)
        toolbar.addWidget(self.mode)
        self.start_button = QPushButton("▶  Avvia scansione")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start_scan)
        toolbar.addWidget(self.start_button)
        self.cancel_button = QPushButton("Interrompi")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_scan)
        toolbar.addWidget(self.cancel_button)
        layout.addWidget(controls)

        stats = QHBoxLayout()
        self.metric_images = self.stat_card(stats, "▧  Immagini analizzate")
        self.metric_duplicates = self.stat_card(stats, "▢  Duplicati trovati")
        self.metric_space = self.stat_card(stats, "◉  Spazio potenziale")
        layout.addLayout(stats)

        splitter = QSplitter()
        layout.addWidget(splitter, 1)
        left, left_layout = card()
        action_row = QHBoxLayout()
        action_row.addWidget(titled("Gruppi di duplicati", "section"), 1)
        self.auto_button = QPushButton("✦  Auto-Select")
        self.auto_button.setObjectName("primary")
        self.auto_button.clicked.connect(self.auto_select)
        action_row.addWidget(self.auto_button)
        settings_button = QPushButton("⚙  Criteri")
        settings_button.clicked.connect(self.configure_auto_select)
        action_row.addWidget(settings_button)
        left_layout.addLayout(action_row)
        self.selection_summary = titled("Nessun file selezionato", "subtitle")
        left_layout.addWidget(self.selection_summary)
        self.only_selected = QCheckBox("Mostra solo gruppi con file selezionati")
        self.only_selected.toggled.connect(self.update_selection_ui)
        left_layout.addWidget(self.only_selected)
        clear_button = QPushButton("Annulla tutte le selezioni")
        clear_button.clicked.connect(self.clear_selection)
        left_layout.addWidget(clear_button)
        left_layout.addWidget(titled("Seleziona un gruppo per confrontare le immagini.", "subtitle"))
        self.group_list = QListWidget()
        self.group_list.currentRowChanged.connect(self.show_group)
        left_layout.addWidget(self.group_list, 1)
        splitter.addWidget(left)

        right, right_layout = card()
        right.setMinimumWidth(500)
        right_layout.addWidget(titled("Dettagli del gruppo", "section"))
        self.group_title = titled("Nessun gruppo selezionato", "subtitle")
        right_layout.addWidget(self.group_title)
        mode_buttons = QHBoxLayout()
        self.view_grid_button = QPushButton("▦  Griglia")
        self.view_compare_button = QPushButton("◫  Confronto")
        self.view_grid_button.clicked.connect(lambda: self.set_view(0))
        self.view_compare_button.clicked.connect(lambda: self.set_view(1))
        mode_buttons.addWidget(self.view_grid_button)
        mode_buttons.addWidget(self.view_compare_button)
        mode_buttons.addStretch()
        right_layout.addLayout(mode_buttons)
        self.content_stack = QStackedWidget()
        right_layout.addWidget(self.content_stack, 1)

        grid_page = QWidget()
        grid_layout = QVBoxLayout(grid_page)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.addWidget(titled("Tutte le immagini del gruppo", "section"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.preview = QWidget()
        self.preview_layout = QGridLayout(self.preview)
        self.preview_layout.setContentsMargins(6, 6, 6, 6)
        self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.preview_layout.setSpacing(10)
        scroll.setWidget(self.preview)
        grid_layout.addWidget(scroll, 1)
        self.content_stack.addWidget(grid_page)

        compare_page = QWidget()
        compare_layout = QVBoxLayout(compare_page)
        compare_layout.setContentsMargins(0, 0, 0, 0)
        compare_controls = QHBoxLayout()
        compare_controls.addWidget(titled("Confronta A", "subtitle"))
        self.compare_a = QComboBox()
        self.compare_a.currentIndexChanged.connect(self.update_comparison)
        compare_controls.addWidget(self.compare_a, 1)
        compare_controls.addWidget(titled("B", "subtitle"))
        self.compare_b = QComboBox()
        self.compare_b.currentIndexChanged.connect(self.update_comparison)
        compare_controls.addWidget(self.compare_b, 1)
        enlarge = QPushButton("⤢  Ingrandisci")
        enlarge.clicked.connect(self.open_comparison)
        compare_controls.addWidget(enlarge)
        compare_layout.addLayout(compare_controls)
        compare_preview = QHBoxLayout()
        self.compare_image_a = QLabel()
        self.compare_image_b = QLabel()
        for preview in (self.compare_image_a, self.compare_image_b):
            preview.setFixedSize(205, 275)
            preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            preview.setStyleSheet("background: #eef1f7; border-radius: 9px;")
            compare_preview.addWidget(preview, 1)
        compare_layout.addLayout(compare_preview)
        compare_layout.addWidget(titled("Scegli due immagini e usa Ingrandisci per "
                                        "vedere i dettagli.", "subtitle"))
        compare_layout.addStretch(1)
        self.content_stack.addWidget(compare_page)
        self.set_view(0)
        self.trash_button = QPushButton("♲  Sposta selezionate nel cestino")
        self.trash_button.setObjectName("danger")
        self.trash_button.clicked.connect(self.trash_selected)
        right_layout.addWidget(self.trash_button)
        splitter.addWidget(right)
        splitter.setSizes([550, 600])

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.status = titled("Aggiungi una cartella per iniziare.", "subtitle")
        layout.addWidget(self.status)
        self.checks: list[tuple[ImageInfo, object]] = []
        self.update_statistics()
        self.auto_button.setEnabled(False)

    def set_view(self, index: int) -> None:
        self.content_stack.setCurrentIndex(index)
        self.view_grid_button.setObjectName("primary" if index == 0 else "")
        self.view_compare_button.setObjectName("primary" if index == 1 else "")
        for button in (self.view_grid_button, self.view_compare_button):
            button.style().unpolish(button)
            button.style().polish(button)

    @staticmethod
    def stat_card(layout: QHBoxLayout, title: str) -> QLabel:
        frame, column = card()
        column.addWidget(titled(title, "subtitle"))
        value = titled("0", "metric")
        column.addWidget(value)
        layout.addWidget(frame, 1)
        return value

    def update_statistics(self) -> None:
        duplicate_count = sum(len(group) - 1 for group in self.groups)
        potential_bytes = sum(item.bytes for group in self.groups for item in group[1:])
        self.metric_images.setText(f"{len(self.images):,}".replace(",", "."))
        self.metric_duplicates.setText(str(duplicate_count))
        self.metric_space.setText(f"{potential_bytes / (1024**2):.1f} MB")

    def add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose image folder")
        if folder and Path(folder) not in self.folders:
            self.folders.append(Path(folder))
            self.folder_list.addItem(folder)

    def remove_folder(self) -> None:
        row = self.folder_list.currentRow()
        if row >= 0:
            self.folder_list.takeItem(row)
            self.folders.pop(row)

    def start_scan(self) -> None:
        if not self.folders or self.thread is not None:
            return
        self.images = []
        self.groups = []
        self.selected_paths.clear()
        self.group_list.clear()
        self.show_group(-1)
        self.progress.setValue(0)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText("Scansione in corso…")
        self.thread = QThread(self)
        self.worker = ScanWorker(self.folders.copy())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.update_progress)
        self.worker.complete.connect(self.on_complete)
        self.worker.failed.connect(self.on_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.start()

    def cancel_scan(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.status.setText("Interruzione dopo l'immagine corrente…")

    @Slot(int, int)
    def update_progress(self, done: int, total: int) -> None:
        self.progress.setValue(round(100 * done / total) if total else 100)

    @Slot(object, object)
    def on_complete(self, images: list[ImageInfo], errors: list[str]) -> None:
        self.images = images
        self.refresh_groups()
        self.status.setText(f"{len(images)} immagini analizzate · {len(self.groups)} gruppi · "
                            f"{len(errors)} file non leggibili")
        if errors:
            QMessageBox.warning(self, "File non leggibili", "Alcuni file sono stati ignorati:\n" +
                                "\n".join(errors[:10]))

    @Slot(str)
    def on_error(self, message: str) -> None:
        QMessageBox.critical(self, "Errore durante la scansione", message)
        self.status.setText("Scansione non riuscita.")

    @Slot()
    def on_thread_finished(self) -> None:
        self.thread = None
        self.worker = None
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def refresh_groups(self) -> None:
        self.selected_paths.clear()
        self.groups = group_similar(self.images, self.mode.currentText())
        self.group_list.clear()
        self.group_badges = []
        for index, group in enumerate(self.groups, 1):
            item = QListWidgetItem()
            item.setSizeHint(QSize(340, 92))
            self.group_list.addItem(item)
            widget = QWidget()
            row = QHBoxLayout(widget)
            row.setContentsMargins(4, 4, 4, 4)
            row.setSpacing(4)
            for photo in group[:4]:
                row.addWidget(thumbnail(photo.path, 50, 65))
            if len(group) > 4:
                row.addWidget(titled(f"+{len(group) - 4}", "tag"))
            information = QVBoxLayout()
            information.addWidget(titled(f"Gruppo {index}", "section"))
            information.addWidget(titled(f"{len(group)} immagini", "subtitle"))
            badge = titled("Nessuna selezione", "subtitle")
            information.addWidget(badge)
            self.group_badges.append(badge)
            information.addStretch()
            row.addLayout(information, 1)
            self.group_list.setItemWidget(item, widget)
        self.update_statistics()
        self.auto_button.setEnabled(bool(self.groups) and self.mode.currentText() == "Strict")
        self.only_selected.setChecked(False)
        self.update_selection_ui()
        if self.groups:
            self.group_list.setCurrentRow(0)
        else:
            self.show_group(-1)

    def show_group(self, row: int) -> None:
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.checks = []
        self.compare_a.blockSignals(True)
        self.compare_b.blockSignals(True)
        self.compare_a.clear()
        self.compare_b.clear()
        if row < 0 or row >= len(self.groups):
            self.group_title.setText("Nessun gruppo selezionato")
            self.trash_button.setEnabled(False)
            self.compare_a.blockSignals(False)
            self.compare_b.blockSignals(False)
            self.compare_image_a.clear()
            self.compare_image_b.clear()
            return
        self.trash_button.setEnabled(True)
        self.group_title.setText(f"Gruppo {row + 1} di {len(self.groups)}")
        for index, image in enumerate(self.groups[row]):
            item, item_layout = card()
            item.setMinimumWidth(205)
            if image.path in self.selected_paths:
                item.setStyleSheet("QFrame { border: 2px solid #d65b5b; background: #fff8f8; }")
            item_layout.addWidget(thumbnail(image.path, 170, 138),
                                  alignment=Qt.AlignmentFlag.AlignHCenter)
            checkbox = QCheckBox("Sposta nel cestino")
            checkbox.setChecked(image.path in self.selected_paths)
            checkbox.toggled.connect(
                lambda checked, path=image.path: self.set_selected(path, checked)
            )
            checkbox.toggled.connect(
                lambda checked, frame=item: frame.setStyleSheet(
                    "QFrame { border: 2px solid #d65b5b; background: #fff8f8; }"
                    if checked else ""
                )
            )
            item_layout.addWidget(checkbox)
            if index == 0:
                item_layout.addWidget(titled("Risoluzione più alta", "tag"))
            label = QLabel(image.path.name)
            label.setWordWrap(True)
            label.setToolTip(str(image.path))
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            item_layout.addWidget(label)
            item_layout.addWidget(titled(f"{image.width} × {image.height} · "
                                        f"{image.bytes / 1024:.0f} KB", "subtitle"))
            self.preview_layout.addWidget(item, index // 2, index % 2)
            self.checks.append((image, checkbox))
            name = f"{index + 1}. {image.path.name}"
            self.compare_a.addItem(name)
            self.compare_b.addItem(name)
        self.compare_a.setCurrentIndex(0)
        self.compare_b.setCurrentIndex(1 if len(self.groups[row]) > 1 else 0)
        self.compare_a.blockSignals(False)
        self.compare_b.blockSignals(False)
        self.update_comparison()

    def comparison_images(self) -> tuple[ImageInfo, ImageInfo] | None:
        row = self.group_list.currentRow()
        if not (0 <= row < len(self.groups)):
            return None
        group = self.groups[row]
        a, b = self.compare_a.currentIndex(), self.compare_b.currentIndex()
        if not (0 <= a < len(group) and 0 <= b < len(group)):
            return None
        return group[a], group[b]

    def update_comparison(self) -> None:
        pair = self.comparison_images()
        if pair is None:
            return
        for info, view in zip(pair, (self.compare_image_a, self.compare_image_b), strict=True):
            pixmap = QPixmap(str(info.path))
            if pixmap.isNull():
                view.setText("Anteprima non disponibile")
                continue
            view.setPixmap(pixmap.scaled(190, 250, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation))

    def open_comparison(self) -> None:
        pair = self.comparison_images()
        if pair is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Confronto ingrandito — VisiLens")
        dialog.resize(1150, 760)
        layout = QVBoxLayout(dialog)
        layout.addWidget(titled("Confronto affiancato", "section"))
        layout.addWidget(titled("Usa lo zoom per esaminare piccoli dettagli nelle due immagini.",
                                "subtitle"))
        pictures = QHBoxLayout()
        source_pixmaps = [QPixmap(str(info.path)) for info in pair]
        display_labels = []
        for info in pair:
            column = QVBoxLayout()
            column.addWidget(titled(info.path.name, "section"))
            column.addWidget(titled(f"{info.width} × {info.height} · "
                                    f"{info.bytes / 1024:.0f} KB", "subtitle"))
            scroll = QScrollArea()
            scroll.setWidgetResizable(False)
            display = QLabel()
            display.setAlignment(Qt.AlignmentFlag.AlignCenter)
            display.setStyleSheet("background: #edf0f6; border-radius: 8px;")
            scroll.setWidget(display)
            column.addWidget(scroll, 1)
            pictures.addLayout(column, 1)
            display_labels.append(display)
        layout.addLayout(pictures, 1)
        zoom_row = QHBoxLayout()
        zoom_row.addWidget(titled("Zoom", "subtitle"))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(50, 300)
        slider.setValue(100)
        zoom_label = titled("100%", "subtitle")
        zoom_row.addWidget(slider, 1)
        zoom_row.addWidget(zoom_label)
        layout.addLayout(zoom_row)

        def apply_zoom(value: int) -> None:
            zoom_label.setText(f"{value}%")
            for pixmap, view in zip(source_pixmaps, display_labels, strict=True):
                if pixmap.isNull():
                    view.setText("Anteprima non disponibile")
                    continue
                baseline = pixmap.scaled(510, 510, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
                scaled = baseline.scaled(round(baseline.width() * value / 100),
                                         round(baseline.height() * value / 100),
                                         Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
                view.setPixmap(scaled)
                view.resize(scaled.size())

        slider.valueChanged.connect(apply_zoom)
        apply_zoom(100)
        close = QPushButton("Chiudi")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        dialog.exec()

    def set_selected(self, path: Path, checked: bool) -> None:
        if checked:
            self.selected_paths.add(path)
        else:
            self.selected_paths.discard(path)
        self.update_selection_ui()

    def update_selection_ui(self) -> None:
        count = len(self.selected_paths)
        self.selection_summary.setText(f"{count} file selezionati per il cestino" if count > 1
                                       else "1 file selezionato per il cestino" if count == 1
                                       else "Nessun file selezionato")
        for row, group in enumerate(self.groups):
            group_count = sum(image.path in self.selected_paths for image in group)
            self.group_badges[row].setText(f"● {group_count} selezionate" if group_count
                                            else "Nessuna selezione")
            self.group_badges[row].setStyleSheet("color: #bb3030; font-weight: 650;"
                                                   if group_count else "color: #606779;")
            self.group_list.item(row).setHidden(
                self.only_selected.isChecked() and group_count == 0
            )

    def clear_selection(self) -> None:
        self.selected_paths.clear()
        self.show_group(self.group_list.currentRow())
        self.update_selection_ui()
        self.status.setText("Selezione annullata. Nessun file è stato modificato.")

    def auto_select(self) -> None:
        if self.mode.currentText() != "Strict" or not self.groups:
            QMessageBox.information(self, "Auto-Select",
                                    "Per sicurezza Auto-Select è disponibile solo in Strict.")
            return
        stored = self.settings.value("protected_folders", [], type=list)
        options = SelectionOptions(
            self.settings.value("prefer_resolution", True, type=bool),
            self.settings.value("prefer_file_size", True, type=bool),
            tuple(Path(p) for p in stored),
        )
        proposal = propose_selection(self.groups, options)
        self.selected_paths = set(proposal.trash_paths)
        self.only_selected.setChecked(True)
        self.update_selection_ui()
        selected_rows = [i for i, group in enumerate(self.groups)
                         if any(image.path in self.selected_paths for image in group)]
        if selected_rows:
            self.group_list.setCurrentRow(selected_rows[0])
        self.show_group(self.group_list.currentRow())
        self.status.setText(
            f"Auto-Select: {len(proposal.trash_paths)} file selezionati in "
            f"{len(proposal.kept_paths)} gruppi · {proposal.tied_groups} parità risolte "
            "per percorso. Controlla prima di spostare nel cestino."
        )

    def configure_auto_select(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Auto-Select — Criteri")
        dialog.setMinimumWidth(490)
        form = QVBoxLayout(dialog)
        form.addWidget(titled("Quale immagine vuoi conservare?", "section"))
        form.addWidget(titled("Nessuna immagine verrà eliminata automaticamente.", "subtitle"))
        prefer_resolution = QCheckBox("Preferisci la risoluzione maggiore")
        prefer_resolution.setChecked(self.settings.value("prefer_resolution", True, type=bool))
        form.addWidget(prefer_resolution)
        prefer_size = QCheckBox("A parità di risoluzione, preferisci il file più grande")
        prefer_size.setChecked(self.settings.value("prefer_file_size", True, type=bool))
        form.addWidget(prefer_size)
        form.addWidget(titled("La dimensione del file non garantisce una qualità migliore.",
                             "subtitle"))
        form.addWidget(titled("Cartelle protette (immagini da conservare)", "section"))
        protected_list = QListWidget()
        protected_list.setMinimumHeight(95)
        folders = [Path(p) for p in self.settings.value("protected_folders", [], type=list)]
        for folder in folders:
            protected_list.addItem(str(folder))
        form.addWidget(protected_list)
        folder_buttons = QHBoxLayout()
        add = QPushButton("Aggiungi cartella protetta")

        def add_protected() -> None:
            chosen = QFileDialog.getExistingDirectory(dialog, "Scegli una cartella protetta")
            if chosen and Path(chosen) not in folders:
                folders.append(Path(chosen))
                protected_list.addItem(chosen)

        add.clicked.connect(add_protected)
        folder_buttons.addWidget(add)
        remove = QPushButton("Rimuovi")

        def remove_protected() -> None:
            index = protected_list.currentRow()
            if index >= 0:
                protected_list.takeItem(index)
                folders.pop(index)

        remove.clicked.connect(remove_protected)
        folder_buttons.addWidget(remove)
        form.addLayout(folder_buttons)
        actions = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        actions.button(QDialogButtonBox.StandardButton.Ok).setText("Salva criteri")
        actions.accepted.connect(dialog.accept)
        actions.rejected.connect(dialog.reject)
        form.addWidget(actions)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.settings.setValue("prefer_resolution", prefer_resolution.isChecked())
        self.settings.setValue("prefer_file_size", prefer_size.isChecked())
        self.settings.setValue("protected_folders", [str(p) for p in folders])
        self.status.setText("Criteri salvati. Premi Auto-Select per applicarli.")

    def trash_selected(self) -> None:
        targets = list(self.selected_paths)
        if not targets:
            QMessageBox.information(self, "Nessuna selezione",
                                    "Seleziona prima le immagini da spostare nel cestino.")
            return
        if any(all(image.path in self.selected_paths for image in group)
               for group in self.groups):
            QMessageBox.warning(self, "Conserva un'immagine",
                                "Deve rimanere almeno un'immagine in ciascun gruppo.")
            return
        response = QMessageBox.question(
            self, "Conferma lo spostamento",
            f"Spostare {len(targets)} immagini nel cestino?\n"
            "Controlla le selezioni: VisiLens non può annullare direttamente l'operazione.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        failures = []
        moved = []
        for path in targets:
            try:
                send2trash(str(path))
                moved.append(path)
            except OSError as exc:
                failures.append(f"{path}: {exc}")
        self.images = [image for image in self.images if image.path not in moved]
        self.selected_paths.difference_update(moved)
        self.refresh_groups()
        self.status.setText(f"{len(moved)} immagini nel cestino · {len(failures)} errori")
        if failures:
            QMessageBox.warning(self, "Alcuni file non sono stati spostati",
                                "\n".join(failures[:10]))

    def closeEvent(self, event) -> None:
        if self.thread is not None:
            QMessageBox.information(self, "Scansione attiva",
                                    "Interrompi la scansione e attendi che termini.")
            event.ignore()
        else:
            event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
