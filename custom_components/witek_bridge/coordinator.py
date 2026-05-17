"""Coordinator for polling one Wi-Tek bridge."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    WiTekBridgeApi,
    WiTekBridgeAuthError,
    WiTekBridgeConnectionError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, MANUFACTURER
from .parsing import WiTekBridgeDeviceInfo

_LOGGER = logging.getLogger(__name__)

UNREACHABLE_REPAIR_FAILURE_THRESHOLD = 3


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
        self._consecutive_update_failures = 0
        self._unreachable_issue_active = False
        self._unreachable_issue_id = f"{entry.entry_id}_bridge_unreachable"

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
            self.api.reset_session()
            _LOGGER.debug("Unable to fetch static bridge metadata: %s", err)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest bridge status."""
        try:
            payload = await self.api.async_fetch_status()
        except WiTekBridgeAuthError as err:
            self.api.reset_session()
            self._consecutive_update_failures = 0
            self._delete_unreachable_issue()
            raise ConfigEntryAuthFailed from err
        except WiTekBridgeConnectionError as err:
            # A network drop often means the bridge rebooted and discarded its
            # session cookie. Reset local auth state so the next coordinator
            # poll performs a full login instead of retrying a stale cookie.
            self.api.reset_session()
            self._consecutive_update_failures += 1
            if (
                self._consecutive_update_failures
                >= UNREACHABLE_REPAIR_FAILURE_THRESHOLD
            ):
                self._create_unreachable_issue(str(err))
            raise UpdateFailed(str(err)) from err

        self._consecutive_update_failures = 0
        self._delete_unreachable_issue()
        return payload

    def _create_unreachable_issue(self, error: str) -> None:
        """Show a Home Assistant Repairs issue while reconnect retries continue."""
        if self._unreachable_issue_active:
            return

        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self._unreachable_issue_id,
            is_fixable=False,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="bridge_unreachable",
            translation_placeholders={
                "host": self.api.host,
                "scan_interval": str(DEFAULT_SCAN_INTERVAL),
                "error": error,
            },
        )
        self._unreachable_issue_active = True

    def clear_unreachable_issue(self) -> None:
        """Remove the runtime connectivity Repairs issue for this config entry."""
        self._delete_unreachable_issue()

    def _delete_unreachable_issue(self) -> None:
        """Clear the Repairs issue after the bridge answers successfully again."""
        if not self._unreachable_issue_active:
            return

        ir.async_delete_issue(self.hass, DOMAIN, self._unreachable_issue_id)
        self._unreachable_issue_active = False
