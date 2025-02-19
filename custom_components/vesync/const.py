"""Constants for VeSync Component."""

DOMAIN: str = "vesync"
FMT_DISCOVERY: function = "vesync_discovery_{}".format
SERVICE_UPDATE_DEVS: str = "update_devices"

UPDATE_INTERVAL = 60  # in seconds
"""
Update interval for DataCoordinator.

The vesync daily quota formula is 3200 + 1500 * device_count.

An interval of 60 seconds amounts 1440 calls/day which
would be below the 4700 daily quota. For 2 devices, the
total would be 2880.

Using 30 seconds interval gives 8640 for 3 devices which
exceeds the quota of 7700.
"""
VS_DEVICES: str = "devices"
VS_COORDINATOR: str = "coordinator"
VS_MANAGER: str = "manager"
VS_NUMBERS: str = "numbers"

SKU_TO_BASE_DEVICE = {
    # Air Purifiers
    "LV-PUR131S": "LV-PUR131S",
    "LV-RH131S": "LV-PUR131S",  # Alt ID Model LV-PUR131S
    "Core200S": "Core200S",
    "LAP-C201S-AUSR": "Core200S",  # Alt ID Model Core200S
    "LAP-C202S-WUSR": "Core200S",  # Alt ID Model Core200S
    "Core300S": "Core300S",
    "LAP-C301S-WJP": "Core300S",  # Alt ID Model Core300S
    "LAP-C301S-WAAA": "Core300S",  # Alt ID Model Core300S
    "LAP-C302S-WUSB": "Core300S",  # Alt ID Model Core300S
    "Core400S": "Core400S",
    "LAP-C401S-WJP": "Core400S",  # Alt ID Model Core400S
    "LAP-C401S-WUSR": "Core400S",  # Alt ID Model Core400S
    "LAP-C401S-WAAA": "Core400S",  # Alt ID Model Core400S
    "Core600S": "Core600S",
    "LAP-C601S-WUS": "Core600S",  # Alt ID Model Core600S
    "LAP-C601S-WUSR": "Core600S",  # Alt ID Model Core600S
    "LAP-C601S-WEU": "Core600S",  # Alt ID Model Core600S,
    "Vital200S": "Vital200S",
    "LAP-V201S-AASR": "Vital200S",  # Alt ID Model Vital200S
    "LAP-V201S-WJP": "Vital200S",  # Alt ID Model Vital200S
    "LAP-V201S-WEU": "Vital200S",  # Alt ID Model Vital200S
    "LAP-V201S-WUS": "Vital200S",  # Alt ID Model Vital200S
    "LAP-V201-AUSR": "Vital200S",  # Alt ID Model Vital200S
    "LAP-V201S-AEUR": "Vital200S",  # Alt ID Model Vital200S
    "LAP-V201S-AUSR": "Vital200S",  # Alt ID Model Vital200S
    "Vital100S": "Vital100S",
    "LAP-V102S-WUS": "Vital100S",  # Alt ID Model Vital100S
    "LAP-V102S-AASR": "Vital100S",  # Alt ID Model Vital100S
    "LAP-V102S-WEU": "Vital100S",  # Alt ID Model Vital100S
    "LAP-V102S-WUK": "Vital100S",  # Alt ID Model Vital100S
    "EverestAir": "EverestAir",
    "LAP-EL551S-AUS": "EverestAir",  # Alt ID Model EverestAir
    "LAP-EL551S-AEUR": "EverestAir",  # Alt ID Model EverestAir
    "LAP-EL551S-WEU": "EverestAir",  # Alt ID Model EverestAir
    "LAP-EL551S-WUS": "EverestAir",  # Alt ID Model EverestAir
}