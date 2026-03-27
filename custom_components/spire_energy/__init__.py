"""Spire Energy Home Assistant integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import SpireEnergyAPI, SpireEnergyAuthError, SpireEnergyConnectionError
from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SA_ID,
    CONF_UTILITY_ACCOUNT_ID,
    DOMAIN,
)
from .coordinator import SpireEnergyCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Spire Energy from a config entry."""
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    utility_account_id = entry.data[CONF_UTILITY_ACCOUNT_ID]
    sa_id = entry.data[CONF_SA_ID]

    api = SpireEnergyAPI()

    try:
        logged_in = await api.login(email, password)
        if not logged_in:
            raise ConfigEntryNotReady("Spire Energy: unable to log in")
    except (SpireEnergyAuthError, SpireEnergyConnectionError) as exc:
        raise ConfigEntryNotReady(f"Spire Energy init error: {exc}") from exc

    coordinator = SpireEnergyCoordinator(
        hass=hass,
        api=api,
        email=email,
        password=password,
        utility_account_id=utility_account_id,
        sa_id=sa_id,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Spire Energy config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
