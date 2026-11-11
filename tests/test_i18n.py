"""UI regression checks for 0.7.0 first-run language and branding."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from visilens.app import MainWindow
from visilens.desktop import app_icon
from visilens.i18n import LANGUAGES, get_language, set_language, tr


def test_translation_catalog() -> None:
    assert list(LANGUAGES) == ["en", "it", "de", "fr"]
    set_language("en")
    assert tr("Opzioni") == "Options"
    set_language("de")
    assert tr("Opzioni") == "Optionen"
    set_language("fr")
    assert tr("Opzioni") == "Options"
    set_language("it")
    assert tr("Opzioni") == "Opzioni"


def test_english_default_menu_language_and_theme(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    settings = QSettings(str(tmp_path / "new-user.ini"), QSettings.Format.IniFormat)
    window = MainWindow(settings=settings)
    assert get_language() == "en"
    assert window.file_menu.title() == "File"
    assert window.edit_menu.title() == "Edit"
    assert window.options_menu.title() == "Options"
    assert window.language_actions["en"].isChecked()
    assert "ko-fi.com/giuclab/tip" in window.support_button.toolTip() or (
        "Support me" in window.support_button.text()
    )
    window.change_language("de")
    assert window.options_menu.title() == "Optionen"
    assert settings.value("ui/language") == "de"
    window.change_theme("dark")
    assert settings.value("ui/theme") == "dark"
    assert "#171c2c" in window.styleSheet()
    window.change_theme("light")
    assert "#f5f6fb" in window.styleSheet()
    window.close()


def test_official_icon_loads() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    assert not app_icon().isNull()
