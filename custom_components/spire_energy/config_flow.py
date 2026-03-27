"""Config flow for Spire Energy integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant

from .api import SpireEnergyAPI, SpireEnergyAuthError, SpireEnergyConnectionError
from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SA_ID,
    CONF_UTILITY_ACCOUNT_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_credentials(
    hass: HomeAssistant, email: str, password: str
) -> dict[str, str]:
    """Validate credentials and discover account IDs."""
    api = SpireEnergyAPI()

    logged_in = await api.login(email, password)
    if not logged_in:
        raise SpireEnergyAuthError("Login failed — check email and password")

    accounts = await api.get_accounts()
    if not accounts:
        raise SpireEnergyConnectionError("No utility accounts found")

    utility_account_id = accounts[0]["utilityAccountId"]
    sa_id = await api.get_sa_id(utility_account_id)

    if not sa_id:
        raise SpireEnergyConnectionError(
            "Could not discover Service Agreement ID — contact Spire support"
        )

    return {
        CONF_UTILITY_ACCOUNT_ID: utility_account_id,
        CONF_SA_ID: sa_id,
    }


class SpireEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Spire Energy config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            try:
                ids = await validate_credentials(self.hass, email, password)
            except SpireEnergyAuthError:
                errors["base"] = "invalid_auth"
            except SpireEnergyConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during Spire login")
                errors["base"] = "unknown"
            else:
                # Avoid duplicate entries for the same account
                await self.async_set_unique_id(ids[CONF_UTILITY_ACCOUNT_ID])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Spire Energy ({ids[CONF_UTILITY_ACCOUNT_ID]})",
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: password,
                        **ids,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
            description_placeholders={
                "portal": "myaccount.spireenergy.com",
            },
        )
