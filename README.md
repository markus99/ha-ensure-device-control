# Ensure Device Control for Home Assistant (BETA)

⚠️ **BETA VERSION - ADVANCED TESTING PHASE** ⚠️

A Home Assistant custom integration that provides **reliable device control** with intelligent retry logic, background recovery, and Hubitat overload protection.

## Why This Integration?

Standard Home Assistant device commands sometimes fail, especially with:
- **Hubitat Maker API** integrations
- **Z-Wave/Zigbee** mesh network congestion
- **Remote devices** with connectivity issues
- **Slow fans** that need extra time to respond
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

**Works with lights, switches, fans, and groups:**

```yaml
# Fan control with retry
action: ensure.turn_on
target:
  entity_id: fan.bedroom
data:
  speed_pct: 60

# Group operations (fast bulk + individual verification)
action: ensure.turn_on
target:
  entity_id: group.living_room_lights
data:
  brightness_pct: 80
```

The integration will automatically retry up to 5 times with increasing delays if the device doesn't respond, and notify you if it ultimately fails.

## ✨ New in v0.3.1-beta

### 🚀 **Performance Improvements**
- **Concurrent Processing**: Groups now process up to 3x faster
- **Smart Rate Limiting**: Protects Hubitat from overload (max 3 concurrent operations)

### 🧠 **Intelligent Background Retry**
- **Automatic Recovery**: 30-second background retry for temporary issues
- **Silent Success**: Most problems resolve without bothering you
- **Configurable Timing**: Adjust background retry delay (10-300 seconds)

### 🔔 **Smart Notifications**
- **Reduced Noise**: Only notify when manual intervention truly needed
- **Specific Details**: Shows exactly which device failed in groups
- **One-Click Retry**: Working retry button in every notification

## Services

- `ensure.turn_on` - Reliably turn on devices with full parameter support
- `ensure.turn_off` - Reliably turn off devices

## Supported Parameters

All standard Home Assistant parameters are supported:
- `brightness` / `brightness_pct` (lights)
- `rgb_color` / `hs_color` / `xy_color` / `color_name` (lights)
- `color_temp_kelvin` / `kelvin` (lights)
- `speed` / `speed_pct` (fans)
- `delay` (custom timeout override)
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

**Fan Speed**: `speed_pct` > `speed`
```yaml
data:
  speed_pct: 75     # This wins
  speed: "high"     # This gets removed
```

### Custom Delay Override

Use the `delay` parameter to override timeout for slower devices:

```yaml
action: ensure.turn_on
target:
  entity_id: fan.slow_ceiling_fan
data:
  speed_pct: 50
  delay: 3000  # 3 seconds instead of default 1 second
```

**No Defaults Added**: The integration only removes conflicts - it doesn't add default values. If you don't specify brightness, the device keeps its current brightness.

## Installation

⚠️ **BETA VERSION**: This integration is in advanced testing. Please test thoroughly before production use.

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
- Background retry delay (10-300 seconds, default: 30s)

## Testing & Feedback

**BETA testing in progress** - feedback needed:

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
