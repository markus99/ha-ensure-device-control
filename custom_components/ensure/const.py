"""Constants for the Ensure Device Control integration."""

DOMAIN = "ensure"

# Service names
SERVICE_TURN_ON = "turn_on"
SERVICE_TURN_OFF = "turn_off"

# Configuration options (user configurable)
CONF_MAX_RETRIES = "max_retries"
CONF_BASE_TIMEOUT = "base_timeout"
CONF_ENABLE_NOTIFICATIONS = "enable_notifications"

# Default configuration values
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_TIMEOUT = 1000  # milliseconds
DEFAULT_ENABLE_NOTIFICATIONS = True

# Fixed retry settings (not configurable)
FIXED_TIMEOUT_INCREMENT = 500  # milliseconds
FIXED_INITIAL_DELAY = 1  # seconds

# Technical tolerance settings (hardcoded, not user configurable)
BRIGHTNESS_TOLERANCE = 8  # brightness units (0-255) - ~3%
BRIGHTNESS_PCT_TOLERANCE = 1  # percentage points
RGB_TOLERANCE = 5  # RGB color value tolerance per channel
KELVIN_TOLERANCE = 50  # color temperature tolerance

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
    "transition"  # Light transition timing (seconds for smooth fade)
]
