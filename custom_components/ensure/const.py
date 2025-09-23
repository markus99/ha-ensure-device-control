"""Constants for the Ensure Device Control integration."""

DOMAIN = "ensure"

# Service names
SERVICE_TURN_ON = "turn_on"
SERVICE_TURN_OFF = "turn_off"

# Configuration options (user configurable)
CONF_MAX_RETRIES = "max_retries"
CONF_BASE_TIMEOUT = "base_timeout"
CONF_ENABLE_NOTIFICATIONS = "enable_notifications"
CONF_BACKGROUND_RETRY_DELAY = "background_retry_delay"

# Default configuration values
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_TIMEOUT = 1000  # milliseconds
DEFAULT_ENABLE_NOTIFICATIONS = True
DEFAULT_BACKGROUND_RETRY_DELAY = 30  # seconds

# Fixed retry settings (not configurable)
FIXED_TIMEOUT_INCREMENT = 500  # milliseconds
FIXED_INITIAL_DELAY = 1  # seconds
BACKGROUND_RETRY_DISABLE_THRESHOLD = 300  # seconds

# Technical tolerance settings (hardcoded, not user configurable)
BRIGHTNESS_TOLERANCE = 8  # brightness units (0-255) - ~3%
BRIGHTNESS_PCT_TOLERANCE = 1  # percentage points
RGB_TOLERANCE = 5  # RGB color value tolerance per channel
KELVIN_TOLERANCE = 50  # color temperature tolerance
HUE_TOLERANCE = 5  # degrees (0-360)
SATURATION_TOLERANCE = 5  # percentage points (0-100)

# Supported service parameters
SUPPORTED_FEATURES = [
    "brightness",
    "brightness_pct",
    "rgb_color",
    "color_name",
    "color_temp_kelvin",
    "kelvin",
    "hue",
    "saturation",
    "xy_color",
    "hs_color",
    "white",
    "color_temp",
    "effect",
    "flash",
    "speed",        # Fan speed (low, medium, high)
    "speed_pct",    # Fan speed percentage (0-100)
    "delay",        # Custom delay override (ensure-specific)
    "transition"    # Light transition timing (seconds for smooth fade)
]
