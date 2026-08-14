# Walkthrough: Stern-Erkennung & Plate Solving für iPhone-Fotos (py-stars)

Dieses Dokument fasst die Implementierung, Testergebnisse, Architekturentscheidungen, Learnings und Erweiterungsmöglichkeiten zusammen.

---

## 1. Was wurde implementiert?

Für das Projekt **py-stars** wurde eine modulare, leicht verständliche und zeilenweise lesbare Pipeline zur Sternerkennung und Himmelslokalisierung (Lost-in-Space Plate Solving) für iPhone-Fotos entwickelt.

### Projektstruktur

```
/workspace/src/py-stars/
├── pyproject.toml                     # uv Projekt- & Tool-Konfiguration
├── deps.md                            # Dokumentation aller Abhängigkeiten & GitHub-Orgs
├── task.md                            # Serielle Implementierungs- & Verifikationsschritte
├── README.md                          # Übersicht, Setup und Nutzungsanleitung
├── data/
│   └── iphone_wide.bin                # Generierte Gaia DR3 Solver-Datenbank (FOV 50°-80°)
├── output/                            # Generierte Ergebnis- & Annotationsbilder
├── src/
│   └── py_stars/
│       ├── __init__.py                # Package Exports
│       ├── heic_loader.py             # Laden & Konvertieren von Apple HEIC/HEIF-Bildern
│       ├── star_detector.py           # Subpixel-Centroid-Extraktion & Preprocessing
│       ├── plate_solver.py            # Plate Solving via tetra3rs & Gaia DR3
│       └── visualizer.py              # Visualisierung mit Stern-Markierung & Solve-Status
├── scripts/
│   └── run_spike.py                   # End-to-End Spike-Skript mit echten Bilddateien
├── tests/
│   ├── test_heic_loader.py            # 13 Tests für HEIC-Laden, Grayscale, Metadaten
│   ├── test_star_detector.py          # 10 Tests für Preprocessing, Centroids, Blob-Detektion
│   ├── test_plate_solver.py           # 7 Tests für Solver-Konstanten, Formatierung, Failure Handling
│   └── test_visualizer.py             # 4 Tests für Plotting & Output-Generierung
└── plan/
    └── 20260814_01_start/
        ├── prompt.txt                 # Original-Aufgabenstellung
        ├── iphone-stars.md            # Geometrische Berechnungen & Astrometrie-Hintergrund
        ├── implementation_plan.md     # Ausführlicher Implementierungsplan für AI-Agenten
        └── walkthrough.md             # Dieses Dokument
```

---

## 2. Detaillierte Modulbeschreibung

### 1. `heic_loader.py`
- Registriert den `pillow_heif`-Opener transparent bei PIL.
- `load_heic(filepath)`: Lädt HEIC-Dateien als RGB `PIL.Image`.
- `load_heic_as_gray(filepath)`: Konvertiert in normalisiertes float64-Array $[0.0, 1.0]$.
- `load_heic_as_uint8(filepath)`: Konvertiert in 2D uint8-Array $[0, 255]$ für Bildverarbeitung.
- `get_image_info(filepath)`: Liest Auflösung, Farbmodus und EXIF-Metadaten aus.

### 2. `star_detector.py`
- `extract_centroids_tetra3(gray, sigma_threshold=10.0, max_centroids=100)`:
  - Führt Background-Estimation via Sigma-Clipping durch.
  - Wendet Gaussian Matched Filter ($\sigma=1.5\text{px}$) für Punkterkennung an.
  - Führt 2D-Quadratic Fitting im $3\times3$ Peak-Bereich für Subpixel-Genauigkeit durch.
  - Sortiert und beschränkt auf die hellsten Centroids (`max_centroids=100`), um exponentielles Matching-Wachstum beim Plate Solving zu verhindern.
- `preprocess_image(gray)`: Optionale Vorverarbeitung mit Gaussian Blur und CLAHE-Kontrastverstärkung.
- `detect_stars_opencv(gray)`: Alternative Schwellwert- und Form-basierte `SimpleBlobDetector`-Erkennung.

### 3. `plate_solver.py`
- Basiert auf `tetra3rs` mit integriertem Gaia DR3-Katalog.
- `get_or_create_database(path)`: Erstellt beim ersten Start in <0.3s eine auf Weitwinkel ($50^\circ-80^\circ$ FOV) optimierte Binärdatenbank (`iphone_wide.bin`).
- `solve_image(db, centroids, image_width, image_height, fov_estimate_deg=71.5)`:
  - Löst das Lost-in-Space Problem anhand von 4-Stern-Mustern (Quads) und Kantenverhältnissen.
  - Liefert `ra_deg`, `dec_deg`, `roll_deg`, `fov_deg`, `num_matches`, `rmse_arcsec`, `probability`.
