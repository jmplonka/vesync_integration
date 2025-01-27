"""Support for VeSync switches and outlets."""

import logging
from typing import Any

from pyvesync.vesyncbasedevice import VeSyncBaseDevice

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchDeviceClass,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, VS_COORDINATOR, VS_DEVICES, VS_DISCOVERY
from .coordinator import VeSyncDataCoordinator
from .entity import VeSyncBaseEntity
from .pyvesync_outlet import outlet_config
from .pyvesync_switch import feature_dict

_LOGGER = logging.getLogger(__name__)

OUTLET = SwitchEntityDescription(
    key="smartSocket",
    device_class=SwitchDeviceClass.OUTLET,
    name="Switch",
    icon="mdi:power-socket-de"
)

SWITCH = SwitchEntityDescription(
    key="smartSwitch",
    device_class=SwitchDeviceClass.SWITCH,
    name="Switch",
    icon="mdi:light-switch"
)

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
            entities.append(VeSyncSwitchEntity(dev, coordinator, OUTLET))
        elif (dev.device_type in feature_dict):
            entities.append(VeSyncSwitchEntity(dev, coordinator, SWITCH))

    async_add_entities(entities, update_before_add=True)


class VeSyncSwitchEntity(VeSyncBaseEntity, SwitchEntity):
    """Representation of a VeSync outlet or switch."""

    _attr_name = None

    def __init__(
        self,
        device: VeSyncBaseDevice,
        coordinator: VeSyncDataCoordinator,
        description: SwitchEntityDescription
    ) -> None:
        """Initialize Base Switch device class."""
        super().__init__(device, coordinator)
        self.entity_description = description

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

