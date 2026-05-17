"""Tests for Wi-Tek API session lifecycle helpers."""

import importlib.util
from pathlib import Path
import sys
import types

INTEGRATION_DIR = Path(__file__).parents[1] / "custom_components" / "witek_bridge"


def _load_api_without_home_assistant():
    """Load api.py with minimal fake package modules for standalone tests."""
    package_name = "witek_bridge_standalone_test"
    package = types.ModuleType(package_name)
    package.__path__ = [str(INTEGRATION_DIR)]
    sys.modules[package_name] = package

    # api.py only needs DEFAULT_TIMEOUT from const.py, but the real const.py
    # imports Home Assistant. A tiny fake keeps this test runnable without a HA
    # development environment.
    const_module = types.ModuleType(f"{package_name}.const")
    const_module.DEFAULT_TIMEOUT = 10
    sys.modules[f"{package_name}.const"] = const_module

    parsing_spec = importlib.util.spec_from_file_location(
        f"{package_name}.parsing",
        INTEGRATION_DIR / "parsing.py",
    )
    assert parsing_spec is not None
    assert parsing_spec.loader is not None
    parsing_module = importlib.util.module_from_spec(parsing_spec)
    sys.modules[f"{package_name}.parsing"] = parsing_module
    parsing_spec.loader.exec_module(parsing_module)

    api_spec = importlib.util.spec_from_file_location(
        f"{package_name}.api",
        INTEGRATION_DIR / "api.py",
    )
    assert api_spec is not None
    assert api_spec.loader is not None
    api_module = importlib.util.module_from_spec(api_spec)
    sys.modules[f"{package_name}.api"] = api_module
    api_spec.loader.exec_module(api_module)
    return api_module


WiTekBridgeApi = _load_api_without_home_assistant().WiTekBridgeApi


def test_reset_session_clears_cached_auth_state() -> None:
    """Session reset makes the next bridge request perform a fresh login."""
    api = WiTekBridgeApi(
        session=object(),
        host="192.0.2.10",
        password="test-password",
        username="admin",
    )
    api._authenticated = True
    api._cookie_header = "_app_=stale-cookie"

    api.reset_session()

    assert api._authenticated is False
    assert api._cookie_header is None
