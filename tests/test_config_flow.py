"""Tests for the config flow."""
from unittest.mock import patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.spire_energy.api import SpireEnergyAuthError

VALIDATE = "custom_components.spire_energy.config_flow.validate_credentials"
SETUP = "custom_components.spire_energy.async_setup_entry"
DATA = {"email": "me@example.com", "password": "pw", "utility_account_id": "123", "sa_id": "456"}
IDS = {"utility_account_id": "123", "sa_id": "456"}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def no_setup():
    with patch(SETUP, return_value=True):
        yield


async def test_reauth_updates_password(hass):
    entry = MockConfigEntry(domain="spire_energy", unique_id="123", data=DATA)
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    with patch(VALIDATE, return_value=IDS) as validate:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"password": "new"})
    validate.assert_called_once_with(hass, "me@example.com", "new")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["password"] == "new"


async def test_reauth_bad_password_shows_error(hass):
    entry = MockConfigEntry(domain="spire_energy", unique_id="123", data=DATA)
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    with patch(VALIDATE, side_effect=SpireEnergyAuthError()):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"password": "nope"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    assert entry.data["password"] == "pw"


async def test_reauth_rejects_other_account(hass):
    entry = MockConfigEntry(domain="spire_energy", unique_id="123", data=DATA)
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    with patch(VALIDATE, return_value={"utility_account_id": "999", "sa_id": "1"}):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"password": "new"})
    assert result["reason"] == "unique_id_mismatch"
