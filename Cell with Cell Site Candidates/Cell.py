from qgis.core import QgsApplication, QgsProject, QgsVectorLayer
from qgis.gui import QgsMapCanvas, QgsMapCanvasItem
import sys
import math
import random

# Define frequencies globally for accessibility
FREQUENCIES = {
    "3G": [700, 715, 730, 755, 780, 805, 830],
    "4G": [1800, 1815, 1850, 1870, 1900, 1930]
}

class Cell:
    def __init__(self, cell_id):
        self.cell_id = cell_id
        self.towers = []  # Stores Cell_Tower_Vertex instances

class Cell_Tower_Vertex:
    def __init__(self, x, y, frequency, node_type):
        
        self.x = x
        self.y = y
        self.op_frequency = frequency
        self.node_type = node_type
        
        # Randomized base station height (150-220m range)
        self.h_ct = 200 + random.choice([-1, 1]) * random.randint(1, 50)
        self.h_ms = 1.5  # Mobile device height
        
        # Calculate coverage radius based on technology
        self.link_budget = self._calculate_link_budget()
        self.coverage_radius = (
            self._okumura_hata_distance() 
            if node_type == "3G" 
            else self._cost231_distance()
        )

    def _calculate_link_budget(self):
        """Calculate maximum allowable path loss"""
        P_t = 30 if self.node_type == "3G" else 50  # Transmit power (dBm)
        P_r = -105 if self.node_type == "3G" else -100  # Receiver sensitivity
        G_t, G_r = 15, 2  # Antenna gains (dBi)
        return P_t + G_t + G_r - P_r  # Simplified model

    def _cost231_distance(self):
        """COST-231 Hata model for 4G (1500-2000 MHz)"""
        f = self.op_frequency
        L = self.link_budget
        hb, hm = self.h_ct, self.h_ms
        
        a_hm = 3.2 * (math.log10(11.75 * hm)**2 - 4.97)  # Urban correction
        numerator = L - 46.3 - 33.9 * math.log10(f) + 13.82 * math.log10(hb) - a_hm
        denominator = 44.9 - 6.55 * math.log10(hb)
        return 10 ** (numerator / denominator)  # Distance in km

    def _okumura_hata_distance(self):
        """Okumura-Hata model for 3G (150-1500 MHz)"""
        f = self.op_frequency
        L = self.link_budget
        hb, hm = self.h_ct, self.h_ms
        
        a_hm = 0.8 + (1.1 * math.log10(f) - 0.7) * hm - 1.56 * math.log10(f)
        A = 69.55 + 26.16 * math.log10(f) - 13.82 * math.log10(hb) - a_hm
        return 10 ** ((L - A) / (44.9 - 6.55 * math.log10(hb)))

def main():
    
    # Load cell site candidates (replace with actual path)
    cells = []
    layer = QgsVectorLayer(r"C:\Users\Ramcie Labadan\Documents\THESIS\Maps and Other Geospatial Data\cell-bounded multi-candidate sites\candidate cell sites.shp", "Cell Sites", "ogr")
    
    # Process features with graph-based clustering
    for feature in layer.getFeatures():
        cell_id = feature["Cell ID"]

        if len(cells) == 0:
            cells.append(Cell(cell_id))
        elif cell_id not in get_used_cellIDs(cells):
            cells.append(Cell(cell_id))

        geom = feature.geometry().asPoint()
        tech = feature["Cell Tech"]  # Field indicating 3G/4G
        print(f"Cell tech: {tech}")
        
        # Assign random frequency from approved band
        freq = random.choice(FREQUENCIES[tech])
        print(f"freq: {freq}")

        # Create cell tower with propagation parameters
        tower = Cell_Tower_Vertex(
            x=geom.x(),
            y=geom.y(),
            frequency=freq,
            node_type=tech
        )
        i = 0
        for cell in cells:
            if cell.cell_id == cell_id:
                cells[i].towers.append(tower)
            i+=1
        
        
    # Print network analysis
    for cell in cells:
        print(f"Cell {cell.cell_id} with {len(cell.towers)} towers")
        for tower in cell.towers:
            print(f"\t{tower.node_type} @ {tower.op_frequency} MHz: "
                  f"{tower.coverage_radius:.1f} km coverage")

    
def get_used_cellIDs(cells):
    cell_ids = []
    for cell in cells:
        cell_ids.append(cell.cell_id)
    return cell_ids

if __name__ == "__main__":
    # Initialize QGIS
    qgs = QgsApplication([], False)
    qgs.setPrefixPath(r"C:\Program Files\QGIS 3.34.12\apps\qgis-ltr", True)
    qgs.initQgis()

    main()

    # Cleanup
    qgs.exitQgis()
