"""About VisiLens dialog with non-blocking GitHub release checks."""

from __future__ import annotations

import json
import re

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .i18n import tr

RELEASES_URL = "https://api.github.com/repos/GiuClab/VisiLens/releases/latest"
PROJECT_URL = "https://github.com/GiuClab/VisiLens"
DONATION_URL = "https://ko-fi.com/giuclab/tip"

BLUE = "#385ad0"
GREEN = "#16875c"
RED = "#c93745"


def version_tuple(version: str) -> tuple[int, ...]:
    """Parse release versions such as v0.7.1, rejecting non-semantic tags."""
    match = re.fullmatch(r"v?(\d+(?:\.\d+){1,3})", version.strip())
    if match is None:
        raise ValueError("Invalid release version")
    parts = tuple(int(part) for part in match.group(1).split("."))
    return parts + (0,) * (4 - len(parts))


def assess_release(payload: bytes, current: str = __version__) -> tuple[str, str, str]:
    """Classify a stable GitHub release without blindly trusting its URL."""
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Invalid GitHub response")
    if data.get("draft") or data.get("prerelease"):
        raise ValueError("Not a stable release")
    latest = data.get("tag_name")
    url = data.get("html_url")
    if not isinstance(latest, str) or not isinstance(url, str):
        raise ValueError("Incomplete release data")
    if not url.startswith(PROJECT_URL + "/releases/tag/"):
        raise ValueError("Unexpected release URL")
    state = "available" if version_tuple(latest) > version_tuple(current) else "current"
    return state, latest, url


