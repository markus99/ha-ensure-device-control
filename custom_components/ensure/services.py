"""Service implementations for Ensure Device Control."""
import asyncio
import logging
from typing import Any, Dict, List

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.template import expand
from homeassistant.exceptions import ServiceValidationError
from homeassistant.components import persistent_notification

from .const import (
    DOMAIN,
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
    SERVICE_TOGGLE,
    SERVICE_TOGGLE_GROUP,
    CONF_MAX_RETRIES,
    CONF_BASE_TIMEOUT,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_BACKGROUND_RETRY_DELAY,
    CONF_LOGGING_LEVEL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BASE_TIMEOUT,
    DEFAULT_ENABLE_NOTIFICATIONS,
    DEFAULT_BACKGROUND_RETRY_DELAY,
    DEFAULT_LOGGING_LEVEL,
    LOGGING_LEVEL_MINIMAL,
    LOGGING_LEVEL_NORMAL,
    LOGGING_LEVEL_VERBOSE,
    FIXED_TIMEOUT_INCREMENT,
    FIXED_INITIAL_DELAY,
    BACKGROUND_RETRY_DISABLE_THRESHOLD,
    BRIGHTNESS_TOLERANCE,
    BRIGHTNESS_PCT_TOLERANCE,
    RGB_TOLERANCE,
    KELVIN_TOLERANCE,
    HUE_TOLERANCE,
    SATURATION_TOLERANCE,
    SUPPORTED_FEATURES,
    COLOR_NAME_TO_RGB,
)

_LOGGER = logging.getLogger(__name__)

# Global config storage for services
_service_config = {
    CONF_MAX_RETRIES: DEFAULT_MAX_RETRIES,
    CONF_BASE_TIMEOUT: DEFAULT_BASE_TIMEOUT,
    CONF_ENABLE_NOTIFICATIONS: DEFAULT_ENABLE_NOTIFICATIONS,
    CONF_BACKGROUND_RETRY_DELAY: DEFAULT_BACKGROUND_RETRY_DELAY,
    CONF_LOGGING_LEVEL: DEFAULT_LOGGING_LEVEL,
}

def _log(level: int, message: str, *args) -> None:
    """Log message based on configured logging level."""
    try:
        # Safely get logging level with fallback
        current_level = _service_config.get(CONF_LOGGING_LEVEL, DEFAULT_LOGGING_LEVEL)

        if level == LOGGING_LEVEL_MINIMAL:
            # Always log errors and critical operations
            _LOGGER.error(message, *args)
        elif level == LOGGING_LEVEL_NORMAL and current_level >= LOGGING_LEVEL_NORMAL:
            # Log standard operations
            _LOGGER.info(message, *args)
        elif level == LOGGING_LEVEL_VERBOSE and current_level >= LOGGING_LEVEL_VERBOSE:
            # Log detailed debug information
            _LOGGER.debug(message, *args)
    except Exception as e:
        # Fallback to standard logging if our custom logging fails
        _LOGGER.warning(f"Logging function error: {e} - Original message: {message}")

async def async_setup_services(hass: HomeAssistant, config: Dict[str, Any] = None) -> None:
    """Set up the ensure services."""
    global _service_config

    # Update global config if provided
    if config:
        _service_config.update(config)
        # Use standard logger during setup to avoid potential recursion issues
        _LOGGER.debug(f"Updated service config: {_service_config}")

    # Only register services once
    if not hass.services.has_service(DOMAIN, SERVICE_TURN_ON):
        async def ensure_turn_on(call: ServiceCall) -> None:
            """Handle ensure turn_on service."""
            await _handle_ensure_service(hass, call, "on")

        async def ensure_turn_off(call: ServiceCall) -> None:
            """Handle ensure turn_off service."""
            await _handle_ensure_service(hass, call, "off")

        async def ensure_toggle(call: ServiceCall) -> None:
            """Handle ensure toggle service."""
            await _handle_ensure_toggle_service(hass, call)

        async def ensure_toggle_group(call: ServiceCall) -> None:
            """Handle ensure toggle_group service."""
            await _handle_ensure_toggle_group_service(hass, call)

        async def retry_failed_device(call: ServiceCall) -> None:
            """Retry a previously failed device."""
            entity_id = call.data.get("entity_id")
            target_state = call.data.get("target_state")

            if not entity_id or not target_state:
                _log(LOGGING_LEVEL_MINIMAL, "❌ Missing entity_id or target_state for retry")
                return

            _log(LOGGING_LEVEL_NORMAL, f"🔄 Manual retry for failed device: {entity_id} -> {target_state}")

            # Create a new service call to retry the device
            await _ensure_entity_state(hass, entity_id, target_state, {})

            # Dismiss the notification
            await persistent_notification.async_dismiss(
                hass, f"device_fail_{entity_id.replace('.', '_')}"
            )

        hass.services.async_register(DOMAIN, SERVICE_TURN_ON, ensure_turn_on)
        hass.services.async_register(DOMAIN, SERVICE_TURN_OFF, ensure_turn_off)
        hass.services.async_register(DOMAIN, SERVICE_TOGGLE, ensure_toggle)
        hass.services.async_register(DOMAIN, SERVICE_TOGGLE_GROUP, ensure_toggle_group)
        hass.services.async_register(DOMAIN, "retry_failed_device", retry_failed_device)

        # Use standard logger during setup to prevent issues
        _LOGGER.info("Ensure services registered successfully")

