from qgis.gui import QgsMapCanvasItem
import math, random


class Cell_Tower_Vertex(QgsMapCanvasItem):
    
    def __init__(self, x=0, y=0, f=None, node_type=None):
        self.x = x
        self.y = y
        self.op_frequency = f
        self.node_type = node_type

        temp_num = random.randint(1, 20) 
        #self.h_ct = 200 + (-temp_num if random.randint(1, 10)%2 != 0 else temp_num) #This will be added with the stark height advantage of the site location or subtracted with the apparent compromised height
        self.h_ct = 200
        self.h_ms = 1.5 #1.5 meters as the generalized height for utilized mobile devices.

        self.link_budget = self.get_linkBudget_threshold()
        self.coverage_radius = self.get_OkumuraHata_distance() if self.node_type == "3G" else  self.get_COST231_distance()


    def get_linkBudget_threshold(self):
        P_r = None
        L_p = None
        P_t = None
        G_t = 15
        L_c = 0
        G_r = 0
        L_o = 0

        if self.node_type == "3G":
            P_r = -100
            P_t = 30
            

        elif self.node_type == "4G":
            P_r = -90
            P_t = 40
    
        L_p = P_t + G_t - L_c + G_r - L_o - P_r
        return L_p

    def get_COST231_distance(self):
        """
        Calculate the maximum distance d (in km) for the COST-231 Hata model (for 4G frequencies).
        
        Parameters:
        f          : Frequency in MHz (typically 1500-2000 MHz)
        L_threshold: Threshold path loss in dB
        hb         : Base station antenna height in meters
        hm         : Mobile antenna height in meters
        Cm         : Correction factor (0 dB for suburban/medium cities, 3 dB for metropolitan areas)
        
        Returns:
        d: Distance in kilometers.
        
        COST-231 Hata model:
        L = 46.3 + 33.9*log10(f) - 13.82*log10(hb) - a(hm) 
            + (44.9 - 6.55*log10(hb))*log10(d) + Cm
        
        Mobile antenna correction factor for COST-231 (small or medium-size city):
        a(hm) = 1.1 * (log(f) - 0.7) * hm - (1.56 * log(f) - 0.8)
        """
        f = self.op_frequency
        L_threshold = self.link_budget
        hb = self.h_ct
        hm = self.h_ms    
        a_hm = 1.1 * (math.log(f) - 0.7) * hm - (1.56 * math.log(f) - 0.8)
        Cm = 3

        numerator = L_threshold - 46.3 - 33.9 * math.log10(f) + 13.82 * math.log10(hb) + a_hm - Cm
        denominator = 44.9 - 6.55 * math.log10(hb)
        log10_d = numerator / denominator
        d = 10 ** log10_d
        return d
        
    def get_OkumuraHata_distance(self):
        """
        Calculate the maximum distance d (in km) for the Okumura-Hata model (urban) for 3G.
        
        Parameters:
        f          : Frequency in MHz (150-1500 MHz range)
        L_threshold: Threshold path loss in dB
        hb         : Base station antenna height in meters
        hm         : Mobile antenna height in meters
        
        Returns:
        d: Distance in kilometers.
        
        Okumura-Hata model (urban):
        L = A_0 - 13.82*log10(hb) - a(hm) 
            + (44.9 - 6.55*log10(hb))*log10(d)
        
        Mobile antenna correction factor (suburban):
        a(hm) = (1.1*log10(f) - 0.7)*hm - (1.56*log10(f) - 0.8)

        Base path loss factor (A_0):
        A_0 = 69.55 + 26.16*log10(f)

        """
        f = self.op_frequency
        L_threshold = self.link_budget
        hb = self.h_ct
        hm = self.h_ms
        a_hm = (1.1 * math.log10(f) - 0.7) * hm - (1.56 * math.log10(f) - 0.8)
        A_0 = 69.55 + 26.16 * math.log10(f)
        numerator = L_threshold - A_0 + 13.82 * math.log10(hb) + a_hm + (2 * math.log(f/28) - 5.4)
        denominator = 44.9 - 6.55 * math.log10(hb)
        log10_d = numerator / denominator
        d = 10 ** log10_d
        return d

if __name__ == "__main__":
    frequencies = {
        "3G": [700, 715, 730, 755, 780, 805, 830],
        "4G": [1800, 1815, 1850, 1870, 1900, 1930]
    }

    for cell_tech, freqs  in frequencies.items():
        for freq in freqs:
            cell_tower = Cell_Tower_Vertex(0, 0, freq, cell_tech)
            print(f"Cell Tower (height: {cell_tower.h_ct}, cell tech: {cell_tower.node_type}): "
                  f"\n\t Operating Frequency: {cell_tower.op_frequency}"
                  f"\n\t Coverage: {cell_tower.coverage_radius}"
                  "\n\n"
                  )

           

