"""Spire Energy Home Assistant integration."""
from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import SpireEnergyAPI
from .const import CONF_EMAIL, CONF_PASSWORD
from .coordinator import SpireConfigEntry, SpireEnergyCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SpireConfigEntry) -> bool:
    """Set up Spire Energy from a config entry."""
    api = SpireEnergyAPI(entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    coordinator = SpireEnergyCoordinator(hass, entry, api)
    # Logs in on the first refresh; bad credentials raise ConfigEntryAuthFailed and start reauth.
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SpireConfigEntry) -> bool:
    """Unload a Spire Energy config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
