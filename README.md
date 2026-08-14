# py-stars 🌟

Sterne in iPhone-Fotos (HEIC) erkennen und identifizieren mittels Plate Solving.

## Überblick

Dieses Projekt erkennt Sterne in Nachtaufnahmen von iPhones und bestimmt die
Blickrichtung der Kamera am Himmel (Right Ascension, Declination, Roll) mittels
[tetra3](https://github.com/esa/tetra3) Plate Solving.

## Pipeline

```
HEIC laden → Graustufen → Stern-Erkennung → Plate Solving → Visualisierung
```

## Voraussetzungen

### System (apt)
```bash
sudo apt install libheif-dev libheif-plugin-libde265 libde265-dev
```

### Python
```bash
uv sync
```

## Benutzung

### Spike ausführen
```bash
uv run python scripts/run_spike.py
```

### Tests
```bash
uv run pytest -v
```

### Linting
```bash
uv run ruff check .
uv run ruff format --check .
```

## Projektstruktur

```
src/py_stars/
├── heic_loader.py     # HEIC-Dateien laden und konvertieren
├── star_detector.py   # Sterne im Bild erkennen
├── plate_solver.py    # Plate Solving mit tetra3
└── visualizer.py      # Ergebnisse visualisieren

scripts/
└── run_spike.py       # End-to-end Spike Script

tests/                 # Unit- und Integration-Tests
```

## Autor

wol pumba (wolpumba@gmail.com)
