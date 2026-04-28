"""Binary sensor entities for Wi-Tek bridge monitoring."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import WiTekBridgeCoordinator
from .entity import WiTekBridgeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wi-Tek bridge binary sensors for one config entry."""
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WiTekBridgeConnectedBinarySensor(runtime_data.coordinator)])


class WiTekBridgeConnectedBinarySensor(WiTekBridgeEntity, BinarySensorEntity):
    """Binary connectivity sensor derived from the primary radio mode."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:wifi"
    _attr_translation_key = "connected"

    def __init__(self, coordinator: WiTekBridgeCoordinator) -> None:
        """Initialize the connected binary sensor."""
        super().__init__(coordinator)
        device_slug = slugify(coordinator.device_info.name)
        self._attr_unique_id = f"{coordinator.device_identifier}_connected"
        self._attr_suggested_object_id = f"{device_slug}_connected"

    @property
    def is_on(self) -> bool | None:
        """Return true when the Wi-Tek radio reports a running link."""
        mode = self.coordinator.radio.get("mode")
        if mode is None:
            return None
        return str(mode).casefold() == "running"
