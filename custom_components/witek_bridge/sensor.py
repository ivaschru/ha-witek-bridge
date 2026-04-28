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
    enabled_default: bool = True
    precision: int | None = None


def _round_value(value: Any, precision: int | None) -> Any:
    """Round noisy numeric values while preserving unavailable values."""
    if precision is None or value is None:
        return value
    rounded = round(float(value), precision)
    if precision == 0:
        return int(rounded)
    return rounded


def _radio_number(
    key: str,
    *,
    precision: int | None = None,
) -> Callable[[WiTekBridgeCoordinator], Any]:
    """Read and numeric-normalize a primary radio field."""
    return lambda coordinator: _round_value(parse_numeric(coordinator.radio.get(key)), precision)


def _sysinfo_number(
    key: str,
    *,
    precision: int | None = None,
) -> Callable[[WiTekBridgeCoordinator], Any]:
    """Read and numeric-normalize a system field."""
    return lambda coordinator: _round_value(parse_numeric(coordinator.sysinfo.get(key)), precision)


def _payload_number(
    key: str,
    *,
    precision: int | None = None,
) -> Callable[[WiTekBridgeCoordinator], Any]:
    """Read and numeric-normalize a top-level status field."""
    return lambda coordinator: _round_value(parse_numeric(coordinator.data.get(key)), precision)


def _payload_bytes_to_megabits(
    key: str,
    *,
    precision: int | None = None,
) -> Callable[[WiTekBridgeCoordinator], Any]:
    """Convert vendor bytes-per-second rates to megabits per second."""
    return lambda coordinator: _round_value(
        (
            bytes_per_second * 8 / 1_000_000
            if (bytes_per_second := parse_numeric(coordinator.data.get(key))) is not None
            else None
        ),
        precision,
    )


def _uptime_days(coordinator: WiTekBridgeCoordinator) -> float | None:
    """Return bridge uptime converted from vendor seconds to days."""
    seconds = parse_numeric(coordinator.sysinfo.get("uptime"))
    if seconds is None:
        return None
    return _round_value(float(seconds) / 86400, 1)


SENSOR_DESCRIPTIONS: tuple[WiTekBridgeSensorDescription, ...] = (
    WiTekBridgeSensorDescription(
        key="signal",
        translation_key="signal",
        icon="mdi:wifi-strength-4",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        precision=0,
        value_fn=_radio_number("signal", precision=0),
    ),
    WiTekBridgeSensorDescription(
        key="noise",
        translation_key="noise",
        icon="mdi:wifi-strength-alert-outline",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        enabled_default=False,
        precision=0,
        value_fn=_radio_number("noise", precision=0),
    ),
    WiTekBridgeSensorDescription(
        key="quality",
        translation_key="quality",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        precision=0,
        value_fn=_radio_number("quality_perentage", precision=0),
    ),
    WiTekBridgeSensorDescription(
        key="bitrate",
        translation_key="bitrate",
        icon="mdi:speedometer",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        precision=0,
        value_fn=_radio_number("bitrate", precision=0),
    ),
    WiTekBridgeSensorDescription(
        key="channel",
        translation_key="channel",
        icon="mdi:numeric",
        enabled_default=False,
        precision=0,
        value_fn=_radio_number("channel", precision=0),
    ),
    WiTekBridgeSensorDescription(
        key="frequency",
        translation_key="frequency",
        icon="mdi:sine-wave",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        enabled_default=False,
        precision=0,
        value_fn=lambda coordinator: parse_numeric(
            coordinator.radio.get("frequency_num") or coordinator.radio.get("frequency")
        ),
    ),
    WiTekBridgeSensorDescription(
        key="uptime",
        translation_key="uptime",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        precision=1,
        value_fn=_uptime_days,
    ),
    WiTekBridgeSensorDescription(
        key="memory",
        translation_key="memory",
        icon="mdi:memory",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        enabled_default=False,
        precision=0,
        value_fn=_sysinfo_number("memory", precision=0),
    ),
    WiTekBridgeSensorDescription(
        key="load",
        translation_key="load",
        icon="mdi:cpu-64-bit",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        enabled_default=False,
        precision=0,
        value_fn=_sysinfo_number("load", precision=0),
    ),
    WiTekBridgeSensorDescription(
        key="active_connections",
        translation_key="active_connections",
        icon="mdi:lan-connect",
        state_class=SensorStateClass.MEASUREMENT,
        precision=0,
        value_fn=_sysinfo_number("active_connect", precision=0),
    ),
    WiTekBridgeSensorDescription(
        key="upload_rate",
        translation_key="upload_rate",
        icon="mdi:upload-network",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        enabled_default=False,
        precision=2,
        value_fn=_payload_bytes_to_megabits("upload", precision=2),
    ),
    WiTekBridgeSensorDescription(
        key="download_rate",
        translation_key="download_rate",
        icon="mdi:download-network",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        enabled_default=False,
        precision=2,
        value_fn=_payload_bytes_to_megabits("download", precision=2),
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
        self._attr_entity_registry_enabled_default = description.enabled_default
        self._attr_suggested_display_precision = description.precision

    @property
    def native_value(self) -> Any:
        """Return the latest parsed value for this sensor."""
        return self.entity_description.value_fn(self.coordinator)
