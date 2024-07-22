from __future__ import annotations

import inspect
from typing import Any, Callable, OrderedDict, Mapping

import jsonpath_ng.ext as jp
from homeassistant.components.button import ButtonEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import DOMAIN
from homeassistant.helpers.entity import Entity, EntityCategory, DeviceInfo

from custom_components.ecoflow_cloud.api import EcoflowApiClient


class EcoFlowAbstractEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, client: EcoflowApiClient, title: str, key: str):
        from custom_components.ecoflow_cloud.devices import BaseDevice
        self._client: EcoflowApiClient = client
        self._device: BaseDevice = client.device
        self._attr_name = title

        type_prefix = "api-" if self._device.device_info.public_api else ""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{type_prefix}{self._device.device_info.sn}")},
            manufacturer="EcoFlow",
            name=self._device.device_info.name,
            model=self._device.device_info.device_type,
        )

        self._attr_unique_id = self.gen_unique_id(type_prefix, self._device.device_info.sn, key)

    @staticmethod
    def gen_unique_id(type_prefix: str, sn: str, key: str):
        return ('ecoflow-' + type_prefix + sn + '-' + key.replace('.', '-')
                .replace('_', '-')
                .replace('[', '-')
                .replace(']', '-')
                )


class EcoFlowDictEntity(EcoFlowAbstractEntity):

    def __init__(self, client: EcoflowApiClient, mqtt_key: str, title: str, enabled: bool = True,
                 auto_enable: bool = False):
        super().__init__(client, title, mqtt_key)
        self._mqtt_key = mqtt_key
        self._mqtt_key_expr = jp.parse(self.__adopted_mqtt_key(self._mqtt_key))

        self._auto_enable = auto_enable
        self._attr_entity_registry_enabled_default = enabled
        self.__attributes_mapping: dict[str, str] = {}
        self.__attrs = OrderedDict[str, Any]()

    def attr(self, mqtt_key: str, title: str, default: Any) -> EcoFlowDictEntity:
        self.__attributes_mapping[mqtt_key] = title
        self.__attrs[title] = default
        return self

    def __adopted_mqtt_key(self, key: str):
        if self._device.flat_json():
            return "'" + key + "'"
        else:
            return key

    @property
    def mqtt_key(self):
        return self._mqtt_key

    @property
    def auto_enable(self):
        return self._auto_enable

    @property
    def enabled_default(self):
        return self._attr_entity_registry_enabled_default

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        d = self._device.data.params_observable().subscribe(self._updated)
        self.async_on_remove(d.dispose)

    def _updated(self, data: dict[str, Any]):
        # update attributes
        for key, title in self.__attributes_mapping.items():
            key_expr = jp.parse(self.__adopted_mqtt_key(key))
            attr_values = key_expr.find(data)
            if len(attr_values) == 1:
                self.__attrs[title] = attr_values[0].value

        # update value
        values = self._mqtt_key_expr.find(data)
        if len(values) == 1:
            self._attr_available = True
            if self._auto_enable:
                self._attr_entity_registry_enabled_default = True

            if self._update_value(values[0].value):
                self.schedule_update_ha_state()

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        return self.__attrs

    def _update_value(self, val: Any) -> bool:
        return False


class EcoFlowBaseCommandEntity(EcoFlowDictEntity):
    def __init__(self, client: EcoflowApiClient, mqtt_key: str, title: str,
                 command: Callable[[Any], dict[str, Any]] | Callable[[Any, dict[str, Any]], dict[str, Any]] | None,
                 enabled: bool = True, auto_enable: bool = False):
        super().__init__(client, mqtt_key, title, enabled, auto_enable)
        self._command = command

    def command_dict(self, value: Any) -> dict[str, Any] | None:
        if self._command:
            p_count = len(inspect.signature(self._command).parameters)
            if p_count == 1:
                return self._command(value)
            elif p_count == 2:
                return self._command(value, self._device.data.params)
        else:
            return None

    def send_set_message(self, target_value: Any, command: dict):
        self._client.mqtt_client.send_set_message({self._mqtt_key: target_value}, command)


class BaseNumberEntity(NumberEntity, EcoFlowBaseCommandEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, client: EcoflowApiClient, mqtt_key: str, title: str, min_value: int, max_value: int,
                 command: Callable[[int], dict[str, Any]] | Callable[[int, dict[str, Any]], dict[str, Any]] | None,
                 enabled: bool = True,
                 auto_enable: bool = False):
        super().__init__(client, mqtt_key, title, command, enabled, auto_enable)
        self._attr_native_max_value = max_value
        self._attr_native_min_value = min_value

    def _update_value(self, val: Any) -> bool:
        if self._attr_native_value != val:
            self._attr_native_value = val
            return True
        else:
            return False


class BaseSensorEntity(SensorEntity, EcoFlowDictEntity):

    def _update_value(self, val: Any) -> bool:
        if self._attr_native_value != val:
            self._attr_native_value = val
            return True
        else:
            return False


class BaseSwitchEntity(SwitchEntity, EcoFlowBaseCommandEntity):
    pass


class BaseSelectEntity(SelectEntity, EcoFlowBaseCommandEntity):
    pass


class BaseButtonEntity(ButtonEntity, EcoFlowBaseCommandEntity):
    pass
