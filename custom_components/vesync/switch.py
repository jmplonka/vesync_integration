"""Support for VeSync switches and outlets."""

import logging
from typing import Any

from .pyvesync_basedevice import VeSyncBaseDevice

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, VS_COORDINATOR, VS_DEVICES, VS_DISCOVERY
from .coordinator import VeSyncDataCoordinator
from .entity import VeSyncBaseEntity
from .pyvesync_outlet import outlet_config

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches."""

    coordinator = hass.data[DOMAIN][VS_COORDINATOR]

    @callback
    def discover(devices):
        """Add new devices to platform."""
        _setup_entities(devices, async_add_entities, coordinator)

    config_entry.async_on_unload(
        async_dispatcher_connect(hass, VS_DISCOVERY.format(VS_DEVICES), discover)
    )

    _setup_entities(hass.data[DOMAIN][VS_DEVICES], async_add_entities, coordinator)


@callback
def _setup_entities(
    devices: list[VeSyncBaseDevice],
    async_add_entities,
    coordinator: VeSyncDataCoordinator,
):
    """Check if device is a switch and add entity."""
    entities: list[VeSyncBaseSwitch] = []
    for dev in devices:
        if (dev.device_type in outlet_config):
            entities.append(VeSyncSwitchEntity(dev, coordinator, "mdi:power-socket-de"))
        elif (dev.device_type in feature_dict):
            entities.append(VeSyncSwitchEntity(dev, coordinator, "mdi:toggle-switch-variant-off"))

    async_add_entities(entities, update_before_add=True)


class VeSyncSwitchEntity(VeSyncBaseEntity, SwitchEntity):
    """Representation of a VeSync outlet or switch."""

    _attr_name = EntityCategory.CONFIG

    def __init__(
        self,
        device: VeSyncBaseDevice,
        coordinator: VeSyncDataCoordinator,
        icon_on: str,
        icon_off: str = None
    ) -> None:
        """Initialize Base Switch device class."""
        super().__init__(device, coordinator)
        self.icon_on  = icon_on
        self.icon_off = icon_on if (icon_off is None) else icon_off

    @property
    def icon(self) -> str:
        """Return the icon of the entity."""
        return self.icon_on if self.is_on else self.icon_off

    @property
    def is_on(self) -> bool:
        """Return True if device is on."""
        return self.device.device_status == "on"

    def turn_on(self) -> bool:
        """Turn the device on."""
        turn = self.device.turn_on()
        if (not turn):
            _LOGGER.error(f"VeSync: can't turn {self.device.device_name} on!")
        return turn

    def turn_off(self) -> bool:
        """Turn the device off."""
        turn = self.device.turn_off()
        if (not turn):
            _LOGGER.error(f"VeSync: can't turn {self.device.device_name} off!")
        return turn

