"""Constants for the Ensure Device Control integration."""

DOMAIN = "ensure"

# Service names
SERVICE_TURN_ON = "turn_on"
SERVICE_TURN_OFF = "turn_off"
SERVICE_TOGGLE = "toggle"
SERVICE_TOGGLE_GROUP = "toggle_group"

# Configuration options (user configurable)
CONF_MAX_RETRIES = "max_retries"
CONF_BASE_TIMEOUT = "base_timeout"
CONF_ENABLE_NOTIFICATIONS = "enable_notifications"
CONF_BACKGROUND_RETRY_DELAY = "background_retry_delay"
CONF_LOGGING_LEVEL = "logging_level"

# Default configuration values
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_TIMEOUT = 1000  # milliseconds
DEFAULT_ENABLE_NOTIFICATIONS = True
DEFAULT_BACKGROUND_RETRY_DELAY = 30  # seconds
DEFAULT_LOGGING_LEVEL = 2  # Normal logging

# Logging levels (user configurable)
LOGGING_LEVEL_MINIMAL = 1  # Minimal: Only errors and critical operations
LOGGING_LEVEL_NORMAL = 2   # Normal: Standard operational logging
LOGGING_LEVEL_VERBOSE = 3  # Verbose: Full debugging information

LOGGING_LEVEL_OPTIONS = {
    LOGGING_LEVEL_MINIMAL: "Minimal (Errors Only)",
    LOGGING_LEVEL_NORMAL: "Normal (Standard)",
    LOGGING_LEVEL_VERBOSE: "Verbose (Full Debug)",
}

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

# Color name to RGB mapping (from Home Assistant standard colors)
COLOR_NAME_TO_RGB = {
    "homeassistant": [3, 169, 244],
    "aliceblue": [240, 248, 255],
    "antiquewhite": [250, 235, 215],
    "aqua": [0, 255, 255],
    "aquamarine": [127, 255, 212],
    "azure": [240, 255, 255],
    "beige": [245, 245, 220],
    "bisque": [255, 228, 196],
    "blue": [0, 0, 255],
    "brown": [165, 42, 42],
    "coral": [255, 127, 80],
    "cyan": [0, 255, 255],
    "gold": [255, 215, 0],
    "gray": [128, 128, 128],
    "grey": [128, 128, 128],
    "green": [0, 128, 0],
    "lime": [0, 255, 0],
    "magenta": [255, 0, 255],
    "navy": [0, 0, 128],
    "orange": [255, 165, 0],
    "pink": [255, 192, 203],
    "purple": [128, 0, 128],
    "red": [255, 0, 0],
    "silver": [192, 192, 192],
    "white": [255, 255, 255],
    "yellow": [255, 255, 0],
}

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
