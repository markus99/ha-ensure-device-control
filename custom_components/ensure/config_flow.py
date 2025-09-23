"""Config flow for Ensure Device Control integration."""
from __future__ import annotations

import voluptuous as vol
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_MAX_RETRIES,
    CONF_BASE_TIMEOUT,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_BACKGROUND_RETRY_DELAY,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BASE_TIMEOUT,
    DEFAULT_ENABLE_NOTIFICATIONS,
    DEFAULT_BACKGROUND_RETRY_DELAY,
)


class EnsureConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ensure Device Control."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate input
            max_retries = user_input.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES)
            base_timeout = user_input.get(CONF_BASE_TIMEOUT, DEFAULT_BASE_TIMEOUT)

            if max_retries < 1 or max_retries > 10:
                errors[CONF_MAX_RETRIES] = "invalid_retries"
            elif base_timeout < 500 or base_timeout > 5000:
                errors[CONF_BASE_TIMEOUT] = "invalid_timeout"
            else:
                # Create the entry
                return self.async_create_entry(
                    title="Ensure Device Control",
                    data={},
                    options=user_input,
                )

        # Show form
        data_schema = vol.Schema({
            vol.Optional(CONF_MAX_RETRIES, default=DEFAULT_MAX_RETRIES): vol.All(
                int, vol.Range(min=1, max=10)
            ),
            vol.Optional(CONF_BASE_TIMEOUT, default=DEFAULT_BASE_TIMEOUT): vol.All(
                int, vol.Range(min=500, max=5000)
            ),
            vol.Optional(CONF_ENABLE_NOTIFICATIONS, default=DEFAULT_ENABLE_NOTIFICATIONS): bool,
            vol.Optional(CONF_BACKGROUND_RETRY_DELAY, default=DEFAULT_BACKGROUND_RETRY_DELAY): vol.All(
                int, vol.Range(min=10, max=300)
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EnsureOptionsFlowHandler:
        """Create the options flow."""
        return EnsureOptionsFlowHandler(config_entry)


class EnsureOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Ensure Device Control."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate input
            max_retries = user_input.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES)
            base_timeout = user_input.get(CONF_BASE_TIMEOUT, DEFAULT_BASE_TIMEOUT)
            background_retry_delay = user_input.get(CONF_BACKGROUND_RETRY_DELAY, DEFAULT_BACKGROUND_RETRY_DELAY)

            if max_retries < 1 or max_retries > 10:
                errors[CONF_MAX_RETRIES] = "invalid_retries"
            elif base_timeout < 500 or base_timeout > 5000:
                errors[CONF_BASE_TIMEOUT] = "invalid_timeout"
            elif background_retry_delay < 10 or background_retry_delay > 300:
                errors[CONF_BACKGROUND_RETRY_DELAY] = "invalid_background_delay"
            else:
                # Update options
                return self.async_create_entry(title="", data=user_input)

        # Get current options or defaults
        current_options = self.config_entry.options

        data_schema = vol.Schema({
            vol.Optional(
                CONF_MAX_RETRIES,
                default=current_options.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES)
            ): vol.All(int, vol.Range(min=1, max=10)),
            vol.Optional(
                CONF_BASE_TIMEOUT,
                default=current_options.get(CONF_BASE_TIMEOUT, DEFAULT_BASE_TIMEOUT)
            ): vol.All(int, vol.Range(min=500, max=5000)),
            vol.Optional(
                CONF_ENABLE_NOTIFICATIONS,
                default=current_options.get(CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS)
            ): bool,
            vol.Optional(
                CONF_BACKGROUND_RETRY_DELAY,
                default=current_options.get(CONF_BACKGROUND_RETRY_DELAY, DEFAULT_BACKGROUND_RETRY_DELAY)
            ): vol.All(int, vol.Range(min=10, max=300)),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )