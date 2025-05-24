import math
#Code 2
def cost231_distance(f, L_threshold, hb, hm, service_level):
    
    Cm = 3 if service_level in ["Critical"] else 0
            
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

def get_coverage_distance(f, service_level, hb=200, hm=1.5):

    # Use realistic values for 3G:
    Pt = 40     # dBm
    Gt = 10     # dBi
    Gr = 0
    Lo = 15     # Adjusted loss to achieve ~125 dB threshold
    
    Pr_sensitivity = -100 #or -80 for > 1500 users, -90 for  1000 <= users <= 1500, -100 for 700 <= users <= 1000 
    if service_level == "Priority":
        Pr_sensitivity -= -10
    elif service_level == "Critical":
        Pr_sensitivity -= -15
    
    print(f"Receiver sensitivity: {Pr_sensitivity}")

    # Pr_sensitivity = -100  # dBm (fixed)

    L_threshold = link_budget(Pt, Gt, Gr, Lo, Pr_sensitivity)
    
    print(f"L_threshold: {L_threshold}")

    distance = cost231_distance(f, L_threshold, hb, hm, service_level)
    
    return distance

def main():
    frequencies = [1800, 1850, 1900, 1950, 2000, 2050]
    service_levels = ["Critical", "Priority", "Enhanced"]

    for frequency in frequencies:
        for service_level in service_levels:
            distance = get_coverage_distance(frequency, service_level)
            print(f"{frequency}MHz, : {distance} kms")
        print("\n\n")

if __name__ == "__main__":
    main()