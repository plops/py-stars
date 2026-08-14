# task.md – Serielle Implementierungsschritte für py-stars

> Jeder Schritt wird implementiert, getestet und validiert, bevor der nächste beginnt.
> Commits im Conventional-Commit-Format mit umfassender Beschreibung.

---

## Schritt 0: Projekt-Setup & Tooling

### Aufgabe
- [x] `uv init` – Projekt initialisieren
- [x] System-Abhängigkeiten installieren (`libheif-dev`, `libde265-dev`, `libheif-plugin-libde265`)
- [x] `uv sync` – Python-Abhängigkeiten installieren
- [x] `ruff check .` und `ruff format .` einrichten und ausführen
- [x] Verzeichnisstruktur erstellen:
  ```
  py-stars/
  ├── src/py_stars/
  │   ├── __init__.py
  │   ├── heic_loader.py       # HEIC-Dateien laden
  │   ├── star_detector.py     # Sterne im Bild finden
  │   ├── plate_solver.py      # Plate Solving mit tetra3
  │   └── visualizer.py        # Ergebnisse visualisieren
  ├── tests/
  │   ├── __init__.py
  │   ├── test_heic_loader.py
  │   ├── test_star_detector.py
  │   ├── test_plate_solver.py
  │   └── test_visualizer.py
  ├── scripts/
  │   └── run_spike.py          # Spike-Script: alles zusammen
  ├── output/                   # Generierte Bilder
  ├── pyproject.toml
  ├── deps.md
  └── README.md
  ```

### Validierung
- `uv run python -c "import pillow_heif; import tetra3; import cv2; print('OK')"`
- `uv run ruff check .`
- `uv run ruff format --check .`

### Commit
```
feat: initialize project with uv, dependencies, and tooling

- Initialize uv project with Python 3.14
- Add dependencies: pillow-heif, tetra3, numpy, scipy, opencv, matplotlib
- Configure ruff for linting and formatting
- Install system dependencies for HEIF support
- Create directory structure for modular spike implementation
```

---

## Schritt 1: HEIC-Dateien laden

### Kontext-Dateien
- `src/py_stars/heic_loader.py` – zu erstellen
- `deps.md` – pillow-heif Referenz
- `/workspace/src/IMG_8556.HEIC` – Beispiel-HEIC-Datei

### Aufgabe
- `heic_loader.py` implementieren:
  - `register_heif()` – HEIF-Plugin bei Pillow registrieren
  - `load_heic(filepath: str) -> PIL.Image.Image` – HEIC laden, als RGB PIL Image zurückgeben
  - `load_heic_as_gray(filepath: str) -> np.ndarray` – HEIC laden, zu Graustufenbild konvertieren
  - `get_image_info(filepath: str) -> dict` – Metadaten (Größe, EXIF) extrahieren
- Hardcoded Dateipfade im Spike-Script, nicht in den Modulen

### Validierung
- Unit-Tests in `tests/test_heic_loader.py`:
  - Test: HEIC-Datei laden ergibt PIL Image mit korrekter Größe
  - Test: Graustufenkonvertierung ergibt 2D numpy array
  - Test: Fehlerbehandlung bei fehlender Datei
- `uv run pytest tests/test_heic_loader.py -v`
- `uv run ruff check src/py_stars/heic_loader.py`

### Commit
```
feat(heic): implement HEIC image loading with pillow-heif

- Register HEIF opener with Pillow for transparent HEIC support
- Implement load_heic() for RGB and load_heic_as_gray() for grayscale
- Extract basic image metadata including EXIF data
- Add unit tests for loading, conversion, and error handling
- Tested with real iPhone HEIC files (IMG_8556.HEIC)
```

---

## Schritt 2: Stern-Erkennung im Bild

### Kontext-Dateien
- `src/py_stars/star_detector.py` – zu erstellen
- `src/py_stars/heic_loader.py` – aus Schritt 1
- `deps.md` – OpenCV, scipy Referenz

### Aufgabe
- `star_detector.py` implementieren:
  - `preprocess_image(gray: np.ndarray) -> np.ndarray` – Rauschunterdrückung, Kontrastverbesserung
  - `detect_stars_simple(gray: np.ndarray, threshold: float = ...) -> np.ndarray` – einfache Schwellwert-basierte Erkennung
  - `detect_stars_blob(gray: np.ndarray) -> list[dict]` – OpenCV SimpleBlobDetector
  - `extract_centroids(gray: np.ndarray) -> np.ndarray` – Schwerpunkte der erkannten Sterne als (x, y) Array
  - `filter_stars(centroids: np.ndarray, min_brightness: float) -> np.ndarray` – zu schwache Punkte filtern

### Validierung
- Unit-Tests in `tests/test_star_detector.py`:
  - Test: Preprocessing verändert Bildgröße nicht
  - Test: Erkennung auf synthetischem Bild (Punkte auf schwarzem Hintergrund) findet korrekte Anzahl
  - Test: Centroids haben korrekte Form (N, 2)
  - Test: Filter reduziert Anzahl der Sterne
- Integration-Test: Echtes HEIC-Bild laden → Sterne erkennen → mindestens einige Centroids gefunden
- `uv run pytest tests/test_star_detector.py -v`

### Commit
```
feat(detection): implement star detection with OpenCV blob detector

- Add image preprocessing (Gaussian blur, contrast stretching)
- Implement SimpleBlobDetector-based star detection
- Extract sub-pixel centroids using moment calculation
- Add brightness-based filtering for noise reduction
- Unit tests with synthetic star images and integration test with real HEIC
```

