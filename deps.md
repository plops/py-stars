# Dependencies – py-stars

Alle Abhängigkeiten mit GitHub-Organisation, damit deepwiki-Abfragen leicht konstruiert werden können.

| Paket | GitHub Org/Repo | Zweck |
|---|---|---|
| pillow-heif | `bigcat88/pillow_heif` | HEIC/HEIF-Dateien lesen (iPhone-Fotos) |
| Pillow | `python-pillow/Pillow` | Bildverarbeitung (PIL) |
| tetra3 | `esa/tetra3` | Plate Solving – Sterne identifizieren, Kameraausrichtung bestimmen |
| numpy | `numpy/numpy` | Numerische Arrays, Matrixoperationen |
| scipy | `scipy/scipy` | Wissenschaftliches Rechnen (ndimage, optimize) |
| opencv-python-headless | `opencv/opencv-python` | Bildverarbeitung (Blob-Erkennung, Filterung) |
| matplotlib | `matplotlib/matplotlib` | Visualisierung der Ergebnisse |
| pytest | `pytest-dev/pytest` | Unit- und Integration-Tests |
| ruff | `astral-sh/ruff` | Python Linter und Formatter |

## System-Abhängigkeiten (apt)

| Paket | Zweck |
|---|---|
| `libheif-dev` | C-Bibliothek für HEIF-Dekodierung (wird von pillow-heif benötigt) |
| `libheif-plugin-libde265` | HEVC-Decoder-Plugin für libheif |
| `libde265-dev` | H.265/HEVC-Codec |

## deepwiki-Abfragen

```bash
# Beispiele für deepwiki-Abfragen:
# deepwiki ask_question repo="bigcat88/pillow_heif" question="How to read HEIC files?"
# deepwiki ask_question repo="esa/tetra3" question="How to generate a custom database for wide FOV?"
# deepwiki ask_question repo="opencv/opencv-python" question="How to detect blobs in images?"
```
