# VisiLens

An open-source, cross-platform desktop application for finding **visually similar photos**.
Inspired by the workflow of VisiPics; not affiliated with its authors.

**Status: 0.6.3 — Windows-first early preview.** Windows 10/11, Python 3.10+.

## Features

- Scan multiple folders recursively (JPEG/JFIF, PNG, WebP, BMP, GIF, TIFF).
- Find visually similar images even when sizes or formats differ.
- Strict / Basic / Loose sensitivity using 64-bit perceptual hashing.
- Browse groups with thumbnails, file paths, resolution and size.
- Show the highest-resolution file first; manually choose every file to trash.
- Move explicitly selected files to the **system Trash** after confirmation.
- Cancel scanning; skip and report damaged/unreadable files.
- Three-pane Italian-language interface: Windows-style folder tree on the left,
  duplicate groups and scan statistics in the center, large preview and file
  details on the right.
- First launch maximizes the window within the desktop work area; later launches
  restore the user's maximized/restored preference and on-screen window size.
  Restored windows are clamped to the screen's usable area, leaving room for
  the taskbar and title bar when the monitor layout changes.
- Three matching statistic cards with large blue photo, red duplicate and green
  disk icons, plus clear counts and recoverable-space totals.
- Every group displays **all of its copies** in a scrollable two-column gallery,
  rather than limiting the display to pairs or a few representative pictures.
- Click a thumbnail to show it in the large preview and highlight its tile
  with a blue border. **Only the checkbox** selects or deselects a file for
  the Trash; viewing a picture never selects it for deletion. **Red borders**
  mark files selected for Trash, including Auto-Select results, and take priority
  over the blue preview border.
- Click the file path below the large preview to reveal that file in Windows
  File Explorer, with the file selected.
- The folder tree includes Windows user locations (Desktop, Documents,
  Downloads, Pictures, Music and Video) with native file icons, plus the disks.
- Similarity slider runs from Loose (blue), through Basic (green), to Strict (red).
- File, Language, Opzioni and Help menus (Italian available; English planned).
- **Opzioni → Includi file e cartelle nascosti**: opt-in traversal of hidden
  files and folders, saved between launches; Windows hidden/system attributes
  and dot-prefixed names are excluded by default.
- Switching similarity level uses a background worker and a per-scan cache of
  already calculated groups, with a short debounce for rapid slider changes.
  Groups are rendered in batches; thumbnails are decoded only near the visible
  viewport to avoid UI freezes on large collections.
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

1. Check folders in the left-hand tree, or use **File → Aggiungi cartella…**.
2. Click **Avvia scansione**; adjust Loose, Basic or Strict using the slider.
3. Scroll through separate groups; all copies within each group are visible.
4. Click a thumbnail to inspect it in the larger preview on the right. Mark
   files for deletion exclusively with the **Cestino** checkboxes. Leave at
   least one copy unchecked in every group.
5. Click **Sposta selezionate nel cestino** and confirm.

Groups with three, four or more copies are shown in full. Auto-Select and
manual checkbox selections apply to every image in every group.
Click a blue underlined image path in the preview to open its location in
Windows Explorer. Enable hidden images explicitly in **Opzioni** if needed.

### Selezione intelligente (Auto-Select)

After a **Strict** scan, click **Auto-Select** to immediately select copies
across every group. Selection borders, checkboxes and a per-group count make
the choices visible immediately; there is no intervening dialog. Use **Criteri**
to customize keeper preferences:
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

The current implementation uses an O(n²) similarity comparison, now executed in
a worker thread instead of blocking the UI. Results are cached for the three
levels during a scan and cleared on rescanning or after moving files to Trash.
Future work: indexing for very large libraries,
better cropped-image matching, packaging signed desktop installers, localization,
and persistence of full scan results.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check src tests
```

The core matcher is in `src/visilens/core.py`, independent of the Qt GUI in
`src/visilens/desktop.py` (`src/visilens/app.py` is the compatibility entry point).
Tests generate temporary images; no personal photo
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
Nessun file viene eliminato automaticamente. La versione 0.6.3 è una prima
anteprima: controlla sempre le selezioni e conserva una copia dei tuoi archivi.
