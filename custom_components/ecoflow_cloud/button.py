import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .api import EcoflowApiClient
from .entities import BaseButtonEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    client: EcoflowApiClient = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(client.device.buttons(client))


class EnabledButtonEntity(BaseButtonEntity):

    def press(self, **kwargs: Any) -> None:
        if self._command:
            self.send_set_message(0, self.command_dict(0))


class DisabledButtonEntity(BaseButtonEntity):

    async def async_press(self, **kwargs: Any) -> None:
        if self._command:
            self.send_set_message(0, self.command_dict(0))
