"""Support for voltage, power & energy sensors for VeSync outlets."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .pyvesync.vesyncbasedevice import VeSyncBaseDevice
from .pyvesync.vesyncfan import VeSyncHumidifier
from .pyvesync.helpers import EDeviceFamily
from .pyvesync.const import MODE_HUMIDITY

from .const import (
    DOMAIN,
    SKU_TO_BASE_DEVICE,
    VS_COORDINATOR,
    VS_DEVICES,
    FMT_DISCOVERY,
)
from .coordinator import VeSyncDataCoordinator
from .entity import VeSyncBaseEntity

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
        async_dispatcher_connect(hass, FMT_DISCOVERY(VS_DEVICES), discover)
    )

    _setup_entities(hass.data[DOMAIN][VS_DEVICES], async_add_entities, coordinator)


@callback
def _setup_entities(
    devices: list[VeSyncBaseDevice],
    async_add_entities: AddEntitiesCallback,
    coordinator: VeSyncDataCoordinator,
):
    """Check if device is online and add entity."""

    async_add_entities(
        (
            VeSyncSensorEntity(dev, coordinator, description)
            for dev in devices
            for description in SENSORS
            if description.exists_fn(dev)
        ),
        update_before_add=True,
    )


@dataclass(frozen=True, kw_only=True)
class VeSyncSensorEntityDescription(SensorEntityDescription):
    """Describe VeSync sensor entity."""

    value_fn: Callable[[VeSyncBaseDevice], StateType]
    exists_fn: Callable[[VeSyncBaseDevice], bool] = lambda _: True
    update_fn: Callable[[VeSyncBaseDevice], None] = lambda _: None


def update_energy(device):
    """Update outlet details and energy usage."""
    device.update()
    device.update_energy()

def update_details(device):
    device.update()

def sku_supported(device, supported):
    """Get the base device of which a device is an instance."""
    return SKU_TO_BASE_DEVICE.get(device.device_type) in supported

FILTER_LIFE_SUPPORTED = [
    "LV-PUR131S",
    "Core200S",
    "Core300S",
    "Core400S",
    "Core600S",
    "EverestAir",
    "Vital100S",
    "Vital200S",
]
AIR_QUALITY_SUPPORTED = [
    "LV-PUR131S",
    "Core300S",
    "Core400S",
    "Core600S",
    "Vital100S",
    "Vital200S",
]
PM25_SUPPORTED = [
    "Core300S",
    "Core400S",
    "Core600S",
    "EverestAir",
    "Vital100S",
    "Vital200S",
]

SENSORS: tuple[VeSyncSensorEntityDescription, ...] = (
    VeSyncSensorEntityDescription(
        key="filter-life",
        translation_key="filter_life",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.filter_life,
        exists_fn=lambda device: sku_supported(device, FILTER_LIFE_SUPPORTED),
    ),
    VeSyncSensorEntityDescription(
        key="air-quality",
        translation_key="air_quality",
        value_fn=lambda device: device.details['air_quality'],
        exists_fn=lambda device: device.supports('air_quality'),
    ),
    VeSyncSensorEntityDescription(
        key="pm25",
        device_class=SensorDeviceClass.PM25,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.details["air_quality_value"],
        exists_fn=lambda device: sku_supported(device, PM25_SUPPORTED),
    ),
    VeSyncSensorEntityDescription(
        key="voltage",
        translation_key="current_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.voltage,
        update_fn=update_details,
        exists_fn=lambda device: device.device_family == EDeviceFamily.OUTLET,
    ),
    VeSyncSensorEntityDescription(
        key="Current",
        translation_key="current_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.current,
        update_fn=update_details,
        exists_fn=lambda device: device.device_family == EDeviceFamily.OUTLET,
    ),
    VeSyncSensorEntityDescription(
        key="power",
        translation_key="current_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.power,
        update_fn=update_details,
        exists_fn=lambda device: device.device_family == EDeviceFamily.OUTLET,
    ),
    VeSyncSensorEntityDescription(
        key="energy",
        translation_key="energy_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda device: device.energy_today,
        update_fn=update_details,
        exists_fn=lambda device: device.device_family == EDeviceFamily.OUTLET,
    ),
    VeSyncSensorEntityDescription(
        key="energy-weekly",
        translation_key="energy_week",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda device: device.weekly_energy_total,
        update_fn=update_energy,
        exists_fn=lambda device: device.supports('energyHistory'),
    ),
    VeSyncSensorEntityDescription(
        key="energy-monthly",
        translation_key="energy_month",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda device: device.monthly_energy_total,
        update_fn=update_energy,
        exists_fn=lambda device: device.supports('energyHistory'),
    ),
    VeSyncSensorEntityDescription(
        key="energy-yearly",
        translation_key="energy_year",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda device: device.yearly_energy_total,
        update_fn=update_energy,
        exists_fn=lambda device: device.supports('energyHistory'),
    ),
    VeSyncSensorEntityDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.details[MODE_HUMIDITY],
        exists_fn=lambda device: isinstance(device, VeSyncHumidifier),
    ),
)


class VeSyncSensorEntity(VeSyncBaseEntity, SensorEntity):
    """Representation of a sensor describing a VeSync device."""

    _attr_unique_id: str

    entity_description: VeSyncSensorEntityDescription

    def __init__(
        self,
        device: VeSyncBaseDevice,
        coordinator: VeSyncDataCoordinator,
        description: VeSyncSensorEntityDescription
    ) -> None:
        """Initialize the VeSync outlet device."""
        super().__init__(device, coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{super().unique_id}-{description.key}"

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.device)

    def update(self) -> None:
        """Run the update function defined for the sensor."""
        return self.entity_description.update_fn(self.device)
