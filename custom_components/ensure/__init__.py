"""Ensure Device Control integration for Home Assistant."""
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from . import services

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Ensure Device Control integration."""
    _LOGGER.info("Setting up Ensure Device Control integration")

    # Set up services
    await services.async_setup_services(hass)

    return True
