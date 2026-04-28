"""Pure parsing helpers for Wi-Tek bridge payloads and HTML."""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import re
from typing import Any

DEFAULT_MANUFACTURER = "Wi-Tek"

_LABEL_VALUE_RE = re.compile(
    r"<label>(?P<label>[^:<]+):?</label>\s*<a[^>]*class=[\"']info[\"'][^>]*>(?P<value>.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(slots=True)
class WiTekBridgeDeviceInfo:
    """Static metadata parsed from the bridge overview page."""

    host: str
    name: str
    manufacturer: str = DEFAULT_MANUFACTURER
    model: str | None = None
    firmware_version: str | None = None
    serial_number: str | None = None
    mac_address: str | None = None
    working_mode: str | None = None


def normalize_base_url(host: str) -> str:
    """Return a normalized HTTP base URL for user-provided host input."""
    host = host.strip()
    if not host:
        raise ValueError("Host is empty")

    if "://" not in host:
        host = f"http://{host}"

    return host.rstrip("/") + "/"


def parse_numeric(value: Any) -> float | int | None:
    """Extract the leading number from vendor values like ``-46 dBm``."""
    if value is None:
        return None

    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if match is None:
        return None

    parsed = float(match.group(0))
    if parsed.is_integer():
        return int(parsed)
    return parsed


def parse_device_info(host: str, html: str) -> WiTekBridgeDeviceInfo:
    """Parse static bridge metadata from the overview HTML page."""
    values: dict[str, str] = {}
    for match in _LABEL_VALUE_RE.finditer(html):
        label = unescape(_TAG_RE.sub("", match.group("label"))).strip()
        value = unescape(_TAG_RE.sub("", match.group("value"))).strip()
        if label and value:
            values[label] = value

    model = values.get("Hardware Model")
    serial = values.get("Serial Number")
    mac = values.get("MAC Address")
    working_mode = values.get("Working Mode")
    version = values.get("Version")

    if model and working_mode:
        name = f"{model} {working_mode} ({host})"
    elif model:
        name = f"{model} ({host})"
    else:
        name = f"Wi-Tek Bridge {host}"

    return WiTekBridgeDeviceInfo(
        host=host,
        name=name,
        model=model,
        firmware_version=version,
        serial_number=serial,
        mac_address=mac.lower() if mac else None,
        working_mode=working_mode,
    )