class AboutDialog(QDialog):
    """A regular resizable QWidget dialog, not QMessageBox.about()."""

    def __init__(self, parent: QWidget | None = None, icon=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Informazioni su VisiLens"))
        if icon is not None:
            self.setWindowIcon(icon)
        self.resize(800, 490)
        self.setMinimumSize(680, 450)
        self.setStyleSheet("""
            QDialog { background: #f5f6fb; color: #242936; }
            QFrame#aboutCard { background: white; border: 1px solid #dfe3ed;
                border-radius: 13px; }
            QLabel { color: #242936; font-size: 12px; }
            QLabel#aboutTitle { font-size: 26px; font-weight: 700; }
            QLabel#aboutSection { font-size: 15px; font-weight: 700; }
            QLabel#aboutMuted { color: #677082; }
            QPushButton { padding: 9px 16px; border-radius: 9px;
                background: #fff; border: 1px solid #d6ddec; }
            QPushButton#aboutPrimary { background: #385ad0; color: white;
                font-weight: 700; border: none; }
            QPushButton#aboutPrimary:hover { background: #2d49ab; }
            QPushButton#aboutDonation { background: #e9f0ff; color: #2348ad;
                border: 1px solid #abc2f5; font-weight: 700; }
        """)
        self.network = QNetworkAccessManager(self)
        self.pending = None
        self.release_url = None

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(13)

        title = QLabel(tr("Informazioni su VisiLens"))
        title.setObjectName("aboutTitle")
        root.addWidget(title)
        subtitle = QLabel(tr("Versione, progetto e modi per supportare lo sviluppo"))
        subtitle.setObjectName("aboutMuted")
        root.addWidget(subtitle)

        hero = self.card()
        hero_row = QHBoxLayout(hero)
        hero_row.setContentsMargins(18, 18, 18, 18)
        icon_label = QLabel()
        icon_label.setFixedSize(80, 80)
        if icon is not None:
            icon_label.setPixmap(icon.pixmap(80, 80))
        hero_row.addWidget(icon_label)
        info = QVBoxLayout()
        product = QLabel(f"VisiLens v{__version__}")
        product.setObjectName("aboutTitle")
        info.addWidget(product)
        info.addWidget(QLabel("Windows 10/11 · x64"))
        platforms = QLabel(tr("Per macOS e Linux sono previste versioni future."))
        platforms.setWordWrap(True)
        platforms.setObjectName("aboutMuted")
        info.addWidget(platforms)
        info.addWidget(QLabel("© 2026 GiuClab · MIT License"))
        signature = QLabel("Made with <span style='color:#d44747'>♥</span> by GiuClab")
        info.addWidget(signature)
        hero_row.addLayout(info, 1)
        root.addWidget(hero)

        updates = self.card()
        u = QVBoxLayout(updates)
        u.setContentsMargins(18, 14, 18, 14)
        u.addWidget(self.section(tr("Aggiornamenti")))
        u.addWidget(QLabel(tr("Verifica la disponibilità di una nuova release ufficiale.")))
        controls = QHBoxLayout()
        self.check_button = QPushButton(tr("Controlla aggiornamenti"))
        self.check_button.setObjectName("aboutPrimary")
        self.check_button.clicked.connect(self.check_updates)
        controls.addWidget(self.check_button)
        self.download_button = QPushButton(tr("Scarica aggiornamento"))
        self.download_button.setVisible(False)
        self.download_button.clicked.connect(self.open_release)
        controls.addWidget(self.download_button)
        controls.addStretch()
        u.addLayout(controls)
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("aboutMuted")
        u.addWidget(self.status_label)
        root.addWidget(updates)

        links = QHBoxLayout()
        links.setSpacing(12)
        git = self.card()
        g = QVBoxLayout(git)
        g.setContentsMargins(18, 14, 18, 14)
        g.addWidget(self.section("GitHub"))
        desc = QLabel(tr("Codice sorgente, segnalazioni e contributi."))
        desc.setWordWrap(True)
        g.addWidget(desc)
        github_button = QPushButton(tr("Apri GitHub"))
        github_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(PROJECT_URL)))
        g.addWidget(github_button)
        links.addWidget(git, 1)

        support = self.card()
        d = QVBoxLayout(support)
        d.setContentsMargins(18, 14, 18, 14)
        d.addWidget(self.section(tr("Supporta il progetto")))
        desc = QLabel(tr(
            "VisiLens è gratuito e open source. Un contributo aiuta a mantenerlo e migliorarlo."
        ))
        desc.setWordWrap(True)
        d.addWidget(desc)
        donate = QPushButton("♥ Ko-fi")
        donate.setObjectName("aboutDonation")
        donate.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DONATION_URL)))
        d.addWidget(donate)
        links.addWidget(support, 1)
        root.addLayout(links)

        bottom = QHBoxLayout()
        bottom.addStretch()
        close = QPushButton(tr("Chiudi"))
        close.clicked.connect(self.accept)
        bottom.addWidget(close)
        root.addLayout(bottom)

    @staticmethod
    def card() -> QFrame:
        frame = QFrame()
        frame.setObjectName("aboutCard")
        return frame

    @staticmethod
    def section(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("aboutSection")
        return label

    def set_status(self, message: str, color: str) -> None:
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: 600;")

    def check_updates(self) -> None:
        if self.pending is not None:
            return
        self.download_button.setVisible(False)
        self.release_url = None
        self.check_button.setEnabled(False)
        self.set_status(tr("Controllo aggiornamenti in corso…"), BLUE)
        request = QNetworkRequest(QUrl(RELEASES_URL))
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setRawHeader(b"User-Agent", b"VisiLens-update-checker")
        request.setTransferTimeout(10000)
        self.pending = self.network.get(request)
        self.pending.finished.connect(self.on_check_finished)

    def on_check_finished(self) -> None:
        reply = self.pending
        self.pending = None
        self.check_button.setEnabled(True)
        if reply is None:
            return
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                raise ValueError(reply.errorString())
            if reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) != 200:
                raise ValueError("GitHub did not return a stable release")
            state, latest, url = assess_release(bytes(reply.readAll()))
            if state == "available":
                self.release_url = url
                self.download_button.setVisible(True)
                self.set_status(
                    tr("Nuova versione disponibile: {version}").format(version=latest), GREEN
                )
            else:
                self.set_status(tr("VisiLens è aggiornato."), GREEN)
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            self.set_status(tr("Impossibile verificare gli aggiornamenti. Riprova."), RED)
        finally:
            reply.deleteLater()

    def open_release(self) -> None:
        if self.release_url:
            QDesktopServices.openUrl(QUrl(self.release_url))

    def reject(self) -> None:
        if self.pending is not None:
            self.pending.abort()
        super().reject()
