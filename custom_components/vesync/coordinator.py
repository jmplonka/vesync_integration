"""Class to manage VeSync data updates."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .pyvesync import VeSync

from .const import UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class VeSyncDataCoordinator(DataUpdateCoordinator[None]):
    """Class representing data coordinator for VeSync devices."""

    _manager: VeSync

    def __init__(self, hass: HomeAssistant, manager: VeSync) -> None:
        """Initialize."""
        self._manager = manager

        super().__init__(
            hass,
            _LOGGER,
            name="VeSyncDataCoordinator",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> None:
        """Fetch data from API endpoint."""
        return await self.hass.async_add_executor_job(self.update_data_all)

    def update_data_all(self) -> None:
        """Update all the devices."""
        # Using `update_all_devices` instead of `update` to avoid fetching
        # device list each time.
        for device in self._manager.device_list:
            device.update()
            device.update_energy()