---

## Schritt 3: Plate Solving mit tetra3

### Kontext-Dateien
- `src/py_stars/plate_solver.py` – zu erstellen
- `src/py_stars/star_detector.py` – aus Schritt 2
- `src/py_stars/heic_loader.py` – aus Schritt 1
- `deps.md` – tetra3 Referenz

### Aufgabe
- `plate_solver.py` implementieren:
  - `create_solver(database_path: str | None = None) -> tetra3.Tetra3` – Solver mit Datenbank erstellen
  - `generate_iphone_database(solver, save_path: str)` – Custom-DB für iPhone FOV (~71°) generieren
  - `solve_image(solver, image: np.ndarray, fov_estimate: float = 71.0) -> dict` – Plate Solving durchführen
  - `solve_from_centroids(solver, centroids: np.ndarray, image_size: tuple, fov_estimate: float) -> dict` – Lösen aus vorberechneten Centroids
  - `format_result(result) -> str` – Ergebnis menschenlesbar formatieren (RA, Dec, Roll)
- Die iPhone 11 FOV-Parameter als Konstanten definieren:
  - `IPHONE11_HFOV = 71.5`  # degrees, horizontal
  - `IPHONE11_VFOV = 56.8`  # degrees, vertical
  - `IPHONE11_FOCAL_LENGTH_EQUIV = 26`  # mm equivalent

### Validierung
- Unit-Tests in `tests/test_plate_solver.py`:
  - Test: Solver erstellen mit Default-DB
  - Test: Custom-DB generieren (kann lange dauern – ggf. mit kleinem Katalog)
  - Test: Ergebnis-Formatierung
- Integration-Test: Echtes Bild → Sterne erkennen → Plate Solve → Ergebnis prüfen
  - Hinweis: Plate Solving kann fehlschlagen wenn kein Sternenbild – Test sollte graceful damit umgehen
- `uv run pytest tests/test_plate_solver.py -v`

### Commit
```
feat(solver): implement plate solving with tetra3

- Create tetra3 solver wrapper with database management
- Generate custom database for iPhone 11 wide FOV (~71°)
- Implement solve_image() and solve_from_centroids()
- Define iPhone 11 camera constants (FOV, focal length)
- Add result formatting for RA/Dec/Roll output
- Tests for solver creation, DB generation, and result formatting
```

---

## Schritt 4: Visualisierung

### Kontext-Dateien
- `src/py_stars/visualizer.py` – zu erstellen
- Alle vorherigen Module

### Aufgabe
- `visualizer.py` implementieren:
  - `plot_detected_stars(image: np.ndarray, centroids: np.ndarray, output_path: str)` – Bild mit markierten Sternen
  - `plot_star_magnitudes(centroids: np.ndarray, brightnesses: np.ndarray, output_path: str)` – Helligkeitsverteilung
  - `create_summary_image(image, centroids, solve_result, output_path: str)` – Zusammenfassendes Bild mit allen Infos
- Output-Verzeichnis `output/` für generierte Bilder

### Validierung
- Unit-Tests in `tests/test_visualizer.py`:
  - Test: Plot-Funktion erstellt Datei
  - Test: Summary-Bild enthält korrekten Titel
- `uv run pytest tests/test_visualizer.py -v`

### Commit
```
feat(viz): add visualization for detected stars and solve results

- Plot detected stars overlaid on original image
- Create brightness distribution chart
- Generate summary image combining image, detections, and solve result
- Output saved to output/ directory
```

---

## Schritt 5: Spike-Script – Alles zusammen

### Kontext-Dateien
- Alle Module aus Schritt 1-4
- `/workspace/src/IMG_8556.HEIC` – Beispiel-HEIC

### Aufgabe
- `scripts/run_spike.py` implementieren:
  - Hardcoded Dateipfade zu den Beispiel-HEIC-Dateien
  - Pipeline: Load → Detect → Solve → Visualize
  - Jeder Schritt mit Print-Ausgaben, damit man den Fortschritt verfolgen kann
  - Ergebnisse in `output/` speichern

### Validierung
- Script manuell ausführen: `uv run python scripts/run_spike.py`
- Prüfen, dass Output-Dateien erstellt werden
- Prüfen, dass keine Exceptions auftreten
- Alle Tests nochmal ausführen: `uv run pytest -v`
- Lint: `uv run ruff check . && uv run ruff format --check .`

### Commit
```
feat(spike): add end-to-end spike script for star detection pipeline

- Run complete pipeline: HEIC load → star detection → plate solving → visualization
- Hardcoded file paths for spike exploration
- Print intermediate results for step-by-step understanding
- Generate annotated output images in output/ directory
```

---

## Schritt 6: Finale Validierung & Walkthrough

### Aufgabe
- Alle Tests ausführen: `uv run pytest -v`
- Lint & Format prüfen: `uv run ruff check . && uv run ruff format --check .`
- Walkthrough-Dokument erstellen: `plan/20260814_01_start/walkthrough.md`
- README.md aktualisieren

### Validierung
- Alle Tests grün
- Linting sauber
- Walkthrough vollständig

### Commit
```
docs: add walkthrough document and update README

- Document what was implemented and key design decisions
- List learnings and potential extensions
- Document system dependencies for Docker
- Update README with project overview and usage instructions
```
