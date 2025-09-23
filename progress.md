# Ensure Device Control Integration - Project Progress

## Project Overview

We're creating a Home Assistant custom integration called "Ensure Device Control" that converts existing Home Assistant scripts into native HA services with retry logic. The goal is to provide reliable device control, especially for Hubitat Maker API integrations that sometimes fail.

## Original Problem

User has Home Assistant scripts that ensure device state changes with retry logic, specifically designed for Hubitat integration reliability issues. Current automation calls look like:

```yaml
action: script.ensure_device_changes
data:
  device: switch.fan_golf_room_zw
  state: "on"
```

## Target Solution

Convert to native HA services that work like built-in services:

```yaml
action: ensure.turn_on
target:
  entity_id: switch.fan_golf_room_zw
```

With support for all light parameters (brightness, RGB, kelvin, etc.).

## Current Script Logic (Refined)

The user's final working script (`ensure_device_changes`):

```yaml
ensure_device_changes:
  sequence:
    - variables:
        device_list: "{{ expand(device) | map(attribute='entity_id') | list }}"
    - alias: Try Default Method First
      service_template: |-
        {% if 'group' in device %}
          homeassistant.turn_{{ state }}
        {% else %}
          {{ device.split('.').0 }}.turn_{{ state }}
        {% endif %}
      data_template:
        entity_id: "{{ device }}"
    - delay: "00:00:01"
    - repeat:
        for_each: "{{ device_list }}"
        sequence:
          - variables:
              device_1: "{{ repeat.item }}"
          - repeat:
              while:
                - condition: template
                  value_template: "{{ states(device_1) != state }}"
                  alias: "WHILE: Device State != Desired State"
                - condition: template
                  value_template: "{{ repeat.index <= 5 }}"
                  alias: "WHILE: # Attempts <= 5"
              sequence:
                - service_template: "{{ device_1.split('.').0 }}.turn_{{ state }}"
                  data_template:
                    entity_id: "{{ device_1 }}"
                  alias: "ServiceTemplate: DEVICE_1.turn_STATE"
                - wait_template: "{{ states(device_1) == state }}"
                  continue_on_timeout: true
                  timeout:
                    milliseconds: "{{ 1000 + (repeat.index * 500) }}"
                  alias: "WAIT FOR: Device State = Desired State (backoff timeout)"
          # Check if device failed after all attempts
          - if:
              - condition: template
                value_template: "{{ states(device_1) != state }}"
            then:
              - service: persistent_notification.create
                data:
                  title: "Device Control Failed"
                  message: "{{ device_1 }} failed to turn {{ state }} after 5 attempts. Current state: {{ states(device_1) }}"
                  notification_id: "device_fail_{{ device_1 | replace('.', '_') }}"
            alias: "Notify if device failed to change state"
  mode: queued
  max: 20
  trace:
    stored_traces: 20
```

## Key Design Decisions Made

1. **Mode: queued** - Prevents overwhelming Hubitat hub with parallel requests
2. **Linear backoff**: 1.5s, 2.0s, 2.5s, 3.0s, 3.5s timeouts
3. **State verification**: Waits and verifies actual state change
4. **Failure notifications**: Persistent notifications when all retries fail
5. **5 retry attempts maximum**

## Related Scripts

User also has specialized scripts for lights:
- `ensure_device_changes_brightpct` - Brightness control
- `ensure_device_changes_colorname_brightpct` - Color names
- `ensure_device_changes_color_rgb_brightpct` - RGB colors  
- `ensure_device_changes_kelvin_brightness` - Color temperature

These will be consolidated into the single `ensure.turn_on` service.

## Hubitat Integration Research

Key findings about Hubitat HA integration reliability issues:

- **Common problem**: Commands not executing or state not updating
- **Root cause**: Maker API reliability, network communication issues
- **Solutions**: Retry logic, queued mode, state verification
- **User's approach**: Correct solution for documented problems

## Repository Structure Created

```
hacs-ensure-integration/
├── README.md                    # GitHub repository description
├── info.md                      # HACS information page  
├── hacs.json                    # HACS metadata
├── LICENSE                      # MIT license
├── .gitignore                   # Python gitignore
└── custom_components/
    └── ensure/
        ├── __init__.py          # Integration setup
        ├── manifest.json        # Integration metadata
        ├── const.py             # Constants and configuration
        ├── services.yaml        # Service definitions
        └── services.py          # Main service logic
```

## Files Created (Artifacts)

All necessary files have been created as artifacts in our conversation:

