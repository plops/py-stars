# py-stars 🌟

Sterne in Smartphone-Fotos (HEIC) erkennen, lokalisieren und astrometrisch vermessen mittels [tetra3rs](https://github.com/esa/tetra3) Plate Solving, Objektiv-Verzeichnungs-Kalibrierung, atmosphärischer Refraktionskorrektur und Grenzhelligkeits-Analyse.

## Überblick

`py-stars` analysiert Nachtaufnahmen von Smartphones und Weitwinkel-Kameras:
1. **Lost-in-Space Plate Solving**: Bestimmt Himmelsausrichtung (RA, Dec, Roll) in Millisekunden gegen den Gaia DR3 Katalog.
2. **Dynamische FOV-Erkennung**: Berechnet das Bildfeld (HFOV, VFOV, DFOV) dynamisch aus EXIF-Metadaten (35mm-Äquivalentbrennweite & Sensor-Seitenverhältnis) ohne fest verdrahtete Konstanten.
3. **Objektiv-Verzeichnungskorrektur (Distortion Calibration)**: Unterstützt radiale (Brown-Conrady) und polynomielle Kameramodelle.
4. **Atmosphärische Refraktionskorrektur**: Modelliert Lichtbeugung am Horizont mittels Bennett-Formel unter Berücksichtigung von Beobachterhöhe (Luftdruck) und Temperatur.
5. **Katalog-Cross-Matching & Residuen**: Gleicht alle sichtbaren Katalogsterne im Bildfeld mit den detektierten Zentroiden ab und berechnet astrometrische Residuen ($dx, dy, \text{RMSE}$).
6. **Grenzhelligkeits-Analyse (Limiting Magnitude)**: Misst die Detektionsrate als Funktion der visuellen Magnitude (50%- und 90%-Vollständigkeitsgrenze, schwächster detektierter Stern) und kalibriert die Instrumental-Photometrie.

## Pipeline

```
HEIC/EXIF laden → Dynamisches FOV → Centroid-Extraktion (mit optionalem Sky-ROI)
       ↓
Plate Solving (mit optionaler Verzerrungskorrektur)
       ↓
Atmosphärische Refraktionskorrektur (Alt/Az Topozentrisch)
       ↓
Katalog Cross-Matching & Residuen-Analyse
       ↓
Grenzhelligkeits- & Photometrie-Bestimmung → 4-Panel-Diagnoseplot
```

## Voraussetzungen

### System (apt)
```bash
sudo apt install libheif-dev libheif-plugin-libde265 libde265-dev
```

### Python (uv)
```bash
uv sync
```

## Benutzung & Beispiele

### 1. Plate Solving, Katalog-Matching & Grenzhelligkeit (`solve`)

Führt die komplette Analyse durch (Plate Solving, Verzerrungskorrektur, Refraktion, Stern-Cross-Matching, Grenzhelligkeit und 4-Panel-Diagnoseplot):

```bash
uv run py-stars solve data/IMG_8867.HEIC --distortion radial --plot
```

#### Beispiel-Ausgabe:

```text
Loaded distortion model: iphone11_camera_radial.bin
Processing 1 image(s)...

======================================================================
  Processing: IMG_8867.HEIC
======================================================================
=== Plate Solve Result ===
  RA:        171.2527° (11h 25m 00.65s)
  Dec:       +86.8005°  (+86° 48' 01.90")
  Roll:      -172.95°
  FOV:       67.15°
  Matches:   96
  RMSE:      165.01"
  Time:      0.9ms
  Prob:      2.66e-111

--- Catalog Matching & Astrometric Accuracy ---
  Catalog Stars in FOV:  1248
  Matched Stars:         79
  Mean Residual:         2.17 px (130.0")
  Median Residual:       1.86 px (111.3")
  Astrometric RMSE:      157.54" (2.63 px)
  Atmospheric Refraction: Disabled / No GPS
  Distortion Model:       Active

--- Limiting Magnitude & Star Detectability ---
  Brightest Star:        1.57 mag
  Faintest Star:         6.30 mag
  90% Completeness Limit: 3.00 mag
  50% Limiting Magnitude: 4.50 mag

  Detection by Magnitude:
    Mag [0.0 - 2.0]:  3 /  3 (100.0%)
    Mag [2.0 - 3.0]:  4 /  4 (100.0%)
    Mag [3.0 - 4.0]: 20 / 27 ( 74.1%)
    Mag [4.0 - 4.5]: 22 / 35 ( 62.9%)
    Mag [4.5 - 5.0]: 18 / 53 ( 34.0%)
    Mag [5.0 - 5.5]: 10 / 97 ( 10.3%)
    Mag [6.0 - 6.5]:  2 / 308 (  0.6%)

  Photometry Zero-point:  13.93 mag (scatter σ = 0.69 mag)
Saved diagnostic visualization: output/IMG_8867_diagnostics.png
```

#### Bedeutung der Ausgabe-Felder:
- **`Plate Solve Result`**: Zeigt die exakte Himmelsausrichtung (Rektaszension, Deklination, Roll-Winkel), das gemessene FOV, Match-Anzahl und Lösezeit (< 1 ms).
- **`Catalog Matching & Astrometric Accuracy`**: Gleicht alle 1248 sichtbaren Gaia-Sterne im Bildfeld mit den Zentroiden ab und berechnet den mittleren Pixelversatz und Astrometrie-RMSE in Bogensekunden.
- **`Limiting Magnitude & Star Detectability`**:
  - **`90% Completeness Limit`**: Bis zu dieser Helligkeit werden 90% aller Sterne zuverlässig detektiert (z. B. $3.0\text{ mag}$).
  - **`50% Limiting Magnitude`**: Die klassische astronomische Grenzhelligkeit (50%-Erkennungsrate, z. B. $4.5\text{ mag}$).
  - **`Faintest Star`**: Der schwächste im Foto noch nachweisbare Stern (z. B. $6.30\text{ mag}$).
- **`Photometry Zero-point`**: Kalibrierte Umrechnung zwischen Pixel-Intensitätsflux und Katalog-Magnitude ($m = -2.5 \log_{10}(\text{Flux}) + \text{ZP}$).
- **`output/<image>_diagnostics.png`**: Generiert ein 4-Panel-Dashboard mit:
  1. *Stern-Identifikationskarte* (gematchte vs ungematchte Sterne und Refraktionsvektoren)
  2. *Astrometrisches Residuenfeld* über den Sensorradius
  3. *Vollständigkeitskurve* nach Helligkeitsklassen
  4. *Photometrie-Fit* (Flux vs. Katalog-Magnitude)

---

### 2. EXIF-Metadaten, GPS & dynamische FOV-Berechnung (`info`)

```bash
uv run py-stars info data/IMG_9144.HEIC
```

#### Beispiel-Ausgabe:
```text
============================================================
  Image Metadata: IMG_9144.HEIC
============================================================
Dimensions: 4032 x 3024
Format:     HEIF (RGB)
Camera:     Apple iPhone 11
Lens:       iPhone 11 back dual wide camera 4.25mm f/1.8
Focal (35): 26 mm (physical: 4.25 mm)
Computed FOV: HFOV = 67.30°, VFOV = 53.06°, DFOV = 79.52°

GPS Data:
  Latitude:   47.412136°
  Longitude:  9.630881°
  Altitude:   405.8 m
  UTC Time:   2026-08-14T21:17:49.990000+00:00
  Heading:    350.17°
```

---

### 3. Kamera-Verzeichnung kalibrieren (`calibrate`)

Kalibriert radiale oder polynomielle Linsenverzerrung über mehrere Aufnahmen:

```bash
uv run py-stars calibrate data/*.HEIC --model radial --output data/iphone11_camera_radial.bin
```

---

### 4. Tests & Validierung

```bash
# Test-Suite (56 Tests)
uv run pytest -v

# Linter & Formatter
uv run ruff check .
uv run ruff format --check .
```

## Projektstruktur

```
src/py_stars/
├── __init__.py         # Öffentliche Package API
├── exif.py             # EXIF-Metadaten, GPS-Parsing & dynamische FOV-Berechnung
├── astrometry.py       # Sternzeit (GMST, LST) & Koordinatentransformationen (RA/Dec ↔ Alt/Az)
├── refraction.py       # Bennett-Refraktionsmodell & barometrische Skalierung
├── calibration.py      # CameraModel-Handling & Mehrbild-Verzeichnungskalibrierung
├── star_matching.py    # Katalog-Matching, Residuen & Grenzhelligkeits-Analyse
├── star_detector.py    # Centroid-Extraktion mit Subpixel-Fitting & ROI-Support
├── plate_solver.py     # tetra3rs Plate Solver Interface & High-Level Workflow
├── visualizer.py       # 4-Panel Astrometrie- & Diagnose-Visualisierungen
└── cli.py              # py-stars CLI Interface

data/                   # Kalibrierte Kameramodelle (.bin) & Gaia-Solver-Datenbank
scripts/                # Ausführliche Analyse-Skripte
tests/                  # Vollständige Unit- & Integrations-Testsuite
output/                 # Generierte Diagnose-Grafiken
```

## Autor

wol pumba (wolpumba@gmail.com)
