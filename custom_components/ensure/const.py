"""Constants for the Ensure Device Control integration."""

DOMAIN = "ensure"

# Service names
SERVICE_TURN_ON = "turn_on"
SERVICE_TURN_OFF = "turn_off"

# Default retry settings
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_TIMEOUT = 1000  # milliseconds
DEFAULT_TIMEOUT_INCREMENT = 500  # milliseconds

# Tolerance settings for different attributes
BRIGHTNESS_TOLERANCE = 5  # brightness units (0-255)
BRIGHTNESS_PCT_TOLERANCE = 2  # percentage points
RGB_TOLERANCE = 10  # RGB color value tolerance
KELVIN_TOLERANCE = 20  # color temperature tolerance
HUE_TOLERANCE = 5  # hue tolerance
SATURATION_TOLERANCE = 5  # saturation tolerance

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
    "transition"
]
