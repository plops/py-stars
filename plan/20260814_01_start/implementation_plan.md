# Implementierungsplan: Stern-Erkennung & Plate Solving für iPhone-Fotos (py-stars)

Dieses Dokument dient als umfassende Anleitung für Entwickler und autonome AI-Agenten, um die Architektur, Abhängigkeiten, Kontextdateien, Commit-Konventionen und Implementierungsschritte von `py-stars` zu verstehen und weiterzuentwickeln.

---

## 1. Kontext & Quellendokumente für AI-Agenten

Bevor ein AI-Agent mit der Weiterentwicklung beginnt, sollte er sich folgende Dateien in der angegebenen Reihenfolge anschauen:

| Datei | Pfad | Beschreibung |
|---|---|---|
| **Prompt** | `plan/20260814_01_start/prompt.txt` | Ursprüngliche Anforderungen von Wol Pumba (Auftraggeber, Zielsetzung, Spike-Anforderungen). |
| **Hintergrundwissen** | `plan/20260814_01_start/iphone-stars.md` | Geometrische Berechnungen für iPhone 11 Weitwinkelobjektiv ($71.5^\circ \times 56.8^\circ$ FOV, 26mm äquivalent), Sternkatalog-Analyse und Plate Solving Grundlagen. |
| **Abhängigkeiten** | `deps.md` | Liste aller Python- und System-Abhängigkeiten mitsamt GitHub-Organisationen für DeepWiki-MCP-Abfragen. |
| **Projektkonfiguration** | `pyproject.toml` | `uv`-Projektdefinition, Dependency-Versionen, Ruff- und Pytest-Konfigurationen. |
| **Serielle Tasks** | `task.md` | Serielle Schritt-für-Schritt Abarbeitungsliste für Implementierung und Verifikation. |
| **HEIC-Loader** | `src/py_stars/heic_loader.py` | Transparentes Laden von Apple HEIC/HEIF-Bildern via `pillow-heif` und Konvertierung in Grayscale/RGB. |
| **Stern-Erkennung** | `src/py_stars/star_detector.py` | Subpixel-Centroid-Extraktion (`tetra3rs.extract_centroids`) sowie OpenCV-basierte Blob-Detektion und CLAHE-Preprocessing. |
| **Plate Solver** | `src/py_stars/plate_solver.py` | Lost-in-Space Plate Solving via `tetra3rs` und Gaia DR3 Katalog, DB-Generierung für Weitwinkel-FOV, RA/Dec/Roll-Formatierung. |
| **Visualisierung** | `src/py_stars/visualizer.py` | Erzeugung von Annotationsbildern (`*_stars.png`, `*_brightness.png`, `*_summary.png`) mit Hervorhebung gematchter Sterne. |
| **Spike-Pipeline** | `scripts/run_spike.py` | End-to-End Pipeline-Skript mit Pfaden zu Beispiel-HEIC-Dateien und Print-Ausgaben für jeden Einzelschritt. |
| **Tests** | `tests/` | Unit- und Integrationstests für alle Module (`test_heic_loader.py`, `test_star_detector.py`, `test_plate_solver.py`, `test_visualizer.py`). |

---

## 2. Analyse der Anforderungen & Vorschläge für Erweiterungen

### Abgedeckte Anforderungen:
1. ✅ **iPhone HEIC-Unterstützung**: Dekodierung von Apple HEIC-Dateien (`pillow-heif` mit `libheif`).
2. ✅ **Stern-Lokalisierung**: Subpixel-Schwerpunktbestimmung für Sternpunkte.
3. ✅ **Plate Solving**: Bestimmung von Himmelskoordinaten (RA, Dec, Roll, FOV).
4. ✅ **uv & Ruff Tooling**: Paketmanagement mit `uv`, sauberes Linting und Formatting mit `ruff`.
5. ✅ **Expliziter Spike-Code**: Klare, zeilenweise lesbare Module, hardcodierte Pfade im Spike-Skript.
6. ✅ **Deps-Dokumentation mit GitHub Orgs**: `deps.md` für einfache DeepWiki-Abfragen.
7. ✅ **Vollständige Testabdeckung**: Unit-Tests mit synthetischen Bildern und Integrationstests mit realen HEIC-Dateien.

### Vorschläge für weitere sinnvolle Features & Anforderungen:
1. **EXIF-Metadaten & Sensor-Kalibrierung**:
   - Auslesen der genauen Brennweite, ISO, Belichtungszeit und des iPhone-Modells aus den EXIF-Tags des HEIC-Bildes zur automatischen FOV-Berechnung (z. B. Weitwinkel vs. Ultraweitwinkel vs. Teleobjektiv).
2. **GPS & Zeitstempel (Horizont-Koordinaten)**:
   - Kombination von EXIF-GPS-Koordinaten (Latitude/Longitude) und Aufnahmezeitstempel (UTC) mit `astropy.coordinates`, um aus RA/Dec die lokalen Koordinaten **Azimut und Elevation (Alt/Az)** sowie die sichtbaren Sternbilder/Planeten zu berechnen.
3. **Objektiv-Verzerrungskorrektur (Lens Distortion)**:
   - Smartphone-Objektive weisen im Randbereich tonnen- oder kissenförmige Verzeichnung auf. Integration von `tetra3rs.CameraModel.calibrate_camera()` bzw. `RadialDistortion` zur Erhöhung der Match-Genauigkeit.
4. **Mehrbild-Stacking (Noise Reduction)**:
   - Wenn mehrere Aufnahmen nacheinander gemacht werden: Alignment der Sterne und Median-Stacking zur Rauschreduktion und Erkennung lichtschwächerer Sterne.
5. **Konstellations-Overlay & Himmelskarten-Rendering**:
   - Einzeichnen von Sternbildlinien (z. B. Großer Wagen, Orion, Kassiopeia) und Benennung der hellsten Sterne direkt im Ausgabebild.

---

## 3. Conventional Commit Richtlinien

Alle Änderungen müssen dem **Conventional Commits 1.0.0** Standard folgen und eine aussagekräftige Beschreibung (Body) enthalten:

### Format
```text
<type>(<scope>): <kurze zusammenfassung im imperativ>

<ausführliche beschreibung der änderung, designentscheidungen, teststatus>
```

### Gültige Typen:
- `feat`: Neues Feature oder Modul
- `fix`: Bugfix
- `test`: Hinzufügen oder Anpassen von Tests
- `docs`: Dokumentation (z. B. README, Walkthrough, Plan)
- `refactor`: Code-Umbau ohne Verhaltensänderung
- `chore`: Tooling, Konfiguration, Abhängigkeiten

---

## 4. Architekturübersicht

```
                    ┌─────────────────────────┐
                    │      iPhone HEIC        │
                    └────────────┬────────────┘
                                 │
                     [pillow-heif / Pillow]
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │     Grayscale Array     │
                    │      (uint8 2D)         │
                    └────────────┬────────────┘
                                 │
                      [tetra3rs / OpenCV]
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   Top 100 Centroids     │
                    │  (x, y, brightness)     │
                    └────────────┬────────────┘
                                 │
                 [tetra3rs + Gaia DR3 Database]
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │    Plate Solve Result   │
                    │  RA, Dec, Roll, FOV,    │
                    │     Matched Stars       │
                    └────────────┬────────────┘
                                 │
                          [matplotlib]
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   Visualisierungen im   │
                    │    output/ Verzeichnis  │
                    └─────────────────────────┘
```
