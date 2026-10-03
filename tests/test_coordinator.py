"""Tests for the coordinator: auth handling and statistics import."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.spire_energy.api import SpireEnergyConnectionError
from custom_components.spire_energy.coordinator import SpireEnergyCoordinator
from custom_components.spire_energy.statistics import parse_bills, parse_daily_reads

from .common import DAILY, MONTHLY

IMPORT = "custom_components.spire_energy.coordinator.async_import_statistics"
DATA = {"email": "me@example.com", "password": "pw", "utility_account_id": "123", "sa_id": "456"}


def make_api(**overrides) -> MagicMock:
    api = MagicMock()
    api.ensure_authenticated = AsyncMock(return_value=True)
    api.get_daily_usage = AsyncMock(return_value=DAILY)
    api.get_monthly_usage = AsyncMock(return_value=MONTHLY)
    api.get_balance = AsyncMock(return_value={"accountBalance": {"currentBalance": "18.28"}})
    for name, value in overrides.items():
        setattr(api, name, value)
    return api


def make_coordinator(hass, api) -> SpireEnergyCoordinator:
    entry = MockConfigEntry(domain="spire_energy", unique_id="123", data=DATA)
    entry.add_to_hass(hass)
    return SpireEnergyCoordinator(hass, entry, api)


async def test_imports_statistics_once_per_change(hass):
    coordinator = make_coordinator(hass, make_api())
    with patch(IMPORT) as imp:
        data = await coordinator._async_update_data()
        await coordinator._async_update_data()
    imp.assert_called_once_with(hass, "123", parse_daily_reads(DAILY), parse_bills(MONTHLY))
    assert data["latest_usage"]["meterRead"] == "110.00"
    assert data["billing"]["last_bill_amount"] == "33.00"


async def test_bill_history_failure_skips_import(hass):
    coordinator = make_coordinator(hass, make_api(get_monthly_usage=AsyncMock(side_effect=SpireEnergyConnectionError())))
    with patch(IMPORT) as imp:
        data = await coordinator._async_update_data()
    assert imp.call_count == 0  # importing without bills would wipe the cost series
    assert data["billing"]["current_balance"] == "18.28"


async def test_rejected_credentials_start_reauth(hass):
    coordinator = make_coordinator(hass, make_api(ensure_authenticated=AsyncMock(return_value=False)))
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_connection_error_is_update_failed(hass):
    coordinator = make_coordinator(hass, make_api(get_daily_usage=AsyncMock(side_effect=SpireEnergyConnectionError())))
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
