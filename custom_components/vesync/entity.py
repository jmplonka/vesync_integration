"""Common entity for VeSync Component."""

import logging
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .pyvesync.vesyncbasedevice import VeSyncBaseDevice

from .const import DOMAIN
from .coordinator import VeSyncDataCoordinator


_LOGGER = logging.getLogger(__name__)


class VeSyncBaseEntity(CoordinatorEntity[VeSyncDataCoordinator]):
    """Base class for VeSync Entity Representations."""

    # The base VeSyncBaseEntity has _attr_has_entity_name
    # and this is to follow the device name
    _attr_name: str = None
    _attr_has_entity_name: bool = True
    _attr_unique_id: str
    device: VeSyncBaseDevice
    entity_description: EntityDescription

    def __init__(
        self,
        device: VeSyncBaseDevice,
        coordinator: VeSyncDataCoordinator,
        description: EntityDescription
    ) -> None:
        """Initialize the VeSync device."""
        super().__init__(coordinator)
        self.device = device
        self.entity_description = description
        self._attr_unique_id = self.base_unique_id

    @property
    def base_unique_id(self):
        """Return the ID of this device."""
        # The unique_id property may be overridden in subclasses, such as in
        # sensors. Maintaining base_unique_id allows us to group related
        # entities under a single device.
        if isinstance(self.device.sub_device_no, int):
            return f"{self.device.cid}{self.device.sub_device_no!s}"
        return self.device.cid

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        return self.device.connection_status == "online"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.base_unique_id)},
            manufacturer="VeSync",
            model=self.device.device_type,
            name=self.device.device_name,
            sw_version=self.device.current_firm_version,
        )

    @property
    def is_on(self) -> bool:
        """Return True if device is on."""
        return self.device.is_on

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        success = self.device.turn_on()
        if not success:
            raise HomeAssistantError("An error occurred while turning on.")

        self.schedule_update_ha_state()

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        success = self.device.turn_off()
        if not success:
            raise HomeAssistantError("An error occurred while turning off.")

        self.schedule_update_ha_state()