async def _handle_ensure_service(hass: HomeAssistant, call: ServiceCall, state: str) -> None:
    """Handle the ensure service call with retry logic."""

    # Get original input for first attempt (preserves groups)
    original_target = _get_original_target(call)
    if not original_target:
        raise ServiceValidationError("No entities specified")

    _log(LOGGING_LEVEL_NORMAL, f"🎯 Ensure {state} called for: {original_target}")
    _log(LOGGING_LEVEL_VERBOSE, f"Service call data: {call.data}")

    # Get service data
    service_data = dict(call.data)
    service_data.pop("entity_id", None)  # Remove if present

    # Expand to individual entities for conflict resolution context
    expanded_entities = _get_target_entities(hass, call)

    # Resolve parameter conflicts with priority order and add smart defaults
    _log(LOGGING_LEVEL_VERBOSE, f"🔧 Before conflict resolution: {list(service_data.keys())}")
    service_data = _resolve_parameter_conflicts(hass, service_data, expanded_entities, state)
    _log(LOGGING_LEVEL_VERBOSE, f"🔧 After conflict resolution: {list(service_data.keys())}")

    # Try original target first (preserves group operations for speed)
    await _try_original_target(hass, original_target, state, service_data)

    # Wait a moment for the command to propagate
    await asyncio.sleep(FIXED_INITIAL_DELAY)
    if not expanded_entities:
        _LOGGER.warning("No entities found after expansion")
        return

    _LOGGER.debug(f"Expanded to individual entities: {expanded_entities}")

    # Process entities concurrently with controlled rate limiting
    await _process_entities_concurrently(hass, expanded_entities, state, service_data, original_target)

