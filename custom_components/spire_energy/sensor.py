"""Spire Energy sensor platform."""
from __future__ import annotations
import logging
from datetime import datetime
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
        SpireCurrentBalanceSensor(coordinator, entry),
        SpireNextBillDateSensor(coordinator, entry),
        SpireLastBillAmountSensor(coordinator, entry),
        SpireLastBillDateSensor(coordinator, entry),
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
    def _billing(self) -> dict[str, Any]:
        return self._data.get("billing") or {}

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Spire Energy",
            "manufacturer": "Spire Inc.",
            "model": "Gas Utility Account",
        }


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


class SpireCurrentBalanceSensor(SpireBaseSensor):
    _attr_name = "Spire Current Balance"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "USD"
    _attr_icon = "mdi:currency-usd"

    def __init__(self, coord, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_balance"

    @property
    def native_value(self):
        val = self._billing.get("current_balance")
        if val is not None:
            return round(float(val), 2)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = {}
        if self._billing.get("past_due_balance") is not None:
            attrs["past_due_balance"] = self._billing["past_due_balance"]
        if self._billing.get("is_past_due") is not None:
            attrs["is_past_due"] = self._billing["is_past_due"]
        return attrs


class SpireNextBillDateSensor(SpireBaseSensor):
    _attr_name = "Spire Next Bill Date"
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coord, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_bill_date"

    @property
    def native_value(self):
        raw = self._billing.get("next_bill_date")
        if raw:
            try:
                # Format: "Mar 30, 2026"
                return datetime.strptime(raw, "%b %d, %Y").date()
            except (ValueError, TypeError):
                _LOGGER.debug("Spire: could not parse next_bill_date: %s", raw)
        return None


class SpireLastBillAmountSensor(SpireBaseSensor):
    _attr_name = "Spire Last Bill Amount"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "USD"
    _attr_icon = "mdi:receipt-text"

    def __init__(self, coord, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_bill_amount"

    @property
    def native_value(self):
        val = self._billing.get("last_bill_amount")
        if val is not None:
            try:
                return round(float(val), 2)
            except (ValueError, TypeError):
                pass
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = {}
        billing = self._billing
        if billing.get("last_bill_usage"):
            attrs["usage_ccf"] = billing["last_bill_usage"]
        if billing.get("last_bill_days"):
            attrs["billing_period_days"] = billing["last_bill_days"]
        if billing.get("last_bill_period_start"):
            attrs["period_start"] = billing["last_bill_period_start"]
        if billing.get("last_bill_period_end"):
            attrs["period_end"] = billing["last_bill_period_end"]
        return attrs


class SpireLastBillDateSensor(SpireBaseSensor):
    _attr_name = "Spire Last Bill Date"
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coord, entry):
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_bill_date"

    @property
    def native_value(self):
        raw = self._billing.get("last_bill_date")
        if raw:
            try:
                # Format: "2026-02-27"
                return datetime.strptime(raw, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                _LOGGER.debug("Spire: could not parse last_bill_date: %s", raw)
        return None
