"""VisiLens desktop UI: folders on the left, groups in the middle, preview on the right."""

from __future__ import annotations

import base64
import html
import os
import subprocess
import sys
from pathlib import Path
from typing import ClassVar

from PySide6.QtCore import (
    QDir,
    QFileInfo,
    QObject,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSettings,
    QSize,
    QStandardPaths,
    Qt,
    QThread,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QDesktopServices,
    QIcon,
    QImageReader,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QComboBox,
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
from .i18n import LANGUAGES, ROWS, get_language, set_language, tr

STYLE = """
QMainWindow, QWidget#root { background: #f5f6fb; }
QWidget { font-family: 'Segoe UI', Arial; color: #242936; font-size: 12px; }
QFrame#panel, QFrame#stat, QFrame#group, QFrame#tile {
 background: white; border: 1px solid #dfe3ed; border-radius: 12px; }
QFrame#tile[active="true"] { border: 2px solid #3d61da; background: #f0f4ff; }
QFrame#tile[trash="true"] { border: 2px solid #cf353e; background: #fff0f1; }
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


def app_icon() -> QIcon:
    """Load the official icon, also from a PyInstaller bundle."""
    icon_file = Path(__file__).resolve().parent / "assets" / "icon.png.b64"
    try:
        bitmap = QPixmap()
        if bitmap.loadFromData(base64.b64decode(icon_file.read_text(encoding="ascii"))):
            return QIcon(bitmap)
    except (OSError, ValueError):
        pass
    return QIcon()


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


def fit_window_rect(saved: QRect | None, available: QRect) -> QRect:
    """Keep the restored window inside a screen's usable area, including the taskbar."""
    # Leave a little room for the non-client Windows frame and title bar.
    bounds = available.adjusted(12, 24, -12, -24)
    if saved is None or not saved.isValid():
        width = min(1450, max(1, bounds.width() - 24))
        height = min(900, max(1, bounds.height() - 24))
        rect = QRect(0, 0, width, height)
        rect.moveCenter(bounds.center())
        return rect
    width = min(max(saved.width(), min(1000, bounds.width())), bounds.width())
    height = min(max(saved.height(), min(580, bounds.height())), bounds.height())
    left = max(bounds.left(), min(saved.left(), bounds.right() - width + 1))
    top = max(bounds.top(), min(saved.top(), bounds.bottom() - height + 1))
    return QRect(left, top, width, height)


class StatIcon(QWidget):
    """Small vector icons, drawn at screen resolution with the app's palette."""

    COLORS: ClassVar[dict[str, tuple[str, str]]] = {
        "photo": ("#385ad0", "#e6edff"),
        "copies": ("#d44747", "#fbe7e9"),
        "storage": ("#1b9b5c", "#e4f4e9"),
    }

    def __init__(self, kind: str) -> None:
        super().__init__()
        self.kind = kind
        self.setFixedSize(62, 62)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        foreground, background = self.COLORS[self.kind]
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(background))
        painter.drawRoundedRect(QRectF(0, 0, 62, 62), 14, 14)
        pen = QPen(QColor(foreground))
        pen.setWidthF(2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.kind == "photo":
            painter.drawRoundedRect(QRectF(17, 19, 29, 25), 4, 4)
            painter.drawEllipse(QRectF(36, 24, 4, 4))
            hills = QPainterPath(QPointF(19, 41))
            hills.lineTo(27, 32)
            hills.lineTo(32, 37)
            hills.lineTo(37, 33)
            hills.lineTo(44, 41)
            painter.drawPath(hills)
        elif self.kind == "copies":
            painter.drawRoundedRect(QRectF(16, 16, 25, 25), 4, 4)
            painter.drawRoundedRect(QRectF(23, 23, 25, 25), 4, 4)
        else:
            painter.drawEllipse(QRectF(18, 17, 26, 9))
            painter.drawLine(QPointF(18, 22), QPointF(18, 41))
            painter.drawLine(QPointF(44, 22), QPointF(44, 41))
            painter.drawArc(QRectF(18, 35, 26, 10), 180 * 16, 180 * 16)
            painter.drawArc(QRectF(18, 26, 26, 9), 180 * 16, 180 * 16)
        painter.end()


class ScanWorker(QObject):
    progress = Signal(int, int)
    complete = Signal(object, object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, folders: list[Path], include_hidden: bool = False) -> None:
        super().__init__()
        self.folders = folders
        self.include_hidden = include_hidden
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        try:
            base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".cache")))
            cache = base / "VisiLens" / "scan-cache.sqlite3"
            images, errors = scan(self.folders, lambda n, total: self.progress.emit(n, total),
                                  lambda: self._cancelled, cache_path=cache,
                                  include_hidden=self.include_hidden)
            self.complete.emit(images, errors)
        except Exception as exc:  # noqa: BLE001 — deliver worker errors to the interface
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class GroupWorker(QObject):
    """Run the existing matching algorithm away from the Qt interface thread."""

    complete = Signal(int, str, object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, images: list[ImageInfo], mode: str, generation: int) -> None:
        super().__init__()
        self.images = images
        self.mode = mode
        self.generation = generation

    @Slot()
    def run(self) -> None:
        try:
            groups = group_similar(self.images, self.mode)
            self.images = []
            self.complete.emit(self.generation, self.mode, groups)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        finally:
            self.images = []
            self.finished.emit()