async def _handle_ensure_toggle_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the ensure toggle service call with retry logic."""

    # Get original input for first attempt (preserves groups)
    original_target = _get_original_target(call)
    if not original_target:
        raise ServiceValidationError("No entities specified")

    _log(LOGGING_LEVEL_NORMAL, f"🎯 Ensure toggle called for: {original_target}")
    _log(LOGGING_LEVEL_VERBOSE, f"Service call data: {call.data}")

    # Get service data
    service_data = dict(call.data)
    service_data.pop("entity_id", None)  # Remove if present

    # Expand to individual entities to check their current states
    expanded_entities = _get_target_entities(hass, call)
    if not expanded_entities:
        _log(LOGGING_LEVEL_MINIMAL, "❌ No entities found for toggle operation")
        return

    _log(LOGGING_LEVEL_VERBOSE, f"Expanded entities for toggle: {expanded_entities}")

    # For toggle, we need to determine the target state for each entity individually
    # Check current state of each entity and create separate on/off lists
    entities_to_turn_on = []
    entities_to_turn_off = []

    for entity_id in expanded_entities:
        current_state = hass.states.get(entity_id)
        if not current_state:
            _log(LOGGING_LEVEL_VERBOSE, f"⚠️ {entity_id}: No state found, assuming off -> will turn on")
            entities_to_turn_on.append(entity_id)
        elif current_state.state in ["on", "open"]:
            _log(LOGGING_LEVEL_VERBOSE, f"🔛 {entity_id}: Currently {current_state.state} -> will turn off")
            entities_to_turn_off.append(entity_id)
        else:
            _log(LOGGING_LEVEL_VERBOSE, f"🔲 {entity_id}: Currently {current_state.state} -> will turn on")
            entities_to_turn_on.append(entity_id)

    # Process each group with their respective target states
    if entities_to_turn_on:
        _log(LOGGING_LEVEL_NORMAL, f"🔛 Toggle ON: {entities_to_turn_on}")
        await _process_entities_concurrently(hass, entities_to_turn_on, "on", service_data, original_target)

    if entities_to_turn_off:
        _log(LOGGING_LEVEL_NORMAL, f"🔲 Toggle OFF: {entities_to_turn_off}")
        await _process_entities_concurrently(hass, entities_to_turn_off, "off", service_data, original_target)

async def _handle_ensure_toggle_group_service(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the ensure toggle_group service call - mirrors HA toggle behavior with retry logic."""

    # Get original input for first attempt (preserves groups)
    original_target = _get_original_target(call)
    if not original_target:
        raise ServiceValidationError("No entities specified")

    _log(LOGGING_LEVEL_NORMAL, f"🎯 Ensure toggle_group called for: {original_target}")
    _log(LOGGING_LEVEL_VERBOSE, f"Service call data: {call.data}")

    # Get service data
    service_data = dict(call.data)
    service_data.pop("entity_id", None)  # Remove if present

    # Expand to individual entities
    expanded_entities = _get_target_entities(hass, call)
    if not expanded_entities:
        _log(LOGGING_LEVEL_MINIMAL, "❌ No entities found for toggle_group operation")
        return

    _log(LOGGING_LEVEL_VERBOSE, f"Expanded entities for toggle_group: {expanded_entities}")

    # Determine group state using Home Assistant's logic:
    # Group is "on" if ANY entity is on, "off" only if ALL entities are off
    group_is_on = False
    entity_states = []

    for entity_id in expanded_entities:
        current_state = hass.states.get(entity_id)
        if current_state and current_state.state in ["on", "open"]:
            group_is_on = True
            entity_states.append(f"{entity_id}=ON")
        else:
            entity_states.append(f"{entity_id}=OFF")

    target_state = "off" if group_is_on else "on"

    _log(LOGGING_LEVEL_NORMAL, f"📊 Group state analysis: {', '.join(entity_states)}")
    _log(LOGGING_LEVEL_NORMAL, f"🎯 Group considered {'ON' if group_is_on else 'OFF'} → All entities will turn {target_state.upper()}")

    # Apply the same action to all entities (like HA's standard toggle)
    await _process_entities_concurrently(hass, expanded_entities, target_state, service_data, original_target)

async def _process_entities_concurrently(hass: HomeAssistant, entity_ids: List[str], state: str, service_data: Dict[str, Any], original_target: str) -> None:
    """Process entities concurrently with rate limiting to avoid overwhelming the hub."""
    if not entity_ids:
        return

    # Limit concurrent operations to avoid overwhelming Hubitat/integrations
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent operations

    async def process_single_entity(entity_id: str) -> None:
        async with semaphore:
            try:
                await _ensure_entity_state(hass, entity_id, state, service_data, original_target)
            except Exception as e:
                _LOGGER.error(f"Error processing entity {entity_id}: {e}")

    # Create tasks for all entities and run them concurrently
    tasks = [process_single_entity(entity_id) for entity_id in entity_ids]
    await asyncio.gather(*tasks, return_exceptions=True)

async def _try_original_target(hass: HomeAssistant, original_target: str, state: str, service_data: Dict[str, Any]) -> None:
    """Try the original target as-is (matching original script logic)."""

    # Validate that the target entity exists
    if not hass.states.get(original_target):
        _log(LOGGING_LEVEL_VERBOSE, f"⚠️ Skipping original target {original_target} - entity not found")
        return

    # Determine service to call based on original script logic
    domain = original_target.split(".")[0]
    if domain == "group":
        service_domain = "homeassistant"
    else:
        service_domain = domain
    service_name = f"turn_{state}"

    # Prepare service data
    data = {"entity_id": original_target}
    if service_data:
        # Filter out ensure-specific parameters that shouldn't go to the device
        filtered_data = {k: v for k, v in service_data.items() if k != "delay"}
        data.update(filtered_data)
        _log(LOGGING_LEVEL_VERBOSE, f"📡 Original target service data: {filtered_data}")

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
    await _ensure_entity_state_core(hass, entity_id, target_state, service_data, original_target, allow_background_retry=True)

