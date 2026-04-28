"""Constants for the Wi-Tek Bridge integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "witek_bridge"

CONF_USERNAME = "username"

DEFAULT_USERNAME = "admin"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_TIMEOUT = 10

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]

MANUFACTURER = "Wi-Tek"
