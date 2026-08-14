# py-stars 🌟

Sterne in Smartphone-Fotos (HEIC) erkennen, lokalisieren und astrometrisch vermessen mittels [tetra3rs](https://github.com/esa/tetra3) Plate Solving, Objektiv-Verzeichnungs-Kalibrierung, atmosphärischer Refraktionskorrektur, Grenzhelligkeits-Analyse, Planeten- & Mond-Ephemeriden ([Skyfield](https://rhodesmill.org/skyfield/)), Deep-Sky-Objekten (Messier/NGC) und Satellitenbahn-Tracking (SGP4 / TLE).

## Überblick

`py-stars` analysiert Nachtaufnahmen von Smartphones und Weitwinkel-Kameras:
1. **Lost-in-Space Plate Solving**: Bestimmt Himmelsausrichtung (RA, Dec, Roll) in Millisekunden gegen den Gaia DR3 Katalog.
2. **Dynamische FOV-Erkennung**: Berechnet das Bildfeld (HFOV, VFOV, DFOV) dynamisch aus EXIF-Metadaten (35mm-Äquivalentbrennweite & Sensor-Seitenverhältnis) ohne fest verdrahtete Konstanten.
3. **Objektiv-Verzeichnungskorrektur (Distortion Calibration)**: Unterstützt radiale (Brown-Conrady) und polynomielle Kameramodelle.
4. **Atmosphärische Refraktionskorrektur**: Modelliert Lichtbeugung am Horizont mittels Bennett-Formel unter Berücksichtigung von Beobachterhöhe (Luftdruck) und Temperatur.
5. **Katalog-Cross-Matching & Residuen**: Gleicht alle sichtbaren Katalogsterne im Bildfeld mit den detektierten Zentroiden ab und berechnet astrometrische Residuen ($dx, dy, \text{RMSE}$).
6. **Grenzhelligkeits-Analyse (Limiting Magnitude)**: Misst die Detektionsrate als Funktion der visuellen Magnitude (50%- und 90%-Vollständigkeitsgrenze, schwächster detektierter Stern) und kalibriert die Instrumental-Photometrie.
7. **Planeten- & Mond-Ephemeriden**: Exakte topozentrische Koordinaten (RA/Dec, Alt/Az, Phase, Helligkeit, Parallaxe) für Sonne, Mond und Planeten (Merkur bis Pluto) zum Aufnahmezeitpunkt via Skyfield / JPL DE421.
8. **Deep Sky Objects (Messier & NGC)**: Kuratierter Katalog mit allen 110 Messier-Objekten und hellen NGC-Objekten (Galaxien, Nebel, Sternhaufen) inklusive FOV-Projektion und Bounding-Shapes.
9. **Satelliten-Tracking (TLE & SGP4)**: Automatischer Download von Two-Line Elements (CelesTrak / Space-Track), SGP4-Bahnorbitpropagation, Strichspur-Berechnung über die Belichtungszeit und Korrelation mit Bild-Zentroiden.

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
Planeten- & Mond-Ephemeriden + Deep Sky Objects (Messier / NGC)
       ↓
Satellitenbahn-Propagation (SGP4 / TLE) & Strichspur-Matching
       ↓
Grenzhelligkeit, Photometrie & Visuelle Overlays (PNG)
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

Führt die komplette Analyse durch (Plate Solving, Verzerrungskorrektur, Refraktion, Stern-Cross-Matching, Ephemeriden, DSOs, Grenzhelligkeit und Diagnoseplots):

```bash
uv run py-stars solve data/IMG_9144.HEIC --distortion radial --satellites --plot
```

#### Beispiel-Ausgabe:

```text
Loaded distortion model: iphone11_camera_radial.bin
Processing 1 image(s)...

======================================================================
  Processing: IMG_9144.HEIC
======================================================================
=== Plate Solve Result ===
  RA:        160.1849° (10h 40m 44.38s)
  Dec:       +43.6722°  (+43° 40' 19.99")
  Roll:      -149.10°
  FOV:       66.41°
  Matches:   82
  RMSE:      119.70"
  Time:      0.7ms
  Prob:      2.47e-58

--- Catalog Matching & Astrometric Accuracy ---
  Catalog Stars in FOV:  1146
  Mean Residual:         2.73 px (162.1")
  Median Residual:       2.45 px (145.0")
  Astrometric RMSE:      188.86" (3.19 px)
  Atmospheric Refraction: Enabled
  Distortion Model:       Active

--- Limiting Magnitude & Star Detectability ---
  Brightest Star:        1.57 mag
  Faintest Star:         6.88 mag
  50% Limiting Magnitude: 2.00 mag

  Detection by Magnitude:
    Mag [0.0 - 2.0]:  2 /  3 ( 66.7%)
    Mag [2.0 - 3.0]:  4 /  9 ( 44.4%)
    Mag [3.0 - 4.0]:  9 / 28 ( 32.1%)
    Mag [4.0 - 4.5]:  8 / 25 ( 32.0%)
    Mag [4.5 - 5.0]: 24 / 65 ( 36.9%)
    Mag [5.0 - 5.5]: 16 / 96 ( 16.7%)
    Mag [5.5 - 6.0]: 15 / 163 (  9.2%)
    Mag [6.0 - 6.5]:  6 / 277 (  2.2%)
    Mag [6.5 - 7.0]:  5 / 480 (  1.0%)

  Photometry Zero-point:  12.48 mag (scatter σ = 0.73 mag)

--- Deep Sky Objects (DSOs) in FOV ---
  🌌 M40     Double Star        (Winnecke 4 Double Star)      8.4 mag  [UMa]
  🌌 M51     Spiral Galaxy      (Whirlpool Galaxy)            8.4 mag  [CVn]
  🌌 M63     Spiral Galaxy      (Sunflower Galaxy)            8.6 mag  [CVn]
  🌌 M65     Spiral Galaxy      (Leo Triplet Galaxy 1)        9.3 mag  [Leo]
  🌌 M66     Spiral Galaxy      (Leo Triplet Galaxy 2)        8.9 mag  [Leo]
  🌌 M81     Spiral Galaxy      (Bode's Galaxy)               6.9 mag  [UMa]
  🌌 M82     Starburst Galaxy   (Cigar Galaxy)                8.4 mag  [UMa]
  🌌 M94     Spiral Galaxy      (Croc's Eye Galaxy)           8.2 mag  [CVn]
  🌌 M97     Planetary Nebula   (Owl Nebula)                  9.9 mag  [UMa]
  🌌 M106    Spiral Galaxy                                    8.4 mag  [CVn]
  🌌 M108    Spiral Galaxy      (Surfboard Galaxy)           10.0 mag  [UMa]
  🌌 M109    Spiral Galaxy      (Vacuum Cleaner Galaxy)       9.8 mag  [UMa]
  🌌 NGC 4565 Spiral Galaxy      (Needle Galaxy)               9.6 mag  [Com]
Saved diagnostic visualization: output/IMG_9144_diagnostics.png
Saved ephemeris & DSO overlay: output/IMG_9144_ephemeris_overlay.png
```

---

### 2. Planeten, Mond & Deep Sky Objects abfragen (`ephem`)

Gibt eine detaillierte Himmels- und Bildfeld-Tabelle aller Planeten und Messier/NGC-Objekte für den exakten Aufnahmezeitpunkt und GPS-Standort aus:

```bash
uv run py-stars ephem data/IMG_9144.HEIC --plot
```

#### Beispiel-Ausgabe:
```text
======================================================================
  Ephemerides & Deep Sky Objects: IMG_9144.HEIC
======================================================================
Observer: 47.412136° N, 9.630881° E, Alt: 405.8 m
UTC Time: 2026-08-14T21:17:49.990000+00:00

Plate Solve: RA=160.1849°, Dec=+43.6722°, FOV=66.41°

--- Solar System Bodies (All-Sky Topocentric) ---
Body       | RA (App)       | Dec            | Alt     | Az      | Mag    | Phase  | In FOV
--------------------------------------------------------------------------------
Sun        | 09h 36m 23.6s  | +14° 15' 35.7" |  -22.1° |  326.2° | -26.7  |  100%  | down  
Moon       | 11h 18m 05.9s  | +01° 31' 47.0" |  -20.2° |  296.1° | -6.7   |    6%  | down  
Mercury    | 08h 45m 26.8s  | +19° 01' 18.5" |  -21.4° |  340.3° | -1.2   |   83%  | down  
Venus      | 12h 25m 45.6s  | -04° 16' 18.4" |  -13.8° |  278.6° | -4.3   |   49%  | down  
Mars       | 06h 08m 33.6s  | +23° 42' 17.3" |  -16.7° |   18.9° | +1.3   |   93%  | down  
Jupiter    | 08h 48m 54.7s  | +18° 18' 45.6" |  -21.9° |  339.3° | -1.8   |  100%  | down  
Saturn     | 00h 55m 48.8s  | +03° 09' 42.9" |   +7.9° |   93.7° | +0.9   |  100%  | (up)  
Uranus     | 04h 12m 25.8s  | +20° 58' 45.5" |   -8.7° |   45.3° | +5.7   |  100%  | down  
Neptune    | 00h 15m 40.9s  | +00° 10' 07.8" |  +12.4° |  103.3° | +7.8   |  100%  | (up)  
Pluto      | 20h 27m 30.8s  | -23° 32' 39.6" |  +17.9° |  165.7° | +14.5  |  100%  | (up)  

--- Deep Sky Objects in Camera FOV (13 objects) ---
  🌌 M40    | Double Star        | (Winnecke 4 Double Star) |  8.4 mag | (1855.4 px,  321.1 px)
  🌌 M51    | Spiral Galaxy      | (Whirlpool Galaxy)       |  8.4 mag | ( 961.0 px,  123.6 px)
  🌌 M63    | Spiral Galaxy      | (Sunflower Galaxy)       |  8.6 mag | ( 772.1 px,  424.1 px)
  🌌 M65    | Spiral Galaxy      | (Leo Triplet Galaxy 1)   |  9.3 mag | ( 586.2 px, 2762.7 px)
  🌌 M66    | Spiral Galaxy      | (Leo Triplet Galaxy 2)   |  8.9 mag | ( 564.6 px, 2757.2 px)
  🌌 M81    | Spiral Galaxy      | (Bode's Galaxy)          |  6.9 mag | (2985.3 px,  359.5 px)
  🌌 M82    | Starburst Galaxy   | (Cigar Galaxy)           |  8.4 mag | (2999.7 px,  321.4 px)
  🌌 M94    | Spiral Galaxy      | (Croc's Eye Galaxy)      |  8.2 mag | ( 907.9 px,  703.1 px)
  🌌 M97    | Planetary Nebula   | (Owl Nebula)             |  9.9 mag | (2112.1 px,  829.7 px)
  🌌 M106   | Spiral Galaxy      |                          |  8.4 mag | (1410.2 px,  751.7 px)
  🌌 M108   | Spiral Galaxy      | (Surfboard Galaxy)       | 10.0 mag | (2154.4 px,  815.9 px)
  🌌 M109   | Spiral Galaxy      | (Vacuum Cleaner Galaxy)  |  9.8 mag | (1791.3 px,  662.8 px)
  🌌 NGC 4565 | Spiral Galaxy      | (Needle Galaxy)          |  9.6 mag | ( 287.9 px, 1410.4 px)
Saved ephemeris & DSO overlay: output/IMG_9144_ephem_dso.png
```

---

### 3. Satelliten-Bahnen & Strichspuren tracken (`satellites`)

Lädt TLEs von CelesTrak (z. B. `stations`, `visual`, `starlink`, `active`) herunter oder verwendet lokale TLE-Dateien, propagiert die Satellitenpositionen via SGP4 und korreliert Strichspuren mit den detektierten Sternpunkten:

```bash
uv run py-stars satellites data/IMG_9144.HEIC --tle data/tles/sample_satellites.tle --plot
```

---

### 4. EXIF-Metadaten & GPS inspizieren (`info`)

```bash
uv run py-stars info data/IMG_9144.HEIC
```

---

### 5. Kamera-Verzeichnung kalibrieren (`calibrate`)

```bash
uv run py-stars calibrate data/*.HEIC --model radial --output data/iphone11_camera_radial.bin
```

---

## Python API

```python
from py_stars import (
    solve_heic_photo,
    query_solar_system_ephemerides,
    project_dsos_to_image,
    parse_tle_data,
    query_satellites_in_fov,
)

# 1. Foto komplett lösen inklusive Planeten, DSOs & Satelliten
result = solve_heic_photo(
    "data/IMG_9144.HEIC",
    query_ephemeris=True,
    query_dso=True,
    query_satellites=True,
    satellite_tle_source="data/tles/sample_satellites.tle",
)

solve_res = result["solve_result"]
print(f"Pointing: RA={solve_res.ra_deg:.4f}°, Dec={solve_res.dec_deg:+.4f}°")

# 2. Planeten im Bildfeld
for planet in result["planets_in_fov"]:
    print(f"Planet: {planet.name}, Pixel: ({planet.image_x:.1f}, {planet.image_y:.1f})")

# 3. Deep Sky Objekte (Messier / NGC) im Bildfeld
for dso in result["dsos_in_fov"]:
    print(f"DSO: {dso.dso.id} {dso.dso.name} ({dso.dso.obj_type}), Mag={dso.dso.magnitude:.1f}")

# 4. Satelliten-Treffer
for sat_pass in result["satellite_result"].passes:
    print(f"Satellit: {sat_pass.name}, Strichspur: {sat_pass.streak_length_px:.1f} px")
```

## Tests

```bash
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
```