async def _ensure_entity_state_core(hass: HomeAssistant, entity_id: str, target_state: str, service_data: Dict[str, Any], original_target: str = None, allow_background_retry: bool = True) -> None:
    """Core retry logic with configurable background retry behavior."""
    global _service_config

    _log(LOGGING_LEVEL_VERBOSE, f"🔍 Starting core retry logic for {entity_id} -> {target_state}")

    # Validate that the entity exists before trying to control it
    if not hass.states.get(entity_id):
        _log(LOGGING_LEVEL_VERBOSE, f"⚠️ Skipping {entity_id} - entity not found in state registry")
        return

    domain = entity_id.split(".")[0]

    # In retry loop, we're dealing with individual entities, so always use their actual domain
    # (This matches original script where the retry loop uses device_1.split('.')[0].turn_state)
    service_domain = domain

    retry_count = 0
    max_retries = _service_config[CONF_MAX_RETRIES]

    _log(LOGGING_LEVEL_VERBOSE, f"🎯 {entity_id}: max_retries={max_retries}, domain={domain}")

    # Use delay parameter override if provided, otherwise use configured base timeout
    base_timeout = service_data.get("delay", _service_config[CONF_BASE_TIMEOUT])
    if "delay" in service_data:
        _log(LOGGING_LEVEL_VERBOSE, f"⏱️ Using custom delay override: {base_timeout}ms for {entity_id}")

    while retry_count < max_retries:
        # Check if entity is already in desired state
        if await _is_entity_in_target_state(hass, entity_id, target_state, service_data):
            _log(LOGGING_LEVEL_NORMAL, f"✅ SUCCESS: {entity_id} reached {target_state} on attempt {retry_count + 1}")
            return

        retry_count += 1

        _log(LOGGING_LEVEL_VERBOSE, f"🔄 {entity_id}: Starting attempt {retry_count}/{max_retries}")

        # Calculate timeout for this attempt
        timeout_ms = base_timeout + (retry_count * FIXED_TIMEOUT_INCREMENT)
        timeout_sec = timeout_ms / 1000

        _log(LOGGING_LEVEL_VERBOSE, f"⏱️ {entity_id}: timeout={timeout_ms}ms for attempt {retry_count}")

        # Remove duplicate debug log (already logged above)

        # Call the service
        data = {"entity_id": entity_id}
        if service_data:
            # Filter out ensure-specific parameters that shouldn't go to the device
            filtered_data = {k: v for k, v in service_data.items() if k != "delay"}
            data.update(filtered_data)

        try:
            service_name = f"turn_{target_state}"
            _log(LOGGING_LEVEL_VERBOSE, f"📡 Calling {service_domain}.{service_name} for {entity_id} with: {data}")
            await hass.services.async_call(service_domain, service_name, data)
            _log(LOGGING_LEVEL_VERBOSE, f"✅ Service call completed for {entity_id}")
        except Exception as e:
            _log(LOGGING_LEVEL_MINIMAL, f"❌ Service call failed for {entity_id} on attempt {retry_count}: {e}")

        # Wait for state change with timeout
        try:
            await asyncio.wait_for(
                _wait_for_state_change(hass, entity_id, target_state, service_data),
                timeout=timeout_sec
            )
        except asyncio.TimeoutError:
            _log(LOGGING_LEVEL_VERBOSE, f"⏰ Timeout waiting for {entity_id} state change on attempt {retry_count}")
            continue

    # If we get here, all retries failed
    current_state = hass.states.get(entity_id)
    current_state_value = current_state.state if current_state else "unknown"

    _log(LOGGING_LEVEL_MINIMAL, f"⚠️ FINAL FAILURE: {entity_id} -> {target_state.upper()} after {max_retries} attempts. Current: {current_state_value}")

    # Handle notification and background retry logic (only if allowed)
    if allow_background_retry and _service_config[CONF_ENABLE_NOTIFICATIONS]:
        background_delay = _service_config[CONF_BACKGROUND_RETRY_DELAY]

        # If background retry is disabled (threshold+), notify immediately
        if background_delay >= BACKGROUND_RETRY_DISABLE_THRESHOLD:
            _log(LOGGING_LEVEL_NORMAL, f"❌ Background retry disabled (delay={background_delay}s), notifying immediately")
            await _create_failure_notification(hass, entity_id, target_state, max_retries, current_state_value, original_target, immediate=True)
        else:
            # Schedule background retry - notification only happens if that fails too
            _log(LOGGING_LEVEL_NORMAL, f"🔄 Scheduling background retry for {entity_id} in {background_delay}s (silent)")
            hass.async_create_task(
                _background_retry(hass, entity_id, target_state, service_data, original_target, background_delay, max_retries)
            )
    elif not allow_background_retry:
        # This is a background retry that failed - raise exception for caller to handle
        raise Exception(f"Retry failed after {max_retries} attempts")

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
        _log(LOGGING_LEVEL_VERBOSE, f"❌ {entity_id}: No state object found")
        return False

    # Check basic on/off state
    if state.state != target_state:
        _log(LOGGING_LEVEL_VERBOSE, f"❌ {entity_id}: State mismatch - current: {state.state}, target: {target_state}")
        return False

    # For "off" state, basic state check is sufficient
    if target_state == "off":
        _log(LOGGING_LEVEL_VERBOSE, f"✅ {entity_id}: OFF state confirmed")
        return True

    # For "on" state, check additional attributes if specified
    if target_state == "on" and service_data:
        result = _check_attribute_tolerances(entity_id, state, service_data)
        _log(LOGGING_LEVEL_VERBOSE, f"✅ {entity_id}: ON state + attributes check = {result}")
        return result

    return True

