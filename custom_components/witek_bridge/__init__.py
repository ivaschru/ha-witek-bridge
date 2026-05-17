"""Home Assistant setup for the Wi-Tek Bridge integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import UpdateFailed

from .api import WiTekBridgeApi
from .const import CONF_USERNAME, DEFAULT_USERNAME, DOMAIN, PLATFORMS
from .coordinator import WiTekBridgeCoordinator


@dataclass
class WiTekBridgeRuntimeData:
    """Runtime objects shared by the integration platforms."""

    api: WiTekBridgeApi
    coordinator: WiTekBridgeCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one Wi-Tek bridge config entry."""
    session = async_get_clientsession(hass)
    api = WiTekBridgeApi(
        session=session,
        host=entry.data[CONF_HOST],
        password=entry.data[CONF_PASSWORD],
        username=entry.data.get(CONF_USERNAME, DEFAULT_USERNAME),
    )

    coordinator = WiTekBridgeCoordinator(hass, entry, api)

    # This first refresh validates the login and gives every entity initial
    # state. If the bridge is offline during Home Assistant startup, surface the
    # failure as ConfigEntryNotReady so HA marks the entry as retrying setup
    # instead of leaving a half-loaded integration behind.
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        api.reset_session()
        raise
    except UpdateFailed as err:
        api.reset_session()
        raise ConfigEntryNotReady(str(err)) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = WiTekBridgeRuntimeData(
        api=api,
        coordinator=coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload one Wi-Tek bridge config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        runtime_data = hass.data[DOMAIN].pop(entry.entry_id)
        runtime_data.coordinator.clear_unreachable_issue()
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok
