#!/usr/bin/env python3 
import math
import sys
from PyQt5.QtGui import QColor, QPen, QPainter, QBrush, QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QGraphicsTextItem, QComboBox
)
from PyQt5.QtCore import Qt, QRectF
from qgis.core import (
    QgsApplication,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsSymbol,
    QgsPointXY,
    QgsDistanceArea,
    QgsWkbTypes
)
from qgis.gui import QgsMapCanvas, QgsMapCanvasItem, QgsMapTool

# Import the processing module.
import processing

# Frequency pools by technology (sorted descending to prioritize largest first)
frequencies = {
    "3G": sorted([950, 925, 900, 875, 850, 825], reverse=True),
    "4G": sorted([2100, 2050, 2000, 1950, 1900, 1850], reverse=True)
}

interference_threshold = {
    "3G": 10500,
    "4G": 2000    
}

# Collect only the optimized towers
def get_optimized_cell_towers(nodes):
    return [
        node
        for node in nodes
        if node.cell_id in optimized_camiguin_cellular_network
    ]

# Build an adjacency list keyed by FREQUENCY (MHz)
def build_interference_graph(nodes):
    optimized = get_optimized_cell_towers(nodes)

    # initialize an empty list for each possible freq
    interference_graph = {
        freq: []
        for freq_list in frequencies.values()
        for freq in freq_list
    }

    # bucket each optimized node under its frequency
    for node in optimized:
        interference_graph.setdefault(node.frequency, []).append(node)

    for key, value in interference_graph.items():
        print(f"Working under {key} MHz: {value}")

    return interference_graph

# Measure, for each optimized tower, the closest same‐freq neighbor
def get_interference_levels(interference_graph, nodes):
    optimized = get_optimized_cell_towers(nodes)

    for node in optimized:
        # all other towers on the same freq
        cochannel = [
            other
            for other in interference_graph.get(node.frequency, [])
            if other.cell_id != node.cell_id
        ]

        if not cochannel:
            # no co‐channel neighbors → zero interference
            node.interference_level = 0.0
            continue
        node.interference_level = 0
        thresh = interference_threshold.get(node.node_type, 1)
        for other in cochannel:
            distance = calculate_distance(node.mapPoint, other.mapPoint)
            if distance < thresh:
                node.interference_level += (((thresh - distance)/ thresh)/2)
            print(f"Under frequency({node.frequency}): Cell Tower no.{node.cell_id} is separated by {distance} meters to Cell Tower no.{other.cell_id}")



def greedy_graph_coloring(pt, tech, graph_manager):
    dummy = QgsPointXY(pt.x(), pt.y())
    opFreq_distances = {}
    optimized_cell_towers = get_optimized_cell_towers(graph_manager.nodes)
    for node in optimized_cell_towers:
        if node.frequency in frequencies[tech]:
            distance = calculate_distance(dummy, node.mapPoint)

            if node.frequency not in opFreq_distances.keys():
                opFreq_distances[node.frequency] = distance
            else:
                if distance < opFreq_distances[node.frequency]:
                    opFreq_distances[node.frequency] = distance

    farthest_frequency = max(opFreq_distances, key=opFreq_distances.get)
    

    for key, value in opFreq_distances.items():
        print(f"{key} MHz with {value} meters")

    print(f"Choice: {farthest_frequency}")        

    return farthest_frequency
    
def hata_distance(f, L_threshold, hb, hm):
    """Okumura-Hata model with density-based adjustments."""
    a_hm = (1.1 * math.log10(f) - 0.7) * hm - (1.56 * math.log10(f) - 0.8)
    A_0 = 69.55 + 26.16 * math.log10(f)
    numerator = L_threshold - A_0 + 13.82 * math.log10(hb) + a_hm + 2 * math.log10(f/28) + 5.4
    denominator = 44.9 - 6.55 * math.log10(hb)
    return 10 ** (numerator / denominator)

#Code1
def cost231_distance(f, L_threshold, hb, hm):
    Cm = 0            
    a_hm = 1.1 * (math.log10(f) - 0.7) * hm - (1.56 * math.log10(f) - 0.8)
    numerator = L_threshold - 46.3 - 33.9 * math.log10(f) + 13.82 * math.log10(hb) + a_hm - Cm
    denominator = 44.9 - 6.55 * math.log10(hb)
    return 10 ** (numerator / denominator)


def link_budget(Pt, Gt, Gr, Lo, Pr_sensitivity):
    """
    Computes the maximum allowable path loss (Lp_max) based on a link budget.
    Lp_max = Pt + Gt + Gr - Lo - Pr_sensitivity
    """
    return Pt + Gt + Gr - Lo - Pr_sensitivity

def get_coverage_distance(f, tech, hb=200, hm=1.5):

    Pr_sensitivity = -100
    if tech == "3G":
        # Use realistic values for 3G:
        Pt = 30     # dBm
        Gt = 10     # dBi
        Gr = 0
        Lo = 20     # Adjusted loss to achieve ~125 dB threshold
        Pr_sensitivity += -5
    elif tech == "4G":
        # Use realistic values for 3G:
        Pt = 40     # dBm
        Gt = 10     # dBi
        Gr = 0
        Lo = 15     

     

    L_threshold = link_budget(Pt, Gt, Gr, Lo, Pr_sensitivity)
    print(f"L_threshold: {L_threshold}")
    
    if tech == "3G":
        distance = hata_distance(f, L_threshold, hb, hm) 
    elif tech == "4G":
        distance = cost231_distance(f, L_threshold, hb, hm)
    
    return distance*1000
    
