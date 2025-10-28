# Ensure Device Control

A simple Home Assistant custom integration that provides reliable device control with automatic retry logic.

## Overview

This integration wraps `script.ensure_device_changes` with clean, easy-to-use services. It provides three services that ensure your devices reach their desired state, even when commands occasionally fail.

## Prerequisites

**IMPORTANT:** This integration requires `script.ensure_device_changes` to be installed in your Home Assistant instance. The custom component acts as a clean interface to this script.

## Services

### `ensure.turn_on`

Turn on devices with optional brightness, color, and effect parameters.

**Parameters:**
- `entity_id` (required): Entity or entities to turn on
- `brightness_pct`: Brightness percentage (0-100)
- `brightness`: Brightness value (0-255)
- `color_rgb`: RGB color as [R, G, B]
- `color_name`: Named color (automatically converted to RGB)
- `kelvin`: Color temperature in Kelvin (1000-12000)
- `effect`: Light effect name

**Example:**
```yaml
service: ensure.turn_on
data:
  entity_id: light.kitchen
  brightness_pct: 75
  color_name: "red"
```

### `ensure.turn_off`

Turn off devices.

**Parameters:**
- `entity_id` (required): Entity or entities to turn off

**Example:**
```yaml
service: ensure.turn_off
data:
  entity_id: light.bedroom
```

### `ensure.toggle`

Toggle device state.

**Parameters:**
- `entity_id` (required): Entity or entities to toggle

**Example:**
```yaml
service: ensure.toggle
data:
  entity_id:
    - light.living_room
    - light.dining_room
```

## Features

- **Automatic color name conversion**: Use friendly color names like "red", "blue", "homeassistant" - automatically converted to RGB
- **Multiple entities**: Target single entities, groups, or lists of entities
- **Parameter precedence**: `brightness_pct` takes precedence over `brightness`
- **Clean UI**: Full service UI integration with dropdowns and sliders
- **No configuration needed**: Just install and use

## Installation via HACS

1. Add this repository to HACS as a custom repository
2. Install "Ensure Device Control"
3. Restart Home Assistant
4. Go to **Settings** → **Devices & Services** → **Add Integration**
5. Search for "Ensure Device Control" and add it
6. Services will be available immediately

## Technical Details

- **Simple UI setup**: Add through Settings → Devices & Services (no parameters to configure)
- **Passthrough architecture**: Simply wraps `script.ensure_device_changes` with a clean interface
- **147 color names**: Supports all CSS3/X11 standard color names
- **Entity ID translation**: Accepts `entity_id` parameter and passes as `device` to the script

## Version

- **Current**: 1.0.3
- **Architecture**: Simple wrapper (no retry logic in component itself)
- **Dependencies**: Requires `script.ensure_device_changes`

## Support

- **Issues**: https://github.com/markus99/ha-ensure-device-control/issues
- **Repository**: https://github.com/markus99/ha-ensure-device-control
