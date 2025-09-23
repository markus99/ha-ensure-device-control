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
    CONF_BACKGROUND_RETRY_DELAY,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BASE_TIMEOUT,
    DEFAULT_ENABLE_NOTIFICATIONS,
    DEFAULT_BACKGROUND_RETRY_DELAY,
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
    CONF_BACKGROUND_RETRY_DELAY: DEFAULT_BACKGROUND_RETRY_DELAY,
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

        async def retry_failed_device(call: ServiceCall) -> None:
            """Retry a previously failed device."""
            entity_id = call.data.get("entity_id")
            target_state = call.data.get("target_state")

            if not entity_id or not target_state:
                _LOGGER.error("Missing entity_id or target_state for retry")
                return

            _LOGGER.info(f"Retrying failed device: {entity_id} -> {target_state}")

            # Create a new service call to retry the device
            await _ensure_entity_state(hass, entity_id, target_state, {})

            # Dismiss the notification
            await persistent_notification.async_dismiss(
                hass, f"device_fail_{entity_id.replace('.', '_')}"
            )

        hass.services.async_register(DOMAIN, SERVICE_TURN_ON, ensure_turn_on)
        hass.services.async_register(DOMAIN, SERVICE_TURN_OFF, ensure_turn_off)
        hass.services.async_register(DOMAIN, "retry_failed_device", retry_failed_device)

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

    # Expand to individual entities for conflict resolution context
    expanded_entities = _get_target_entities(hass, call)

    # Resolve parameter conflicts with priority order and add smart defaults
    service_data = _resolve_parameter_conflicts(hass, service_data, expanded_entities, state)

    # Try original target first (preserves group operations for speed)
    await _try_original_target(hass, original_target, state, service_data)

    # Wait a moment for the command to propagate
    await asyncio.sleep(FIXED_INITIAL_DELAY)
    if not expanded_entities:
        _LOGGER.warning("No entities found after expansion")
        return

    _LOGGER.debug(f"Expanded to individual entities: {expanded_entities}")

    # Process each individual entity with retry logic (queued mode)
    for entity_id in expanded_entities:
        await _ensure_entity_state(hass, entity_id, state, service_data, original_target)

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
        # Filter out ensure-specific parameters that shouldn't go to the device
        filtered_data = {k: v for k, v in service_data.items() if k != "delay"}
        data.update(filtered_data)

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

