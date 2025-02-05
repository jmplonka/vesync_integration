"""Common utilities for VeSync Component."""

import logging

from homeassistant.core import HomeAssistant

from .pyvesync.vesyncbasedevice import VeSyncBaseDevice

from .const import VeSyncHumidifierDevice

_LOGGER = logging.getLogger(__name__)


async def async_generate_device_list(
    hass: HomeAssistant, manager
) -> list[VeSyncBaseDevice]:
    """Assign devices to proper component."""
    await hass.async_add_executor_job(manager.update)

    return manager.device_list


def is_humidifier(device: VeSyncBaseDevice) -> bool:
    """Check if the device represents a humidifier."""

    return isinstance(device, VeSyncHumidifierDevice)