# Ensure Device Control for Home Assistant (BETA)

⚠️ **BETA VERSION - EARLY TESTING PHASE** ⚠️

**This integration is currently in BETA and undergoing active testing. Use with caution in production environments.**

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
- `rgb_color` / `hs_color` / `xy_color` / `color_name`
- `color_temp_kelvin` / `kelvin`
- `transition` (Light Transition Timing)
- `effect` / `flash`
- And more...

### Parameter Conflict Resolution

If you specify conflicting parameters, the integration uses priority order (first found wins):

**Brightness**: `brightness_pct` > `brightness`
```yaml
data:
  brightness_pct: 75  # This wins
  brightness: 100     # This gets removed
```

**Color**: `rgb_color` > `hs_color` > `xy_color` > `color_name`
```yaml
data:
  rgb_color: [255, 0, 0]  # This wins (red)
  color_name: "blue"      # This gets removed
```

**Temperature**: `color_temp_kelvin` > `kelvin`
```yaml
data:
  color_temp_kelvin: 3000  # This wins
  kelvin: 4000             # This gets removed
```

**No Defaults Added**: The integration only removes conflicts - it doesn't add default values. If you don't specify brightness, the device keeps its current brightness.

## Installation

⚠️ **BETA WARNING**: This integration is in early testing. Please test thoroughly in a non-production environment first.

### Via HACS (Recommended)
1. Add this repository as a custom HACS repository
2. Install "Ensure Device Control (BETA)"
3. Restart Home Assistant

### Manual Installation
1. Copy `custom_components/ensure/` to your HA installation
2. Restart Home Assistant

## Configuration

The integration includes a configuration UI accessible via:
**Settings** → **Integrations** → **Add Integration** → **Ensure Device Control**

Configure:
- Max retry attempts (1-10, default: 5)
- Base timeout (500-5000ms, default: 1000ms)
- Failure notifications (on/off, default: on)

## Testing & Feedback

**This is a BETA release** - please help us improve it:

1. **Test thoroughly** with non-critical devices first
2. **Report issues** via GitHub Issues
3. **Share feedback** on functionality and reliability
4. **Check logs** for any errors or unexpected behavior

Known areas needing testing:
- Group entity handling
- Various device types (lights, switches, fans, etc.)
- Configuration options functionality
- Error handling and recovery

## Contributing

Issues and pull requests welcome! This integration was born from real-world Hubitat reliability problems.

## License

MIT License - see LICENSE file for details.
