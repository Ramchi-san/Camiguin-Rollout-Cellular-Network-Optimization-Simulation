#!/usr/bin/env python3
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QHBoxLayout, QComboBox, QGraphicsTextItem
)
from PyQt5.QtGui import QPen, QPainter, QBrush, QColor, QFont
from PyQt5.QtCore import Qt, QRectF

from qgis.core import (
    QgsApplication,
    QgsRasterLayer,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsRectangle,
    QgsDistanceArea,
    QgsVectorLayer,
    QgsWkbTypes,
    QgsGeometry
)
from qgis.gui import QgsMapCanvas, QgsMapCanvasItem, QgsMapTool

# -----------------------------------------------------------------------------
# Helper class to support distance comparisons with clicks.
# -----------------------------------------------------------------------------
class DummyNode:
    def __init__(self, point):
        self.mapPoint = point

# -----------------------------------------------------------------------------
# Frequency Assignment Functions
# -----------------------------------------------------------------------------
frequencies = {
    "3G": [700, 715, 730, 755, 780, 805, 830],
    "4G": [1800, 1815, 1850, 1870, 1900, 1930]
}

def calculate_distance(node1, node2):
    """
    Computes the geodetic distance (in meters) between the mapPoint of two nodes.
    """
    d = QgsDistanceArea()
    d.setSourceCrs(QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance().transformContext())
    d.setEllipsoid("WGS84")
    print(f"node1 mapPoint: {node1.mapPoint}")
    print(f"node2 mapPoint: {node2.mapPoint}")
    distance = d.measureLine(node1.mapPoint, node2.mapPoint)
    print(f"Distance between {node1.mapPoint} and {node2.mapPoint} is {distance:.2f} meters")
    return distance

def build_graph(manager):
    """
    Constructs a graph based on overlapping coverages.
    Two nodes are adjacent if the distance between them is less than or equal to
    the sum of half their coverage radii.
    """
    nodes = manager.nodes
    graph = {node: [] for node in nodes}
    for i, node1 in enumerate(nodes):
        for node2 in nodes[i+1:]:
            d = calculate_distance(node1, node2)
            r1 = node1.coverage_radius / 2.0  # in meters
            r2 = node2.coverage_radius / 2.0  # in meters
            if d <= (r1 + r2):
                graph[node1].append(node2)
                graph[node2].append(node1)
    return graph

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

def greedy_graph_coloring(manager, graph):
    """
    Assign frequencies using a greedy graph coloring algorithm
    based on overlapping coverages.
    """
    for node in manager.nodes:
        used = set()
        for neighbor in graph[node]:
            if neighbor.frequency is not None:
                used.add(neighbor.frequency)
        for freq in frequencies[node.node_type]:
            if freq not in used:
                node.frequency = freq
                break
        node.update_label()

def assign_frequencies_with_graph_coloring(manager):
    graph = build_graph(manager)
    greedy_graph_coloring(manager, graph)