# -----------------------------------------------------------
# Global optimized network graph as adjacency list
# -----------------------------------------------------------
# Maps cell_id -> list of neighbor cell_ids
optimized_camiguin_cellular_network = {}

frequencies = {
    "3G": [950, 925, 900, 875, 850, 825],
    "4G": [2100, 2050, 2000, 1950, 1900, 1850]    
}


# -----------------------------------------------------------
# Utility functions for converting meters to canvas pixels
# -----------------------------------------------------------
def calculate_distance(point1, point2):
    """
    Computes the geodetic distance (in meters) between two QgsPointXY objects.
    """
    d = QgsDistanceArea()
    d.setSourceCrs(QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance().transformContext())
    d.setEllipsoid("WGS84")
    
    distance = d.measureLine(point1, point2)
    
    return distance

def metersPerPixel(canvas):
    extent = canvas.extent()
    center = extent.center()
    left = QgsPointXY(extent.xMinimum(), center.y())
    right = QgsPointXY(extent.xMaximum(), center.y())
    d = QgsDistanceArea()
    d.setSourceCrs(QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance().transformContext())
    d.setEllipsoid("WGS84")
    widthInMeters = d.measureLine(left, right)
    mpp = widthInMeters / canvas.width()
    return mpp

def metersToPixels(distance_meters, canvas):
    return distance_meters / metersPerPixel(canvas)

# -----------------------------------------------------------
# Node Class (derived from QgsMapCanvasItem)
# -----------------------------------------------------------
class Node(QgsMapCanvasItem):
    def __init__(self, canvas, graph_manager, x, y, node_type):
        super().__init__(canvas)
        self.canvas = canvas
        self.graph_manager = graph_manager
        self.node_type = node_type
        self.optimized = False
        
        self.frequency = None  
        self.service_level = None
        self.cell_id = None
        self.edges = []
        self.node_radius = 10  # for drawing only
        
        # Default; updated later if a value is provided.
        self.coverage_radius = None
        self.interference_level = None
        
        self.brush = QColor("yellow") if node_type == "3G" else QColor("green")
        
        self.selected = False
        
        self.setZValue(1)
        
        self.mapPoint = QgsPointXY(x, y)
        
        self.label = QGraphicsTextItem("", self)
        self.label.setDefaultTextColor(Qt.black)
        self.label.setPos(-self.node_radius/2, self.node_radius/2)
        self.updatePosition()

    def updatePosition(self):
        transform = self.canvas.getCoordinateTransform()
        screen_point = transform.transform(self.mapPoint)
        self.setPos(screen_point.x(), screen_point.y())
        self.prepareGeometryChange()
        self.update()
 
    def pixelCoverageRadius(self):
        return metersToPixels(self.coverage_radius, self.canvas)
    
    def boundingRect(self):
        r = self.pixelCoverageRadius()
        return QRectF(-r, -r, 2*r, 2*r)
    
    def paint(self, painter, option, widget):

        if self.optimized:
            pixel_radius = self.pixelCoverageRadius()
            coverage_rect = QRectF(-pixel_radius, -pixel_radius, 2*pixel_radius, 2*pixel_radius)

            # 1) Create a yellow color with reduced opacity (0–255)
            semi_green = QColor(0, 255, 0)   # pure yellow
            semi_green.setAlpha(50)            # ~20% opacity

            # 2) Use that as a fill brush, and draw a dashed outline
            painter.setPen(QPen(Qt.yellow, 2, Qt.DashLine))
            painter.setBrush(QBrush(semi_green))
            painter.drawEllipse(coverage_rect)

        # 3) Draw your node on top as before
        node_rect = QRectF(-self.node_radius/2, -self.node_radius/2,
                            self.node_radius, self.node_radius)
        painter.setPen(QPen(Qt.black, 1))
        painter.setBrush(QBrush(self.brush))
        painter.drawEllipse(node_rect)

        if self.selected:
            painter.setPen(QPen(Qt.yellow, 2))
            painter.setBrush(QBrush(QColor("yellow")))
            painter.drawEllipse(node_rect)

# -----------------------------------------------------------
# Edge Class (derived from QgsMapCanvasItem)
# -----------------------------------------------------------
class Edge(QgsMapCanvasItem):
    def __init__(self, canvas, start_node, end_node):
        super().__init__(canvas)
        self.canvas = canvas
        self.start_node = start_node
        self.end_node = end_node
        self.pen = QPen(Qt.white, 1)
        self.setZValue(0)
        self.update_position()

    def boundingRect(self):
        p1 = self.start_node.pos()
        p2 = self.end_node.pos()
        return QRectF(p1, p2).normalized().adjusted(-5, -5, 5, 5)

    def paint(self, painter, option, widget):
        p1 = self.start_node.pos()
        p2 = self.end_node.pos()
        painter.setPen(self.pen)
        painter.drawLine(p1, p2)

    def update_position(self):
        self.prepareGeometryChange()
        self.update()

