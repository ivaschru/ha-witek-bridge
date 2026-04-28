"""Config flow for Wi-Tek Bridge."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WiTekBridgeApi, WiTekBridgeAuthError, WiTekBridgeConnectionError
from .const import CONF_USERNAME, DEFAULT_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
)


async def _validate_input(
    hass: HomeAssistant,
    user_input: dict[str, Any],
) -> tuple[str, str | None]:
    """Validate credentials and return a title plus optional unique id.

    A real login and status poll happen here so Home Assistant only stores
    entries that are known to work from the current network.
    """
    session = async_get_clientsession(hass)
    api = WiTekBridgeApi(
        session=session,
        host=user_input[CONF_HOST],
        password=user_input[CONF_PASSWORD],
        username=DEFAULT_USERNAME,
    )
    await api.async_login()
    await api.async_fetch_status()

    device_info = await api.async_fetch_device_info()
    unique_id = device_info.mac_address or api.host
    title = device_info.name
    return title, unique_id


class WiTekBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Wi-Tek Bridge."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                CONF_HOST: user_input[CONF_HOST].strip(),
                CONF_PASSWORD: user_input[CONF_PASSWORD],
                CONF_USERNAME: DEFAULT_USERNAME,
            }

            try:
                title, unique_id = await _validate_input(self.hass, data)
            except WiTekBridgeAuthError:
                errors["base"] = "invalid_auth"
            except WiTekBridgeConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error while setting up Wi-Tek bridge")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
