"""Ensure Device Control integration for Home Assistant."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
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
)
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Ensure Device Control integration (YAML config - deprecated)."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ensure Device Control from a config entry."""
    _LOGGER.info("Setting up Ensure Device Control integration")

    # Get configuration options
    options = entry.options
    config_data = {
        CONF_MAX_RETRIES: options.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES),
        CONF_BASE_TIMEOUT: options.get(CONF_BASE_TIMEOUT, DEFAULT_BASE_TIMEOUT),
        CONF_ENABLE_NOTIFICATIONS: options.get(CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS),
        CONF_BACKGROUND_RETRY_DELAY: options.get(CONF_BACKGROUND_RETRY_DELAY, DEFAULT_BACKGROUND_RETRY_DELAY),
        CONF_LOGGING_LEVEL: options.get(CONF_LOGGING_LEVEL, DEFAULT_LOGGING_LEVEL),
    }

    # Store config in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = config_data

    # Set up services with configuration
    await async_setup_services(hass, config_data)

    # Set up options update listener
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.info("Ensure Device Control integration setup complete")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Remove services when last entry is unloaded
    if len(hass.data[DOMAIN]) == 1:
        hass.services.async_remove(DOMAIN, "turn_on")
        hass.services.async_remove(DOMAIN, "turn_off")
        hass.services.async_remove(DOMAIN, "toggle")
        hass.services.async_remove(DOMAIN, "retry_failed_device")

    # Remove config data
    hass.data[DOMAIN].pop(entry.entry_id)

    return True

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
