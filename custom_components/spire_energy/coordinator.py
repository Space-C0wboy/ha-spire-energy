"""DataUpdateCoordinator for Spire Energy."""
from __future__ import annotations
import logging
from datetime import timedelta
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import SpireEnergyAPI, SpireEnergyAuthError, SpireEnergyConnectionError
from .const import DOMAIN, UPDATE_INTERVAL_HOURS

_LOGGER = logging.getLogger(__name__)

class SpireEnergyCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, email, password, utility_account_id, sa_id):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(hours=UPDATE_INTERVAL_HOURS))
        self.api = api
        self.email = email
        self.password = password
        self.utility_account_id = utility_account_id
        self.sa_id = sa_id

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            if not await self.api.ensure_authenticated():
                raise UpdateFailed("Unable to authenticate with Spire Energy")
            daily = await self.api.get_daily_usage(self.utility_account_id, self.sa_id)
            latest_usage = self._extract_latest_usage(daily)
            return {"daily_raw": daily, "latest_usage": latest_usage, "is_daily_read_customer": daily.get("isDailyReadCustomer", False)}
        except SpireEnergyAuthError as exc:
            raise UpdateFailed(f"Auth error: {exc}") from exc
        except SpireEnergyConnectionError as exc:
            raise UpdateFailed(f"Connection error: {exc}") from exc

    @staticmethod
    def _extract_latest_usage(data):
        try:
            premises = data.get("premises", [])
            if not premises: return None
            for yearly in premises[0].get("yearlyUsages", []):
                for detail in yearly.get("usageDetails", []):
                    if detail.get("meterRead"):
                        return detail
        except (KeyError, IndexError, TypeError):
            pass
        return None
