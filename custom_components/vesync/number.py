"""Support for VeSync numeric entities."""

from collections.abc import Callable
from dataclasses import dataclass
import logging

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .pyvesync.vesyncbasedevice import VeSyncBaseDevice
from .pyvesync.vesyncfan import VeSyncHumidifier

from .const import DOMAIN, VS_COORDINATOR, VS_DEVICES, FMT_DISCOVERY
from .coordinator import VeSyncDataCoordinator
from .entity import VeSyncBaseEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class VeSyncNumberEntityDescription(NumberEntityDescription):
    """Class to describe a VeSync number entity."""

    exists_fn: Callable[[VeSyncBaseDevice], bool]
    value_fn: Callable[[VeSyncBaseDevice], float]
    set_value_fn: Callable[[VeSyncBaseDevice, float], bool]
    key: str
    translation_key: str
    native_min_value: int
    native_max_value: int
    native_step: int
    mode: NumberMode

NUMBER_DESCRIPTIONS: list[VeSyncNumberEntityDescription] = [
    VeSyncNumberEntityDescription(
        key="mist_level",
        translation_key="mist_level",
        native_min_value=1,
        native_max_value=9,
        native_step=1,
        mode=NumberMode.SLIDER,
        exists_fn=lambda device: isinstance(device, VeSyncHumidifier),
        set_value_fn=lambda device, value: device.set_mist_level(value),
        value_fn=lambda device: device.mist_level,
    )
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities."""
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
    async_add_entities: AddEntitiesCallback,
    coordinator: VeSyncDataCoordinator,
):
    """Add number entities."""
    async_add_entities(
        VeSyncNumberEntity(dev, coordinator, description)
        for dev in devices
        for description in NUMBER_DESCRIPTIONS
        if description.exists_fn(dev)
    )


class VeSyncNumberEntity(VeSyncBaseEntity, NumberEntity):
    """A class to set numeric options on VeSync device."""

    def __init__(
        self,
        device: VeSyncBaseDevice,
        coordinator: VeSyncDataCoordinator,
        description: VeSyncNumberEntityDescription
    ) -> None:
        """Initialize the VeSync number device."""
        super().__init__(device, coordinator, description)
        self._attr_unique_id = f"{super().unique_id}-{description.key}"

    @property
    def native_value(self) -> float:
        """Return the value reported by the number."""
        return self.entity_description.value_fn(self.device)

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        if await self.hass.async_add_executor_job(
            self.entity_description.set_value_fn, self.device, value
        ):
            await self.coordinator.async_request_refresh()