- `format_result(result)`: Formatiert Koordinaten in Stunden/Minuten/Sekunden (RA: `HHh MMm SSs`) und Grad/Bogenminuten/Bogensekunden (Dec: `±DD° MM' SS"`).

### 4. `visualizer.py`
- `plot_detected_stars(image, centroids, output_path)`: Zeichnet alle detektierten Centroids in das Bild ein.
- `plot_star_brightnesses(centroids, output_path)`: Erstellt ein Histogramm der Helligkeitsverteilung samt Median.
- `create_summary_image(image, centroids, solve_result, output_path)`: Erstellt eine übersichtliche 2-Panel-Grafik:
  - Links: Bild mit grün markierten gematchten Sternen und cyan markierten ungematchten Centroids.
  - Rechts: Übersichtliche Infobox mit RA, Dec, Roll, FOV, Anzahl Matches, RMSE und Rechenzeit.

---

## 3. Testergebnisse & Validierung

### Test-Suite (`pytest -v`)
Alle **34 Tests** wurden erfolgreich ausgeführt und validiert:
```
tests/test_heic_loader.py::TestLoadHeic::test_loads_as_pil_image PASSED
tests/test_heic_loader.py::TestLoadHeic::test_returns_rgb_mode PASSED
tests/test_heic_loader.py::TestLoadHeic::test_has_positive_dimensions PASSED
tests/test_heic_loader.py::TestLoadHeic::test_raises_on_missing_file PASSED
tests/test_heic_loader.py::TestLoadHeicAsGray::test_returns_numpy_array PASSED
tests/test_heic_loader.py::TestLoadHeicAsGray::test_is_2d PASSED
tests/test_heic_loader.py::TestLoadHeicAsGray::test_is_float64 PASSED
tests/test_heic_loader.py::TestLoadHeicAsGray::test_values_normalized_0_to_1 PASSED
tests/test_heic_loader.py::TestLoadHeicAsUint8::test_returns_uint8 PASSED
tests/test_heic_loader.py::TestLoadHeicAsUint8::test_is_2d PASSED
tests/test_heic_loader.py::TestGetImageInfo::test_returns_dict PASSED
tests/test_heic_loader.py::TestGetImageInfo::test_has_required_keys PASSED
tests/test_heic_loader.py::TestGetImageInfo::test_dimensions_are_positive PASSED
tests/test_plate_solver.py::TestConstants::test_iphone11_hfov_reasonable PASSED
tests/test_plate_solver.py::TestConstants::test_iphone11_vfov_reasonable PASSED
tests/test_plate_solver.py::TestCoordinateFormatting::test_deg_to_hms_zero PASSED
tests/test_plate_solver.py::TestCoordinateFormatting::test_deg_to_hms_180 PASSED
tests/test_plate_solver.py::TestCoordinateFormatting::test_deg_to_dms_positive PASSED
tests/test_plate_solver.py::TestCoordinateFormatting::test_deg_to_dms_negative PASSED
tests/test_plate_solver.py::TestFormatResult::test_format_failure PASSED
tests/test_star_detector.py::TestPreprocessImage::test_preserves_shape PASSED
tests/test_star_detector.py::TestPreprocessImage::test_returns_uint8 PASSED
tests/test_star_detector.py::TestPreprocessImage::test_accepts_float64 PASSED
tests/test_star_detector.py::TestExtractCentroidsTetra3::test_returns_extraction_result PASSED
tests/test_star_detector.py::TestExtractCentroidsTetra3::test_finds_centroids_in_synthetic_image PASSED
tests/test_star_detector.py::TestExtractCentroidsTetra3::test_empty_image_finds_nothing PASSED
tests/test_star_detector.py::TestCentroidsToArray::test_empty_list_returns_empty_array PASSED
tests/test_star_detector.py::TestCentroidsToArray::test_converts_centroids PASSED
tests/test_star_detector.py::TestDetectStarsOpencv::test_returns_list PASSED
tests/test_star_detector.py::TestDetectStarsOpencv::test_star_dicts_have_required_keys PASSED
tests/test_visualizer.py::TestEnsureOutputDir::test_creates_directory PASSED
tests/test_visualizer.py::TestPlotDetectedStars::test_creates_output_file PASSED
tests/test_visualizer.py::TestPlotStarBrightnesses::test_creates_output_file PASSED
tests/test_visualizer.py::TestPlotStarBrightnesses::test_handles_empty_centroids PASSED
============================== 34 passed in 2.01s ==============================
```