class ImageTile(QFrame):
    def __init__(self, image: ImageInfo, callback) -> None:
        super().__init__()
        self.image = image
        self.setObjectName("tile")
        self.setProperty("active", False)
        self.setProperty("trash", False)
        self.setFixedWidth(142)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)
        self.button = QPushButton()
        self.button.setObjectName("thumb")
        self.button.setFixedSize(130, 110)
        self.button.setToolTip(f"{image.path}\nClicca per vedere l'anteprima")
        self.button.setText("Anteprima…")
        self.thumbnail_loaded = False
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
        if self.property("active") != (active and not checked) or self.property("trash") != checked:
            self.setProperty("active", active and not checked)
            self.setProperty("trash", checked)
            self.style().unpolish(self)
            self.style().polish(self)

    def load_thumbnail(self) -> None:
        if self.thumbnail_loaded:
            return
        self.thumbnail_loaded = True
        reader = QImageReader(str(self.image.path))
        reader.setAutoTransform(True)
        dimensions = reader.size()
        if dimensions.isValid():
            reader.setScaledSize(dimensions.scaled(QSize(126, 106),
                                                    Qt.AspectRatioMode.KeepAspectRatio))
        image = reader.read()
        if image.isNull():
            self.button.setText(tr("Anteprima non disponibile"))
        else:
            self.button.setIcon(QIcon(QPixmap.fromImage(image)))
            self.button.setIconSize(QSize(126, 106))
            self.button.setText("")


