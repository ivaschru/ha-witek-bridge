"""Button entities for Wi-Tek bridge management."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import WiTekBridgeError
from .const import DOMAIN
from .coordinator import WiTekBridgeCoordinator
from .entity import WiTekBridgeEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the reboot button for one Wi-Tek bridge config entry."""
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WiTekBridgeRebootButton(runtime_data.coordinator)])


class WiTekBridgeRebootButton(WiTekBridgeEntity, ButtonEntity):
    """Button that reboots the bridge through the vendor web UI endpoint."""

    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_translation_key = "reboot"

    def __init__(self, coordinator: WiTekBridgeCoordinator) -> None:
        """Initialize the reboot button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_identifier}_reboot"

    async def async_press(self) -> None:
        """Send the reboot command to the bridge."""
        try:
            await self.coordinator.api.async_reboot()
        except WiTekBridgeError as err:
            _LOGGER.exception("Failed to reboot Wi-Tek bridge")
            raise HomeAssistantError("Failed to reboot Wi-Tek bridge") from err

        # Do not force an immediate refresh here: a successful reboot command
        # usually makes the bridge drop off the LAN before it can answer again.
        # The normal coordinator poll will mark entities unavailable if needed.
