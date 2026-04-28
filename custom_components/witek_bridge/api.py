"""HTTP client for Wi-Tek bridge devices.

The vendor UI does not expose a documented API, so this module keeps all
reverse-engineered endpoint details in one place. The rest of the integration
works with parsed dictionaries and does not need to know about cookies, forms,
or vendor field spellings such as ``quality_perentage``.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from urllib.parse import urljoin

import aiohttp

from .const import DEFAULT_TIMEOUT
from .parsing import (
    WiTekBridgeDeviceInfo,
    cookie_header_from_set_cookie_headers,
    normalize_base_url,
    parse_device_info,
)

_LOGGER = logging.getLogger(__name__)


class WiTekBridgeError(Exception):
    """Base exception for Wi-Tek bridge communication errors."""


class WiTekBridgeAuthError(WiTekBridgeError):
    """Raised when the bridge rejects credentials or asks for login again."""


class WiTekBridgeConnectionError(WiTekBridgeError):
    """Raised when the bridge cannot be reached or returns unusable data."""


class WiTekBridgeApi:
    """Small async client for one Wi-Tek bridge."""

    def __init__(
        self,
        *,
        session: aiohttp.ClientSession,
        host: str,
        password: str,
        username: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the client without making network calls."""
        self._session = session
        try:
            self._base_url = normalize_base_url(host)
        except ValueError as err:
            raise WiTekBridgeConnectionError("Host is empty") from err
        self.host = self._base_url.removeprefix("http://").removeprefix("https://").rstrip("/")
        self._password = password
        self._username = username
        self._timeout = timeout
        self._authenticated = False
        self._cookie_header: str | None = None

    @property
    def configuration_url(self) -> str:
        """Return the bridge web UI URL shown in Home Assistant device info."""
        return self._base_url

    async def async_login(self, *, force: bool = False) -> None:
        """Authenticate against the bridge web UI and keep its session cookie."""
        if self._authenticated and not force:
            return
        if force:
            self._cookie_header = None

        payload = {
            "username": self._username,
            "password": self._password,
            "lang": "en-US",
        }

        try:
            async with asyncio.timeout(self._timeout):
                async with self._session.post(
                    urljoin(self._base_url, "login"),
                    data=payload,
                ) as response:
                    response.raise_for_status()
                    data = await response.json(content_type=None)
                    self._cookie_header = _cookie_header_from_response(response)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise WiTekBridgeConnectionError(f"Unable to connect to {self.host}") from err
        except ValueError as err:
            raise WiTekBridgeConnectionError("Login response is not valid JSON") from err

        if data.get("success") is not True:
            raise WiTekBridgeAuthError("Bridge rejected the supplied password")

        self._authenticated = True

    async def async_fetch_device_info(self) -> WiTekBridgeDeviceInfo:
        """Fetch and parse static metadata from the authenticated overview page."""
        await self.async_login()
        html = await self._async_request_text("GET", "")
        return parse_device_info(self.host, html)

    async def async_fetch_status(self) -> dict[str, Any]:
        """Fetch the live monitoring payload from the bridge."""
        await self.async_login()
        return await self._async_request_json("POST", "update/system_status")

    async def async_reboot(self) -> None:
        """Ask the bridge to reboot.

        The device normally drops off the network immediately after accepting
        this request, so the method treats a successful JSON response and a
        sudden disconnect after request dispatch as an expected reboot path.
        """
        await self.async_login()
        try:
            await self._async_request_json(
                "POST",
                "system/reboot",
                data={"REBOOT": 1},
            )
        except WiTekBridgeConnectionError as err:
            _LOGGER.debug("Bridge disconnected while reboot command was in flight: %s", err)

        self._authenticated = False

    async def _async_request_json(
        self,
        method: str,
        path: str,
        *,
        data: dict[str, Any] | None = None,
        retry_auth: bool = True,
    ) -> dict[str, Any]:
        """Run an authenticated request and decode a JSON object response."""
        text = await self._async_request_text(method, path, data=data)
        try:
            parsed = _json_from_text(text)
        except ValueError as err:
            if retry_auth and _looks_like_login_page(text):
                self._authenticated = False
                await self.async_login(force=True)
                return await self._async_request_json(
                    method,
                    path,
                    data=data,
                    retry_auth=False,
                )
            raise WiTekBridgeConnectionError(f"{path} did not return JSON") from err

        if parsed.get("success") is False:
            raise WiTekBridgeConnectionError(f"{path} returned success=false")

        return parsed

    async def _async_request_text(
        self,
        method: str,
        path: str,
        *,
        data: dict[str, Any] | None = None,
    ) -> str:
        """Run an authenticated HTTP request and return the response body."""
        url = urljoin(self._base_url, path)
        headers = {"Cookie": self._cookie_header} if self._cookie_header else None
        try:
            async with asyncio.timeout(self._timeout):
                async with self._session.request(
                    method,
                    url,
                    data=data,
                    headers=headers,
                ) as response:
                    response.raise_for_status()
                    return await response.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise WiTekBridgeConnectionError(f"Unable to fetch {path or '/'} from {self.host}") from err


def _json_from_text(text: str) -> dict[str, Any]:
    """Decode JSON text and require an object payload."""
    decoded = json.loads(text)
    if not isinstance(decoded, dict):
        raise ValueError("JSON response is not an object")
    return decoded


def _cookie_header_from_response(response: aiohttp.ClientResponse) -> str | None:
    """Build a Cookie header from Set-Cookie headers returned by the bridge.

    Home Assistant's shared aiohttp session uses the safe cookie policy, which
    rejects cookies set by IP-address hosts. These bridges are normally added by
    IP address, so we keep only the session cookie value ourselves and attach it
    to follow-up requests.
    """
    return cookie_header_from_set_cookie_headers(response.headers.getall("Set-Cookie", []))


def _looks_like_login_page(text: str) -> bool:
    """Return true when a session expired and the bridge sent HTML login UI."""
    lowered = text.lower()
    return "<html" in lowered and "administrator login" in lowered
