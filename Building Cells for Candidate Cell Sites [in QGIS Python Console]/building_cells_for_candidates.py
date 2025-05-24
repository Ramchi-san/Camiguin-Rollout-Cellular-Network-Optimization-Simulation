import math, random
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsField, QgsGeometry,
    QgsPointXY, QgsDistanceArea, QgsUnitTypes, QgsFeatureSink, QgsWkbTypes
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QMessageBox

#########################################
# CODE 1: Service Level Lookup Function #
#########################################
cells_layer = QgsProject.instance().mapLayersByName("Popn Density Cells")[0]

def get_service_level(cell_id):
    """
    Returns the service level for the given cell_id.
    Assumes the cells layer has fields "Cell ID" and "Service Le".
    """
    for cell_feature in cells_layer.getFeatures():
        if cell_feature["id"] == cell_id:
            return cell_feature["Service Le"]
    return None

#############################################
# CODE 2: Propagation and Link Budget Model #
#############################################

def link_budget(Pt, Gt, Gr, Lo, Pr_sensitivity):
    """
    Computes the maximum allowable path loss (Lp_max) based on a link budget.
    Lp_max = Pt + Gt + Gr - Lo - Pr_sensitivity
    """
    return Pt + Gt + Gr - Lo - Pr_sensitivity

def hata_distance(f, L_threshold, hb, hm, density_tier):
    """Okumura-Hata model with density-based adjustments."""

    """
    if density_tier == "Ultra-High":
        L_threshold -= 10
    elif density_tier == "Low":
        L_threshold += 15
    """

    a_hm = (1.1 * math.log10(f) - 0.7) * hm - (1.56 * math.log10(f) - 0.8)
    A_0 = 69.55 + 26.16 * math.log10(f)
    numerator = L_threshold - A_0 + 13.82 * math.log10(hb) + a_hm + (2 * math.log10(f/28) - 5.4)
    denominator = 44.9 - 6.55 * math.log10(hb)
    return 10 ** (numerator / denominator)

def cost231_distance(f, L_threshold, hb, hm, density_tier):
    """COST-231 Hata model with density-based adjustments."""
    Cm = 3 if density_tier in ["Ultra-High", "High"] else 0
    
    """
    if density_tier == "Ultra-High":
        L_threshold -= 15
    elif density_tier == "Low":
        L_threshold += 10
    """
        
    a_hm = 1.1 * (math.log10(f) - 0.7) * hm - (1.56 * math.log10(f) - 0.8)
    numerator = L_threshold - 46.3 - 33.9 * math.log10(f) + 13.82 * math.log10(hb) + a_hm - Cm
    denominator = 44.9 - 6.55 * math.log10(hb)
    return 10 ** (numerator / denominator)

def get_coverage_distance(tech, f, hb, hm, service_level, model="cost231"):
    """
    Computes the predicted coverage distance (in km) using a propagation model.
    Uses link budget as basis for service level. Mapping:
      For 4G: if service_level=="Critical" then density tier = "Ultra-High",
            if service_level=="Enhanced" then density tier = "Low".
      For 3G: if service_level=="Basic" then density tier = "Ultra-High",
            if service_level=="Trivial" then density tier = "Low".
    """
    # Determine density tier based on service level and technology.
    if tech == "4G":
        if service_level == "Critical":
            density_tier = "Ultra-High"
        elif service_level == "Enhanced":
            density_tier = "Low"
        else:
            density_tier = "Low"  # Default fallback
        # Use realistic values for 4G:
        Pt = 50     # dBm
        Gt = 15     # dBi
        Gr = 0
        Lo = 15     # Adjusted loss to achieve ~150 dB threshold
        Pr_sensitivity = -100
    elif tech == "3G":
        if service_level == "Basic":
            density_tier = "Ultra-High"
        elif service_level == "Trivial":
            density_tier = "Low"
        else:
            density_tier = "Low"
        # Use realistic values for 3G:
        Pt = 40     # dBm
        Gt = 10     # dBi
        Gr = 0
        Lo = 20     # Adjusted loss to achieve ~125 dB threshold
        Pr_sensitivity = -105
    else:
        raise ValueError("tech must be either '4G' or '3G'")
    

    # Pr_sensitivity = -100  # dBm (fixed)

    L_threshold = link_budget(Pt, Gt, Gr, Lo, Pr_sensitivity)
    

    if model.lower() == "cost231":
        L_threshold -= 15
        distance = cost231_distance(f, L_threshold, hb, hm, density_tier)
    elif model.lower() == "hata":
        distance = hata_distance(f, L_threshold, hb, hm, density_tier)
    else:
        raise ValueError("model must be either 'cost231' or 'hata'")
    
    print(f"Distance = {distance}")
    
    return distance
    

