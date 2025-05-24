layer = iface.activeLayer()
sum_elevation = 0.0
count = 0

for feature in layer.getFeatures():
    elevation = feature['VALUE']  # Ensure the field name matches your data
    sum_elevation += float(elevation)
    count += 1

if count > 0:
    average_elevation = sum_elevation / count
    print(f"Average elevation (PyQGIS):"
        f"\n\t {sum_elevation} / {count} = {average_elevation}"
    )
else:
    print("No features found!")
