"""Fail Windows packaging if VisiLens.exe lacks embedded Windows icon resources."""
from __future__ import annotations

from pathlib import Path

import pefile

EXE = Path("dist/VisiLens/VisiLens.exe")


def main() -> None:
    if not EXE.is_file():
        raise FileNotFoundError(EXE)
    pe = pefile.PE(str(EXE), fast_load=False)
    resources = getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None)
    if resources is None:
        raise RuntimeError("EXE has no Windows resources")
    ids = {entry.id for entry in resources.entries}
    if 3 not in ids or 14 not in ids:
        raise RuntimeError(
            "EXE is missing RT_ICON or RT_GROUP_ICON resources; check --icon"
        )
    print("Verified embedded Windows icon resources in", EXE)


if __name__ == "__main__":
    main()