async def _ensure_entity_state(hass: HomeAssistant, entity_id: str, target_state: str, service_data: Dict[str, Any], original_target: str = None) -> None:
    """Ensure a single entity reaches the target state with retry logic."""
    global _service_config

    domain = entity_id.split(".")[0]
    retry_count = 0
    max_retries = _service_config[CONF_MAX_RETRIES]

    # Use delay parameter override if provided, otherwise use configured base timeout
    base_timeout = service_data.get("delay", _service_config[CONF_BASE_TIMEOUT])
    if "delay" in service_data:
        _LOGGER.debug(f"Using custom delay override: {base_timeout}ms for {entity_id}")

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
            # Filter out ensure-specific parameters that shouldn't go to the device
            filtered_data = {k: v for k, v in service_data.items() if k != "delay"}
            data.update(filtered_data)

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

    _LOGGER.error(f"{entity_id} failed to ensure device is {target_state.upper()} after {max_retries} attempts. Current state: {current_state_value}")

    # Handle notification and background retry logic
    if _service_config[CONF_ENABLE_NOTIFICATIONS]:
        background_delay = _service_config[CONF_BACKGROUND_RETRY_DELAY]

        # If background retry is disabled (300s+), notify immediately
        if background_delay >= 300:
            _LOGGER.info(f"Background retry disabled (delay={background_delay}s), notifying immediately")
            await _create_failure_notification(hass, entity_id, target_state, max_retries, current_state_value, original_target, immediate=True)
        else:
            # Schedule background retry - notification only happens if that fails too
            _LOGGER.info(f"Scheduling background retry for {entity_id} in {background_delay} seconds (no immediate notification)")
            hass.async_create_task(
                _background_retry(hass, entity_id, target_state, service_data, original_target, background_delay, max_retries)
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

def _resolve_parameter_conflicts(hass: HomeAssistant, service_data: Dict[str, Any], entity_ids: List[str], state: str) -> Dict[str, Any]:
    """Resolve parameter conflicts using priority order and add smart defaults."""

    resolved_data = dict(service_data)

    # Only add defaults for 'on' operations
    if state != "on":
        return resolved_data

    # BRIGHTNESS CONFLICT RESOLUTION (first found wins)
    brightness_params = ["brightness_pct", "brightness"]
    found_brightness = None
    for param in brightness_params:
        if param in resolved_data:
            found_brightness = param
            break

    # Remove conflicting brightness parameters (keep only the first found)
    if found_brightness:
        for param in brightness_params:
            if param != found_brightness and param in resolved_data:
                _LOGGER.debug(f"Removing conflicting brightness parameter '{param}', keeping '{found_brightness}'")
                resolved_data.pop(param)

    # COLOR CONFLICT RESOLUTION (first found wins)
    color_params = ["rgb_color", "hs_color", "xy_color", "color_name"]
    found_color = None
    for param in color_params:
        if param in resolved_data:
            found_color = param
            break

    # Remove conflicting color parameters (keep only the first found)
    if found_color:
        for param in color_params:
            if param != found_color and param in resolved_data:
                _LOGGER.debug(f"Removing conflicting color parameter '{param}', keeping '{found_color}'")
                resolved_data.pop(param)

    # COLOR TEMPERATURE CONFLICT RESOLUTION
    kelvin_params = ["color_temp_kelvin", "kelvin"]
    found_kelvin = None
    for param in kelvin_params:
        if param in resolved_data:
            found_kelvin = param
            break

    # Remove conflicting kelvin parameters (keep only the first found)
    if found_kelvin:
        for param in kelvin_params:
            if param != found_kelvin and param in resolved_data:
                _LOGGER.debug(f"Removing conflicting kelvin parameter '{param}', keeping '{found_kelvin}'")
                resolved_data.pop(param)

    # FAN SPEED CONFLICT RESOLUTION
    speed_params = ["speed_pct", "speed"]
    found_speed = None
    for param in speed_params:
        if param in resolved_data:
            found_speed = param
            break

    # Remove conflicting speed parameters (keep only the first found)
    if found_speed:
        for param in speed_params:
            if param != found_speed and param in resolved_data:
                _LOGGER.debug(f"Removing conflicting fan speed parameter '{param}', keeping '{found_speed}'")
                resolved_data.pop(param)

    return resolved_data

async def _create_failure_notification(hass: HomeAssistant, entity_id: str, target_state: str, max_retries: int, current_state_value: str, original_target: str = None, immediate: bool = False) -> None:
    """Create a failure notification with appropriate message."""

    # Create more specific message if this was part of a group operation
    if original_target and original_target != entity_id and 'group' in original_target:
        message = f"Device {entity_id} (from group {original_target}) failed to ensure device is {target_state.upper()} after {max_retries} attempts. Current state: {current_state_value}"
        title = "Ensure Device Control Failed (Group Member)"
    else:
        message = f"{entity_id} failed to ensure device is {target_state.upper()} after {max_retries} attempts. Current state: {current_state_value}"
        title = "Ensure Device Control Failed"

    if not immediate:
        title += " (Background Retry Also Failed)"
        message = f"⚠️ {message}\n\nBoth immediate and background retries failed. Manual intervention may be required."

    notification_id = f"device_fail_{entity_id.replace('.', '_')}"
    await persistent_notification.async_create(
        hass,
        f"{message}\n\n**[Retry Device Now](/api/services/ensure/retry_failed_device?entity_id={entity_id}&target_state={target_state})**",
        title,
        notification_id
    )

async def _background_retry(hass: HomeAssistant, entity_id: str, target_state: str, service_data: Dict[str, Any], original_target: str, delay_seconds: int, original_max_retries: int) -> None:
    """Background retry function that waits and then retries the failed device."""

    _LOGGER.debug(f"Background retry sleeping {delay_seconds}s for {entity_id}")
    await asyncio.sleep(delay_seconds)

    # Check if device is already in correct state
    if await _is_entity_in_target_state(hass, entity_id, target_state, service_data):
        _LOGGER.info(f"Background retry: {entity_id} already in correct state, skipping retry")
        return

    _LOGGER.info(f"Background retry: Starting retry attempt for {entity_id} -> {target_state}")

    try:
        # Attempt the retry with full retry logic, but avoid infinite background retries
        await _ensure_entity_state_no_background(hass, entity_id, target_state, service_data, original_target)

        # If successful, just log it (no notification for success)
        _LOGGER.info(f"Background retry successful: {entity_id} is now {target_state.upper()}")

    except Exception as e:
        _LOGGER.error(f"Background retry failed for {entity_id}: {e}")

        # Now create the failure notification since both immediate and background failed
        current_state = hass.states.get(entity_id)
        current_state_value = current_state.state if current_state else "unknown"

        if _service_config[CONF_ENABLE_NOTIFICATIONS]:
            await _create_failure_notification(hass, entity_id, target_state, original_max_retries, current_state_value, original_target, immediate=False)

async def _ensure_entity_state_no_background(hass: HomeAssistant, entity_id: str, target_state: str, service_data: Dict[str, Any], original_target: str = None) -> None:
    """Ensure entity state with retry logic but without background retry (prevents infinite loops)."""
    global _service_config

    domain = entity_id.split(".")[0]
    retry_count = 0
    max_retries = _service_config[CONF_MAX_RETRIES]

    # Use delay parameter override if provided, otherwise use configured base timeout
    base_timeout = service_data.get("delay", _service_config[CONF_BASE_TIMEOUT])

    while retry_count < max_retries:
        # Check if entity is already in desired state
        if await _is_entity_in_target_state(hass, entity_id, target_state, service_data):
            _LOGGER.debug(f"{entity_id} reached target state on background retry attempt {retry_count + 1}")
            return

        retry_count += 1

        # Calculate timeout for this attempt
        timeout_ms = base_timeout + (retry_count * FIXED_TIMEOUT_INCREMENT)
        timeout_sec = timeout_ms / 1000

        _LOGGER.debug(f"Background retry {retry_count}/{max_retries} for {entity_id}, timeout: {timeout_sec}s")

        # Call the service
        data = {"entity_id": entity_id}
        if service_data:
            # Filter out ensure-specific parameters that shouldn't go to the device
            filtered_data = {k: v for k, v in service_data.items() if k != "delay"}
            data.update(filtered_data)

        try:
            await hass.services.async_call(
                domain,
                f"turn_{target_state}",
                data
            )
        except Exception as e:
            _LOGGER.warning(f"Background retry service call failed for {entity_id} on attempt {retry_count}: {e}")

        # Wait for state change with timeout
        try:
            await asyncio.wait_for(
                _wait_for_state_change(hass, entity_id, target_state, service_data),
                timeout=timeout_sec
            )
        except asyncio.TimeoutError:
            _LOGGER.debug(f"Background retry timeout waiting for {entity_id} state change on attempt {retry_count}")
            continue

    # If we get here, background retry failed too
    _LOGGER.error(f"Background retry failed for {entity_id} after {max_retries} attempts")
    raise Exception(f"Background retry failed after {max_retries} attempts")
