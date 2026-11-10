# VisiLens

An open-source, cross-platform desktop application for finding **visually similar photos**.
Inspired by the workflow of VisiPics; not affiliated with its authors.

**Status: 0.5.0 — Windows-first early preview.** Windows 10/11, Python 3.10+.

## Features

- Scan multiple folders recursively (JPEG/JFIF, PNG, WebP, BMP, GIF, TIFF).
- Find visually similar images even when sizes or formats differ.
- Strict / Basic / Loose sensitivity using 64-bit perceptual hashing.
- Browse groups with thumbnails, file paths, resolution and size.
- Show the highest-resolution file first; manually choose every file to trash.
- Move explicitly selected files to the **system Trash** after confirmation.
- Cancel scanning; skip and report damaged/unreadable files.
- Modernized Italian-language desktop layout with sidebar, image thumbnails,
  group details and scan statistics.
- Scrollable two-column gallery showing **every image** in the selected group.
  The group list previews up to four thumbnails and displays the total count.
- Choose any two members of a group for side-by-side comparison, then enlarge
  them in a dedicated zoomable dialog.
- SQLite fingerprint cache on Windows in `%LOCALAPPDATA%\\VisiLens` to speed up
  subsequent scans of unchanged files (paths and image fingerprints are stored locally).
- Optional **Selezione intelligente** for Strict groups, with resolution preference,
  opt-in file-size tiebreaker, protected folders and a review summary.

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

Groups with three, four or many more copies are fully visible in the details
gallery. Use the **Confronta A/B** selectors to inspect any two files; the
**Ingrandisci** button opens a larger comparison with a shared zoom control.
Auto-Select and manual checkboxes still apply to all images in the group.

### Selezione intelligente (Auto-Select)

After a **Strict** scan, click **Auto-Select** to immediately select copies
across every group. The list visibly marks groups containing selected files;
you can review them with **Mostra solo gruppi con file selezionati**. There is
no intervening dialog. Use **Criteri** to customize keeper preferences:
protected folders, highest resolution and file-size tiebreaking (enabled by
default). Remaining ties are resolved by stable path order, which is **not** a
quality assessment. Review all selections before moving files to Trash. The
feature only checks boxes; **it never deletes files on its own**. Use **Annulla
tutte le selezioni** to undo in one click.

**Important:** Check every group before deleting. Visually similar files may be
different photos. The suggested keeper is based on pixel count, not artistic
quality or image fidelity. On some systems, Trash availability depends on the
filesystem and its configuration. Back up important photo collections.

## How matching works

Each image is EXIF-rotated and converted to a 64-bit pHash, plus a compact RGB
sample. pHash first filters candidate pairs (Strict <= 2, Basic <= 7, Loose <= 13);
then pixel color difference and the fraction of substantially changed pixels
must also pass conservative thresholds. This excludes many color-swapped logos,
different outfits and alternate designs that pHash alone mistakenly identifies.
Every pair in a group must match directly: indirect A-B-C chains are rejected.
The algorithm intentionally prioritizes **precision over recall**: altered crops,
color variations and some genuine duplicates may be omitted. Always review
the previews before selecting any image for the Trash.

**Strict** in version 0.3.0 is deliberately much stricter: even small local
changes in clothing, backgrounds or graphic elements should be rejected. Use
Basic if you also want to discover recompressed photos that Strict may miss.
Version 0.3.1 additionally checks the alpha (transparency) channel in Strict:
the same artwork over a solid background versus a transparent background is
not considered an exact visual duplicate. The SQLite cache stores alpha
fingerprints in a new schema, so older cached RGB-only results are not reused.

The current implementation uses an O(n²) similarity comparison and is aimed
at small-to-medium libraries. Future work: indexing for large libraries,
better cropped-image matching, packaging signed desktop installers, localization,
and persistence of full scan results.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check src tests
```

The core matcher is in `src/visilens/core.py`, independent of the Qt GUI in
`src/visilens/app.py`. Tests generate temporary images; no personal photo
library is needed. GitHub Actions currently tests and packages Windows only;
macOS/Linux builds are paused during the Windows-first phase.

## License

MIT. Project name and branding are original; VisiPics is mentioned only to
describe the inspiration.

---

## Italiano

VisiLens è un programma desktop open source per trovare foto duplicate o
visivamente simili, attualmente sviluppato e distribuito per Windows. Aggiungi le cartelle, avvia la
scansione, confronta le anteprime e scegli quali immagini spostare nel cestino.
Nessun file viene eliminato automaticamente. La versione 0.5.0 è una prima
anteprima: controlla sempre le selezioni e conserva una copia dei tuoi archivi.
