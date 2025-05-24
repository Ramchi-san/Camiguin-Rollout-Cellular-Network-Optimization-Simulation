from qgis.core import QgsProject, QgsDistanceArea, QgsCoordinateReferenceSystem, QgsPointXY

point1 = QgsPointXY(x, y)
point2 = QgsPointXY(x, y)

def calculate_distance(point1, point2):
    """
    Computes the geodetic distance (in meters) between the mapPoint of two nodes.
    """
    d = QgsDistanceArea()
    d.setSourceCrs(QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance().transformContext())
    d.setEllipsoid("WGS84")

    distance = d.measureLine(point1, point2)
    print(f"Distance between {point1} and {point2} is {distance:.2f} meters")
    return distance