##################################################
# CODE 3: Buffering Candidate Cell Site Points   #
# Using dynamic coverage distances as buffer size  #
##################################################

# Function to convert meters to degrees (approximate conversion for latitude in EPSG:4326)
def meters_to_degrees_lat(meters):
    return meters / 111320.0

def get_frequency(cell_tech):
    frequencies = {
        "3G": [700, 750,  800, 850, 900],
        "4G": [1800, 1850, 1900, 1950, 2000]
    }
    temp_slot = random.randint(0, 4)
    if cell_tech:
        return frequencies[cell_tech][temp_slot] 
    
    return None

def create_buffer_layer():
    # Assume candidate cell sites are in a point layer named "candidate_cell_sites"
    candidate_layer = QgsProject.instance().mapLayersByName("candidate_cell_sites_v8")[0]
    
    # Create a memory layer for the buffers
    buffer_layer = QgsVectorLayer("Polygon?crs=" + candidate_layer.crs().authid(), 
                                  "Coverage Buffers", "memory")
    provider = buffer_layer.dataProvider()
    
    # Optionally, add fields to the buffer layer (e.g., Cell_ID, Tech, Frequency, Buffer_km)
    provider.addAttributes([
        QgsField("Cell_ID", QVariant.Int),
        QgsField("tech", QVariant.String),
        QgsField("frequency", QVariant.Int),
        QgsField("Buffer_km", QVariant.Double)
    ])
    buffer_layer.updateFields()
    
    # Start editing candidate layer (if needed) for reading attributes
    # We'll iterate through candidate points.
    # For each candidate, get its cell ID, tech, and frequency.
    # Look up the service level from the cells layer.
    # Compute coverage distance (in km) using our propagation model function.
    # Convert that distance to meters.
    # If the candidate layer is in EPSG:4326 (geographic coordinates), convert the meter distance to degrees.
    
    # Iterate through candidate points
    for candidate in candidate_layer.getFeatures():
        cell_id = candidate["Cell ID"]
        
        service_level = get_service_level(cell_id)
        if not service_level is None:
            if service_level in ["Critical", "Enhanced"]:
                tech = "4G"            # Assumed attribute: "tech" is "3G" or "4G"
            elif service_level in ["Basic", "Trivial"]:
                tech = "3G"
            frequency = get_frequency(tech)# Frequency in MHz
            
        model = "cost231" if tech == "4G" else "hata"

        # Compute coverage distance (km)

        cov_distance_km = get_coverage_distance(tech, frequency, hb=200, hm=1.5, service_level=service_level, model=model)
        
        # Convert coverage distance to meters
        cov_distance_m = cov_distance_km * 1000.0
        
        print(f"Cell id. {cell_id}: {cov_distance_m}" )
        
        # If candidate_layer is in EPSG:4326, convert meters to degrees (using latitude conversion)
        # (This is an approximation; for more precise buffering, reproject to a projected CRS)
        buffer_radius_degrees = meters_to_degrees_lat(cov_distance_m)
        
        # Get candidate point geometry as QgsPointXY
        pt = candidate.geometry().asPoint()
        pt_xy = QgsPointXY(pt)
        
        # Create buffer geometry around candidate point
        buffer_geom = QgsGeometry.fromPointXY(pt_xy).buffer(buffer_radius_degrees, 25)
        
        # Create new feature for the buffer layer and copy candidate attributes
        buff_feat = QgsFeature()
        buff_feat.setGeometry(buffer_geom)
        buff_feat.setAttributes([cell_id, tech, frequency, round(cov_distance_km, 3)])
        provider.addFeature(buff_feat)
    
    # Add buffer layer to the project
    QgsProject.instance().addMapLayer(buffer_layer)
    QMessageBox.information(None, "Buffering", f"Created {buffer_layer.featureCount()} buffer features!")
    
# Run the buffering function
create_buffer_layer()
