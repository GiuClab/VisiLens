"""Qt desktop interface for VisiLens."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from send2trash import send2trash

from .core import ImageInfo, group_similar, scan


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
            images, errors = scan(self.folders, lambda n, total: self.progress.emit(n, total),
                                  lambda: self._cancelled)
            self.complete.emit(images, errors)
        except Exception as exc:  # noqa: BLE001 — report unexpected worker errors to GUI
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VisiLens — Visual Duplicate Finder")
        self.resize(1120, 740)
        self.folders: list[Path] = []
        self.images: list[ImageInfo] = []
        self.groups: list[list[ImageInfo]] = []
        self.thread: QThread | None = None
        self.worker: ScanWorker | None = None

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)
        add = QPushButton("+ Add folder")
        add.clicked.connect(self.add_folder)
        toolbar.addWidget(add)
        self.start_button = QPushButton("Scan")
        self.start_button.clicked.connect(self.start_scan)
        toolbar.addWidget(self.start_button)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_scan)
        toolbar.addWidget(self.cancel_button)
        toolbar.addWidget(QLabel("Similarity:"))
        self.mode = QComboBox()
        self.mode.addItems(["Strict", "Basic", "Loose"])
        self.mode.setCurrentText("Basic")
        self.mode.currentTextChanged.connect(self.refresh_groups)
        toolbar.addWidget(self.mode)
        toolbar.addStretch()

        splitter = QSplitter()
        layout.addWidget(splitter, 1)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Folders"))
        self.folder_list = QListWidget()
        left_layout.addWidget(self.folder_list, 1)
        remove = QPushButton("Remove selected folder")
        remove.clicked.connect(self.remove_folder)
        left_layout.addWidget(remove)
        left_layout.addWidget(QLabel("Similar image groups"))
        self.group_list = QListWidget()
        self.group_list.currentRowChanged.connect(self.show_group)
        left_layout.addWidget(self.group_list, 2)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        note = QLabel("Best resolution is suggested for keeping. Review every selection before trashing.")
        note.setWordWrap(True)
        right_layout.addWidget(note)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.preview = QWidget()
        self.preview_layout = QVBoxLayout(self.preview)
        self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.preview)
        right_layout.addWidget(scroll)
        self.trash_button = QPushButton("Move checked images to Trash…")
        self.trash_button.clicked.connect(self.trash_selected)
        right_layout.addWidget(self.trash_button)
        splitter.addWidget(right)
        splitter.setSizes([330, 790])

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.status = QLabel("Add one or more folders to begin.")
        layout.addWidget(self.status)
        self.checks: list[tuple[ImageInfo, object]] = []

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
        self.group_list.clear()
        self.show_group(-1)
        self.progress.setValue(0)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText("Scanning images…")
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
            self.status.setText("Stopping after current image…")

    @Slot(int, int)
    def update_progress(self, done: int, total: int) -> None:
        self.progress.setValue(round(100 * done / total) if total else 100)

    @Slot(object, object)
    def on_complete(self, images: list[ImageInfo], errors: list[str]) -> None:
        self.images = images
        self.refresh_groups()
        self.status.setText(f"{len(images)} images analyzed; {len(self.groups)} similar groups; "
                            f"{len(errors)} unreadable files.")
        if errors:
            QMessageBox.warning(self, "Unreadable files", "Some files were skipped:\n" +
                                "\n".join(errors[:10]))

    @Slot(str)
    def on_error(self, message: str) -> None:
        QMessageBox.critical(self, "Scan failed", message)
        self.status.setText("Scan failed.")

    @Slot()
    def on_thread_finished(self) -> None:
        self.thread = None
        self.worker = None
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def refresh_groups(self) -> None:
        self.groups = group_similar(self.images, self.mode.currentText())
        self.group_list.clear()
        for index, group in enumerate(self.groups, 1):
            self.group_list.addItem(f"Group {index} — {len(group)} images")
        if self.groups:
            self.group_list.setCurrentRow(0)
        else:
            self.show_group(-1)

    def show_group(self, row: int) -> None:
        from PySide6.QtWidgets import QCheckBox

        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.checks = []
        if row < 0 or row >= len(self.groups):
            return
        for index, image in enumerate(self.groups[row]):
            item = QWidget()
            item_layout = QHBoxLayout(item)
            thumb = QLabel()
            pixmap = QPixmap(str(image.path))
            if not pixmap.isNull():
                thumb.setPixmap(pixmap.scaled(180, 140, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation))
            thumb.setFixedSize(190, 150)
            item_layout.addWidget(thumb)
            details = QVBoxLayout()
            checkbox = QCheckBox("Move to Trash" if index else "Keep (recommended)")
            checkbox.setChecked(index > 0)
            details.addWidget(checkbox)
            label = QLabel(str(image.path))
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            details.addWidget(label)
            details.addWidget(QLabel(f"{image.width} × {image.height}  ·  {image.bytes / 1024:.0f} KB"))
            item_layout.addLayout(details, 1)
            self.preview_layout.addWidget(item)
            self.checks.append((image, checkbox))

    def trash_selected(self) -> None:
        targets = [image.path for image, checkbox in self.checks if checkbox.isChecked()]
        if not targets:
            return
        if len(targets) == len(self.checks):
            QMessageBox.warning(self, "Keep an image", "At least one image must remain in the group.")
            return
        response = QMessageBox.question(
            self, "Confirm move to Trash",
            f"Move {len(targets)} selected image(s) to the system Trash?\n"
            "Review your selections: the app cannot undo this action directly.",
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
        self.refresh_groups()
        self.status.setText(f"Moved {len(moved)} file(s) to Trash; {len(failures)} failures.")
        if failures:
            QMessageBox.warning(self, "Some files were not moved", "\n".join(failures[:10]))

    def closeEvent(self, event) -> None:
        if self.thread is not None:
            QMessageBox.information(self, "Scan active", "Cancel the scan and wait for it to stop.")
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
