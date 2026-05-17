# Wi-Tek Bridge for Home Assistant

Home Assistant custom integration for monitoring Wi-Tek wireless bridge devices such as `WI-CPE111-KIT`.

This integration uses the local web UI API exposed by the devices. It does not use any cloud service.

## Features

- Add multiple bridge devices through the Home Assistant UI.
- Configure each device with its IP address and password.
- Monitor radio and system status.
- Reboot a bridge from Home Assistant.
- Retry setup and reconnect automatically when a bridge is temporarily offline.

## Entities

Each configured device creates these entities:

- Connected
- Signal
- Noise
- Link quality
- Bitrate
- Channel
- Frequency
- Uptime
- Memory usage
- Load
- Active connections
- Upload rate
- Download rate
- Reboot button

## Installation with HACS

1. Open HACS in Home Assistant.
2. Open custom repositories.
3. Add this repository URL as category `Integration`.
4. Install `Wi-Tek Bridge`.
5. Restart Home Assistant.
6. Go to **Settings -> Devices & services -> Add integration**.
7. Search for `Wi-Tek Bridge`.
8. Add one bridge by entering its IP address and password.
9. Repeat the add integration flow for every additional bridge.

## Manual Installation

Copy `custom_components/witek_bridge` into your Home Assistant `custom_components` directory, then restart Home Assistant.

## Supported Devices

Tested against Wi-Tek `WI-CPE111-KIT` firmware builds:

- `v5.0.build20220712-1317`
- `v5.0.build20221010-1054`

Other Wi-Tek devices using the same web UI may work, but are not verified.

## Notes

- The password is stored by Home Assistant in the config entry storage, not in YAML.
- The integration polls `POST /update/system_status`.
- The reboot button calls `POST /system/reboot`.
- Reboot or a network outage temporarily makes the device and its entities unavailable until the bridge comes back online.
- If the bridge is offline while Home Assistant starts, the config entry is marked as retrying setup instead of loading partially.
- During normal runtime outages, the integration resets the cached web UI session, retries every polling interval, and creates a Home Assistant Repairs issue after several consecutive failures. The issue is cleared automatically after a successful poll.

## Troubleshooting

If setup fails:

- Check that Home Assistant can reach the bridge IP address.
- Open the bridge web UI from the same network and verify that the password works.
- Make sure the bridge is reachable over plain HTTP on port `80`.

If an already configured bridge becomes unavailable:

- Check bridge power and wireless link first; the integration will continue reconnect attempts without manual reload.
- Look for a Home Assistant Repairs issue named `Wi-Tek bridge is unreachable` after repeated failed polls.
- If the web UI works but entities stay unavailable, reload the config entry once to force a fresh setup path.

Enable debug logging if you need more detail:

```yaml
logger:
  logs:
    custom_components.witek_bridge: debug
```
