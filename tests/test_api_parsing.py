"""Tests for parser helpers that do not need a Home Assistant runtime."""

from pathlib import Path
import sys

INTEGRATION_DIR = Path(__file__).parents[1] / "custom_components" / "witek_bridge"
sys.path.insert(0, str(INTEGRATION_DIR))

from parsing import parse_device_info, parse_numeric  # noqa: E402


def test_parse_numeric() -> None:
    """Numeric parser handles vendor strings with units."""
    assert parse_numeric("-46 dBm") == -46
    assert parse_numeric("137.2MBit/s") == 137.2
    assert parse_numeric("2412 MHz") == 2412
    assert parse_numeric(None) is None


def test_parse_device_info() -> None:
    """Overview parser extracts static metadata from Wi-Tek HTML labels."""
    html = """
    <label>Working Mode:</label> <a class="info">Base Station</a>
    <label>Serial Number:</label> <a class="info">CPE111V2227RU1547</a>
    <label>Version:</label> <a class="info">v5.0.build20220712-1317</a>
    <label>Hardware Model:</label> <a class="info">WI-CPE111-KIT</a>
    <label>MAC Address:</label> <a class="info"> 54:3d:92:02:60:f2</a>
    """

    info = parse_device_info("10.0.0.2", html)

    assert info.name == "WI-CPE111-KIT Base Station (10.0.0.2)"
    assert info.model == "WI-CPE111-KIT"
    assert info.firmware_version == "v5.0.build20220712-1317"
    assert info.serial_number == "CPE111V2227RU1547"
    assert info.mac_address == "54:3d:92:02:60:f2"
