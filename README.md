# VisiLens

An open-source, cross-platform desktop application for finding **visually similar photos**.
Inspired by the workflow of VisiPics; not affiliated with its authors.

**Status: 0.1.0 — early preview.** Windows, macOS and Linux, Python 3.10+.

## Features

- Scan multiple folders recursively (JPEG, PNG, WebP, BMP, GIF, TIFF).
- Find visually similar images even when sizes or formats differ.
- Strict / Basic / Loose sensitivity using 64-bit perceptual hashing.
- Browse groups with thumbnails, file paths, resolution and size.
- Suggest keeping the highest-resolution file; manually override selections.
- Move explicitly selected files to the **system Trash** after confirmation.
- Cancel scanning; skip and report damaged/unreadable files.

## Installation

Install Python 3.10 or newer, then from the project directory:

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
python -m pip install -e .
visilens
```

If `visilens` is not on your PATH, run `python -m visilens.app`.

## Usage

1. Select **Add folder** for each location you want to scan.
2. Click **Scan**; choose Strict, Basic or Loose to regroup results.
3. Select a group and review the image previews and proposed selections.
4. Adjust checkboxes, leaving at least one image unchecked.
5. Click **Move checked images to Trash** and confirm.

**Important:** Check every group before deleting. Visually similar files may be
different photos. The suggested keeper is based on pixel count, not artistic
quality or image fidelity. On some systems, Trash availability depends on the
filesystem and its configuration. Back up important photo collections.

## How matching works

Each image is EXIF-rotated and converted to a 64-bit pHash. Hamming distance
thresholds are Strict <= 2, Basic <= 7, Loose <= 13. Matches are combined into
connected groups: **two items in the same group are not necessarily direct
matches**. Compare them manually before moving files to Trash.

The current implementation uses an O(n²) similarity comparison and is aimed
at small-to-medium libraries. Future work: indexing for large libraries,
better cropped-image matching, packaging signed desktop installers, localization,
and persistence of scan results.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check src tests
```

The core matcher is in `src/visilens/core.py`, independent of the Qt GUI in
`src/visilens/app.py`. Tests generate temporary images; no personal photo
library is needed. GitHub Actions tests on Windows, macOS and Linux.

## License

MIT. Project name and branding are original; VisiPics is mentioned only to
describe the inspiration.

---

## Italiano

VisiLens è un programma desktop open source per trovare foto duplicate o
visivamente simili su Windows, macOS e Linux. Aggiungi le cartelle, avvia la
scansione, confronta le anteprime e scegli quali immagini spostare nel cestino.
Nessun file viene eliminato automaticamente. La versione 0.1.0 è una prima
anteprima: controlla sempre le selezioni e conserva una copia dei tuoi archivi.