class GraphMapTool(QgsMapTool):
    def __init__(self, canvas, graph_manager, main_window):
        super().__init__(canvas)
        self.canvas = canvas
        self.graph_manager = graph_manager
        self.main_window = main_window    # ← store this
        self.active_node = None
        self.start_pos   = None
        self.moved = False
        self.mode = 'move'  # 'move', 'add', 'delete'

    def canvasPressEvent(self, event):
        pt = event.mapPoint()
        if self.mode == 'add':
            self.main_window.add_custom_site(pt)
            return
        if self.mode == 'delete':
            node = self.findClickedNode(pt)
            if node:
                node.selected = True
                node.update()
                self.main_window.delete_custom_site()
            return
        
        node = self.findClickedNode(pt)
        print(f"The clicked node had the cell_id of {node.cell_id}")
        if node:
            self.active_node = node
            self.start_pos   = pt
            node.selected    = True
            node.update()
            for edge in self.graph_manager.edge_instances:
                if edge.start_node == self.active_node or edge.end_node == self.active_node:
                    edge.hide()
    
    def canvasMoveEvent(self, event):
        if self.mode != 'move' or not self.active_node:
            return
        new_pt = event.mapPoint()
        dx = new_pt.x() - self.start_pos.x()
        dy = new_pt.y() - self.start_pos.y()
        
        # shift the node’s geographic point
        mp = self.active_node.mapPoint
        self.active_node.mapPoint = QgsPointXY(mp.x() + dx, mp.y() + dy)
        self.start_pos = new_pt
        
        # move its screen‑item
        self.active_node.updatePosition()
        
    """
        # hide its edges while dragging
        for e in self.active_node.edges:
            e.hide()
        
        self.active_node.edges = []
        to_remove = []    
        for edge in self.graph_manager.edge_instances:
            if edge.start_node == self.active_node or edge.end_node == self.active_node:
                edge.hide()
        
        for edge in self.graph_manager.edge_instances:
            if edge.start_node.cell_id == self.active_node.cell_id or edge.end_node.cell_id == self.active_node.cell_id:
                edge.hide()
                edge.setParentItem(None)
                to_remove.append(edge)

        # 2. Remove them from edge_instances and nodes' edges lists
        for edge in to_remove:
            if edge in self.graph_manager.edge_instances:
                self.graph_manager.edge_instances.remove(edge)
            if edge.start_node.edges and edge in edge.start_node.edges:
                edge.start_node.edges.remove(edge)
            if edge.end_node.edges and edge in edge.end_node.edges:
                edge.end_node.edges.remove(edge)
        
        for vertex1, vertex2 in self.graph_manager.edges:
            if vertex1 == self.active_node.cell_id or vertex2 == self.active_node.cell_id:
                self.graph_manager.edges.remove((vertex1, vertex2))
        

    
    def canvasReleaseEvent(self, event):
        if not self.active_node:
            return

        # 4.1 Remove *all* lines touching this node
        self.graph_manager.edge_instances[:] = [
            e for e in self.graph_manager.edge_instances
            if not (e.start_node == self.active_node or e.end_node == self.active_node)
        ]
        self.graph_manager.edges = {
            (a,b) for (a,b) in self.graph_manager.edges
            if a != self.active_node.cell_id and b != self.active_node.cell_id
        }

        # 4.2 Recompute adjacency for this node (and optionally its neighbors)
        self.graph_manager.update_edges_per_node(self.active_node)
        # If you also want to restore edges between other nodes:
        for other in self.graph_manager.nodes:
            if other is not self.active_node:
                self.graph_manager.update_edges_per_node(other)

        self.active_node.selected = False
        self.active_node = None
        self.canvas.refresh()
    """
    
    def canvasReleaseEvent(self, event):
        
        if self.mode != 'move' or not self.active_node:
            return
        
        # rebuild all edges and refresh
        #self.graph_manager.update_edges_per_node(self.active_node)
        incidence = []
        
        self.active_node.edges = []
        to_remove = []    
        
        for edge in self.graph_manager.edge_instances:
            if edge.start_node.cell_id == self.active_node.cell_id or edge.end_node.cell_id == self.active_node.cell_id:
                edge.hide()
                edge.setParentItem(None)
                to_remove.append(edge)

        # 2. Remove them from edge_instances and nodes' edges lists
        for edge in to_remove:
            if edge in self.graph_manager.edge_instances:
                self.graph_manager.edge_instances.remove(edge)
            if edge.start_node.edges and edge in edge.start_node.edges:
                edge.start_node.edges.remove(edge)
            if edge.end_node.edges and edge in edge.end_node.edges:
                edge.end_node.edges.remove(edge)
        """
        for vertex1, vertex2 in self.graph_manager.edges:
            if vertex1 == self.active_node.cell_id or vertex2 == self.active_node.cell_id:
                self.graph_manager.edges.remove((vertex1, vertex2))
        """

        # new—iterate over a snapshot list
        for vertex1, vertex2 in list(self.graph_manager.edges):
            if vertex1 == self.active_node.cell_id or vertex2 == self.active_node.cell_id:
                self.graph_manager.edges.remove((vertex1, vertex2))


        optimized_camiguin_cellular_network[self.active_node.cell_id].clear()

        for vertex in self.graph_manager.nodes:
            if vertex.cell_id in optimized_camiguin_cellular_network.keys():
                distance = calculate_distance(self.active_node.mapPoint, vertex.mapPoint)
                total_coverage = self.active_node.coverage_radius + vertex.coverage_radius
                handover_margin = total_coverage * 0.10
                if distance < (total_coverage - handover_margin):
                    edge = Edge(self.canvas, self.active_node, vertex)
                    self.graph_manager.edge_instances.append(edge)
                    incidence.append(vertex.cell_id)
        self.graph_manager.manage_edges(self.active_node, incidence)
        optimized_camiguin_cellular_network[self.active_node.cell_id].extend(incidence)

        self.active_node.selected = False
        self.active_node.update()
        self.active_node = None
        self.moved = True #Check if manual management is erroneous
        

        # right here:
        self.main_window.get_level_of_handover()
        self.main_window.get_coverage_level()

        #self.graph_manager.redraw()  # you can combine refresh/frequency logic here
    

    def findClickedNode(self, pt):
        # 1000 m hit‑radius
        dummy = QgsPointXY(pt.x(), pt.y())
        for node in self.graph_manager.nodes:
            d = calculate_distance(node.mapPoint, dummy)
            if d <= 300.0:
                return node
        return None
    