1. **manifest.json** - Integration metadata for Home Assistant
2. **__init__.py** - Main integration setup and service registration
3. **const.py** - Constants, tolerances, and configuration values
4. **services.yaml** - Service definitions for HA UI (all parameters)
5. **services.py** - Main service implementation with retry logic
6. **hacs.json** - HACS integration metadata
7. **info.md** - HACS description page with features and examples
8. **README.md** - GitHub repository description
9. **File Structure Guide** - Complete setup instructions

## Key Implementation Details

### Retry Logic
- **Base timeout**: 1000ms + (attempt * 500ms)
- **Max retries**: 5 attempts
- **Queued processing**: One entity at a time to avoid hub overload
- **State verification**: Checks actual state with tolerances

### Tolerance Settings
- **Brightness**: ±5 units (0-255), ±2% for percentage
- **RGB colors**: ±10 per color channel
- **Color temperature**: ±20 Kelvin
- **Hue/Saturation**: ±5 units

### Service Features
- **Full parameter support**: All standard HA light parameters
- **Entity targeting**: Supports areas, device classes, entity groups
- **Failure notifications**: Persistent notifications on ultimate failure
- **Debug logging**: Comprehensive logging for troubleshooting

## Critical Implementation Note: Group Handling and Speed

**IMPORTANT**: The current Python code has a mismatch with the original script logic that needs correction:

### Original Script Logic (Correct):
```yaml
service_template: |-
  {% if 'group' in device %}
    homeassistant.turn_{{ state }}
  {% else %}
    {{ device.split('.').0 }}.turn_{{ state }}
  {% endif %}
```

### What This Means:
- **If INPUT contains 'group'** → use `homeassistant.turn_on` (faster, bulk operation)
- **Otherwise** → use domain-specific service (`light.turn_on`, `switch.turn_on`, etc.)

### Current Python Code Issue:
The Python code checks each **individual entity's domain** instead of the **original input**. This breaks the logic.

### Goal: SPEED + CONFIRMATION
1. **SPEED**: Try the fastest method first (bulk operations when possible)
2. **CONFIRMATION**: Then verify each individual device actually changed state
3. **Group expansion**: Only happens for the individual retry verification phase

### Correct Flow Should Be:
1. **Try original input as-is** (group operation if it's a group)
2. **Wait 1 second** for propagation
3. **Expand groups into individual entities**
4. **Retry individual entities** that didn't reach target state

### Files Reference:
- **scripts.yaml** - Original working logic for group handling
- **automation.yaml** - Examples of how groups were called

## Service Design Preferences

User prefers **simplified service interface**:
- **ensure.turn_on** - Only service needed for "on" operations
- **ensure.turn_off** - Only service needed for "off" operations
- **Required parameter**: ENTITY (entity_id/target)
- **Optional parameters**: kelvin, color, brightness, etc. (all as optional)

This means users can call:
```yaml
# Simple on
action: ensure.turn_on
target:
  entity_id: light.living_room

# With any optional parameters
action: ensure.turn_on
target:
  entity_id: light.living_room
data:
  brightness_pct: 75
  kelvin: 3000
```

## Next Steps for Claude Code

1. **Create GitHub repository** named `hacs-ensure-integration`
2. **Set up directory structure** as shown above
3. **Copy artifact contents** into corresponding files
4. **Update placeholders**: Replace `YOUR_USERNAME` with actual GitHub username
5. **Simplify services.yaml** - Make entity required, all others optional
6. **Test integration locally** in Home Assistant
7. **Publish to HACS** once tested

## Testing Plan

1. **Manual installation**: Copy `custom_components/ensure` to HA
2. **Service testing**: Use Developer Tools → Services
3. **Automation testing**: Replace existing script calls
4. **Failure testing**: Verify retry logic and notifications
5. **Parameter testing**: Test brightness, RGB, kelvin controls

## Repository Settings

- **Name**: `hacs-ensure-integration` (or similar)
- **Description**: "Reliable device control for Home Assistant with retry logic - perfect for Hubitat integration"
- **License**: MIT
- **Public**: Required for HACS
- **Topics**: home-assistant, hacs, hubitat, automation, reliability

## Important Notes

- **Web Claude limitations**: Cannot directly access local files or GitHub
- **WSL Claude Code**: Can work directly with repository files
- **File encoding**: Ensure UTF-8 encoding for all Python files
- **Version**: Start with 1.0.0 for initial release
- **Dependencies**: No external dependencies required

## User Context

- **Experienced with HA**: Has complex automation scripts
- **Hubitat user**: Dealing with Maker API reliability issues  
- **WSL environment**: Running Claude Code in Windows WSL
- **Goal**: Professional HACS integration for community use

This integration will solve a real problem many Hubitat+HA users face and could become a valuable community resource.
