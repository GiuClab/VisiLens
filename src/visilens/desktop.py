"""VisiLens desktop UI: folders on the left, groups in the middle, preview on the right."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import (
    QDir,
    QFileInfo,
    QObject,
    QSettings,
    QStandardPaths,
    Qt,
    QThread,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFileIconProvider,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from send2trash import send2trash

from .core import ImageInfo, group_similar, scan
from .selection import SelectionOptions, propose_selection

STYLE = """
QMainWindow, QWidget#root { background: #f5f6fb; }
QWidget { font-family: 'Segoe UI', Arial; color: #242936; font-size: 12px; }
QFrame#panel, QFrame#stat, QFrame#group, QFrame#tile {
 background: white; border: 1px solid #dfe3ed; border-radius: 12px; }
QFrame#tile[active="true"] { border: 2px solid #3d61da; background: #f0f4ff; }
QLabel#title { font-size: 18px; font-weight: 750; }
QLabel#metric { font-size: 25px; font-weight: 750; }
QLabel#muted { color: #677082; }
QLabel#section { font-size: 14px; font-weight: 700; }
QPushButton { border: 1px solid #d6ddec; border-radius: 9px; background: white;
 padding: 9px 12px; font-weight: 600; }
QPushButton:hover { background: #edf2ff; border-color: #9eb3e8; }
QPushButton#primary { background: #385ad0; color: white; border: none; }
QPushButton#primary:hover { background: #2d49ab; }
QPushButton#danger { background: #fff5f5; color: #ad2323; border-color: #ecc3c3; }
QPushButton#thumb { background: #eef1f7; border: none; padding: 0; }
QTreeWidget, QListWidget { border: 1px solid #e0e4ee; border-radius: 9px; background: white; }
QTreeWidget::item, QListWidget::item { padding: 4px; }
QTreeWidget::item:selected, QListWidget::item:selected { background: #dbe5ff; color: #2445a1; }
QScrollArea { border: none; background: transparent; }
QProgressBar { border: none; background: #e1e5f0; border-radius: 5px; height: 9px; }
QProgressBar::chunk { background: #4064d6; border-radius: 5px; }
QSlider::groove:horizontal { height: 6px; background: #d4dbea; border-radius: 3px; }
QSlider::handle:horizontal { width: 16px; margin: -5px 0; border-radius: 8px;
 background: #365cce; }
"""


def lbl(value: str, kind: str = "") -> QLabel:
    widget = QLabel(value)
    if kind:
        widget.setObjectName(kind)
    return widget


def box(name: str = "panel") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName(name)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(9)
    return frame, layout


def pretty_bytes(size: int) -> str:
    if size >= 1024**3:
        return f"{size / 1024**3:.2f} GB"
    if size >= 1024**2:
        return f"{size / 1024**2:.1f} MB"
    return f"{size / 1024:.0f} KB"


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
            cache = base / "VisiLens" / "scan-cache.sqlite3"
            images, errors = scan(self.folders, lambda n, total: self.progress.emit(n, total),
                                  lambda: self._cancelled, cache_path=cache)
            self.complete.emit(images, errors)
        except Exception as exc:  # noqa: BLE001 — deliver worker errors to the interface
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class ImageTile(QFrame):
    def __init__(self, image: ImageInfo, callback) -> None:
        super().__init__()
        self.image = image
        self.setObjectName("tile")
        self.setProperty("active", False)
        self.setFixedWidth(142)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)
        self.button = QPushButton()
        self.button.setObjectName("thumb")
        self.button.setFixedSize(130, 110)
        self.button.setToolTip(f"{image.path}\nClicca per vedere l'anteprima")
        pixmap = QPixmap(str(image.path))
        if not pixmap.isNull():
            self.button.setIcon(QIcon(pixmap))
            from PySide6.QtCore import QSize

            self.button.setIconSize(QSize(126, 106))
        else:
            self.button.setText("Anteprima non disponibile")
        layout.addWidget(self.button)
        name = lbl(self.fontMetrics().elidedText(image.path.name,
                                                 Qt.TextElideMode.ElideMiddle, 130))
        name.setToolTip(image.path.name)
        layout.addWidget(name)
        layout.addWidget(lbl(f"{image.width} × {image.height} · {pretty_bytes(image.bytes)}",
                             "muted"))
        self.checkbox = QCheckBox("Cestino")
        layout.addWidget(self.checkbox)
        self.checkbox.toggled.connect(lambda checked: callback(image.path, checked))

    def set_state(self, checked: bool, active: bool) -> None:
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(checked)
        self.checkbox.blockSignals(False)
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    MODES = ("Loose", "Basic", "Strict")
    MODE_COLORS = ("#385ad0", "#1baf71", "#d44747")

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VisiLens — Trova le foto duplicate")
        self.resize(1600, 950)
        self.setMinimumSize(1180, 720)
        self.setStyleSheet(STYLE)
        self.settings = QSettings("GiuClab", "VisiLens")
        self.folders: list[Path] = []
        self.images: list[ImageInfo] = []
        self.groups: list[list[ImageInfo]] = []
        self.selected_paths: set[Path] = set()
        self.tiles: dict[Path, ImageTile] = {}
        self.group_labels: list[QLabel] = []
        self.thread: QThread | None = None
        self.worker: ScanWorker | None = None
        self.preview_path: Path | None = None
        self.image_by_path: dict[Path, ImageInfo] = {}
        self.icon_provider = QFileIconProvider()

        self.create_menus()
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outside = QVBoxLayout(root)
        outside.setContentsMargins(10, 8, 10, 8)
        outside.setSpacing(8)
        columns = QHBoxLayout()
        columns.setSpacing(12)
        outside.addLayout(columns, 1)

        left, left_layout = box()
        left.setFixedWidth(255)
        columns.addWidget(left)
        left_layout.addWidget(lbl("Seleziona le cartelle da analizzare", "section"))
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemExpanded.connect(self.populate_node)
        self.tree.itemChanged.connect(self.folder_checked)
        left_layout.addWidget(self.tree, 1)
        self.setup_tree()
        left_layout.addWidget(lbl("Cartelle selezionate", "section"))
        self.folder_list = QListWidget()
        self.folder_list.setMaximumHeight(92)
        left_layout.addWidget(self.folder_list)
        remove = QPushButton("Rimuovi cartella")
        remove.clicked.connect(self.remove_folder)
        left_layout.addWidget(remove)
        left_layout.addWidget(lbl("Livello di somiglianza", "section"))
        self.filter_name = lbl("Loose — confronto flessibile", "muted")
        left_layout.addWidget(self.filter_name)
        self.mode_slider = QSlider(Qt.Orientation.Horizontal)
        self.mode_slider.setRange(0, 2)
        self.mode_slider.setValue(0)
        self.mode_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.mode_slider.setTickInterval(1)
        self.mode_slider.valueChanged.connect(self.mode_changed)
        left_layout.addWidget(self.mode_slider)
        self.set_mode_color(0)
        scan_buttons = QHBoxLayout()
        self.start_button = QPushButton("▶ Avvia scansione")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start_scan)
        scan_buttons.addWidget(self.start_button)
        self.cancel_button = QPushButton("Interrompi")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_scan)
        scan_buttons.addWidget(self.cancel_button)
        left_layout.addLayout(scan_buttons)

        middle = QVBoxLayout()
        middle.setSpacing(10)
        columns.addLayout(middle, 1)
        stats = QHBoxLayout()
        self.stat_images = self.stat(stats, "▧  Immagini analizzate")
        self.stat_duplicates = self.stat(stats, "▢  Duplicati trovati")
        self.stat_space = self.stat(stats, "◉  Spazio recuperabile")
        middle.addLayout(stats)
        actions = QHBoxLayout()
        self.auto_button = QPushButton("✦ Auto-Select")
        self.auto_button.setObjectName("primary")
        self.auto_button.clicked.connect(self.auto_select)
        self.auto_button.setEnabled(False)
        actions.addWidget(self.auto_button)
        criteria = QPushButton("⚙ Criteri")
        criteria.clicked.connect(self.configure_auto_select)
        actions.addWidget(criteria)
        reset = QPushButton("Annulla selezione")
        reset.clicked.connect(self.clear_selection)
        actions.addWidget(reset)
        middle.addLayout(actions)
        self.selection_info = lbl("Nessun file selezionato", "muted")
        middle.addWidget(self.selection_info)
        self.groups_scroll = QScrollArea()
        self.groups_scroll.setWidgetResizable(True)
        self.groups_host = QWidget()
        self.groups_layout = QVBoxLayout(self.groups_host)
        self.groups_layout.setContentsMargins(3, 3, 3, 3)
        self.groups_layout.setSpacing(12)
        self.groups_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.groups_scroll.setWidget(self.groups_host)
        middle.addWidget(self.groups_scroll, 1)

        right, right_layout = box()
        right.setMinimumWidth(370)
        columns.addWidget(right, 1)
        right_layout.addWidget(lbl("Anteprima", "title"))
        self.big_preview = QLabel("Seleziona una miniatura")
        self.big_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.big_preview.setMinimumSize(0, 300)
        self.big_preview.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Expanding)
        self.big_preview.setStyleSheet("background: #eef1f7; border-radius: 10px;")
        right_layout.addWidget(self.big_preview, 1)
        self.preview_name = lbl("Nessuna immagine selezionata", "section")
        self.preview_name.setWordWrap(True)
        right_layout.addWidget(self.preview_name)
        self.preview_details = lbl("", "muted")
        self.preview_details.setWordWrap(True)
        self.preview_details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        right_layout.addWidget(self.preview_details)
        self.trash_button = QPushButton("♲ Sposta selezionate nel cestino")
        self.trash_button.setObjectName("danger")
        self.trash_button.clicked.connect(self.trash_selected)
        right_layout.addWidget(self.trash_button)

        bottom = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setValue(0)
        bottom.addWidget(self.progress, 1)
        self.status = lbl("Seleziona una cartella e avvia la scansione.", "muted")
        bottom.addWidget(self.status, 2)
        outside.addLayout(bottom)
        self.update_stats()

    def create_menus(self) -> None:
        self.menuBar().setNativeMenuBar(False)
        brand = lbl("◈  VisiLens", "section")
        brand.setContentsMargins(8, 0, 12, 0)
        brand.setToolTip("Spazio riservato al logo ufficiale di VisiLens")
        self.menuBar().setCornerWidget(brand, Qt.Corner.TopRightCorner)
        file_menu = self.menuBar().addMenu("File")
        for caption, action in (("Aggiungi cartella…", self.add_folder),
                                ("Avvia scansione", self.start_scan),
                                ("Interrompi", self.cancel_scan),
                                ("Esci", self.close)):
            entry = QAction(caption, self)
            entry.triggered.connect(action)
            file_menu.addAction(entry)
        language = self.menuBar().addMenu("Language")
        italian = QAction("Italiano", self)
        italian.setCheckable(True)
        italian.setChecked(True)
        language.addAction(italian)
        english = QAction("English — prossimamente", self)
        english.setEnabled(False)
        language.addAction(english)
        help_menu = self.menuBar().addMenu("Help")
        about = QAction("Informazioni su VisiLens", self)
        about.triggered.connect(lambda: QMessageBox.information(
            self, "VisiLens", "VisiLens 0.6.1 — anteprima Windows\n"
            "Trova immagini duplicate, controlla le selezioni prima del cestino."))
        help_menu.addAction(about)
        repo = QAction("Progetto su GitHub", self)
        repo.triggered.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://github.com/GiuClab/VisiLens")))
        help_menu.addAction(repo)

    def setup_tree(self) -> None:
        self.tree.blockSignals(True)
        root = QTreeWidgetItem(["Questo PC"])
        root.setFlags(root.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
        root.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.tree.addTopLevelItem(root)
        locations = (
            ("Desktop", QStandardPaths.StandardLocation.DesktopLocation),
            ("Documenti", QStandardPaths.StandardLocation.DocumentsLocation),
            ("Download", QStandardPaths.StandardLocation.DownloadLocation),
            ("Immagini", QStandardPaths.StandardLocation.PicturesLocation),
            ("Musica", QStandardPaths.StandardLocation.MusicLocation),
            ("Video", QStandardPaths.StandardLocation.MoviesLocation),
        )
        seen: set[Path] = set()
        for title, location in locations:
            folder_name = QStandardPaths.writableLocation(location)
            if folder_name:
                folder = Path(folder_name)
                if folder not in seen:
                    self.add_tree_folder(root, folder, title)
                    seen.add(folder)
        objects_3d = Path.home() / "3D Objects"
        if sys.platform == "win32" and objects_3d.is_dir():
            self.add_tree_folder(root, objects_3d, "Oggetti 3D")
        drives = [Path(info.absoluteFilePath()) for info in QDir.drives()]
        if not drives:
            drives = [Path.home()]
        for drive in drives:
            drive_label = f"Disco locale ({drive.drive or str(drive).rstrip('/')})"
            self.add_tree_folder(root, drive, drive_label)
        root.setExpanded(True)
        self.tree.blockSignals(False)

    def add_tree_folder(self, parent: QTreeWidgetItem, folder: Path,
                        label: str | None = None) -> QTreeWidgetItem:
        name = label or folder.name or str(folder)
        item = QTreeWidgetItem([name])
        item.setData(0, Qt.ItemDataRole.UserRole, str(folder))
        item.setIcon(0, self.icon_provider.icon(QFileInfo(str(folder))))
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked if folder in self.folders
                           else Qt.CheckState.Unchecked)
        item.addChild(QTreeWidgetItem(["…"]))
        parent.addChild(item)
        return item

    def populate_node(self, item: QTreeWidgetItem) -> None:
        value = item.data(0, Qt.ItemDataRole.UserRole)
        if not value or item.childCount() != 1 or item.child(0).text(0) != "…":
            return
        item.takeChild(0)
        try:
            folders = sorted((p for p in Path(value).iterdir() if p.is_dir()),
                             key=lambda p: p.name.casefold())
        except (OSError, PermissionError):
            return
        self.tree.blockSignals(True)
        for folder in folders:
            self.add_tree_folder(item, folder)
        self.tree.blockSignals(False)

    def folder_checked(self, item: QTreeWidgetItem, column: int) -> None:
        value = item.data(0, Qt.ItemDataRole.UserRole)
        if not value:
            return
        path = Path(value)
        if item.checkState(column) == Qt.CheckState.Checked:
            if path not in self.folders:
                self.folders.append(path)
        else:
            if path in self.folders:
                self.folders.remove(path)
        self.refresh_folder_list()

    def refresh_folder_list(self) -> None:
        self.folder_list.clear()
        for folder in self.folders:
            self.folder_list.addItem(str(folder))

    def add_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Seleziona cartella")
        if chosen and Path(chosen) not in self.folders:
            self.folders.append(Path(chosen))
            self.refresh_folder_list()

    def remove_folder(self) -> None:
        row = self.folder_list.currentRow()
        if row < 0:
            return
        removed = self.folders.pop(row)
        self.refresh_folder_list()
        iterator = self.tree.findItems(removed.name, Qt.MatchFlag.MatchRecursive)
        for item in iterator:
            if item.data(0, Qt.ItemDataRole.UserRole) == str(removed):
                self.tree.blockSignals(True)
                item.setCheckState(0, Qt.CheckState.Unchecked)
                self.tree.blockSignals(False)

    def mode_changed(self, index: int) -> None:
        mode = self.MODES[index]
        self.filter_name.setText({"Strict": "Strict — confronto rigoroso",
                                  "Basic": "Basic — somiglianza equilibrata",
                                  "Loose": "Loose — confronto flessibile"}[mode])
        self.set_mode_color(index)
        self.refresh_groups()

    def set_mode_color(self, index: int) -> None:
        color = self.MODE_COLORS[index]
        self.mode_slider.setStyleSheet(
            "QSlider::handle:horizontal { width: 16px; margin: -5px 0; "
            f"border-radius: 8px; background: {color}; }}"
        )

    def start_scan(self) -> None:
        if self.thread is not None:
            return
        if not self.folders:
            self.status.setText("Seleziona almeno una cartella.")
            return
        self.images, self.groups = [], []
        self.selected_paths.clear()
        self.render_groups()
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
            self.status.setText("Arresto dopo l'immagine corrente…")

    @Slot(int, int)
    def update_progress(self, done: int, total: int) -> None:
        self.progress.setValue(round(done * 100 / total) if total else 100)

    @Slot(object, object)
    def on_complete(self, images: list[ImageInfo], errors: list[str]) -> None:
        self.images = images
        self.refresh_groups()
        self.status.setText(f"{len(images)} immagini analizzate · "
                            f"{len(self.groups)} gruppi · {len(errors)} errori")
        if errors:
            QMessageBox.warning(self, "File ignorati", "\n".join(errors[:10]))

    @Slot(str)
    def on_error(self, error: str) -> None:
        QMessageBox.critical(self, "Errore durante la scansione", error)
        self.status.setText("Scansione non riuscita")

    @Slot()
    def on_thread_finished(self) -> None:
        self.thread = None
        self.worker = None
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def refresh_groups(self) -> None:
        self.selected_paths.clear()
        self.groups = group_similar(self.images, self.MODES[self.mode_slider.value()])
        self.image_by_path = {image.path: image for image in self.images}
        self.render_groups()

    def render_groups(self) -> None:
        while self.groups_layout.count():
            item = self.groups_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.tiles.clear()
        self.group_labels.clear()
        for number, group in enumerate(self.groups, 1):
            frame, body = box("group")
            heading = QHBoxLayout()
            heading.addWidget(lbl(f"Gruppo {number} · {len(group)} immagini", "section"), 1)
            selected = lbl("", "muted")
            heading.addWidget(selected)
            self.group_labels.append(selected)
            body.addLayout(heading)
            grid = QGridLayout()
            grid.setSpacing(8)
            for index, info in enumerate(group):
                tile = ImageTile(info, self.thumbnail_toggled)
                self.tiles[info.path] = tile
                tile.button.clicked.connect(lambda _checked=False, path=info.path:
                                            self.show_preview(path))
                # Two columns keep entire thumbnails visible even at the
                # minimum supported window width (1180 px).
                grid.addWidget(tile, index // 2, index % 2,
                               alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            body.addLayout(grid)
            self.groups_layout.addWidget(frame)
        self.auto_button.setEnabled(bool(self.groups) and self.mode_slider.value() == 2)
        self.update_stats()
        self.update_selection_ui()
        if self.groups:
            self.show_preview(self.groups[0][0].path)
        else:
            self.preview_path = None
            self.big_preview.clear()
            self.preview_name.setText("Nessuna immagine selezionata")
            self.preview_details.setText("")

    def thumbnail_toggled(self, path: Path, checked: bool) -> None:
        if checked:
            self.selected_paths.add(path)
        else:
            self.selected_paths.discard(path)
        self.update_selection_ui()

    def update_selection_ui(self) -> None:
        for path, tile in self.tiles.items():
            tile.set_state(path in self.selected_paths, path == self.preview_path)
        for group, badge in zip(self.groups, self.group_labels, strict=True):
            count = sum(info.path in self.selected_paths for info in group)
            badge.setText(f"{count} per il cestino" if count else "")
        count = len(self.selected_paths)
        self.selection_info.setText(f"{count} file selezionati per il cestino" if count != 1
                                    else "1 file selezionato per il cestino")

    def clear_selection(self) -> None:
        self.selected_paths.clear()
        self.update_selection_ui()
        self.status.setText("Selezione annullata; nessun file modificato")

    def show_preview(self, path: Path) -> None:
        info = self.image_by_path.get(path)
        if info is None:
            return
        self.preview_path = path
        self.update_selection_ui()
        self.preview_name.setText(path.name)
        self.preview_details.setText(f"{info.width} × {info.height} · {pretty_bytes(info.bytes)}\n"
                                     f"{path}\n" +
                                     ("Selezionata per il cestino" if path in self.selected_paths
                                      else "Da conservare"))
        self.update_preview_image()

    def update_preview_image(self) -> None:
        if self.preview_path is None:
            return
        pixmap = QPixmap(str(self.preview_path))
        if pixmap.isNull():
            self.big_preview.setText("Anteprima non disponibile")
            return
        width = max(100, self.big_preview.width() - 16)
        height = max(100, self.big_preview.height() - 16)
        self.big_preview.setPixmap(pixmap.scaled(width, height,
                                                  Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self.update_preview_image)

    def update_stats(self) -> None:
        duplicate_count = sum(len(group) - 1 for group in self.groups)
        potential = sum(image.bytes for group in self.groups for image in group[1:])
        self.stat_images.setText(f"{len(self.images):,}".replace(",", "."))
        self.stat_duplicates.setText(str(duplicate_count))
        self.stat_space.setText(pretty_bytes(potential))

    @staticmethod
    def stat(layout: QHBoxLayout, title: str) -> QLabel:
        frame, column = box("stat")
        column.addWidget(lbl(title, "muted"))
        metric = lbl("0", "metric")
        column.addWidget(metric)
        layout.addWidget(frame, 1)
        return metric

    def auto_select(self) -> None:
        if self.mode_slider.value() != 2 or not self.groups:
            return
        saved_folders = self.settings.value("protected_folders", [], type=list)
        options = SelectionOptions(
            self.settings.value("prefer_resolution", True, type=bool),
            self.settings.value("prefer_file_size", True, type=bool),
            tuple(Path(path) for path in saved_folders),
        )
        proposal = propose_selection(self.groups, options)
        self.selected_paths = set(proposal.trash_paths)
        self.update_selection_ui()
        self.status.setText(f"Auto-Select: {len(self.selected_paths)} file selezionati · "
                            "controlla prima di spostare nel cestino")

    def configure_auto_select(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Criteri Auto-Select")
        dialog.setMinimumWidth(450)
        layout = QVBoxLayout(dialog)
        layout.addWidget(lbl("Quale copia vuoi conservare?", "section"))
        resolution = QCheckBox("Preferisci la risoluzione maggiore")
        resolution.setChecked(self.settings.value("prefer_resolution", True, type=bool))
        layout.addWidget(resolution)
        size = QCheckBox("A parità, preferisci il file più grande")
        size.setChecked(self.settings.value("prefer_file_size", True, type=bool))
        layout.addWidget(size)
        layout.addWidget(lbl("La dimensione del file non garantisce qualità migliore.", "muted"))
        layout.addWidget(lbl("Cartelle protette", "section"))
        protected = QListWidget()
        protected.setMinimumHeight(90)
        folders = [Path(p) for p in self.settings.value("protected_folders", [], type=list)]
        for folder in folders:
            protected.addItem(str(folder))
        layout.addWidget(protected)
        row = QHBoxLayout()
        add = QPushButton("Aggiungi")

        def add_folder() -> None:
            name = QFileDialog.getExistingDirectory(dialog, "Cartella protetta")
            if name and Path(name) not in folders:
                folders.append(Path(name))
                protected.addItem(name)

        add.clicked.connect(add_folder)
        row.addWidget(add)
        remove = QPushButton("Rimuovi")

        def remove_folder() -> None:
            index = protected.currentRow()
            if index >= 0:
                folders.pop(index)
                protected.takeItem(index)

        remove.clicked.connect(remove_folder)
        row.addWidget(remove)
        layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings.setValue("prefer_resolution", resolution.isChecked())
            self.settings.setValue("prefer_file_size", size.isChecked())
            self.settings.setValue("protected_folders", [str(path) for path in folders])
            self.status.setText("Criteri salvati. Premi Auto-Select per applicarli.")

    def trash_selected(self) -> None:
        targets = list(self.selected_paths)
        if not targets:
            QMessageBox.information(self, "Nessuna selezione", "Seleziona prima le immagini.")
            return
        if any(all(image.path in self.selected_paths for image in group)
               for group in self.groups):
            QMessageBox.warning(self, "Conserva un'immagine",
                                "Deve rimanere almeno un'immagine per gruppo.")
            return
        answer = QMessageBox.question(
            self, "Conferma cestino", f"Spostare {len(targets)} file nel cestino?\n"
            "Questa operazione non può essere annullata direttamente da VisiLens.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        moved: set[Path] = set()
        failures: list[str] = []
        for path in targets:
            try:
                send2trash(str(path))
                moved.add(path)
            except OSError as exc:
                failures.append(f"{path}: {exc}")
        self.images = [image for image in self.images if image.path not in moved]
        self.refresh_groups()
        self.status.setText(f"{len(moved)} file nel cestino · {len(failures)} errori")
        if failures:
            QMessageBox.warning(self, "File non spostati", "\n".join(failures[:10]))

    def closeEvent(self, event) -> None:
        if self.thread is not None:
            QMessageBox.information(self, "Scansione in corso",
                                    "Interrompi la scansione prima di chiudere.")
            event.ignore()
        else:
            event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("VisiLens")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
