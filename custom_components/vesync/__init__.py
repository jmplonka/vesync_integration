"""VeSync integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    SERVICE_UPDATE_DEVS,
    VS_COORDINATOR,
    VS_DEVICES,
    FMT_DISCOVERY,
    VS_MANAGER,
)
from .coordinator import VeSyncDataCoordinator
from .pyvesync import VeSync

PLATFORMS = [
    Platform.FAN,
    Platform.HUMIDIFIER,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up VeSync as config entry."""
    try:
        username = config_entry.data[CONF_USERNAME]
        password = config_entry.data[CONF_PASSWORD]

        time_zone = str(hass.config.time_zone)

        manager = VeSync(username, password, time_zone)

        login = await hass.async_add_executor_job(manager.login)
        if not login:
            _LOGGER.error("VeSync: unable to login on server")
            return False

        manager.update()

        coordinator = VeSyncDataCoordinator(hass, manager)

        hass.data[DOMAIN] = {}
        hass.data[DOMAIN][VS_MANAGER] = manager

        # Store coordinator at domain level since only single integration
        # instance is permitted.
        hass.data[DOMAIN][VS_COORDINATOR] = coordinator
        hass.data[DOMAIN][VS_DEVICES] = manager.device_list

        await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

        async def async_new_device_discovery(service: ServiceCall) -> None:
            """Discover if new devices should be added."""
            manager: VeSync = hass.data[DOMAIN][VS_MANAGER]
            devices: list = hass.data[DOMAIN][VS_DEVICES]

            device_set = set(manager.device_list)
            new_devices = list(device_set.difference(devices))
            if new_devices and devices:
                devices.extend(new_devices)
                async_dispatcher_send(hass, FMT_DISCOVERY(VS_DEVICES), new_devices)
                return
            if new_devices and not devices:
                devices.extend(new_devices)

        hass.services.async_register(
            DOMAIN, SERVICE_UPDATE_DEVS, async_new_device_discovery
        )

    except Exception as ex:
        _LOGGER.exception(ex)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        if unload_ok:
            hass.data.pop(DOMAIN)

        return unload_ok
    except Exception as ex:
        _LOGGER.critical('VeSync.common: %s', ex)
        return True