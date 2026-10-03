"""Tests for sensor values."""
from unittest.mock import MagicMock

from custom_components.spire_energy.sensor import SpireGasUsageLatestDaySensor

from .common import daily


def make_sensor(data):
    coordinator = MagicMock(data=data)
    return SpireGasUsageLatestDaySensor(coordinator, MagicMock(entry_id="abc"))


def test_latest_day_reports_most_recent_read_whatever_its_date():
    sensor = make_sensor({"latest_usage": daily("2026-09-28", "6716.14", "0.27999999999999997")})
    assert sensor.unique_id == "abc_gas_usage_latest_day"
    assert sensor.native_value == 0.28
    assert sensor.extra_state_attributes == {"date": "2026-09-28"}


def test_latest_day_unknown_without_reads():
    sensor = make_sensor({"latest_usage": None})
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}