# -----------------------------------------------------------
# GraphManager: Holds Nodes & Edges and loads candidate nodes
# -----------------------------------------------------------
class GraphManager:
    def __init__(self, canvas):
        self.canvas = canvas
        self.nodes = []
        self.edges = set()         # edges are tuples: (cell_id, incident_cell_id)
        self.edge_instances = []   # list to hold Edge instances

        self.node_type = "3G"  # default value

        self.candidate_sites = None
        self.candidate_cells = None
        self.DEM_layer = None

    def add_node(self, cell_id, x, y, frequency, service_level, node_type="0", buffer_km=None, tech=None, overlaps=None):
        if node_type != "0":
            node = Node(self.canvas, self, x, y, node_type)
        else:
            node = Node(self.canvas, self, x, y, self.node_type)
        node.cell_id = cell_id
        if buffer_km is not None:
            node.coverage_radius = buffer_km * 1000
        if tech is not None:
            node.node_type = tech
        if overlaps is not None:
            node.edges = overlaps
        if frequency is not None:
            node.frequency = frequency
        if service_level is not None:
            node.service_level = service_level
        self.nodes.append(node)
    
    def build_edges(self):
        for cell_id1, cell_id2 in self.edges:
            node1 = None
            node2 = None
            for vertex in self.nodes:
                if vertex.cell_id == cell_id1:
                    node1 = vertex
                elif vertex.cell_id == cell_id2:
                    node2 = vertex
                if node1 is not None and node2 is not None:
                    break
            if node1 is None or node2 is None:
                print(f"Warning: Missing node(s) for edge ({cell_id1}, {cell_id2}).")
                continue
            edge = Edge(self.canvas, node1, node2)
            self.edge_instances.append(edge)
    

    def update_edges_per_node(self, node):
        incidence = []
        for vertex in self.nodes:
            if vertex.cell_id in optimized_camiguin_cellular_network.keys():
                distance = calculate_distance(node.mapPoint, vertex.mapPoint)
                total_coverage = node.coverage_radius + vertex.coverage_radius
                handover_margin = total_coverage * 0.10
                if distance < (total_coverage - handover_margin):
                    edge = Edge(self.canvas, node, vertex)
                    self.edge_instances.append(edge)
                    incidence.append(vertex.cell_id)
        self.manage_edges(node, incidence)
    

    def load_nodes_from_candidate_layer(self):
        for site_feature in self.candidate_sites.getFeatures():
            geom = site_feature.geometry()
            if geom is None or geom.isEmpty():
                continue

            if geom.wkbType() == QgsWkbTypes.PointGeometry:
                point = geom.asPoint()
            else:
                point = geom.centroid().asPoint()
            
            cell_id_raw = site_feature["Cell ID"]
            try:
                cell_id = int(cell_id_raw)
            except Exception:
                cell_id = cell_id_raw

            frequency = site_feature["Frequency"]
            tech = site_feature["Cell Tech"]
            buffer_km = site_feature["Coverage"]
            service_level = site_feature["Serv. Lev."]
            overlaps = site_feature["Overlaps"] if "Overlaps" in site_feature.fields().names() else None
            if overlaps:
                incident_nodes = self.get_incident_nodes(overlaps)
            else:
                incident_nodes = []

            self.manage_edges(cell_id, incident_nodes)
            self.add_node(cell_id, point.x(), point.y(), frequency, service_level, node_type=tech, buffer_km=buffer_km, overlaps=incident_nodes)

        self.build_edges()

    def get_incident_nodes(self, overlaps):
        string_list = overlaps.split(',')
        num_overlaps = [int(num) for num in string_list if num.strip()]
        return num_overlaps
    
    def manage_edges(self, cell_id, incidence):
        for vertex in incidence:
            edge = (cell_id, vertex)
            self.edges.add(edge)
        #print(f"The edges here are: {self.edges}")

