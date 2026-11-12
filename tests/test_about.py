"""About screen: version logic and local GUI checks (no GitHub network required)."""

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from visilens.about import AboutDialog, assess_release, version_tuple
from visilens.desktop import app_icon
from visilens.i18n import set_language


def release(tag: str, **overrides) -> bytes:
    data = {
        "tag_name": tag,
        "html_url": "https://github.com/GiuClab/VisiLens/releases/tag/" + tag,
        "prerelease": False,
        "draft": False,
    }
    data.update(overrides)
    return json.dumps(data).encode("utf-8")


def test_version_compare_and_stable_releases() -> None:
    assert version_tuple("v0.7") == version_tuple("0.7.0")
    assert assess_release(release("v0.8.0"), "0.7.0")[0] == "available"
    assert assess_release(release("v0.7.0"), "0.7.0")[0] == "current"
    assert assess_release(release("v0.6.4"), "0.7.0")[0] == "current"


@pytest.mark.parametrize(
    "payload",
    [
        release("v0.8.0", prerelease=True),
        release("v0.8.0", draft=True),
        release("v0.8.0", html_url="https://example.com/visilens"),
        release("nightly-build"),
        b"not JSON",
        b"[]",
    ],
)
def test_reject_invalid_or_unofficial_releases(payload: bytes) -> None:
    with pytest.raises((ValueError, json.JSONDecodeError)):
        assess_release(payload, "0.7.0")


def test_about_dialog_is_wider_and_shows_update_controls() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    set_language("en")
    dialog = AboutDialog(icon=app_icon())
    assert dialog.width() >= 680
    assert dialog.check_button.text() == "Check for updates"
    assert not dialog.download_button.isVisible()
    dialog.set_status("Checking for updates…", "#385ad0")
    assert "#385ad0" in dialog.status_label.styleSheet()
    dialog.set_status("Network error", "#c93745")
    assert "#c93745" in dialog.status_label.styleSheet()
    dialog.close()