# -----------------------------------------------------------------------------
# Node & Edge Classes (QgsMapCanvasItem)
# -----------------------------------------------------------------------------
class Node(QgsMapCanvasItem):
    def __init__(self, canvas, x, y, node_type="3G", node_radius=10):
        super().__init__(canvas)
        self.canvas = canvas
        self.node_type = node_type
        self.frequency = None
        self.edges = []
        self.node_radius = node_radius  # used for drawing only
        # Set coverage_radius in meters
        self.coverage_radius = 1500
        self.brush = QColor("blue") if node_type == "3G" else QColor("green")
        self.selected = False
        # Ensure nodes appear above edges.
        self.setZValue(1)
        # Store the map coordinate (in EPSG:4326).
        self.mapPoint = QgsPointXY(x, y)
        # Create a label as a child item.
        self.label = QGraphicsTextItem("", self)
        self.label.setDefaultTextColor(Qt.black)
        # Position the label slightly below the node.
        self.label.setPos(-self.node_radius/2, self.node_radius/2)
        self.update_label()
        self.updatePosition()

    def update_label(self):
        self.label.setPlainText(f"{self.node_type}\n{self.frequency or 'N/A'} MHz")
    
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
        # Draw cell coverage.
        pixel_radius = self.pixelCoverageRadius()
        coverage_rect = QRectF(-pixel_radius, -pixel_radius, 2*pixel_radius, 2*pixel_radius)
        painter.setPen(QPen(Qt.red, 1, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(coverage_rect)
        # Draw the node circle.
        node_rect = QRectF(-self.node_radius/2, -self.node_radius/2, self.node_radius, self.node_radius)
        painter.setPen(QPen(Qt.black, 1))
        painter.setBrush(QBrush(self.brush))
        painter.drawEllipse(node_rect)
        # Highlight if selected.
        if self.selected:
            painter.setPen(QPen(Qt.yellow, 2))
            painter.setBrush(QBrush(QColor("yellow")))
            painter.drawEllipse(node_rect)

class Edge(QgsMapCanvasItem):
    def __init__(self, canvas, start_node, end_node):
        super().__init__(canvas)
        self.canvas = canvas
        self.start_node = start_node
        self.end_node = end_node
        self.pen = QPen(Qt.black, 2)
        # Ensure edges appear behind nodes.
        self.setZValue(0)
        # Add this edge to each node’s edge list.
        self.start_node.edges.append(self)
        self.end_node.edges.append(self)
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

# -----------------------------------------------------------------------------
# GraphManager: Holds Nodes & Edges
# -----------------------------------------------------------------------------
class GraphManager:
    def __init__(self, canvas):
        self.canvas = canvas
        self.nodes = []
        self.edges = []
        # Modes: "add_node", "delete_node", or "drag"
        self.mode = "drag"
        self.node_type = "3G"
        # Callback to update coverage display (set by main window)
        self.update_coverage_callback = None

    def add_node(self, x, y, node_type="0"):
        if node_type != "0":
            node = Node(self.canvas, x, y, node_type)
        else:
            node = Node(self.canvas, x, y, self.node_type)
        self.nodes.append(node)
        assign_frequencies_with_graph_coloring(self)
        self.update_edges()
        if self.update_coverage_callback:
            self.update_coverage_callback()

    def delete_node(self, node):
        for edge in node.edges[:]:
            if edge in self.edges:
                self.edges.remove(edge)
            edge.hide()
        if node in self.nodes:
            self.nodes.remove(node)
        node.hide()
        assign_frequencies_with_graph_coloring(self)
        self.update_edges()
        if self.update_coverage_callback:
            self.update_coverage_callback()

    def update_edges(self):
        # Remove all existing edges and recalculate overlapping coverage.
        for node in self.nodes:
            node.edges = []
        for edge in self.edges:
            edge.hide()
        self.edges = []
        for i, node1 in enumerate(self.nodes):
            for node2 in self.nodes[i+1:]:
                d = calculate_distance(node1, node2)
                r1 = node1.coverage_radius / 2.0  # in meters
                r2 = node2.coverage_radius / 2.0  # in meters
                if d <= (r1 + r2):
                    edge = Edge(self.canvas, node1, node2)
                    self.edges.append(edge)
                    
    def assign_frequencies_with_graph_coloring(self):
        assign_frequencies_with_graph_coloring(self)

    def load_nodes_from_shapefile(self, shp_path):
        """
        Loads point features from the provided shapefile and creates nodes.
        """
        layer = QgsVectorLayer(shp_path, "CentroidNodes", "ogr")
        if not layer.isValid():
            print("Failed to load the nodes layer!")
            return
        if layer.geometryType() == QgsWkbTypes.PointGeometry:
            for feature in layer.getFeatures():
                geom = feature.geometry()
                if geom and not geom.isEmpty():
                    point = geom.asPoint()
                    # Add node using the point's x and y coordinates.
                    self.add_node(point.x(), point.y())
        else:
            print("The provided layer is not a point layer.")

# -----------------------------------------------------------------------------
# GraphMapTool: Graph Interaction + Print Clicked Coordinates
# Updated to use a 1000-meter threshold for node selection.
# -----------------------------------------------------------------------------
class GraphMapTool(QgsMapTool):
    def __init__(self, canvas, graph_manager):
        super().__init__(canvas)
        self.canvas = canvas
        self.graph_manager = graph_manager
        self.active_node = None
        self.start_pos = None

    def canvasPressEvent(self, event):
        pos = event.mapPoint()
        print("Clicked coordinates: X: {:.3f}, Y: {:.3f}".format(pos.x(), pos.y()))
        if self.graph_manager.mode == "add_node":
            self.graph_manager.add_node(pos.x(), pos.y())
            return
        elif self.graph_manager.mode == "delete_node":
            node = self.findClickedNode(pos)
            if node:
                self.graph_manager.delete_node(node)
                return
        node = self.findClickedNode(pos)
        if node:
            self.active_node = node
            self.start_pos = pos
            node.selected = True
            node.update()

    def canvasMoveEvent(self, event):
        if self.active_node and self.start_pos:
            new_pos = event.mapPoint()
            dx = new_pos.x() - self.start_pos.x()
            dy = new_pos.y() - self.start_pos.y()
            self.active_node.mapPoint = QgsPointXY(
                self.active_node.mapPoint.x() + dx,
                self.active_node.mapPoint.y() + dy
            )
            self.start_pos = new_pos
            self.active_node.updatePosition()
            # Remove node characterizing values by clearing its label.
            self.active_node.label.setPlainText("")
            # Hide all edges connected to this node.
            for edge in self.active_node.edges:
                edge.hide()

    def canvasReleaseEvent(self, event):
        if self.active_node:
            # When movement is finished, recalculate edges and frequencies.
            self.graph_manager.update_edges()
            self.graph_manager.assign_frequencies_with_graph_coloring()
            # Restore the node's label.
            self.active_node.update_label()
            self.active_node.selected = False
            self.active_node.update()
            self.active_node = None
            # Trigger coverage update after drag.
            if self.graph_manager.update_coverage_callback:
                self.graph_manager.update_coverage_callback()

    def findClickedNode(self, point):
        """
        Returns the first node whose geodesic distance from the click is <= 1000 m.
        """
        threshold = 1000.0  # meters
        dummy = DummyNode(point)
        for node in self.graph_manager.nodes:
            d = calculate_distance(node, dummy)
            if d <= threshold:
                return node
        return None

# -----------------------------------------------------------------------------
# Main Window using QgsMapCanvas with OSM Base Layer in EPSG:4326 (WGS84)
# Also loads a polygon layer and displays the current coverage level.
# -----------------------------------------------------------------------------
class GraphWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.canvas = QgsMapCanvas()
        self.canvas.setCanvasColor(Qt.white)
        self.canvas.enableAntiAliasing(True)
        crs = QgsCoordinateReferenceSystem("EPSG:4326")
        self.canvas.setDestinationCrs(crs)

        # Add the OSM base layer.
        osm_url = "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        osm_layer = QgsRasterLayer(osm_url, "OpenStreetMap", "wms")
        if not osm_layer.isValid():
            print("Failed to load the OSM layer!")
            sys.exit(1)
        QgsProject.instance().addMapLayer(osm_layer)
        self.canvas.setLayers([osm_layer])

        # Set the initial view.
        center4326 = QgsPointXY(124.7408, 9.1726)
        buffer = (9783 * 1.5) / 111320.0  # ~0.132 degrees
        extent = QgsRectangle(
            center4326.x() - buffer, center4326.y() - buffer,
            center4326.x() + buffer, center4326.y() + buffer
        )
        self.canvas.setExtent(extent)
        
        # --- New code: Load the polygon vector layer for coverage comparison ---
        self.coverage_polygon = None
        poly_path = r"C:\Users\Ramcie Labadan\Desktop\Final Maps\Camiguin Area for Cell Coverage\CamiguinAreaForCellCoverage.shp"
        poly_layer = QgsVectorLayer(poly_path, "CoveragePolygon", "ogr")
        if poly_layer.isValid():
            for feat in poly_layer.getFeatures():
                self.coverage_polygon = feat.geometry()
                break
        else:
            print("Failed to load the coverage polygon layer!")
        
        # --- New code: Create a QGraphicsTextItem for displaying coverage level ---
        self.coverage_text_item = QGraphicsTextItem("")
        self.coverage_text_item.setDefaultTextColor(Qt.black)
        self.coverage_text_item.setFont(QFont("Arial", 14))
        self.coverage_text_item.setZValue(2)  # ensure it appears on top
        self.canvas.scene().addItem(self.coverage_text_item)
        self.coverage_text_item.setPos(10, 10)
        
        # Set up the Graph Manager and Map Tool.
        self.graph_manager = GraphManager(self.canvas)
        # Set the update coverage callback so the coverage recalculates on events.
        self.graph_manager.update_coverage_callback = self.updateCoverageDisplay
        
        # --- New code: Load nodes from the given shapefile ---
        shp_path = r"C:\Users\Ramcie Labadan\Documents\THESIS\Maps and Other Geospatial Data\Normative Graph Centroids\Normative_Graph_Centroids.shp"
        self.graph_manager.load_nodes_from_shapefile(shp_path)
        # ---------------------------------------------------------
        self.map_tool = GraphMapTool(self.canvas, self.graph_manager)
        self.canvas.setMapTool(self.map_tool)
        
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        button_layout = QHBoxLayout()

        self.node_button = QPushButton("Add Node")
        self.node_button.setCheckable(True)
        self.node_button.setChecked(False)
        self.node_button.clicked.connect(self.update_mode)

        self.delete_button = QPushButton("Delete Node")
        self.delete_button.setCheckable(True)
        self.delete_button.setChecked(False)
        self.delete_button.clicked.connect(self.update_mode)

        self.type_selector = QComboBox()
        self.type_selector.addItems(["3G", "4G"])
        self.type_selector.currentTextChanged.connect(self.update_node_type)

        button_layout.addWidget(self.node_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.type_selector)

        layout.addLayout(button_layout)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        self.setWindowTitle("Graph Editor with OSM Base – Automatic Nodes & Coverage Display (EPSG:4326)")
        self.resize(800, 600)

    def update_mode(self):
        if self.node_button.isChecked():
            self.delete_button.setChecked(False)
            self.graph_manager.mode = "add_node"
        elif self.delete_button.isChecked():
            self.node_button.setChecked(False)
            self.graph_manager.mode = "delete_node"
        else:
            self.graph_manager.mode = "drag"

    def update_node_type(self, node_type):
        self.graph_manager.node_type = node_type

    def updateCoverageDisplay(self):
        """
        Calculates the union of all node coverage areas (circles) and then determines
        the percentage of the coverage polygon that is covered by these areas.
        """
        if not self.coverage_polygon:
            return
        union_geom = None
        for node in self.graph_manager.nodes:
            # Create a circular geometry for the node using its coverage radius.
            circle = QgsGeometry.fromPointXY(node.mapPoint).buffer(node.coverage_radius, 50)
            if union_geom is None:
                union_geom = circle
            else:
                # Use combine() to merge the geometries.
                union_geom = union_geom.combine(circle)
        if union_geom is None:
            covered_area = 0
        else:
            intersection = union_geom.intersection(self.coverage_polygon)
            if intersection is None or intersection.isEmpty():
                covered_area = 0
            else:
                d = QgsDistanceArea()
                d.setSourceCrs(QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance().transformContext())
                d.setEllipsoid("WGS84")
                covered_area = d.measureArea(intersection)
        # Measure total area of the coverage polygon.
        d = QgsDistanceArea()
        d.setSourceCrs(QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance().transformContext())
        d.setEllipsoid("WGS84")
        total_area = d.measureArea(self.coverage_polygon)
        if total_area > 0:
            coverage_percent = (covered_area / total_area) * 100
        else:
            coverage_percent = 0
        self.coverage_text_item.setPlainText(f"Coverage Level: {coverage_percent:.2f}%")

# -----------------------------------------------------------------------------
# Main Application Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    QgsApplication.setPrefixPath(r"C:\Program Files\QGIS 3.34.9\apps\qgis-ltr", True)
    qgs = QgsApplication([], False)
    qgs.initQgis()

    app = QApplication(sys.argv)
    window = GraphWindow()
    window.show()
    ret = app.exec_()

    qgs.exitQgis()
    sys.exit(ret)
