"""Service implementations for Ensure Device Control."""
import asyncio
import logging
from typing import Any, Dict, List

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.exceptions import ServiceValidationError
from homeassistant.components import persistent_notification

from .const import (
    DOMAIN,
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
    CONF_MAX_RETRIES,
    CONF_BASE_TIMEOUT,
    CONF_ENABLE_NOTIFICATIONS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BASE_TIMEOUT,
    DEFAULT_ENABLE_NOTIFICATIONS,
    FIXED_TIMEOUT_INCREMENT,
    FIXED_INITIAL_DELAY,
    BRIGHTNESS_TOLERANCE,
    BRIGHTNESS_PCT_TOLERANCE,
    RGB_TOLERANCE,
    KELVIN_TOLERANCE,
    SUPPORTED_FEATURES,
)

_LOGGER = logging.getLogger(__name__)

# Global config storage for services
_service_config = {
    CONF_MAX_RETRIES: DEFAULT_MAX_RETRIES,
    CONF_BASE_TIMEOUT: DEFAULT_BASE_TIMEOUT,
    CONF_ENABLE_NOTIFICATIONS: DEFAULT_ENABLE_NOTIFICATIONS,
}

async def async_setup_services(hass: HomeAssistant, config: Dict[str, Any] = None) -> None:
    """Set up the ensure services."""
    global _service_config

    # Update global config if provided
    if config:
        _service_config.update(config)
        _LOGGER.debug(f"Updated service config: {_service_config}")

    # Only register services once
    if not hass.services.has_service(DOMAIN, SERVICE_TURN_ON):
        async def ensure_turn_on(call: ServiceCall) -> None:
            """Handle ensure turn_on service."""
            await _handle_ensure_service(hass, call, "on")

        async def ensure_turn_off(call: ServiceCall) -> None:
            """Handle ensure turn_off service."""
            await _handle_ensure_service(hass, call, "off")

        hass.services.async_register(DOMAIN, SERVICE_TURN_ON, ensure_turn_on)
        hass.services.async_register(DOMAIN, SERVICE_TURN_OFF, ensure_turn_off)

        _LOGGER.info("Ensure services registered successfully")

async def _handle_ensure_service(hass: HomeAssistant, call: ServiceCall, state: str) -> None:
    """Handle the ensure service call with retry logic."""

    # Get original input for first attempt (preserves groups)
    original_target = _get_original_target(call)
    if not original_target:
        raise ServiceValidationError("No entities specified")

    _LOGGER.debug(f"Ensure {state} called for original target: {original_target}")

    # Get service data
    service_data = dict(call.data)
    service_data.pop("entity_id", None)  # Remove if present

    # Try original target first (preserves group operations for speed)
    await _try_original_target(hass, original_target, state, service_data)

    # Wait a moment for the command to propagate
    await asyncio.sleep(FIXED_INITIAL_DELAY)

    # Now expand to individual entities for verification/retry
    expanded_entities = _get_target_entities(hass, call)
    if not expanded_entities:
        _LOGGER.warning("No entities found after expansion")
        return

    _LOGGER.debug(f"Expanded to individual entities: {expanded_entities}")

    # Process each individual entity with retry logic (queued mode)
    for entity_id in expanded_entities:
        await _ensure_entity_state(hass, entity_id, state, service_data)

async def _try_original_target(hass: HomeAssistant, original_target: str, state: str, service_data: Dict[str, Any]) -> None:
    """Try the original target as-is (matching original script logic)."""

    # Determine service to call based on original script logic
    if 'group' in original_target:
        service_domain = "homeassistant"
        service_name = f"turn_{state}"
    else:
        domain = original_target.split(".")[0]
        service_domain = domain
        service_name = f"turn_{state}"

    # Prepare service data
    data = {"entity_id": original_target}
    if service_data:
        data.update(service_data)

    try:
        await hass.services.async_call(service_domain, service_name, data)
        _LOGGER.debug(f"Called {service_domain}.{service_name} for original target: {original_target}")
    except Exception as e:
        _LOGGER.warning(f"Original target method failed for {original_target}: {e}")

