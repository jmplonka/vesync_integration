"""Diagnostics support for VeSync."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import REDACTED
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntry

from .pyvesync import VeSync
from .pyvesync.vesync_enums import EDeviceFamily

from .const import DOMAIN, VS_MANAGER, VS_DEVICES
from .entity import VeSyncBaseDevice

KEYS_TO_REDACT = {"manager", "uuid", "mac_id", "cid"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    try:
        manager: VeSync = hass.data[DOMAIN][VS_MANAGER]
        devices = {}
        counts = {family: 0 for family in EDeviceFamily}
        for family in EDeviceFamily:
            devices[family.value] = [device for device in manager.device_list if device.device_family == family]
            counts[family] += 1

        return {
            DOMAIN: {
                "bulb_count": counts[EDeviceFamily.BULB],
                "fan_count": counts[EDeviceFamily.FAN],
                "outlets_count": counts[EDeviceFamily.OUTLET],
                "switch_count": counts[EDeviceFamily.SWITCH],
                "timezone": manager.time_zone,
            },
            VS_DEVICES: devices
        }
    except Exception as ex:
        _LOGGER.critical('VeSync.common: %s', ex)
        return []


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device entry."""
    manager: VeSync = hass.data[DOMAIN][VS_MANAGER]
    device_dict = _build_device_dict(manager)
    vesync_device_id = next(id[1] for id in device.identifiers if id[0] == DOMAIN)

    # Base device information, without sensitive information.
    data = _redact_device_values(device_dict[vesync_device_id])

    data["home_assistant"] = {
        "name": device.name,
        "name_by_user": device.name_by_user,
        "disabled": device.disabled,
        "disabled_by": device.disabled_by,
        "entities": [],
    }

    # Gather information how this VeSync device is represented in Home Assistant
    entity_registry = er.async_get(hass)
    hass_entities = er.async_entries_for_device(
        entity_registry,
        device_id=device.id,
        include_disabled_entities=True,
    )

    for entity_entry in hass_entities:
        state = hass.states.get(entity_entry.entity_id)
        state_dict = None
        if state:
            state_dict = dict(state.as_dict())
            # The context doesn't provide useful information in this case.
            state_dict.pop("context", None)

        data["home_assistant"]["entities"].append(
            {
                "domain": entity_entry.domain,
                "entity_id": entity_entry.entity_id,
                "entity_category": entity_entry.entity_category,
                "device_class": entity_entry.device_class,
                "original_device_class": entity_entry.original_device_class,
                "name": entity_entry.name,
                "original_name": entity_entry.original_name,
                "icon": entity_entry.icon,
                "original_icon": entity_entry.original_icon,
                "unit_of_measurement": entity_entry.unit_of_measurement,
                "state": state_dict,
                "disabled": entity_entry.disabled,
                "disabled_by": entity_entry.disabled_by,
            }
        )

    return data


def _build_device_dict(manager: VeSync) -> dict:
    """Build a dictionary of ALL VeSync devices."""
    try:
        return {x.cid: x for x in manager.device_list}
    except Exception as ex:
        _LOGGER.critical('VeSync.common: %s', ex)
        return {}


def _redact_device_values(device: VeSyncBaseDevice) -> dict:
    """Rebuild and redact values of a VeSync device."""
    data = {}
    try:
        for key, item in device.__dict__.items():
            if key not in KEYS_TO_REDACT:
                data[key] = item
            else:
                data[key] = REDACTED
    except Exception as ex:
        _LOGGER.critical('VeSync.common: %s', ex)

    return data