def _check_attribute_tolerances(entity_id: str, state, service_data: Dict[str, Any]) -> bool:
    """Check if entity attributes match target values within tolerance."""

    attributes = state.attributes
    _log(LOGGING_LEVEL_VERBOSE, f"🔍 {entity_id}: Checking attributes for parameters: {list(service_data.keys())}")

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
        _log(LOGGING_LEVEL_VERBOSE, f"🎨 {entity_id}: RGB check - target: {target_rgb}, actual: {actual_rgb}")
        if actual_rgb and len(target_rgb) == 3 and len(actual_rgb) == 3:
            for i in range(3):
                if abs(actual_rgb[i] - target_rgb[i]) > RGB_TOLERANCE:
                    _log(LOGGING_LEVEL_VERBOSE, f"❌ {entity_id}: RGB mismatch - channel {i}: target {target_rgb[i]}, actual {actual_rgb[i]}, diff {abs(actual_rgb[i] - target_rgb[i])}")
                    return False
            _log(LOGGING_LEVEL_VERBOSE, f"✅ {entity_id}: RGB values match within tolerance")
        elif not actual_rgb:
            # Many lights don't report RGB back accurately - if light is on, assume RGB worked
            _log(LOGGING_LEVEL_VERBOSE, f"⚠️ {entity_id}: RGB not reported back, assuming command succeeded")

    # Check color temperature (Kelvin)
    if "color_temp_kelvin" in service_data or "kelvin" in service_data:
        target_kelvin = service_data.get("color_temp_kelvin") or service_data.get("kelvin")
        actual_kelvin = attributes.get("color_temp_kelvin")
        if actual_kelvin and abs(actual_kelvin - target_kelvin) > KELVIN_TOLERANCE:
            return False
        elif not actual_kelvin:
            # Some lights don't report color temp back - if light is on, assume command worked
            _log(LOGGING_LEVEL_VERBOSE, f"⚠️ {entity_id}: Color temperature not reported back, assuming command succeeded")

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
            # Some lights don't report HS color back - if light is on, assume command worked
            _log(LOGGING_LEVEL_VERBOSE, f"⚠️ {entity_id}: HS color not reported back, assuming command succeeded")

    # Check color name
    if "color_name" in service_data:
        target_color_name = service_data["color_name"]
        if target_color_name in COLOR_NAME_TO_RGB:
            target_rgb = COLOR_NAME_TO_RGB[target_color_name]
            actual_rgb = attributes.get("rgb_color")
            _log(LOGGING_LEVEL_VERBOSE, f"🎨 {entity_id}: Color name '{target_color_name}' -> RGB {target_rgb}, actual: {actual_rgb}")
            if actual_rgb and len(actual_rgb) == 3:
                for i in range(3):
                    if abs(actual_rgb[i] - target_rgb[i]) > RGB_TOLERANCE:
                        _log(LOGGING_LEVEL_VERBOSE, f"❌ {entity_id}: Color name RGB mismatch - channel {i}: target {target_rgb[i]}, actual {actual_rgb[i]}, diff {abs(actual_rgb[i] - target_rgb[i])}")
                        return False
                _log(LOGGING_LEVEL_VERBOSE, f"✅ {entity_id}: Color name RGB values match within tolerance")
            elif not actual_rgb:
                _log(LOGGING_LEVEL_VERBOSE, f"⚠️ {entity_id}: Color name '{target_color_name}' set but RGB not reported back, assuming command succeeded")
        else:
            _log(LOGGING_LEVEL_VERBOSE, f"⚠️ {entity_id}: Unknown color name '{target_color_name}', assuming command succeeded")

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

    # Expand groups to individual entities to prevent group.turn_on calls in retry loop
    expanded_entities = []
    for entity_id in unique_entity_ids:
        if entity_id.startswith("group."):
            # Use Home Assistant's expand function to get individual entities
            group_state = hass.states.get(entity_id)
            if group_state:
                expanded = expand(hass, [group_state])
                expanded_entities.extend([entity.entity_id for entity in expanded])
            else:
                # If group doesn't exist, still include it (will fail gracefully later)
                expanded_entities.append(entity_id)
        else:
            expanded_entities.append(entity_id)

    # Remove duplicates again after expansion
    seen = set()
    final_entity_ids = []
    for entity_id in expanded_entities:
        if entity_id not in seen:
            seen.add(entity_id)
            final_entity_ids.append(entity_id)

    return final_entity_ids

