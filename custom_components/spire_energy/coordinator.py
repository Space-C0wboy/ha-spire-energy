"""DataUpdateCoordinator for Spire Energy."""
from __future__ import annotations
import logging
from datetime import timedelta
from typing import Any
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import SpireEnergyAPI, SpireEnergyAuthError, SpireEnergyConnectionError
from .const import CONF_SA_ID, CONF_UTILITY_ACCOUNT_ID, DOMAIN, UPDATE_INTERVAL_HOURS
from .statistics import async_import_statistics, parse_bills, parse_daily_reads

_LOGGER = logging.getLogger(__name__)

type SpireConfigEntry = ConfigEntry[SpireEnergyCoordinator]


class SpireEnergyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: SpireEnergyAPI) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(hours=UPDATE_INTERVAL_HOURS),
        )
        self.api = api
        self.utility_account_id = entry.data[CONF_UTILITY_ACCOUNT_ID]
        self.sa_id = entry.data[CONF_SA_ID]
        self._imported: tuple[list, list] | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            if not await self.api.ensure_authenticated():
                # Stop polling until the user re-enters the password, instead of retrying into a lockout.
                raise ConfigEntryAuthFailed("Spire Energy rejected the stored credentials")

            # Fetch daily usage (meter reads)
            daily = await self.api.get_daily_usage(self.utility_account_id, self.sa_id)
        except SpireEnergyAuthError as exc:
            raise UpdateFailed(f"Auth error: {exc}") from exc
        except SpireEnergyConnectionError as exc:
            raise UpdateFailed(f"Connection error: {exc}") from exc
        latest_usage = self._extract_latest_usage(daily)

        # Fetch billing data (balance + due dates + bill history)
        billing, monthly = await self._fetch_billing_data()
        if monthly is not None:
            self._import_statistics(daily, monthly)

        return {
            "daily_raw": daily,
            "latest_usage": latest_usage,
            "is_daily_read_customer": daily.get("isDailyReadCustomer", False),
            "billing": billing,
        }

    def _import_statistics(self, daily: dict, monthly: dict) -> None:
        """Rebuild the Energy dashboard series whenever Spire posts new reads or bills."""
        history = (parse_daily_reads(daily), parse_bills(monthly))
        if history != self._imported:
            async_import_statistics(self.hass, self.utility_account_id, *history)
            self._imported = history

    async def _fetch_billing_data(self) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Fetch balance and last bill info, plus the raw bill history (None if it failed)."""
        billing: dict[str, Any] = {}
        monthly = None
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
            history = await self.api.get_monthly_usage(self.utility_account_id)
            last_bill = self._extract_last_bill(history)
            if last_bill:
                billing["last_bill_amount"] = last_bill.get("dollars")
                billing["last_bill_date"] = last_bill.get("measuredOn")
                billing["last_bill_period_start"] = last_bill.get("startDate")
                billing["last_bill_period_end"] = last_bill.get("endDate")
                billing["last_bill_usage"] = last_bill.get("units")
                billing["last_bill_days"] = last_bill.get("daysInPeriod")
            monthly = history
        except Exception:
            _LOGGER.warning("Spire: failed to fetch monthly usage data")

        return billing, monthly

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
        """Extract the most recent daily usage reading by date."""
        try:
            premises = data.get("premises", [])
            if not premises:
                return None
            # Collect all details across all years
            all_details = []
            for yearly in premises[0].get("yearlyUsages", []):
                for detail in yearly.get("usageDetails", []):
                    if detail.get("meterRead") and detail.get("measuredOn"):
                        all_details.append(detail)
            if not all_details:
                return None
            # Sort by date descending and return the most recent
            all_details.sort(key=lambda d: d.get("measuredOn", ""), reverse=True)
            return all_details[0]
        except (KeyError, IndexError, TypeError):
            pass
        return None