def _get_original_target(call: ServiceCall) -> str:
    """Get the original target entity_id as specified in the call (before expansion)."""

    # Check entity_id in data first (legacy)
    if "entity_id" in call.data:
        entity_id = call.data["entity_id"]
        if isinstance(entity_id, str):
            return entity_id
        elif isinstance(entity_id, list) and len(entity_id) == 1:
            return entity_id[0]
        elif isinstance(entity_id, list) and len(entity_id) > 1:
            # Multiple entities - use first one as representative
            return entity_id[0]

    # Check target parameter (modern)
    if hasattr(call, 'target') and call.target:
        if call.target.entity_id and len(call.target.entity_id) == 1:
            return call.target.entity_id[0]
        elif call.target.entity_id and len(call.target.entity_id) > 1:
            # Multiple entities - use first one as representative
            return call.target.entity_id[0]

    return None

async def _ensure_entity_state(hass: HomeAssistant, entity_id: str, target_state: str, service_data: Dict[str, Any]) -> None:
    """Ensure a single entity reaches the target state with retry logic."""
    global _service_config

    domain = entity_id.split(".")[0]
    retry_count = 0
    max_retries = _service_config[CONF_MAX_RETRIES]
    base_timeout = _service_config[CONF_BASE_TIMEOUT]

    while retry_count < max_retries:
        # Check if entity is already in desired state
        if await _is_entity_in_target_state(hass, entity_id, target_state, service_data):
            _LOGGER.debug(f"{entity_id} reached target state on attempt {retry_count + 1}")
            return

        retry_count += 1

        # Calculate timeout for this attempt
        timeout_ms = base_timeout + (retry_count * FIXED_TIMEOUT_INCREMENT)
        timeout_sec = timeout_ms / 1000

        _LOGGER.debug(f"Retry {retry_count}/{max_retries} for {entity_id}, timeout: {timeout_sec}s")

        # Call the service
        service_name = f"{domain}.turn_{target_state}"
        data = {"entity_id": entity_id}
        if service_data:
            data.update(service_data)

        try:
            await hass.services.async_call(
                domain,
                f"turn_{target_state}",
                data
            )
        except Exception as e:
            _LOGGER.warning(f"Service call failed for {entity_id} on attempt {retry_count}: {e}")

        # Wait for state change with timeout
        try:
            await asyncio.wait_for(
                _wait_for_state_change(hass, entity_id, target_state, service_data),
                timeout=timeout_sec
            )
        except asyncio.TimeoutError:
            _LOGGER.debug(f"Timeout waiting for {entity_id} state change on attempt {retry_count}")
            continue

    # If we get here, all retries failed
    current_state = hass.states.get(entity_id)
    current_state_value = current_state.state if current_state else "unknown"

    _LOGGER.error(f"{entity_id} failed to turn {target_state} after {max_retries} attempts. Current state: {current_state_value}")

    # Create persistent notification if enabled
    if _service_config[CONF_ENABLE_NOTIFICATIONS]:
        await persistent_notification.async_create(
            hass,
            f"{entity_id} failed to turn {target_state} after {max_retries} attempts. Current state: {current_state_value}",
            "Device Control Failed",
            f"device_fail_{entity_id.replace('.', '_')}"
        )

async def _wait_for_state_change(hass: HomeAssistant, entity_id: str, target_state: str, service_data: Dict[str, Any]) -> None:
    """Wait for entity to reach target state."""

    while True:
        if await _is_entity_in_target_state(hass, entity_id, target_state, service_data):
            return
        await asyncio.sleep(0.1)  # Check every 100ms

