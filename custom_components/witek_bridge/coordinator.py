"""Coordinator for polling one Wi-Tek bridge."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    WiTekBridgeApi,
    WiTekBridgeAuthError,
    WiTekBridgeConnectionError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, MANUFACTURER
from .parsing import WiTekBridgeDeviceInfo

_LOGGER = logging.getLogger(__name__)


class WiTekBridgeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll one bridge once and fan the data out to all entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: WiTekBridgeApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            always_update=False,
        )
        self.api = api
        self.device_info = WiTekBridgeDeviceInfo(
            host=api.host,
            name=f"Wi-Tek Bridge {api.host}",
            manufacturer=MANUFACTURER,
        )

    @property
    def radio(self) -> dict[str, Any]:
        """Return the primary radio status block from the latest payload."""
        radios = self.data.get("data") if self.data else None
        if isinstance(radios, list) and radios:
            return radios[0]
        return {}

    @property
    def sysinfo(self) -> dict[str, Any]:
        """Return the system status block from the latest payload."""
        system = self.data.get("system") if self.data else None
        if isinstance(system, dict) and isinstance(system.get("sysinfo"), dict):
            return system["sysinfo"]
        return {}

    @property
    def device_identifier(self) -> str:
        """Return the most stable identifier available for this bridge."""
        if self.device_info.mac_address:
            return self.device_info.mac_address
        return self.api.host

    async def _async_setup(self) -> None:
        """Load static device metadata before the first status refresh."""
        try:
            self.device_info = await self.api.async_fetch_device_info()
        except WiTekBridgeConnectionError as err:
            # Live status is more important than pretty metadata. If the HTML
            # page changes, sensors can still work from the JSON status endpoint.
            _LOGGER.debug("Unable to fetch static bridge metadata: %s", err)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest bridge status."""
        try:
            return await self.api.async_fetch_status()
        except WiTekBridgeAuthError as err:
            raise ConfigEntryAuthFailed from err
        except WiTekBridgeConnectionError as err:
            raise UpdateFailed(str(err)) from err
