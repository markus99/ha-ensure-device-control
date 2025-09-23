# Ensure Device Control for Home Assistant

A Home Assistant custom integration that provides reliable device control with intelligent retry logic and state verification.

## Why This Integration?

Standard Home Assistant device commands sometimes fail, especially with:
- **Hubitat Maker API** integrations
- **Z-Wave/Zigbee** mesh network congestion  
- **Remote devices** with connectivity issues
- **Critical automations** that must work reliably

This integration solves those problems by adding retry logic with exponential backoff and state verification to ensure your devices actually respond.

## Quick Start

After installation, replace your existing service calls:

```yaml
# Instead of this:
action: light.turn_on
target:
  entity_id: light.living_room
data:
  brightness_pct: 75

# Use this:
action: ensure.turn_on
target:
  entity_id: light.living_room  
data:
  brightness_pct: 75
```

The integration will automatically retry up to 5 times with increasing delays if the device doesn't respond, and notify you if it ultimately fails.

## Services

- `ensure.turn_on` - Reliably turn on devices with full parameter support
- `ensure.turn_off` - Reliably turn off devices

## Supported Parameters

All standard Home Assistant parameters are supported:
- `brightness` / `brightness_pct`
- `rgb_color`
- `color_name`
- `color_temp_kelvin`
- And more...

## Installation

### Via HACS (Recommended)
1. Add this repository as a custom HACS repository
2. Install "Ensure Device Control"
3. Restart Home Assistant

### Manual Installation
1. Copy `custom_components/ensure/` to your HA installation
2. Restart Home Assistant

## Configuration

No configuration needed - install and use immediately!

## Contributing

Issues and pull requests welcome! This integration was born from real-world Hubitat reliability problems.

## License

MIT License - see LICENSE file for details.
