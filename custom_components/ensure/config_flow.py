"""Config flow for Ensure Device Control integration."""
from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class EnsureConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ensure Device Control."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - no user input required."""
        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Ensure Device Control", data={})

        # Show a simple form with no fields (just a confirmation)
        return self.async_show_form(step_id="user")
