"""Spire Energy API client."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    BASE_URL,
    EP_ACCOUNTS,
    EP_ACCOUNT,
    EP_DAILY_USAGE,
    EP_MONTHLY_USAGE,
    EP_BALANCE,
    EP_MFA_VALIDATE,
)

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE_URL,
}


class SpireEnergyAuthError(Exception):
    """Authentication failed."""


class SpireEnergyConnectionError(Exception):
    """Connection error."""


class SpireEnergyAPI:
    """Client for the Spire Energy customer portal API."""

    def __init__(self) -> None:
        self._cookies: dict[str, str] = {}
        self._email: str = ""
        self._password: str = ""

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    async def login(self, email: str, password: str) -> bool:
        """Log in via JSON POST to Spire's MFA API and store session cookies."""
        self._email = email
        self._password = password

        login_url = f"{BASE_URL}/o/rest/mfa/v1.0/login"
        _LOGGER.debug("Spire: logging in as %s", email)

        try:
            jar = aiohttp.CookieJar(unsafe=True)
            login_headers = {
                **HEADERS,
                "Content-Type": "application/json",
                "Origin": BASE_URL,
                "Referer": BASE_URL + "/",
            }
            async with aiohttp.ClientSession(headers=login_headers, cookie_jar=jar) as session:
                # Seed initial session cookies
                async with session.get(BASE_URL, ssl=True) as resp:
                    resp.raise_for_status()

                # JSON POST to the real login endpoint
                async with session.post(
                    login_url,
                    json={"userName": email, "password": password, "rememberMe": False},
                    ssl=True,
                ) as resp:
                    resp.raise_for_status()
                    result = await resp.json(content_type=None)

            status = result.get("status", "")
            if status != "AUTHENTICATED":
                _LOGGER.warning("Spire login returned status: %s", status)
                return False

            self._cookies = {c.key: c.value for c in jar}
            _LOGGER.debug("Spire login successful, cookies: %s", list(self._cookies.keys()))
            return bool(self._cookies.get("mya-mfa-jwt"))

        except aiohttp.ClientError as exc:
            raise SpireEnergyConnectionError(f"Login HTTP error: {exc}") from exc

    async def validate_session(self) -> bool:
        """Return True if the current session cookies are still valid."""
        try:
            data = await self._get(EP_MFA_VALIDATE)
            return data.get("status") == "VALID-JWT"
        except Exception:
            return False

    async def ensure_authenticated(self) -> bool:
        """Validate session, re-login if needed."""
        if self._cookies and await self.validate_session():
            return True
        _LOGGER.info("Spire: session invalid, re-authenticating")
        return await self.login(self._email, self._password)

    # ------------------------------------------------------------------
    # Data endpoints
    # ------------------------------------------------------------------

    async def get_accounts(self) -> list[dict[str, Any]]:
        """Return list of utility accounts."""
        return await self._get(EP_ACCOUNTS)  # type: ignore[return-value]

    async def get_account_detail(self, utility_account_id: str) -> dict[str, Any]:
        """Return full account detail including saId."""
        url = EP_ACCOUNT.format(account_id=utility_account_id)
        return await self._get(url)

    async def get_sa_id(self, utility_account_id: str) -> str | None:
        """Discover the Service Agreement ID for an account."""
        detail = await self.get_account_detail(utility_account_id)
        addresses = detail.get("addresses", [])
        if addresses:
            return addresses[0].get("saId")
        return None

    async def get_daily_usage(
        self, utility_account_id: str, sa_id: str
    ) -> dict[str, Any]:
        """Return daily usage history with cumulative meter reads."""
        url = EP_DAILY_USAGE.format(account_id=utility_account_id)
        return await self._get(url, params={"saId": sa_id})

    async def get_monthly_usage(
        self, utility_account_id: str
    ) -> dict[str, Any]:
        """Return monthly/billing-period usage history."""
        url = EP_MONTHLY_USAGE.format(account_id=utility_account_id)
        return await self._get(url, params={"onOverviewPage": "true"})

    async def get_balance(self, utility_account_id: str) -> dict[str, Any]:
        """Return current balance and billing info."""
        url = EP_BALANCE.format(account_id=utility_account_id)
        return await self._get(url)

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    async def _get(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        """Perform an authenticated GET request."""
        if not self._cookies:
            raise SpireEnergyAuthError("Not authenticated — call login() first")

        try:
            async with aiohttp.ClientSession(
                headers=HEADERS,
                cookies=self._cookies,
            ) as session:
                async with session.get(url, params=params, ssl=True) as resp:
                    if resp.status == 401:
                        raise SpireEnergyAuthError("Session expired (401)")
                    resp.raise_for_status()
                    return await resp.json(content_type=None)
        except aiohttp.ClientError as exc:
            raise SpireEnergyConnectionError(f"HTTP error: {exc}") from exc
