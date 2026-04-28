"""Sensor entities for Wi-Tek bridge monitoring."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfDataRate,
    UnitOfFrequency,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import WiTekBridgeCoordinator
from .entity import WiTekBridgeEntity
from .parsing import parse_numeric


@dataclass(frozen=True, kw_only=True)
class WiTekBridgeSensorDescription(SensorEntityDescription):
    """Describe how one sensor reads its value from coordinator data."""

    value_fn: Callable[[WiTekBridgeCoordinator], Any]


def _radio_number(key: str) -> Callable[[WiTekBridgeCoordinator], Any]:
    """Read and numeric-normalize a primary radio field."""
    return lambda coordinator: parse_numeric(coordinator.radio.get(key))


def _sysinfo_number(key: str) -> Callable[[WiTekBridgeCoordinator], Any]:
    """Read and numeric-normalize a system field."""
    return lambda coordinator: parse_numeric(coordinator.sysinfo.get(key))


def _payload_number(key: str) -> Callable[[WiTekBridgeCoordinator], Any]:
    """Read and numeric-normalize a top-level status field."""
    return lambda coordinator: parse_numeric(coordinator.data.get(key))


SENSOR_DESCRIPTIONS: tuple[WiTekBridgeSensorDescription, ...] = (
    WiTekBridgeSensorDescription(
        key="signal",
        translation_key="signal",
        icon="mdi:wifi-strength-4",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_radio_number("signal"),
    ),
    WiTekBridgeSensorDescription(
        key="noise",
        translation_key="noise",
        icon="mdi:wifi-strength-alert-outline",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_radio_number("noise"),
    ),
    WiTekBridgeSensorDescription(
        key="quality",
        translation_key="quality",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_radio_number("quality_perentage"),
    ),
    WiTekBridgeSensorDescription(
        key="bitrate",
        translation_key="bitrate",
        icon="mdi:speedometer",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_radio_number("bitrate"),
    ),
    WiTekBridgeSensorDescription(
        key="channel",
        translation_key="channel",
        icon="mdi:numeric",
        value_fn=_radio_number("channel"),
    ),
    WiTekBridgeSensorDescription(
        key="frequency",
        translation_key="frequency",
        icon="mdi:sine-wave",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: parse_numeric(
            coordinator.radio.get("frequency_num") or coordinator.radio.get("frequency")
        ),
    ),
    WiTekBridgeSensorDescription(
        key="uptime",
        translation_key="uptime",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_sysinfo_number("uptime"),
    ),
    WiTekBridgeSensorDescription(
        key="memory",
        translation_key="memory",
        icon="mdi:memory",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_sysinfo_number("memory"),
    ),
    WiTekBridgeSensorDescription(
        key="load",
        translation_key="load",
        icon="mdi:cpu-64-bit",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_sysinfo_number("load"),
    ),
    WiTekBridgeSensorDescription(
        key="active_connections",
        translation_key="active_connections",
        icon="mdi:lan-connect",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_sysinfo_number("active_connect"),
    ),
    WiTekBridgeSensorDescription(
        key="upload_rate",
        translation_key="upload_rate",
        icon="mdi:upload-network",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_payload_number("upload"),
    ),
    WiTekBridgeSensorDescription(
        key="download_rate",
        translation_key="download_rate",
        icon="mdi:download-network",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_payload_number("download"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wi-Tek bridge sensors for one config entry."""
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: WiTekBridgeCoordinator = runtime_data.coordinator
    async_add_entities(
        WiTekBridgeSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class WiTekBridgeSensor(WiTekBridgeEntity, SensorEntity):
    """Representation of one Wi-Tek bridge monitoring sensor."""

    entity_description: WiTekBridgeSensorDescription

    def __init__(
        self,
        coordinator: WiTekBridgeCoordinator,
        description: WiTekBridgeSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        device_slug = slugify(coordinator.device_info.name)
        self._attr_unique_id = f"{coordinator.device_identifier}_{description.key}"
        self._attr_suggested_object_id = f"{device_slug}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the latest parsed value for this sensor."""
        return self.entity_description.value_fn(self.coordinator)
