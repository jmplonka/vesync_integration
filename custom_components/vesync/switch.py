"""Support for VeSync switches and outlets."""

import logging

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchDeviceClass,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .pyvesync.vesyncbasedevice import VeSyncBaseDevice
from .pyvesync.vesync_enums import EDeviceFamily

from .const import DOMAIN, VS_COORDINATOR, VS_DEVICES, FMT_DISCOVERY
from .coordinator import VeSyncDataCoordinator
from .entity import VeSyncBaseEntity

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

DEVICE_FAMILIES: dict[EDeviceFamily, SwitchEntityDescription] = {
    EDeviceFamily.OUTLET: OUTLET,
    EDeviceFamily.SWITCH: SWITCH
}
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
        async_dispatcher_connect(hass, FMT_DISCOVERY(VS_DEVICES), discover)
    )

    _setup_entities(hass.data[DOMAIN][VS_DEVICES], async_add_entities, coordinator)


@callback
def _setup_entities(
    devices: list[VeSyncBaseDevice],
    async_add_entities,
    coordinator: VeSyncDataCoordinator,
):
    """Check if device is a switch and add entity."""
    entities: list[VeSyncSwitchEntity] = []
    for dev in devices:
        family = DEVICE_FAMILIES.get(dev.device_family)
        if (family is not None):
            entity = VeSyncSwitchEntity(dev, coordinator, family)
            entities.append(entity)

    async_add_entities(entities, update_before_add=True)


class VeSyncSwitchEntity(VeSyncBaseEntity, SwitchEntity):
    """Representation of a VeSync outlet or switch."""

    def __init__(
        self,
        device: VeSyncBaseDevice,
        coordinator: VeSyncDataCoordinator,
        description: SwitchEntityDescription
    ) -> None:
        """Initialize Base Switch device class."""
        super().__init__(device, coordinator, description)
