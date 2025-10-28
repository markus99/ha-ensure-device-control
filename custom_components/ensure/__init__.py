"""Ensure Device Control integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from . import services

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Ensure Device Control integration from YAML (legacy support)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ensure Device Control from a config entry."""
    _LOGGER.info("Setting up Ensure Device Control integration")

    # Set up services (only once)
    if not hass.services.has_service(DOMAIN, "turn_on"):
        await services.async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Ensure Device Control integration")

    # Remove services
    hass.services.async_remove(DOMAIN, "turn_on")
    hass.services.async_remove(DOMAIN, "turn_off")
    hass.services.async_remove(DOMAIN, "toggle")

    return True
