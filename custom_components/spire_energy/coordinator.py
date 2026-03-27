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

            # Fetch daily usage (meter reads)
            daily = await self.api.get_daily_usage(self.utility_account_id, self.sa_id)
            latest_usage = self._extract_latest_usage(daily)

            # Fetch billing data (balance + due dates)
            billing = await self._fetch_billing_data()

            return {
                "daily_raw": daily,
                "latest_usage": latest_usage,
                "is_daily_read_customer": daily.get("isDailyReadCustomer", False),
                "billing": billing,
            }
        except SpireEnergyAuthError as exc:
            raise UpdateFailed(f"Auth error: {exc}") from exc
        except SpireEnergyConnectionError as exc:
            raise UpdateFailed(f"Connection error: {exc}") from exc

    async def _fetch_billing_data(self) -> dict[str, Any]:
        """Fetch balance and last bill info. Returns empty dict on failure."""
        billing: dict[str, Any] = {}
        try:
            balance_data = await self.api.get_balance(self.utility_account_id)
            acct_balance = balance_data.get("accountBalance", {})
            billing["current_balance"] = acct_balance.get("currentBalance")
            billing["next_bill_date"] = acct_balance.get("nextBillDate")
            billing["past_due_balance"] = acct_balance.get("pastDueBalance")
            billing["is_past_due"] = acct_balance.get("isPastDue", False)
        except Exception:
            _LOGGER.warning("Spire: failed to fetch balance data")

        try:
            monthly = await self.api.get_monthly_usage(self.utility_account_id)
            last_bill = self._extract_last_bill(monthly)
            if last_bill:
                billing["last_bill_amount"] = last_bill.get("dollars")
                billing["last_bill_date"] = last_bill.get("measuredOn")
                billing["last_bill_period_start"] = last_bill.get("startDate")
                billing["last_bill_period_end"] = last_bill.get("endDate")
                billing["last_bill_usage"] = last_bill.get("units")
                billing["last_bill_days"] = last_bill.get("daysInPeriod")
        except Exception:
            _LOGGER.warning("Spire: failed to fetch monthly usage data")

        return billing

    @staticmethod
    def _extract_last_bill(data: dict) -> dict | None:
        """Extract the most recent billing period from monthly usage."""
        try:
            premises = data.get("premises", [])
            if not premises:
                return None
            yearly_usages = premises[0].get("yearlyUsages", [])
            # yearlyUsages are ordered newest first; grab first detail
            for yearly in yearly_usages:
                details = yearly.get("usageDetails", [])
                if details:
                    return details[0]
        except (KeyError, IndexError, TypeError):
            pass
        return None

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
