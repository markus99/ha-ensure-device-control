"""Service implementations for Ensure Device Control."""
import logging
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
    SERVICE_TOGGLE,
    TARGET_SCRIPT,
    COLOR_NAME_TO_RGB,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the ensure services."""

    async def handle_turn_on(call: ServiceCall) -> None:
        """Handle the ensure.turn_on service call."""
        # Get all parameters
        entity_id = call.data.get("entity_id")
        # Convert entity_id from Wrapper/list to string or comma-separated list
        if isinstance(entity_id, str):
            device_param = entity_id
        elif entity_id is not None:
            # Convert to list first (handles Wrapper objects), then join
            entity_list = list(entity_id)
            # If single entity, pass as string; if multiple, pass as comma-separated
            device_param = entity_list[0] if len(entity_list) == 1 else ", ".join(entity_list)
        else:
            device_param = None

        brightness_pct = call.data.get("brightness_pct")
        brightness = call.data.get("brightness")
        color_rgb = call.data.get("color_rgb")
        color_name = call.data.get("color_name")
        kelvin = call.data.get("kelvin")
        effect = call.data.get("effect")

        # Convert color_name to color_rgb if provided
        if color_name and not color_rgb:
            color_name_lower = color_name.lower()
            if color_name_lower in COLOR_NAME_TO_RGB:
                color_rgb = COLOR_NAME_TO_RGB[color_name_lower]
                _LOGGER.debug(f"Converted color_name '{color_name}' to rgb_color {color_rgb}")
            else:
                _LOGGER.warning(f"Unknown color_name '{color_name}', ignoring")

        # Build service data for script
        script_data = {
            "device": device_param,
            "state": "on",
        }

        # Add optional parameters if provided
        if brightness_pct is not None:
            script_data["brightness_pct"] = brightness_pct
        if brightness is not None:
            script_data["brightness"] = brightness
        if color_rgb is not None:
            script_data["color_rgb"] = color_rgb
        if kelvin is not None:
            script_data["kelvin"] = kelvin
        if effect is not None:
            script_data["effect"] = effect

        _LOGGER.debug(f"Calling {TARGET_SCRIPT} with data: {script_data}")

        # Call the ensure_device_changes script
        await hass.services.async_call(
            "script",
            "ensure_device_changes",
            script_data,
            blocking=False,
        )

    async def handle_turn_off(call: ServiceCall) -> None:
        """Handle the ensure.turn_off service call."""
        entity_id = call.data.get("entity_id")
        # Convert entity_id from Wrapper/list to string or comma-separated list
        if isinstance(entity_id, str):
            device_param = entity_id
        elif entity_id is not None:
            # Convert to list first (handles Wrapper objects), then join
            entity_list = list(entity_id)
            # If single entity, pass as string; if multiple, pass as comma-separated
            device_param = entity_list[0] if len(entity_list) == 1 else ", ".join(entity_list)
        else:
            device_param = None

        script_data = {
            "device": device_param,
            "state": "off",
        }

        _LOGGER.debug(f"Calling {TARGET_SCRIPT} with data: {script_data}")

        await hass.services.async_call(
            "script",
            "ensure_device_changes",
            script_data,
            blocking=False,
        )

    async def handle_toggle(call: ServiceCall) -> None:
        """Handle the ensure.toggle service call."""
        entity_id = call.data.get("entity_id")
        # Convert entity_id from Wrapper/list to string or comma-separated list
        if isinstance(entity_id, str):
            device_param = entity_id
        elif entity_id is not None:
            # Convert to list first (handles Wrapper objects), then join
            entity_list = list(entity_id)
            # If single entity, pass as string; if multiple, pass as comma-separated
            device_param = entity_list[0] if len(entity_list) == 1 else ", ".join(entity_list)
        else:
            device_param = None

        script_data = {
            "device": device_param,
            "state": "toggle",
        }

        _LOGGER.debug(f"Calling {TARGET_SCRIPT} with data: {script_data}")

        await hass.services.async_call(
            "script",
            "ensure_device_changes",
            script_data,
            blocking=False,
        )

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_TURN_ON,
        handle_turn_on,
        schema=vol.Schema({
            vol.Required("entity_id"): cv.entity_ids,
            vol.Optional("brightness_pct"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
            vol.Optional("brightness"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
            vol.Optional("color_rgb"): vol.All(list, vol.Length(min=3, max=3)),
            vol.Optional("color_name"): cv.string,
            vol.Optional("kelvin"): vol.All(vol.Coerce(int), vol.Range(min=1000, max=12000)),
            vol.Optional("effect"): cv.string,
        }),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_TURN_OFF,
        handle_turn_off,
        schema=vol.Schema({
            vol.Required("entity_id"): cv.entity_ids,
        }),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_TOGGLE,
        handle_toggle,
        schema=vol.Schema({
            vol.Required("entity_id"): cv.entity_ids,
        }),
    )

    _LOGGER.info("Ensure services registered successfully")