async def _is_entity_in_target_state(hass: HomeAssistant, entity_id: str, target_state: str, service_data: Dict[str, Any]) -> bool:
    """Check if entity is in the target state with tolerances."""

    state = hass.states.get(entity_id)
    if not state:
        return False

    # Check basic on/off state
    if state.state != target_state:
        return False

    # For "off" state, basic state check is sufficient
    if target_state == "off":
        return True

    # For "on" state, check additional attributes if specified
    if target_state == "on" and service_data:
        return _check_attribute_tolerances(state, service_data)

    return True

def _check_attribute_tolerances(state, service_data: Dict[str, Any]) -> bool:
    """Check if entity attributes match target values within tolerance."""

    attributes = state.attributes

    # Check brightness
    if "brightness" in service_data:
        target_brightness = service_data["brightness"]
        actual_brightness = attributes.get("brightness", 0)
        if abs(actual_brightness - target_brightness) > BRIGHTNESS_TOLERANCE:
            return False

    if "brightness_pct" in service_data:
        target_brightness_pct = service_data["brightness_pct"]
        actual_brightness = attributes.get("brightness", 0)
        actual_brightness_pct = round((actual_brightness / 255) * 100) if actual_brightness else 0
        if abs(actual_brightness_pct - target_brightness_pct) > BRIGHTNESS_PCT_TOLERANCE:
            return False

    # Check RGB color
    if "rgb_color" in service_data:
        target_rgb = service_data["rgb_color"]
        actual_rgb = attributes.get("rgb_color")
        if actual_rgb and len(target_rgb) == 3 and len(actual_rgb) == 3:
            for i in range(3):
                if abs(actual_rgb[i] - target_rgb[i]) > RGB_TOLERANCE:
                    return False
        elif not actual_rgb:
            return False

    # Check color temperature (Kelvin)
    if "color_temp_kelvin" in service_data or "kelvin" in service_data:
        target_kelvin = service_data.get("color_temp_kelvin") or service_data.get("kelvin")
        actual_kelvin = attributes.get("color_temp_kelvin")
        if actual_kelvin and abs(actual_kelvin - target_kelvin) > KELVIN_TOLERANCE:
            return False
        elif not actual_kelvin:
            return False

    # Check hue and saturation
    if "hs_color" in service_data:
        target_hs = service_data["hs_color"]
        actual_hs = attributes.get("hs_color")
        if actual_hs and len(target_hs) == 2 and len(actual_hs) == 2:
            if abs(actual_hs[0] - target_hs[0]) > HUE_TOLERANCE:
                return False
            if abs(actual_hs[1] - target_hs[1]) > SATURATION_TOLERANCE:
                return False
        elif not actual_hs:
            return False

    return True

def _get_target_entities(hass: HomeAssistant, call: ServiceCall) -> List[str]:
    """Get list of target entity IDs from service call."""

    entity_ids = []

    # Handle entity_id in data (legacy)
    if "entity_id" in call.data:
        entity_id = call.data["entity_id"]
        if isinstance(entity_id, str):
            entity_ids.append(entity_id)
        elif isinstance(entity_id, list):
            entity_ids.extend(entity_id)

    # Handle target parameter (modern)
    if hasattr(call, 'target') and call.target:
        if call.target.entity_id:
            entity_ids.extend(call.target.entity_id)

        # Handle area_id and device_id targets
        if call.target.area_id or call.target.device_id:
            registry = er.async_get(hass)

            if call.target.area_id:
                for area_id in call.target.area_id:
                    area_entities = er.async_entries_for_area(registry, area_id)
                    entity_ids.extend([entry.entity_id for entry in area_entities])

            if call.target.device_id:
                for device_id in call.target.device_id:
                    device_entities = er.async_entries_for_device(registry, device_id)
                    entity_ids.extend([entry.entity_id for entry in device_entities])

    # Remove duplicates while preserving order
    seen = set()
    unique_entity_ids = []
    for entity_id in entity_ids:
        if entity_id not in seen:
            seen.add(entity_id)
            unique_entity_ids.append(entity_id)

    return unique_entity_ids
