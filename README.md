Camiguin Cellular‑Network Optimization Simulation

This repository hosts the Camiguin Cellular‑Network Optimization Simulator, a PyQGIS‑powered desktop application that designs a heterogeneous 3G/4G rollout for Camiguin Island by combining geospatial analysis, graph algorithms, and radio‑propagation models.

1. Simulation Overview

Module

Role

Data Loader

Imports raster and vector layers (DEM, population hexes, road network, candidate cells/sites).

Coverage Engine

Computes Okumura‑Hata (3G) and COST‑231 (4G) radii, builds coverage polygons, derives overlap graph.

Frequency Planner

Greedy graph‑colouring assigns channels to minimise co‑channel interference and respect reuse distance.

Handover Analyzer

Builds an undirected overlap graph; computes degree, path redundancy and flags one‑edge towers.

Interference Monitor

Builds an interference graph and quantifies residual interference per site.

Manual Site Manager

Supports on‑map move / add / delete of towers with live recomputation of all metrics.

2. Layer‑Loading Workflow

raster_path         = r"...\Camiguin Raster Base Maps\Camiguin_fin1.tif"
hex_layer_path      = r"...\Population Cell Density Analysis\Popn Density Cells.shp"
roads_layer_path    = r"...\Road Network by Cell\road_network.shp"
candidate_cells_path= r"...\Final Candidate Cells\v1\final_candidate_cells.shp"
candidate_sites_path= r"...\Final Candidate Cell Sites\v3\final_candidate_cell_sites.shp"

Camiguin_fin1.tif – reference DEM/orthophoto used as basemap.

Popn Density Cells.shp – hexagonal mesh with per‑cell population counts.

road_network.shp – classified road polylines used as weighted edges.

final_candidate_cells.shp – filtered hexes that meet elevation & land‑cover constraints.

final_candidate_cell_sites.shp – point layer of peak‑elevation candidates within each hex.

The DataLoader verifies each layer’s validity, recolours them for clarity, and registers them in the active QgsProject before handing control to the optimisation engine.

3. Changing Data Paths

Copy or clone the entire Maps and Other Geospatial Data directory to your preferred location (e.g. D:/geo/Camiguin/).

Open config.py (or the header of main.py, depending on your fork).

Replace the hard‑coded absolute paths with either:

Option A – Absolute paths

DATA_ROOT = r"D:/geo/Camiguin/Maps and Other Geospatial Data"
raster_path          = DATA_ROOT + r"/Camiguin Raster Base Maps/Camiguin_fin1.tif"
hex_layer_path       = DATA_ROOT + r"/Population Cell Density Analysis/Popn Density Cells.shp"
# …and so on

Option B – Environment variables

set CAM_DATA=D:/geo/Camiguin/Maps and Other Geospatial Data

import os, pathlib
DATA_ROOT = pathlib.Path(os.environ['CAM_DATA'])
raster_path = DATA_ROOT / "Camiguin Raster Base Maps" / "Camiguin_fin1.tif"
# …

Save and restart the simulator.  The layer‑validation log in VSCode’s terminal will confirm each successful load.

Tip Keep directory names identical to avoid touching style (*.qml) references embedded in the project.

4. Running the Simulator

# Activate QGIS‑aware virtual environment (see setup section below)
python main.py --output results/camiguin.qgz --log debug

The script produces:

results/camiguin.qgz – a self‑contained QGIS project with all generated layers.

reports/summary.md – tabulated KPIs (coverage %, average SINR, interference histogram, handover degree stats).

Shapefiles/GeoPackages of the optimised towers and coverage polygons for external GIS use.

5. PyQGIS Development Setup for VSCode

If you have already configured your workstation, you may skip this section.

Prerequisites

QGIS ≥ 3.34

Visual Studio Code

Python 3.9+ compatible with QGIS’s ABI

Platform‑specific package manager (OSGeo4W, Homebrew, APT/YUM, Flatpak, Snap)

1  Install QGIS

# 1  Download and run the **64‑bit OSGeo4W Network Installer**
#    https://download.osgeo.org/osgeo4w/osgeo4w-setup-x86_64.exe
# 2  Choose **Advanced Install**.
# 3  In the package list search for and tick:
#       • qgis‑ltr *or* qgis‑dev (GUI + Python bindings)
#       • python3‑qgis (stand‑alone bindings)
#       • gdal, proj, grass (optional but recommended)
# 4  Complete the install accepting defaults.

Add QGIS to the system PATH so VSCode & Python can locate the DLLs:

setx OSGEO4W_ROOT "C:\OSGeo4W64"
setx QGIS_PREFIX_PATH "%OSGEO4W_ROOT%\apps\qgis"
setx PATH "%OSGEO4W_ROOT%\bin;%OSGEO4W_ROOT%\apps\qgis\bin;%PATH%"

💡 Open a new PowerShell or Command Prompt after setting variables so the changes propagate to VSCode.

Verify that the bindings load:

%OSGEO4W_ROOT%\apps\qgis\bin\python3 - <<"PY"
import qgis, sys
print("Python exe:", sys.executable)
print("QGIS core found at:", qgis.__file__)
PY

If both paths print without errors, you are ready to proceed.

Download the .dmg, double‑click, and follow prompts.

sudo apt update && sudo apt install qgis python3-qgis

2  Configure Python Environment

# optional virtual‑env (keeps system QGIS clean)
python3 -m venv ~/.venvs/pyqgis
source ~/.venvs/pyqgis/bin/activate
pip install pyqt5

Locate QGIS’s bundled Python path:

python3 -c "import qgis, sys; print(sys.executable); print(qgis.__file__)"

3  VSCode Workspace Settings

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

macOS/Linux users: replace with the appropriate paths or use an .env file.

Enable linting (pylint) and IntelliSense for full API auto‑completion.

4  Test a PyQGIS Script

from qgis.core import QgsApplication, QgsProject
QgsApplication.setPrefixPath("C:/OSGeo4W64/apps/qgis", True)
qgs = QgsApplication([], False); qgs.initQgis()
project = QgsProject.instance(); project.read('path/to/project.qgz')
print(project.mapLayers().keys()); qgs.exitQgis()

Run with:

python test_qgis.py

5  Troubleshooting

Symptom

Fix

ModuleNotFoundError: qgis

Check interpreter & extraPaths.

ABI mismatch

Ensure Python version matches QGIS build.

Plugin dev packaging

pip install qgis-plugin-ci or use QGIS Plugin Builder.

6. Project Team

Name

Key Roles

Ramcie M. Labadan

Team Leader · Lead Writer & Proof‑reader · Lead Simulation Developer · QGIS Geospatial Analyzer

Sammy Isidro

Lead Technical Writer · QGIS Geospatial Analyzer · Simulation Programmer

Francis Bengua

Lead QGIS Geospatial Analyzer · Technical Writer · Simulation Programmer

Haron Hakeen Lua

Thesis Adviser

------|-----------|
| Ramcie M. Labadan | Team Leader · Lead Writer & Proof‑reader · Lead Simulation Developer · QGIS Geospatial Analyzer |
| Sammy Isidro | Lead Technical Writer · QGIS Geospatial Analyzer · Simulation Programmer |
| Francis Bengua | Lead QGIS Geospatial Analyzer · Technical Writer · Simulation Programmer |

Enjoy exploring Camiguin’s optimisation landscape!  Pull requests for additional metrics, 5 G propagation, or alternative frequency‑planning heuristics are welcome.

