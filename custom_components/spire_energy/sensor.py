"""Spire Energy sensor platform."""
from __future__ import annotations
import logging
from typing import Any
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .coordinator import SpireEnergyCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
UNIT_CCF = "CCF"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SpireEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SpireGasMeterSensor(coordinator, entry),
        SpireGasUsageTodaySensor(coordinator, entry),
    ], update_before_add=True)

class SpireBaseSensor(SensorEntity):
    _attr_should_poll = True
    def __init__(self, coordinator: SpireEnergyCoordinator, entry: ConfigEntry) -> None:
        self._coord = coordinator
        self._entry = entry
        self._last_good: dict[str, Any] = {}
    async def async_update(self) -> None:
        if self._coord.data:
            self._last_good = self._coord.data
    @property
    def _data(self) -> dict[str, Any]:
        return self._coord.data or getattr(self, "_last_good", {})
    @property
    def device_info(self) -> dict[str, Any]:
        return {"identifiers": {(DOMAIN, self._entry.entry_id)}, "name": "Spire Energy", "manufacturer": "Spire Inc.", "model": "Gas Utility Account"}

class SpireGasMeterSensor(SpireBaseSensor):
    _attr_name = "Spire Gas Meter Reading"
    _attr_device_class = SensorDeviceClass.GAS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UNIT_CCF
    _attr_icon = "mdi:meter-gas"
    def __init__(self, coord, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.entry_id}_gas_meter_reading"
    @property
    def native_value(self):
        u = self._data.get("latest_usage") or {}
        return u.get("meterRead")

class SpireGasUsageTodaySensor(SpireBaseSensor):
    _attr_name = "Spire Gas Usage Today"
    _attr_device_class = SensorDeviceClass.GAS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UNIT_CCF
    _attr_icon = "mdi:fire"
    def __init__(self, coord, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.entry_id}_gas_usage_today"
    @property
    def native_value(self):
        u = self._data.get("latest_usage") or {}
        return u.get("consumption")