class MainWindow(QMainWindow):
    MODES = ("Loose", "Basic", "Strict")
    MODE_COLORS = ("#385ad0", "#1baf71", "#d44747")

    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()
        self.setWindowTitle("VisiLens v0.7.0 — © 2026 GiuClab")
        self.setWindowIcon(app_icon())
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else QRect(0, 0, 1366, 768)
        self.setMinimumSize(min(1000, max(1, available.width() - 48)),
                            min(580, max(1, available.height() - 64)))
        self.settings = settings if settings is not None else QSettings("GiuClab", "VisiLens")
        initial_language = self.settings.value("ui/language", "en", type=str)
        set_language(initial_language if initial_language in LANGUAGES else "en")
        self.apply_theme(self.settings.value("ui/theme", "system", type=str))
        self.folders: list[Path] = []
        self.images: list[ImageInfo] = []
        self.groups: list[list[ImageInfo]] = []
        self.selected_paths: set[Path] = set()
        self.tiles: dict[Path, ImageTile] = {}
        self.group_labels: list[QLabel] = []
        self.thread: QThread | None = None
        self.worker: ScanWorker | None = None
        self.group_thread: QThread | None = None
        self.group_worker: GroupWorker | None = None
        # Retain Python wrappers until the window closes; Qt deletes the C++
        # QObjects after their threads finish. Dropping wrappers immediately
        # during finished signals can race with queued worker events.
        self._group_jobs: list[tuple[QThread, GroupWorker]] = []
        self.group_cache: dict[str, list[list[ImageInfo]]] = {}
        self.image_generation = 0
        self.render_generation = 0
        self.render_iterator = None
        self._render_grid: QGridLayout | None = None
        self.group_timer = QTimer(self)
        self.group_timer.setSingleShot(True)
        self.group_timer.setInterval(180)
        self.group_timer.timeout.connect(self.request_groups)
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
        self.stat_images = self.stat(stats, "Immagini analizzate", "photo")
        self.stat_duplicates = self.stat(stats, "Duplicati trovati", "copies")
        self.stat_space = self.stat(stats, "Spazio recuperabile", "storage")
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
        self.groups_scroll.verticalScrollBar().valueChanged.connect(self.load_visible_thumbnails)
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
        self.apply_theme(self.settings.value("ui/theme", "system", type=str))
        right_layout.addWidget(self.big_preview, 1)
        self.preview_name = lbl("Nessuna immagine selezionata", "section")
        self.preview_name.setWordWrap(True)
        right_layout.addWidget(self.preview_name)
        self.preview_link = QLabel()
        self.preview_link.setWordWrap(True)
        self.preview_link.setTextFormat(Qt.TextFormat.RichText)
        self.preview_link.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction)
        self.preview_link.setOpenExternalLinks(False)
        self.preview_link.linkActivated.connect(self.reveal_preview_file)
        self.preview_link.setToolTip("Apri la cartella in Esplora file e seleziona l'immagine")
        right_layout.addWidget(self.preview_link)
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
        self.retranslate_interface()

    def create_menus(self) -> None:
        self.menuBar().setNativeMenuBar(False)
        self.file_menu = self.menuBar().addMenu("File")
        self.edit_menu = self.menuBar().addMenu("Modifica")
        self.options_menu = self.menuBar().addMenu("Opzioni")
        self.help_menu = self.menuBar().addMenu("Aiuto")
        self._actions = []

        def add(menu, caption, callback, shortcut=None):
            action = QAction(tr(caption), self)
            action.setProperty("source_caption", caption)
            action.triggered.connect(callback)
            if shortcut:
                action.setShortcut(shortcut)
            menu.addAction(action)
            self._actions.append(action)
            return action

        add(self.file_menu, "Aggiungi cartella…", self.add_folder, "Ctrl+O")
        add(self.file_menu, "Avvia scansione", self.start_scan, "Ctrl+R")
        add(self.file_menu, "Interrompi", self.cancel_scan)
        self.file_menu.addSeparator()
        add(self.file_menu, "Esci", self.close)

        add(self.edit_menu, "Auto-Select", self.auto_select)
        add(self.edit_menu, "Criteri Auto-Select", self.configure_auto_select)
        add(self.edit_menu, "Annulla selezione", self.clear_selection)

        self.language_menu = self.options_menu.addMenu(tr("Lingua"))
        self.language_actions = {}
        for code, title in LANGUAGES.items():
            action = QAction(title, self)
            action.setCheckable(True)
            action.setChecked(code == get_language())
            action.triggered.connect(lambda checked=False, code=code: self.change_language(code))
            self.language_menu.addAction(action)
            self.language_actions[code] = action

        self.theme_menu = self.options_menu.addMenu(tr("Tema"))
        self.theme_actions = {}
        for code, title in (("system", "Segui Windows"), ("light", "Chiaro"),
                            ("dark", "Scuro")):
            action = add(self.theme_menu, title, lambda checked=False, code=code: self.change_theme(code))
            action.setCheckable(True)
            action.setChecked(code == self.settings.value("ui/theme", "system"))
            self.theme_actions[code] = action
        self.options_menu.addSeparator()
        self.hidden_action = add(self.options_menu, "Includi file e cartelle nascosti",
                                 lambda checked=False: self.settings.setValue("include_hidden", checked))
        self.hidden_action.setCheckable(True)
        self.hidden_action.setChecked(self.settings.value("include_hidden", False, type=bool))

        add(self.help_menu, "Informazioni su VisiLens", self.show_about)
        add(self.help_menu, "Progetto su GitHub", lambda: QDesktopServices.openUrl(
            QUrl("https://github.com/GiuClab/VisiLens")))
        self.support_button = QPushButton("❤️ Support me")
        self.support_button.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://ko-fi.com/giuclab/tip")))
        self.menuBar().setCornerWidget(self.support_button, Qt.Corner.TopRightCorner)

    def show_about(self) -> None:
        QMessageBox.about(
            self, tr("Informazioni su VisiLens"),
            "<h2>VisiLens v0.7.0</h2>"
            "<p>Made with <span style='color:#d44747'>♥</span> by GiuClab</p>"
            "<p>© 2026 GiuClab · MIT License</p>"
            "<p><a href='https://github.com/GiuClab/VisiLens'>GitHub</a> · "
            "<a href='https://ko-fi.com/giuclab/tip'>Ko-fi</a></p>",
        )

    def change_language(self, code: str) -> None:
        set_language(code)
        self.settings.setValue("ui/language", code)
        for language, action in self.language_actions.items():
            action.setChecked(language == code)
        self.retranslate_interface()

    def change_theme(self, value: str) -> None:
        if value not in ("system", "light", "dark"):
            return
        self.settings.setValue("ui/theme", value)
        self.apply_theme(value)
        for theme, action in self.theme_actions.items():
            action.setChecked(theme == value)

    def apply_theme(self, value: str) -> None:
        if value == "system":
            value = ("dark" if QApplication.palette().window().color().lightness() < 128
                     else "light")
        sheet = STYLE
        if value == "dark":
            colors = {"#f5f6fb": "#171c2c", "#242936": "#e8edf8",
                      "background: white": "background: #252d40",
                      "#dfe3ed": "#3b455a", "#d6ddec": "#3b455a",
                      "#e0e4ee": "#3b455a", "#677082": "#b3bdd1",
                      "#edf2ff": "#334362", "#eef1f7": "#303a50",
                      "#e1e5f0": "#35415a", "#d4dbea": "#4d5b78",
                      "#f0f4ff": "#263f6f", "#fff0f1": "#503039",
                      "#fff5f5": "#503039", "#dbe5ff": "#34486a",
                      "#2445a1": "#b2c8ff"}
            for old, new in colors.items():
                sheet = sheet.replace(old, new)
        self.setStyleSheet(sheet)
        if hasattr(self, "big_preview"):
            self.big_preview.setStyleSheet(
                "background: #303a50; border-radius: 10px;" if value == "dark"
                else "background: #eef1f7; border-radius: 10px;")

    def retranslate_interface(self) -> None:
        """Translate static text while preserving dynamic values and file paths."""
        for menu, original in ((self.file_menu, "File"), (self.edit_menu, "Modifica"),
                               (self.options_menu, "Opzioni"), (self.help_menu, "Aiuto"),
                               (self.language_menu, "Lingua"), (self.theme_menu, "Tema")):
            menu.setTitle(tr(original))
        for action in self._actions:
            action.setText(tr(action.property("source_caption")))
        for widget in self.findChildren(QWidget):
            if not isinstance(widget, (QLabel, QPushButton, QCheckBox)):
                continue
            source = widget.property("source_caption")
            if source is None:
                source = widget.text()
                if source not in ROWS:
                    continue
                widget.setProperty("source_caption", source)
            widget.setText(tr(source))
        self.support_button.setText("❤️ " + tr("Support me"))
        mode = self.MODES[self.mode_slider.value()]
        self.filter_name.setText(tr({"Strict": "Strict — confronto rigoroso",
                                     "Basic": "Basic — somiglianza equilibrata",
                                     "Loose": "Loose — confronto flessibile"}[mode]))

    def prompt_language_first_run(self) -> None:
        if self.settings.value("ui/language_chosen", False, type=bool):
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Welcome to VisiLens")
        dialog.setMinimumWidth(400)
        layout = QVBoxLayout(dialog)
        message = QLabel("Welcome to VisiLens! Choose your preferred language.")
        message.setWordWrap(True)
        layout.addWidget(message)
        language = QComboBox()
        for code, name in LANGUAGES.items():
            language.addItem(name, code)
        language.setCurrentIndex(list(LANGUAGES).index(get_language()))
        layout.addWidget(language)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.change_language(language.currentData())
            self.settings.setValue("ui/language_chosen", True)

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
        self.filter_name.setText(tr({"Strict": "Strict — confronto rigoroso",
                                     "Basic": "Basic — somiglianza equilibrata",
                                     "Loose": "Loose — confronto flessibile"}[mode]))
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
            self.status.setText(tr("Seleziona almeno una cartella."))
            return
        self.image_generation += 1
        self.group_cache.clear()
        self.group_timer.stop()
        self.images, self.groups = [], []
        self.selected_paths.clear()
        self.render_groups()
        self.progress.setValue(0)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText(tr("Scansione in corso…"))
        self.thread = QThread(self)
        self.worker = ScanWorker(self.folders.copy(), self.hidden_action.isChecked())
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
            self.status.setText(tr("Arresto dopo l'immagine corrente…"))

    @Slot(int, int)
    def update_progress(self, done: int, total: int) -> None:
        self.progress.setValue(round(done * 100 / total) if total else 100)

    @Slot(object, object)
    def on_complete(self, images: list[ImageInfo], errors: list[str]) -> None:
        self.images = images
        self.image_by_path = {image.path: image for image in images}
        self.refresh_groups()
        self.status.setText(f"{len(images)} immagini analizzate · "
                            f"confronto in corso · {len(errors)} errori")
        if errors:
            QMessageBox.warning(self, "File ignorati", "\n".join(errors[:10]))

    @Slot(str)
    def on_error(self, error: str) -> None:
        QMessageBox.critical(self, "Errore durante la scansione", error)
        self.status.setText(tr("Scansione non riuscita"))

    @Slot()
    def on_thread_finished(self) -> None:
        self.thread = None
        self.worker = None
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def refresh_groups(self) -> None:
        self.selected_paths.clear()
        self.image_by_path = {image.path: image for image in self.images}
        self.groups = []
        self.render_groups()
        self.group_timer.start()

    @Slot()
    def request_groups(self) -> None:
        if not self.images:
            return
        mode = self.MODES[self.mode_slider.value()]
        if mode in self.group_cache:
            self.apply_groups(self.group_cache[mode])
            return
        if self.group_thread is not None:
            self.status.setText(f"Attendo il calcolo in corso · prossimo livello: {mode}")
            return
        self.status.setText(f"Calcolo duplicati {mode} in background…")
        thread = QThread(self)
        worker = GroupWorker(self.images.copy(), mode, self.image_generation)
        self.group_thread = thread
        self.group_worker = worker
        self._group_jobs.append((thread, worker))
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.complete.connect(self.on_group_complete)
        worker.failed.connect(lambda error, g=self.image_generation, m=mode:
                              self.on_group_error(g, m, error))
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self.on_group_finished)
        thread.start()

    @Slot(int, str, object)
    def on_group_complete(self, generation: int, mode: str,
                          groups: list[list[ImageInfo]]) -> None:
        if generation != self.image_generation:
            return
        self.group_cache[mode] = groups
        if mode == self.MODES[self.mode_slider.value()]:
            self.apply_groups(groups)

    def on_group_error(self, generation: int, mode: str, error: str) -> None:
        if generation == self.image_generation:
            self.group_cache[mode] = []
            self.status.setText(f"Errore confronto {mode}: {error}")

    @Slot()
    def on_group_finished(self) -> None:
        self.group_thread = None
        self.group_worker = None
        mode = self.MODES[self.mode_slider.value()]
        if self.images and mode not in self.group_cache:
            QTimer.singleShot(0, self.request_groups)

    def apply_groups(self, groups: list[list[ImageInfo]]) -> None:
        self.groups = groups
        self.selected_paths.clear()
        self.render_groups()
        self.status.setText(f"{len(self.images)} immagini · {len(groups)} gruppi ({self.MODES[self.mode_slider.value()]})")

    def render_groups(self) -> None:
        self.render_generation += 1
        token = self.render_generation
        while self.groups_layout.count():
            item = self.groups_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.tiles.clear()
        self.group_labels.clear()
        self.render_iterator = ((number, group, index, info)
                                for number, group in enumerate(self.groups, 1)
                                for index, info in enumerate(group))
        self.auto_button.setEnabled(bool(self.groups) and self.mode_slider.value() == 2)
        self.trash_button.setEnabled(not self.groups)
        self.update_stats()
        self.update_selection_ui()
        if self.groups:
            self.show_preview(self.groups[0][0].path)
            QTimer.singleShot(0, lambda: self.render_group_batch(token))
        else:
            self.preview_path = None
            self.big_preview.clear()
            self.preview_name.setText(tr("Nessuna immagine selezionata"))
            self.preview_link.clear()
            self.preview_details.setText("")

    def render_group_batch(self, token: int) -> None:
        if token != self.render_generation:
            return
        for _ in range(20):
            try:
                number, group, index, info = next(self.render_iterator)
            except StopIteration:
                self.render_iterator = None
                self.trash_button.setEnabled(True)
                self.load_visible_thumbnails()
                return
            if index == 0:
                frame, body = box("group")
                heading = QHBoxLayout()
                heading.addWidget(lbl(f"Gruppo {number} · {len(group)} immagini", "section"), 1)
                selected = lbl("", "muted")
                count = sum(info.path in self.selected_paths for info in group)
                selected.setText(f"{count} per il cestino" if count else "")
                heading.addWidget(selected)
                self.group_labels.append(selected)
                body.addLayout(heading)
                grid = QGridLayout()
                grid.setSpacing(8)
                body.addLayout(grid)
                self._render_grid = grid
                self.groups_layout.addWidget(frame)
            tile = ImageTile(info, self.thumbnail_toggled)
            self.tiles[info.path] = tile
            tile.set_state(info.path in self.selected_paths, info.path == self.preview_path)
            tile.button.clicked.connect(lambda _checked=False, path=info.path:
                                        self.show_preview(path))
            self._render_grid.addWidget(tile, index // 2, index % 2,
                                        alignment=Qt.AlignmentFlag.AlignTop |
                                        Qt.AlignmentFlag.AlignLeft)
        QTimer.singleShot(5, lambda: self.render_group_batch(token))
        QTimer.singleShot(0, self.load_visible_thumbnails)

    def load_visible_thumbnails(self) -> None:
        viewport = self.groups_scroll.viewport()
        loaded = 0
        for tile in self.tiles.values():
            if tile.thumbnail_loaded:
                continue
            y = tile.mapTo(viewport, QPoint(0, 0)).y()
            if -180 <= y <= viewport.height() + 180:
                tile.load_thumbnail()
                loaded += 1
                if loaded >= 12:
                    QTimer.singleShot(0, self.load_visible_thumbnails)
                    break

    def thumbnail_toggled(self, path: Path, checked: bool) -> None:
        if checked:
            self.selected_paths.add(path)
        else:
            self.selected_paths.discard(path)
        self.update_selection_ui()
        if self.preview_path == path:
            self.update_preview_details()

    def update_selection_ui(self) -> None:
        for path, tile in self.tiles.items():
            tile.set_state(path in self.selected_paths, path == self.preview_path)
        for group, badge in zip(self.groups, self.group_labels):
            count = sum(info.path in self.selected_paths for info in group)
            badge.setText(f"{count} per il cestino" if count else "")
        count = len(self.selected_paths)
        self.selection_info.setText(f"{count} file selezionati per il cestino" if count != 1
                                    else "1 file selezionato per il cestino")
        if self.preview_path is not None:
            self.update_preview_details()

    def clear_selection(self) -> None:
        self.selected_paths.clear()
        self.update_selection_ui()
        self.status.setText(tr("Selezione annullata; nessun file modificato"))

    def show_preview(self, path: Path) -> None:
        info = self.image_by_path.get(path)
        if info is None:
            return
        self.preview_path = path
        self.update_selection_ui()
        self.preview_name.setText(path.name)
        self.preview_link.setText(
            f'<a href="#" style="color:#385ad0;text-decoration:underline;">'
            f'{html.escape(str(path))}</a>')
        self.update_preview_details()
        self.update_preview_image()

    def update_preview_details(self) -> None:
        info = self.image_by_path.get(self.preview_path)
        if info is not None:
            self.preview_details.setText(
                f"{info.width} × {info.height} · {pretty_bytes(info.bytes)}\n" +
                ("Selezionata per il cestino" if info.path in self.selected_paths
                 else "Da conservare"))

    def reveal_preview_file(self, _link: str = "") -> None:
        if self.preview_path is None:
            return
        if sys.platform == "win32":
            try:
                subprocess.Popen(["explorer.exe", "/select,", str(self.preview_path)])
            except OSError as exc:
                QMessageBox.warning(self, "Esplora file", str(exc))
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.preview_path.parent)))

    def update_preview_image(self) -> None:
        if self.preview_path is None:
            return
        width = max(100, self.big_preview.width() - 16)
        height = max(100, self.big_preview.height() - 16)
        reader = QImageReader(str(self.preview_path))
        reader.setAutoTransform(True)
        dimensions = reader.size()
        if dimensions.isValid():
            reader.setScaledSize(dimensions.scaled(QSize(width, height),
                                                   Qt.AspectRatioMode.KeepAspectRatio))
        image = reader.read()
        if image.isNull():
            self.big_preview.setText("Anteprima non disponibile")
            return
        pixmap = QPixmap.fromImage(image)
        self.big_preview.setPixmap(pixmap.scaled(width, height,
                                                  Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self.update_preview_image)
        QTimer.singleShot(0, self.load_visible_thumbnails)

    def update_stats(self) -> None:
        duplicate_count = sum(len(group) - 1 for group in self.groups)
        potential = sum(image.bytes for group in self.groups for image in group[1:])
        self.stat_images.setText(f"{len(self.images):,}".replace(",", "."))
        self.stat_duplicates.setText(str(duplicate_count))
        self.stat_space.setText(pretty_bytes(potential))

    @staticmethod
    def stat(layout: QHBoxLayout, title: str, icon: str) -> QLabel:
        frame = QFrame()
        frame.setObjectName("stat")
        row = QHBoxLayout(frame)
        row.setContentsMargins(12, 12, 12, 12)
        row.setSpacing(12)
        row.addWidget(StatIcon(icon))
        column = QVBoxLayout()
        column.setSpacing(2)
        column.addWidget(lbl(title))
        metric = lbl("0", "metric")
        column.addWidget(metric)
        row.addLayout(column, 1)
        layout.addWidget(frame, 1)
        return metric

    def open_initial_window(self) -> None:
        """First launch is maximized; later launches restore the user's preference."""
        saved = self.settings.value("window/normal_geometry")
        rect = saved if isinstance(saved, QRect) and saved.isValid() else None
        screen = QApplication.screenAt(rect.center()) if rect is not None else None
        screen = screen or QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else QRect(0, 0, 1366, 768)
        self.setGeometry(fit_window_rect(rect, available))
        if self.settings.value("window/maximized", True, type=bool):
            self.showMaximized()
        else:
            self.show()

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
        dialog.setWindowTitle(tr("Criteri Auto-Select"))
        dialog.setMinimumWidth(450)
        layout = QVBoxLayout(dialog)
        layout.addWidget(lbl(tr("Quale copia vuoi conservare?"), "section"))
        resolution = QCheckBox(tr("Preferisci la risoluzione maggiore"))
        resolution.setChecked(self.settings.value("prefer_resolution", True, type=bool))
        layout.addWidget(resolution)
        size = QCheckBox(tr("A parità, preferisci il file più grande"))
        size.setChecked(self.settings.value("prefer_file_size", True, type=bool))
        layout.addWidget(size)
        layout.addWidget(lbl(tr("La dimensione del file non garantisce qualità migliore."), "muted"))
        layout.addWidget(lbl(tr("Cartelle protette"), "section"))
        protected = QListWidget()
        protected.setMinimumHeight(90)
        folders = [Path(p) for p in self.settings.value("protected_folders", [], type=list)]
        for folder in folders:
            protected.addItem(str(folder))
        layout.addWidget(protected)
        row = QHBoxLayout()
        add = QPushButton(tr("Aggiungi"))

        def add_folder() -> None:
            name = QFileDialog.getExistingDirectory(dialog, "Cartella protetta")
            if name and Path(name) not in folders:
                folders.append(Path(name))
                protected.addItem(name)

        add.clicked.connect(add_folder)
        row.addWidget(add)
        remove = QPushButton(tr("Rimuovi"))

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
            self.status.setText(tr("Criteri salvati. Premi Auto-Select per applicarli."))

    def trash_selected(self) -> None:
        targets = list(self.selected_paths)
        if not targets:
            QMessageBox.information(self, tr("Nessuna selezione"), tr("Seleziona prima le immagini."))
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
        self.image_generation += 1
        self.group_cache.clear()
        self.refresh_groups()
        self.status.setText(f"{len(moved)} file nel cestino · {len(failures)} errori")
        if failures:
            QMessageBox.warning(self, "File non spostati", "\n".join(failures[:10]))

    def closeEvent(self, event) -> None:
        if self.thread is not None or self.group_thread is not None:
            QMessageBox.information(self, tr("Scansione in corso"),
                                    "Attendi il completamento dell'elaborazione prima di chiudere.")
            event.ignore()
        else:
            if self.groups and not self.confirm_close():
                event.ignore()
                return
            geometry = self.normalGeometry()
            if geometry.isValid():
                self.settings.setValue("window/normal_geometry", geometry)
            self.settings.setValue("window/maximized", self.isMaximized())
            event.accept()

    def confirm_close(self) -> bool:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setWindowTitle(tr("Conferma chiusura"))
        dialog.setText(tr("Vuoi davvero chiudere VisiLens?"))
        dialog.setInformativeText(tr(
            "I gruppi trovati e le selezioni correnti non saranno più disponibili "
            "alla prossima apertura. Nessuna immagine verrà eliminata."))
        close_button = dialog.addButton(tr("Chiudi"), QMessageBox.ButtonRole.AcceptRole)
        cancel_button = dialog.addButton(tr("Annulla"), QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(cancel_button)
        dialog.exec()
        return dialog.clickedButton() is close_button


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("VisiLens")
    app.setWindowIcon(app_icon())
    window = MainWindow()
    window.open_initial_window()
    QTimer.singleShot(0, window.prompt_language_first_run)
    sys.exit(app.exec())
