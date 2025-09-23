# Ensure Device Control

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/YOUR_USERNAME/hacs-ensure-integration.svg)](https://github.com/YOUR_USERNAME/hacs-ensure-integration/releases)

**Reliable device control for Home Assistant with intelligent retry logic.**

Perfect for Hubitat integrations and other unreliable device connections that sometimes fail to respond to commands.

## Features

- 🔄 **Intelligent Retry Logic**: Automatically retries failed commands with exponential backoff
- 🎯 **State Verification**: Ensures devices actually reach the desired state
- 🌈 **Full Light Control**: Supports brightness, RGB colors, color names, and color temperature
- 🔔 **Failure Notifications**: Get notified when devices fail after all retry attempts
- ⚡ **Native HA Integration**: Works just like built-in `light.turn_on` and `switch.turn_on` services
- 🎛️ **Entity Selection**: Use areas, device classes, and entity groups naturally

## Use Cases

- **Hubitat Integration**: Overcome Maker API reliability issues
- **Z-Wave/Zigbee Mesh**: Handle network congestion and timing issues  
- **Remote Devices**: Retry commands for devices with spotty connectivity
- **Critical Automations**: Ensure important devices always respond

## Services

### `ensure.turn_on`
Reliably turn on devices with optional parameters:

```yaml
# Simple on
action: ensure.turn_on
target:
  entity_id: light.living_room

# With brightness
action: ensure.turn_on
target:
  entity_id: light.living_room
data:
  brightness_pct: 75

# With color and brightness
action: ensure.turn_on
target:
  entity_id: light.living_room
data:
  rgb_color: [255, 0, 0]
  brightness_pct: 50

# Multiple devices
action: ensure.turn_on
target:
  area_id: living_room
  device_class: light
```

### `ensure.turn_off`
Reliably turn off devices:

```yaml
action: ensure.turn_off
target:
  entity_id: switch.fan
```

## Configuration

No configuration required! Install and use immediately.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL
6. Select "Integration" as the category
7. Click "Add"
8. Find "Ensure Device Control" and click "Install"
9. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Copy the `custom_components/ensure` folder to your HA `custom_components` directory
3. Restart Home Assistant

## Comparison to Built-in Services

| Feature | Built-in Services | Ensure Services |
|---------|------------------|-----------------|
| Reliability | Single attempt | Up to 5 retries with backoff |
| State Verification | None | Waits and verifies actual state |
| Failure Handling | Silent failure | Persistent notifications |
| Hubitat Compatibility | Unreliable | Designed for Hubitat issues |

## Support

If you find this integration helpful, consider:
- ⭐ Starring this repository
- 🐛 Reporting issues
- 💡 Suggesting improvements
