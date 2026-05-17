# AGENTS.md

## Project Purpose

- This repository contains a Home Assistant custom integration for Wi-Tek wireless bridge devices.
- The integration is intended for HACS installation and local LAN operation.
- Supported functionality is intentionally narrow: monitoring plus a reboot button.

## Repository Layout

- `custom_components/witek_bridge/` — Home Assistant custom integration files managed by HACS.
- `custom_components/witek_bridge/api.py` — local HTTP client for Wi-Tek web UI endpoints.
- `custom_components/witek_bridge/sensor.py` — monitoring entities.
- `custom_components/witek_bridge/button.py` — reboot button entity.
- `tests/` — lightweight tests for parser/helper behavior that can run outside Home Assistant.

## Security Rules

- Never commit real bridge passwords, Home Assistant tokens, cookies, SSH keys, or endpoint-specific secrets.
- Passwords must be entered through the Home Assistant config flow and stored in Home Assistant config entries.
- Do not add default credentials to docs, examples, tests, or fixtures.
- Avoid adding management actions beyond reboot unless the user explicitly asks for it.

## Maintenance Notes

- Keep `README.md`, `hacs.json`, and `manifest.json` in sync when changing installation requirements or supported features.
- Keep code comments helpful and explicit around device HTTP quirks because this API is reverse-engineered from the vendor web UI.
- Runtime connectivity failures are handled by `WiTekBridgeCoordinator`: setup-time outages should surface as Home Assistant setup retry, runtime outages should reset the cached web UI session, keep coordinator polling, and raise/clear the Repairs issue after the configured consecutive-failure threshold.
- If new writable endpoints are added, document their blast radius and keep them out of default dashboards unless they are safe.