### Validierung mit echten Aufnahmen (`scripts/run_spike.py`)

Die Pipeline wurde an realen Testdateien ausgeführt:

1. **`IMG_8556.HEIC` (Echtes Nachtfoto vom Sternenhimmel)**:
   - **Status**: ✅ **ERFOLGREICH GELÖST**
   - **Dauer**: Centroid-Extraktion: 0.24s, Plate Solving: **0.24s (236.7ms)**
   - **Ergebnis**:
     - **Rektaszension (RA)**: `190.8340°` (`12h 43m 20.16s`)
     - **Deklination (Dec)**: `+31.9410°` (`+31° 56' 27.63"`)
     - **Kameraroll (Roll)**: `-135.88°`
     - **Tatsächliches FOV**: `66.41°`
     - **Identifizierte Sterne**: `12` Sterne gematcht
     - **RMS-Fehler**: `186.84"` (~3 Bogenminuten)
     - **Falsch-Positiv-Wahrscheinlichkeit**: $1.38 \times 10^{-6}$

2. **`IMG_7260.HEIC`, `IMG_7267.HEIC`, `IMG_7268.HEIC`, `IMG_7269.HEIC` (Kalibrierungsbilder ohne Sterne)**:
   - **Status**: ✅ Graceful Failure (`no_match`), sauber in <0.5s abgefangen ohne Exceptions oder Timeouts.

---

## 4. Wichtige Learnings & Anpassungen

1. **Begrenzung der Centroid-Anzahl (`max_centroids=100`)**:
   - *Problem*: In hochauflösenden iPhone-Bildern ($4032 \times 3024$) lieferte die Centroid-Suche ohne Begrenzung über 15.000 Punkte (Rauschen, Hot Pixel). Dies führte beim Plate Solver zu einem Timeout (>5s).
   - *Lösung*: Die Centroids werden standardmäßig auf die 100 hellsten Punkte beschränkt. Dadurch sank die Lösungszeit von $\infty$ (Timeout) auf **236 Millisekunden** bei perfektem Matching von 12 Leitsternen.

2. **`tetra3rs` vs `tetra3`**:
   - *Problem*: Das originale ESA-`tetra3`-Repository ist nicht auf PyPI verfügbar und erfordert manuelle Hipparcos-Katalog-Downloads.
   - *Lösung*: Wir nutzen `tetra3rs`, einen modernen, schnellen Rust-Port mit Python-Bindings und vorintegriertem Gaia DR3-Katalog. Die Datenbankgenerierung dauert nur ca. 0.2 Sekunden.

3. **Numpy Array Truth Value Handling**:
   - *Problem*: In `visualizer.py` löste die Abfrage `if getattr(solve_result, "matched_centroids", None):` einen `ValueError` aus, da `matched_centroids` ein mehrdimensionales Numpy-Array ist.
   - *Lösung*: Saubere Prüfung mit `if mc is not None:` und Konvertierung in ein `set` von Integern.

---

## 5. Empfohlene Pakete für den Docker-Container

Zur festen Integration in das Dockerfile des Containers sollten folgende APT-Pakete aufgenommen werden:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libheif-dev \
    libheif-plugin-libde265 \
    libde265-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
```

---

## 6. Mögliche Erweiterungen & Nächste Schritte

1. **Automatische EXIF-Brennweiten-Erkennung**:
   - Dynamisches Einstellen des `fov_estimate_deg` anhand der EXIF-Tags `FocalLengthIn35mmFilm` oder `FocalLength` und `SensorSize`.
2. **Azimut & Höhenwinkel-Berechnung (Alt/Az)**:
   - Verbindung mit `astropy.time` und `astropy.coordinates`, um aus Aufnahmezeitpunkt + GPS die genaue Blickrichtung relativ zum lokalen Horizont (Kompassrichtung und Elevationswinkel) zu bestimmen.
3. **Objektiv-Verzeichnungskorrektur (Distortion Calibration)**:
   - Nutzung von `db.calibrate_camera()` für Weitwinkel-Optiken mit radialer Verzerrung.
4. **Interaktive CLI / Web-UI**:
   - Hinzufügen eines CLI-Befehls `py-stars solve <pfad-zu-bild>` oder einer einfachen Web-Visualisierung.
