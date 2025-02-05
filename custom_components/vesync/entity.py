"""Common entity for VeSync Component."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .pyvesync.vesyncbasedevice import VeSyncBaseDevice

from .const import DOMAIN
from .coordinator import VeSyncDataCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

class VeSyncBaseEntity(CoordinatorEntity[VeSyncDataCoordinator]):
    """Base class for VeSync Entity Representations."""

    _attr_has_entity_name = True

    def __init__(
        self, device: VeSyncBaseDevice, coordinator: VeSyncDataCoordinator
    ) -> None:
        """Initialize the VeSync device."""
        super().__init__(coordinator)
        self.device = device
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
