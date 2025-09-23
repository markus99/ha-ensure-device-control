"""Ensure Device Control integration for Home Assistant."""
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Ensure Device Control integration."""
    _LOGGER.info("Setting up Ensure Device Control integration")

    # Set up services
    await async_setup_services(hass)

    _LOGGER.info("Ensure Device Control integration setup complete")
    return True

async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    """Unload the integration."""
    return True
