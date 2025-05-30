# Camiguin Cellular‑Network Optimization Simulator

A PyQGIS‑driven desktop toolkit that designs a heterogeneous 3G/4G rollout for **Camiguin Island**, blending geospatial analysis, graph algorithms, and radio‑propagation modelling.

---

## Table of Contents

1. [Simulation Overview](#1-simulation-overview)
2. [Layer‑Loading Workflow](#2-layer‑loading-workflow)
3. [Changing Data Paths](#3-changing-data-paths)
4. [Running the Simulator](#4-running-the-simulator)
5. [PyQGIS + VSCode Setup](#5-pyqgis--vscode-setup)
6. [Project Team](#6-project-team)
7. [Contributing](#7-contributing)

---

## 1. Simulation Overview

| Module                   | Purpose                                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------------------ |
| **Data Loader**          | Ingests raster & vector assets (DEM, population hexes, roads, candidate cells/sites).            |
| **Coverage Engine**      | Computes Okumura‑Hata (3 G) and COST‑231 (4 G) radii, then builds coverage and overlap polygons. |
| **Frequency Planner**    | Greedy graph‑colouring minimises co‑channel interference and honours reuse distances.            |
| **Handover Analyzer**    | Constructs an undirected overlap graph, reporting degree, redundancy, and one‑edge towers.       |
| **Interference Monitor** | Quantifies residual interference via an interference graph.                                      |
| **Manual Site Manager**  | Move / add / delete towers interactively with live metric recomputation.                         |

---

## 2. Layer‑Loading Workflow

```python
raster_path          = r".../Camiguin Raster Base Maps/Camiguin_fin1.tif"
hex_layer_path       = r".../Population Cell Density Analysis/Popn Density Cells.shp"
roads_layer_path     = r".../Road Network by Cell/road_network.shp"
candidate_cells_path = r".../Final Candidate Cells/v1/final_candidate_cells.shp"
candidate_sites_path = r".../Final Candidate Cell Sites/v3/final_candidate_cell_sites.shp"
```

| Layer                                 | Description                                           |
| ------------------------------------- | ----------------------------------------------------- |
| **Camiguin\_fin1.tif**                | Reference DEM / orthophoto basemap.                   |
| **Popn Density Cells.shp**            | Hexagonal mesh with per‑cell population counts.       |
| **road\_network.shp**                 | Classified road polylines.                            |
| **final\_candidate\_cells.shp**       | Filtered hexes passing elevation & land‑cover checks. |
| **final\_candidate\_cell\_sites.shp** | Peak‑elevation points per candidate cell.             |

`DataLoader` validates each layer, recolours symbology, and registers assets in the active **QgsProject** before optimisation begins.

---

## 3. Changing Data Paths

1. Clone or copy **Maps and Other Geospatial Data** to a convenient location (e.g. `D:/geo/Camiguin/`).
2. Open `config.py` (or the constants section of `main.py`).
3. Replace hard‑coded paths with **either**: <br>**A · Absolute paths**

   ```python
   DATA_ROOT = r"D:/geo/Camiguin/Maps and Other Geospatial Data"
   raster_path = DATA_ROOT + r"/Camiguin Raster Base Maps/Camiguin_fin1.tif"
   # …repeat for other layers
   ```

   **B · Environment variable**

   ```bash
   # PowerShell / Bash
   export CAM_DATA="D:/geo/Camiguin/Maps and Other Geospatial Data"
   ```

   ```python
   import os, pathlib
   DATA_ROOT = pathlib.Path(os.environ["CAM_DATA"])
   raster_path = DATA_ROOT / "Camiguin Raster Base Maps" / "Camiguin_fin1.tif"
   ```
4. Restart the simulator—layer‑validation logs in VSCode confirm successful loads.

> **Tip :** Keep directory names unchanged to avoid breaking any embedded QML style links.

---

## 4. Running the Simulator

```bash
# Activate your QGIS‑aware virtual‑env (see section 5)
python main.py --output results/camiguin.qgz --log debug
```

Outputs

* `results/camiguin.qgz` — self‑contained QGIS project with generated layers.
* `reports/summary.md` — key performance indicators (coverage %, SINR, interference, handover stats).
* Shapefiles/GeoPackages of optimised towers & coverage polygons for external GIS workflows.

---

## 5. PyQGIS + VSCode Setup

> Skip if your workstation is already configured.

### 5.1 Prerequisites

* **QGIS ≥ 3.34**
* **Visual Studio Code**
* **Python 3.9+** compatible with QGIS ABI
* Platform‑specific manager: OSGeo4W (Win), Homebrew (macOS), APT/YUM (Linux)

### 5.2 Install QGIS

<details>
<summary>Windows (OSGeo4W)</summary>

```powershell
# 1 Download the 64‑bit OSGeo4W network installer
#   https://download.osgeo.org/osgeo4w/osgeo4w-setup-x86_64.exe
# 2 Choose **Advanced Install**.
# 3 Tick the following packages:
#     • qgis‑ltr *or* qgis‑dev
#     • python3‑qgis
#     • gdal, proj, grass (optional but recommended)
# 4 Finish with default options.

# Add QGIS paths for VSCode & Python
setx OSGEO4W_ROOT "C:\\OSGeo4W64"
setx QGIS_PREFIX_PATH "%OSGEO4W_ROOT%\\apps\\qgis"
setx PATH "%OSGEO4W_ROOT%\\bin;%OSGEO4W_ROOT%\\apps\\qgis\\bin;%PATH%"

# Verify bindings
%OSGEO4W_ROOT%\\apps\\qgis\\bin\\python3 - <<"PY"
import qgis, sys
print("Python exe:", sys.executable)
print("QGIS core at:", qgis.__file__)
PY
```

</details>

<details>
<summary>macOS</summary>

Download the `.dmg`, open, and follow prompts.

</details>

<details>
<summary>Linux (APT example)</summary>

```bash
sudo apt update && sudo apt install qgis python3-qgis
```

</details>

### 5.3 Configure Python Environment

```bash
# Optional: isolate dependencies
python3 -m venv ~/.venvs/pyqgis
source ~/.venvs/pyqgis/bin/activate
pip install pyqt5
```

Locate bundled Python:

```bash
python3 - <<"PY"
import qgis, sys; print(sys.executable); print(qgis.__file__)
PY
```

### 5.4 VSCode Workspace Settings

```jsonc
{
  "python.pythonPath": "C:/OSGeo4W64/apps/qgis/bin/python3.exe",
  "python.analysis.extraPaths": [
    "C:/OSGeo4W64/apps/qgis/python"
  ],
  "terminal.integrated.env.windows": {
    "PATH": "C:/OSGeo4W64/bin;${env:PATH}",
    "QGIS_PREFIX_PATH": "C:/OSGeo4W64/apps/qgis"
  }
}
```

For macOS/Linux, replace with appropriate paths or an `.env` file.

Enable linting (`pylint`) and IntelliSense for full API auto‑completion.

### 5.5 Smoke Test

```python
from qgis.core import QgsApplication, QgsProject
QgsApplication.setPrefixPath("C:/OSGeo4W64/apps/qgis", True)
qgs = QgsApplication([], False); qgs.initQgis()
print("Layers:", QgsProject.instance().mapLayers().keys())
qgs.exitQgis()
```

```bash
python test_qgis.py
```

### 5.6 Troubleshooting

| Symptom                     | Remedy                                                     |
| --------------------------- | ---------------------------------------------------------- |
| `ModuleNotFoundError: qgis` | Check interpreter & `extraPaths`.                          |
| ABI mismatch                | Ensure Python version matches QGIS build.                  |
| Packaging PyQGIS plugins    | `pip install qgis-plugin-ci` or use *QGIS Plugin Builder*. |

---

## 6. Project Team

| Member                | Responsibilities                                                                             |
| --------------------- | -------------------------------------------------------------------------------------------- |
| **Ramcie M. Labadan** | Team Lead · Lead Writer & Proof‑reader · Lead Simulation Developer · QGIS Geospatial Analyst |
| **Sammy Isidro**      | Lead Technical Writer · QGIS Geospatial Analyst · Simulation Programmer                      |
| **Francis Bengua**    | Lead QGIS Geospatial Analyst · Technical Writer · Simulation Programmer                      |
| **Haron Hakeen Lua**  | Thesis Adviser                                                                               |

---

## 7. Contributing

Pull requests are welcome—especially additions for 5 G propagation models, alternative frequency‑planning heuristics, and enhanced reporting. Please open an issue first to discuss substantial changes.

---

Enjoy exploring Camiguin’s optimisation landscape! 🚀
