"""Support for VeSync fans."""

from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)
from homeassistant.util.scaling import int_states_in_range

from .pyvesync.vesyncbasedevice import VeSyncBaseDevice
from .pyvesync.const import MODE_AUTO, MODE_SLEEP, MODE_PET, MODE_TURBO, MODE_MANUAL
from .pyvesync.helpers import EDeviceFamily

from .const import DOMAIN, VS_COORDINATOR, VS_DEVICES, FMT_DISCOVERY
from .coordinator import VeSyncDataCoordinator
from .entity import VeSyncBaseEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VeSync fan platform."""

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
    """Check if device is fan and add entity."""
    entities = [
        VeSyncFanEntity(dev, coordinator)
        for dev in devices
        if dev.device_family == EDeviceFamily.FAN
    ]

    async_add_entities(entities, update_before_add=True)


class VeSyncFanEntity(VeSyncBaseEntity, FanEntity):
    """Representation of a VeSync fan."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.TURN_ON
    )

    _attr_translation_key = "vesync"

    def __init__(
        self, fan: VeSyncBaseDevice, coordinator: VeSyncDataCoordinator
    ) -> None:
        """Initialize the VeSync fan device."""
        super().__init__(fan, coordinator)

    @property
    def is_on(self) -> bool:
        """Return True if device is on."""
        return self.device.is_on

    @property
    def percentage(self) -> int | None:
        """Return the current speed."""
        if (
            self.device.mode == MODE_MANUAL
            and (current_level := self.device.fan_level) is not None
        ):
            return ranged_value_to_percentage(self.device.mist_levels, current_level)
        return None

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return int_states_in_range(self.device.mist_levels)

    @property
    def preset_modes(self) -> list[str]:
        """Get the list of available preset modes."""
        return self.device.mist_modes

    @property
    def preset_mode(self) -> str | None:
        """Get the current preset mode."""
        if self.device.mode in self.device.mist_modes:
            return self.device.mode
        return None

    @property
    def unique_info(self):
        """Return the ID of this fan."""
        return self.device.uuid

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the fan."""
        attr = {}

        if hasattr(self.device, "active_time"):
            attr["active_time"] = self.device.active_time

        if hasattr(self.device, "screen_status"):
            attr["screen_status"] = self.device.screen_status

        if hasattr(self.device, "child_lock"):
            attr["child_lock"] = self.device.child_lock

        if hasattr(self.device, "night_light"):
            attr["night_light"] = self.device.night_light

        if hasattr(self.device, "mode"):
            attr["mode"] = self.device.mode

        return attr

    def set_percentage(self, percentage: int) -> None:
        """Set the speed of the device."""
        if percentage == 0:
            self.device.turn_off()
            return

        if not self.device.is_on:
            self.device.turn_on()

        self.device.manual_mode()
        self.device.change_fan_speed(
            math.ceil(percentage_to_ranged_value(self.device.mist_levels, percentage))
        )
        self.schedule_update_ha_state()

    def set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of device."""
        if preset_mode not in self.preset_modes:
            raise ValueError(
                f"{preset_mode} is not one of the valid preset modes: "
                f"{self.preset_modes}"
            )

        if not self.device.is_on:
            self.device.turn_on()

        if preset_mode == MODE_AUTO:
            self.device.auto_mode()
        elif preset_mode == MODE_SLEEP:
            self.device.sleep_mode()
        elif preset_mode == MODE_PET:
            self.device.pet_mode()
        elif preset_mode == MODE_TURBO:
            self.device.turbo_mode()

        self.schedule_update_ha_state()

    def turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the device on."""
        if preset_mode:
            self.set_preset_mode(preset_mode)
            return
        if percentage is None:
            percentage = 50
        self.set_percentage(percentage)

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        self.device.turn_off()
