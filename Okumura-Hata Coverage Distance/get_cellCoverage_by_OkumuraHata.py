import math

def hata_distance(f, L_threshold, hb, hm):
    """Okumura-Hata model with density-based adjustments."""

    a_hm = (1.1 * math.log10(f) - 0.7) * hm - (1.56 * math.log10(f) - 0.8)
    A_0 = 69.55 + 26.16 * math.log10(f)
    numerator = L_threshold - A_0 + 13.82 * math.log10(hb) + a_hm + 2 * math.log10(f/28) + 5.4
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
    Pt = 30     # dBm
    Gt = 10     # dBi
    Gr = 0
    Lo = 20     # Adjusted loss to achieve ~125 dB threshold
    
    Pr_sensitivity = -105 #or -105
    
    if service_level == "Basic":
        Pr_sensitivity -= -5
    print(f"Receiver sensitivity: {Pr_sensitivity}")
    # Pr_sensitivity = -100  # dBm (fixed)

    L_threshold = link_budget(Pt, Gt, Gr, Lo, Pr_sensitivity)
    
    distance = hata_distance(f, L_threshold, hb, hm)
    
    return distance

def main():
    frequencies = [825, 850, 875, 900, 925, 950]
    service_levels = ["Trivial", "Basic"]

    for frequency in frequencies:
        for service_level in service_levels:
            distance = get_coverage_distance(frequency, service_level)
            print(f"{frequency}, {service_level}: {distance} kms")

if __name__ == "__main__":
    main()