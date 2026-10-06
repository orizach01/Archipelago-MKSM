from .locations import REGION_NAME_LOCATIONS, PURCHASE_LOCATIONS, FINISHING_MOVES_LOCATIONS

region_locations_flattened = [loc for region, locs_dict in REGION_NAME_LOCATIONS.items() for loc in locs_dict]

LOCATION_GROUPS = {
    "Red koins": [loc for loc in region_locations_flattened if 'koin' in loc],
    "Medallions": [loc for loc in region_locations_flattened if 'obtained' in loc or 'Medallion' in loc],
    "Health upgrades": [loc for loc in region_locations_flattened if 'health upgrade' in loc],
    "Bosses": [loc for loc in region_locations_flattened if 'defeated' in loc],
    "Shopsanity": PURCHASE_LOCATIONS,
    "Fatalitysanity": [loc for char, locs_dict in FINISHING_MOVES_LOCATIONS.items() for loc in locs_dict]
}