# -----------------------------------------------------------
# Main Application Window
# -----------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.canvas = QgsMapCanvas()
        self.canvas.setCanvasColor(Qt.white)
        self.canvas.enableAntiAliasing(True)
        self.canvas.setFixedSize(700, 600)

        self.coverage_patching = False

        crs = QgsCoordinateReferenceSystem("EPSG:4326")
        self.canvas.setDestinationCrs(crs)

        raster_path = r"C:\Users\Ramcie Labadan\Documents\THESIS\Maps and Other Geospatial Data\Camiguin Raster Base Maps\Camiguin_fin1.tif"
        raster_layer = QgsRasterLayer(raster_path, "Base Raster")
        if not raster_layer.isValid():
            print("Error: Base raster layer failed to load!")
        else:
            QgsProject.instance().addMapLayer(raster_layer)

        hex_layer_path = r"C:\Users\Ramcie Labadan\Documents\THESIS\Maps and Other Geospatial Data\Population Cell Density Analysis\Popn Density Cells.shp"
        hex_layer = QgsVectorLayer(hex_layer_path, "Hexagonal Cells", "ogr")
        if not hex_layer.isValid():
            print("Error: Hexagonal cells layer failed to load!")
        else:
            symbol = hex_layer.renderer().symbol()
            symbol.setColor(QColor("brown"))
            QgsProject.instance().addMapLayer(hex_layer)
            self.hex_layer = hex_layer    # <<< keep it for coverage testing

        roads_layer_path = r"C:\Users\Ramcie Labadan\Documents\THESIS\Maps and Other Geospatial Data\Road Network by Cell\road_network.shp"
        roads_layer = QgsVectorLayer(roads_layer_path, "Road Network", "ogr")
        if not roads_layer.isValid():
            print("Error: Road network layer failed to load!")
        else:
            symbol = roads_layer.renderer().symbol()
            symbol.setColor(QColor("blue"))
            symbol.setWidth(1.0)
            QgsProject.instance().addMapLayer(roads_layer)

        candidate_cells_path = r"C:\Users\Ramcie Labadan\Documents\THESIS\Maps and Other Geospatial Data\Final Candidate Cells\v1\final_candidate_cells.shp"
        candidate_cells_layer = QgsVectorLayer(candidate_cells_path, "Candidate Cells", "ogr")
        if not candidate_cells_layer.isValid():
            print("Error: Candidate cells layer failed to load!")
        else:
            QgsProject.instance().addMapLayer(candidate_cells_layer)

        candidate_sites_path = r"C:\Users\Ramcie Labadan\Documents\THESIS\Maps and Other Geospatial Data\Final Candidate Cell Sites\v3\final_candidate_cell_sites.shp"
        candidate_sites_layer = QgsVectorLayer(candidate_sites_path, "Candidate Cell Sites", "ogr")
        if not candidate_sites_layer.isValid():
            print("Error: Candidate cell sites layer failed to load!")
        else:
            QgsProject.instance().addMapLayer(candidate_sites_layer)

        self.canvas.setLayers([roads_layer, hex_layer, raster_layer])
        self.canvas.setExtent(raster_layer.extent())

        self.graph_manager = GraphManager(self.canvas)
        if candidate_sites_layer.isValid():
            self.graph_manager.candidate_sites = candidate_sites_layer
            self.graph_manager.candidate_cells = candidate_cells_layer
            self.graph_manager.load_nodes_from_candidate_layer()
        else:
            print("Candidate cell sites layer failed to load!")        

        self.map_tool = GraphMapTool(self.canvas, self.graph_manager, self)
        self.canvas.setMapTool(self.map_tool)

         
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.canvas)

        button_layout = QHBoxLayout()
        self.optimizer_btn = QPushButton("Optimize")
        self.optimizer_btn.clicked.connect(self.optimize)
        button_layout.addWidget(self.optimizer_btn)

        # Technology combo box (3G/4G)
        self.tech_combo = QComboBox()
        self.tech_combo.addItems(["3G", "4G"])
        self.tech_combo.setEnabled(False)
        button_layout.addWidget(self.tech_combo)

        # Add button
        self.add_btn = QPushButton("Add")
        self.add_btn.setCheckable(True)
        self.add_btn.toggled.connect(self.on_add_toggled)
        
        button_layout.addWidget(self.add_btn)

        # Delete button
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setCheckable(True)
        self.delete_btn.toggled.connect(self.on_delete_toggled)
        
        button_layout.addWidget(self.delete_btn)

        #self.add_btn.clicked.connect(self.add_custom_site)
        #self.delete_btn.clicked.connect(self.delete_custom_site)

        # initially disabled
        self.add_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.tech_combo.setEnabled(False)


        main_layout.addLayout(button_layout)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.setWindowTitle("Camiguin Cellular Network Optimization Simulator")

        # --- New code: Create a QGraphicsTextItem for displaying coverage level ---
        self.coverage_text_item = QGraphicsTextItem("")
        self.coverage_text_item.setDefaultTextColor(Qt.black)
        self.coverage_text_item.setFont(QFont("Arial", 14))
        self.coverage_text_item.setZValue(2)
        self.canvas.scene().addItem(self.coverage_text_item)
        # position it just below the handover label:
        self.coverage_text_item.setPos(10, 0)

        self.handover_text_item = QGraphicsTextItem("")
        self.handover_text_item.setDefaultTextColor(Qt.black)
        self.handover_text_item.setFont(QFont("Arial", 14))
        self.handover_text_item.setZValue(2)  # ensure it appears on top
        self.canvas.scene().addItem(self.handover_text_item)
        self.handover_text_item.setPos(10, 20)

        self.interference_text_item = QGraphicsTextItem("")
        self.interference_text_item.setDefaultTextColor(Qt.black)
        self.interference_text_item.setFont(QFont("Arial", 14))
        self.interference_text_item.setZValue(2)  # ensure it appears on top
        self.canvas.scene().addItem(self.interference_text_item)
        self.interference_text_item.setPos(10, 40)

        if self.map_tool.moved:
            self.get_level_of_handover()
            self.get_coverage_level()
            self.map_tool.moved = False
            print("YEAHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHh!!!!!!!!")
    

    def on_add_toggled(self, checked):
        if checked:
            self.delete_btn.setChecked(False)
            self.map_tool.mode = 'add'
            self.tech_combo.setEnabled(True)
        else:
            if not self.delete_btn.isChecked():
                self.map_tool.mode = 'move'
                self.tech_combo.setEnabled(False)

    def on_delete_toggled(self, checked):
        if checked:
            self.add_btn.setChecked(False)
            self.map_tool.mode = 'delete'
        else:
            if not self.add_btn.isChecked():
                self.map_tool.mode = 'move'


    def get_coverage_level(self):
        """Compute the % of hexagon vertices covered by at least one visible node."""
        total_verts = 0
        covered_verts = 0

        coverage_patching = False
        # iterate through every feature’s exterior ring vertices
        for feat in self.hex_layer.getFeatures():
            geom = feat.geometry()
            if geom.isMultipart():
                rings = geom.asMultiPolygon()
            else:
                rings = [geom.asPolygon()]
            counter = 0
            for polygon in rings:
                
                exterior = polygon[0]  # list of QgsPointXY, closed (first==last)
                for pt in exterior:
                    total_verts += 1
                    for node in self.graph_manager.nodes:
                        if not node.isVisible():
                            continue
                        dist = calculate_distance(QgsPointXY(pt), node.mapPoint)
                        if dist <= node.coverage_radius:
                            covered_verts += 1
                            counter += 1
                            break
            #print(f"counter ({counter}) / len(rings) {len(rings)} = {counter/len(rings)}")
            
            if counter/7 < 0.80:
                for node in self.graph_manager.nodes:
                    if node.cell_id == feat["id"]:
                        node.setVisible(True)
                        self.graph_manager.update_edges_per_node(node)
                        optimized_camiguin_cellular_network[node.cell_id] = []
                        
                        # Find all nodes connected to this one and get their cell_ids
                        for other_node in self.graph_manager.nodes:
                            if other_node.cell_id in optimized_camiguin_cellular_network.keys():
                                # Check if there's an edge between these nodes
                                for edge in self.graph_manager.edge_instances:
                                    if ((edge.start_node == node and edge.end_node == other_node) or 
                                        (edge.start_node == other_node and edge.end_node == node)):
                                        optimized_camiguin_cellular_network[node.cell_id].append(other_node.cell_id)
                                        break
                        node.optimized = True
                        coverage_patching = True
                        print(f"Coverage patching selected node: {node.cell_id}")
                        break
                covered_verts -= counter
                covered_verts += 7 
                
        pct = (covered_verts / total_verts * 100) if total_verts else 0
        self.coverage_text_item.setPlainText(f"Coverage Level: {pct}%")
        print(f"The number of optimized cell towers are: {len(optimized_camiguin_cellular_network.keys())}")
        
        self.get_level_of_handover()

    def get_level_of_handover(self):
        denominator = len(optimized_camiguin_cellular_network.keys())
        numerator = denominator
        for value in optimized_camiguin_cellular_network.values():
            if len(value) == 0:
                numerator -= 1
        coverage_percent = float(numerator/denominator)
        self.handover_text_item.setPlainText(f"Handover Level: {coverage_percent*100}%")
    
    def get_level_of_interference(self):
        denominator = len(optimized_camiguin_cellular_network.keys())
        numerator = 0
        op_cell_towers = get_optimized_cell_towers(self.graph_manager.nodes)
        for node in op_cell_towers:
            numerator += node.interference_level
        interference_percent = float(numerator/denominator)
        self.interference_text_item.setPlainText(f"Interference Level: {interference_percent*100}%")        

    def optimize(self):
        # Hide all nodes and edges.
        for node in self.graph_manager.nodes:
            node.setVisible(False)
        for edge in self.graph_manager.edge_instances:
            edge.setVisible(False)
        self.canvas.refresh()

        # Build set of critical cell IDs from candidate cells
        critical_cell_ids = set()
        optimize_cells = []
        for feature in self.graph_manager.candidate_cells.getFeatures():
            if feature["Serv. Lev."] == "Critical":
                critical_cell_ids.add(feature["Cell ID"])
                optimize_cells.append(feature)
        
        # Determine necessary enhanced cell IDs.
        necessary_priority_cell_ids = set()
        for feature in self.graph_manager.candidate_cells.getFeatures():
            if feature["Serv. Lev."] == "Priority":
                enhanced_cell_id = feature["Cell ID"]
                status = True

                geom1 = feature.geometry()
                if geom1.isMultipart():
                    point1 = geom1.centroid().asPoint()
                else:
                    point1 = geom1.asPoint()
                point_xy1 = QgsPointXY(point1.x(), point1.y())
                
                for crit_cell in optimize_cells:
                    geom2 = crit_cell.geometry()
                    if geom2.isMultipart():
                        point2 = geom2.centroid().asPoint()
                    else:
                        point2 = geom2.asPoint()
                    point_xy2 = QgsPointXY(point2.x(), point2.y())
                    
                    crit_coverage = crit_cell["Coverage"]
                    distance = calculate_distance(point_xy1, point_xy2)
                    if distance < crit_coverage:
                        status = False
                        break
                if status:
                    necessary_priority_cell_ids.add(enhanced_cell_id)
                    optimize_cells.append(feature)


        # Determine necessary enhanced cell IDs.
        necessary_enhanced_cell_ids = set()
        
        for feature in self.graph_manager.candidate_cells.getFeatures():
            if feature["Serv. Lev."] == "Enhanced":
                enhanced_cell_id = feature["Cell ID"]
                status = True

                geom1 = feature.geometry()
                if geom1.isMultipart():
                    point1 = geom1.centroid().asPoint()
                else:
                    point1 = geom1.asPoint()
                point_xy1 = QgsPointXY(point1.x(), point1.y())
                
                for crit_cell in optimize_cells:
                    geom2 = crit_cell.geometry()
                    if geom2.isMultipart():
                        point2 = geom2.centroid().asPoint()
                    else:
                        point2 = geom2.asPoint()
                    point_xy2 = QgsPointXY(point2.x(), point2.y())
                    
                    crit_coverage = crit_cell["Coverage"]
                    distance = calculate_distance(point_xy1, point_xy2)
                    if distance < crit_coverage:
                        status = False
                        break
                if status:
                    necessary_enhanced_cell_ids.add(enhanced_cell_id)
                    optimize_cells.append(feature)

        necessary_basic_cell_ids = set()
        for feature in self.graph_manager.candidate_cells.getFeatures():
            if feature["Serv. Lev."] == "Basic" or feature["Serv. Lev."] == "Trivial":
                basic_cell_id = feature["Cell ID"]
                status = True
                geom1 = feature.geometry()
                if geom1.isMultipart():
                    point1 = geom1.centroid().asPoint()
                else:
                    point1 = geom1.asPoint()
                point_xy1 = QgsPointXY(point1.x(), point1.y())
                
                for opt_cell in optimize_cells:
                    geom2 = opt_cell.geometry()
                    if geom2.isMultipart():
                        point2 = geom2.centroid().asPoint()
                    else:
                        point2 = geom2.asPoint()
                    point_xy2 = QgsPointXY(point2.x(), point2.y())
                    
                    crit_coverage = opt_cell["Coverage"]
                    distance = calculate_distance(point_xy1, point_xy2)
                    if distance < crit_coverage:
                        status = False
                        break
                if status:
                    necessary_basic_cell_ids.add(basic_cell_id)
                    optimize_cells.append(feature)
                
                
        print(f"Necessary basic cells: {necessary_basic_cell_ids}")
        optimize_cell_ids = critical_cell_ids | necessary_priority_cell_ids | necessary_enhanced_cell_ids | necessary_basic_cell_ids
        # Show nodes whose cell_id is in critical_cell_ids or necessary_enhanced_cell_ids.
        for node in self.graph_manager.nodes:
            if node.cell_id in optimize_cell_ids:
                node.setVisible(True)
                optimized_camiguin_cellular_network[node.cell_id] = []
            else:
                node.setVisible(False)

        # Show edges only if both connected nodes are visible.
        for edge in self.graph_manager.edge_instances:
            if edge.start_node.isVisible() and edge.end_node.isVisible():
                edge.setVisible(True)
                optimized_camiguin_cellular_network[edge.start_node.cell_id].append(edge.end_node.cell_id)
            else:
                edge.setVisible(False)
        
        service_levels = ["Trivial", "Basic", "Necessary", "Priority"]

        #Pseudo-BFS algorithm via checking an adjacency list
        for key, value in optimized_camiguin_cellular_network.items():
            if len(value) == 0:
                for service_level in service_levels:
                    for node in self.graph_manager.nodes:
                        if service_level == node.service_level and node.cell_id not in optimized_camiguin_cellular_network.keys() and node.cell_id in self.get_node_via_id(key).edges:
                            node.setVisible(True)

                            optimized_camiguin_cellular_network[node.cell_id] = []
                    
                            # Show edges only if both connected nodes are visible.
                            for edge in self.graph_manager.edge_instances:
                                if edge.start_node.isVisible() and edge.end_node.isVisible():
                                    edge.setVisible(True)
                                    optimized_camiguin_cellular_network[edge.start_node.cell_id].append(edge.end_node.cell_id)
                                else:
                                    edge.setVisible(False)

        self.coverage_patching = True
        self.node_coverage_visualization()
        self.canvas.refresh()
        self.print_out_optimized_network()
        self.get_coverage_level() 

        #self.get_level_of_handover()
        #self.coverage_patching = False
        # Enable add/delete controls
        self.remove_unnecessary()

        interference_graph = build_interference_graph(self.graph_manager.nodes)
        get_interference_levels(interference_graph, self.graph_manager.nodes)
        self.get_level_of_interference()

        self.data_printout()

        self.tech_combo.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.optimizer_btn.setEnabled(False)


    def remove_unnecessary(self):
        # 1. Figure out which cell_ids we want to keep
        valid_ids = set(optimized_camiguin_cellular_network.keys())

        # 2. Remove any Node instances whose cell_id isn't in valid_ids
        nodes_to_remove = [n for n in self.graph_manager.nodes if n.cell_id not in valid_ids]
        for node in nodes_to_remove:
            # remove from the QGIS scene
            self.canvas.scene().removeItem(node)
            # remove from our manager
            self.graph_manager.nodes.remove(node)

        # 3. Prune the optimized_camiguin_cellular_network dict itself (just in case)
        for cid in list(optimized_camiguin_cellular_network):
            if cid not in valid_ids:
                optimized_camiguin_cellular_network.pop(cid)

        # 4. Remove any Edge instances that touch a deleted node
        edges_to_remove = [
            e for e in self.graph_manager.edge_instances
            if e.start_node.cell_id not in valid_ids or e.end_node.cell_id not in valid_ids
        ]
        for edge in edges_to_remove:
            self.canvas.scene().removeItem(edge)
            self.graph_manager.edge_instances.remove(edge)

        # 5. Also clean up the underlying edges set of tuples
        self.graph_manager.edges = {
            (a, b) for (a, b) in self.graph_manager.edges
            if a in valid_ids and b in valid_ids
        }

        # 6. Finally, make sure each remaining adjacency list only refers to valid neighbors
        for cid, nbrs in optimized_camiguin_cellular_network.items():
            optimized_camiguin_cellular_network[cid] = [n for n in nbrs if n in valid_ids]

        # 7. Refresh the canvas so the deletions actually show up
        self.canvas.refresh()

        


    def add_custom_site(self, pt):
        tech = self.tech_combo.currentText()
        print(f"Add button clicked: adding a {tech} site")
        
        # Calculate a suitable frequency and coverage
        operational_frequency = greedy_graph_coloring(pt, tech, self.graph_manager)
        coverage_meters = get_coverage_distance(operational_frequency, tech)
        print(f"Coverage meters: {coverage_meters}")
        coverage_km = coverage_meters / 1000  # Convert to km for buffer_km parameter
        print(f"Coverage meters: {coverage_km}")
        # Create a new unique cell ID
        cell_id = max([n.cell_id for n in self.graph_manager.nodes if isinstance(n.cell_id, int)], default=0) + 1
        
        # Add the node with all required parameters
        self.graph_manager.add_node(cell_id, pt.x(), pt.y(), 
                                    operational_frequency, 
                                    service_level='Custom', 
                                    node_type=tech, 
                                    buffer_km=coverage_km, 
                                    tech=tech)
        
        # Find the newly created node (last one added to the list)
        new_node = self.graph_manager.nodes[-1]
        new_node.setVisible(True)  # Make it visible
        new_node.optimized = True
        

        # Initialize its entry in the optimized network
        optimized_camiguin_cellular_network[cell_id] = []
        
        # Update the edges for the new node
        self.graph_manager.update_edges_per_node(new_node)
        
        overlaps = []
        for a, b in self.graph_manager.edges:
            if a == cell_id:
                overlaps.append(b)
            elif b == cell_id:
                overlaps.append(a)

        new_node.edges = overlaps
        optimized_camiguin_cellular_network[cell_id].extend(overlaps)

        # Update metrics
        self.get_coverage_level()
        self.get_level_of_handover()
        
        # Refresh the canvas
        self.canvas.refresh()
    """
    def add_custom_site(self, pt):
        tech = self.tech_combo.currentText()
        print(f"Add button clicked: adding a {tech} site")
        operational_frequency = greedy_graph_coloring(pt, tech, self.graph_manager)
        coverage = get_coverage_distance(operational_frequency, tech)
        print(f"Coverage: {coverage}")
        cell_id = len(self.graph_manager.nodes) + 1
        self.graph_manager.add_node(self, cell_id, pt.x(), pt.y(), operational_frequency, node_type=tech, buffer_km=coverage, tech=tech, overlaps=None)
        for node in self.graph_manager.nodes:
            if node.cell_id == cell_id:
                node.isVisible(True)
                self.graph_manager.update_edges_per_node(node)


        add_node(self, cell_id, x, y, frequency, service_level, node_type="0", buffer_km=None, tech=None, overlaps=None)
        # Add a new node at clicked point
        tech = self.tech_combo.currentText()
        new_id = max([n.cell_id for n in self.graph_manager.nodes if isinstance(n.cell_id, int)], default=0) + 1
        self.graph_manager.add_node(new_id, pt.x(), pt.y(), frequency=None,
                                     service_level='Custom', node_type=tech,
                                     buffer_km=0.5, tech=tech)
        node = self.graph_manager.nodes[-1]
        node.setVisible(True)
        self.get_coverage_level()
        self.get_level_of_handover()
    """

    def delete_custom_site(self):
        print("Delete button clicked: removing selected site")
        """
        Removes the currently selected node from the canvas, the graph, and
        the optimized network data structures, then refreshes all metrics.
        """
        # Find selected node
        target_node = None
        for node in self.graph_manager.nodes:
            if getattr(node, 'selected', False):
                target_node = node
                break

        if not target_node:
            print("Delete: no node selected.")
            return

        cell_id = target_node.cell_id

        # Remove from optimized network dict
        optimized_camiguin_cellular_network.pop(cell_id, None)

        for nbrs in optimized_camiguin_cellular_network.values():
            if cell_id in nbrs:
                nbrs.remove(cell_id)

        # Remove edges instances tied to this node
        to_remove_edges = [e for e in self.graph_manager.edge_instances
                           if e.start_node == target_node or e.end_node == target_node]
        
        for edge in to_remove_edges:
            self.canvas.scene().removeItem(edge)
            self.graph_manager.edge_instances.remove(edge)

        # Remove from QGIS canvas
        self.canvas.scene().removeItem(target_node)
        self.graph_manager.nodes.remove(target_node)

        # Clear selection flag
        target_node.selected = False

        """
        # Refresh remaining edges
        for edge in self.graph_manager.edge_instances:
            edge.update_position()
            edge.setVisible(True)
        """

        # Recompute metrics
        self.get_coverage_level()
        self.get_level_of_handover()

        print(f"Deleted node {cell_id} and updated network.")
    
    def node_coverage_visualization(self):
        for node in self.graph_manager.nodes:
            if node.cell_id in optimized_camiguin_cellular_network.keys():
                node.optimized = True
                node.update()
    
    def get_node_via_id(self, id):
        for node in self.graph_manager.nodes:
            if node.cell_id == id:
                return node

    def print_out_optimized_network(self):
        """
        for node_id in optimized_camiguin_cellular_network.keys():
            for edge in self.graph_manager.edges:
                if edge[0] == node_id:
                    optimized_camiguin_cellular_network[node_id].append(edge[1])
        """    
        print(f"The optimized cellular network for Camiguin is composed of cell towers {optimized_camiguin_cellular_network.keys()}")
        print(f"Here's their connectivity projection: ")
        for key, value in optimized_camiguin_cellular_network.items():
            print(f"\tCell tower no. {key}: {value}")
        
    
    def data_printout(self):
        
        print(f"\n\nCell Tower Data:")
        for node in self.graph_manager.nodes:
            if node.cell_id in optimized_camiguin_cellular_network.keys():
                print(f"Cell Tower {node.cell_id}: {node.node_type} | {node.frequency} MHz | {node.coverage_radius} meters | {node.interference_level}%") 

        print(f"\n\nHandover Analysis Data:")
        for key, value in optimized_camiguin_cellular_network.items():
            print(f"\tCell Tower {key} overlaps with {value}")
        
        

if __name__ == "__main__":
    QgsApplication.setPrefixPath(r"C:\Program Files\QGIS 3.34.9\apps\qgis", True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    ret = app.exec_()
    qgs.exitQgis()
    sys.exit(ret)