def _resolve_parameter_conflicts(hass: HomeAssistant, service_data: Dict[str, Any], entity_ids: List[str], state: str) -> Dict[str, Any]:
    """Resolve parameter conflicts using priority order."""
    resolved_data = dict(service_data)

    # Only resolve conflicts for 'on' operations
    if state != "on":
        return resolved_data

    # Define conflict groups with priority order (first has highest priority)
    conflict_groups = {
        'brightness': ["brightness_pct", "brightness"],
        'color': ["rgb_color", "hs_color", "xy_color", "color_name"],
        'temperature': ["color_temp_kelvin", "kelvin"],
        'speed': ["speed_pct", "speed"]
    }

    # Resolve each conflict group
    for group_name, params in conflict_groups.items():
        resolved_data = _resolve_conflict_group(resolved_data, params, group_name)

    return resolved_data

def _resolve_conflict_group(data: Dict[str, Any], params: List[str], group_name: str) -> Dict[str, Any]:
    """Resolve conflicts within a parameter group using priority order."""
    # Find the first parameter present (highest priority)
    found_param = None
    for param in params:
        if param in data:
            found_param = param
            break

    # Remove all other conflicting parameters
    if found_param:
        for param in params:
            if param != found_param and param in data:
                _LOGGER.debug(f"Removing conflicting {group_name} parameter '{param}', keeping '{found_param}'")
                data.pop(param)

    return data

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
    persistent_notification.async_create(
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
        _log(LOGGING_LEVEL_NORMAL, f"✅ Background retry: {entity_id} already in correct state, skipping")
        return

    _log(LOGGING_LEVEL_NORMAL, f"🔄 Background retry: Starting for {entity_id} -> {target_state}")

    try:
        # Attempt the retry with full retry logic, but avoid infinite background retries
        await _ensure_entity_state_core(hass, entity_id, target_state, service_data, original_target, allow_background_retry=False)

        # If successful, just log it (no notification for success)
        _log(LOGGING_LEVEL_NORMAL, f"✨ Background retry SUCCESS: {entity_id} -> {target_state.upper()}")

    except Exception as e:
        _log(LOGGING_LEVEL_MINIMAL, f"❌ Background retry FAILED for {entity_id}: {e}")

        # Now create the failure notification since both immediate and background failed
        current_state = hass.states.get(entity_id)
        current_state_value = current_state.state if current_state else "unknown"

        if _service_config[CONF_ENABLE_NOTIFICATIONS]:
            await _create_failure_notification(hass, entity_id, target_state, original_max_retries, current_state_value, original_target, immediate=False)

