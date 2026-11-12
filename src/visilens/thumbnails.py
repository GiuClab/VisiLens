"""Decode thumbnail images off the GUI thread.

Only QImage crosses worker boundaries. QPixmap/QIcon are created in the GUI thread.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal
from PySide6.QtGui import QImage, QImageReader
from PySide6.QtCore import QSize, Qt


class ThumbnailEvents(QObject):
    loaded = Signal(str, int, QImage)


class ThumbnailTask(QRunnable):
    def __init__(self, path: str, generation: int, events: ThumbnailEvents) -> None:
        super().__init__()
        self.path = path
        self.generation = generation
        self.events = events

    def run(self) -> None:
        reader = QImageReader(self.path)
        reader.setAutoTransform(True)
        dimensions = reader.size()
        if dimensions.isValid():
            reader.setScaledSize(dimensions.scaled(
                QSize(126, 106), Qt.AspectRatioMode.KeepAspectRatio
            ))
        image = reader.read()
        self.events.loaded.emit(self.path, self.generation, image)
