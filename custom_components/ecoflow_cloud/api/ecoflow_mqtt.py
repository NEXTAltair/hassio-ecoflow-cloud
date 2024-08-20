import json
import logging
import random
import ssl
import time
from typing import Any

import paho.mqtt.client as mqtt_client

from custom_components.ecoflow_cloud.api import EcoflowMqttInfo
from custom_components.ecoflow_cloud.devices import BaseDevice

_LOGGER = logging.getLogger(__name__)


class EcoflowMQTTClient:

    def __init__(self, mqtt_info: EcoflowMqttInfo, devices: dict[str, BaseDevice]):

        from ..devices import BaseDevice
        # Status pour ne pas boucler
        self.__autorise = True
        self.__mqtt_info = mqtt_info
        self.__error_count = 0
        self.__devices: dict[str, BaseDevice] = devices
        self.__client = mqtt_client.Client(client_id=self.__mqtt_info.client_id, clean_session=True, reconnect_on_failure=True)
        self.__client.username_pw_set(self.__mqtt_info.username, self.__mqtt_info.password)
        self.__client.tls_set(certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED)
        self.__client.tls_insecure_set(False)
        self.__client.on_connect = self.on_connect
        self.__client.on_disconnect = self.on_disconnect
        self.__client.on_message = self.on_message
        self.__client.on_socket_close = self.on_socket_close

        _LOGGER.info(f"Connecting to MQTT Broker {self.__mqtt_info.url}:{self.__mqtt_info.port} with client id {self.__mqtt_info.client_id} and username {self.__mqtt_info.username}")
        self.__client.connect(self.__mqtt_info.url, self.__mqtt_info.port, 30)

    def is_connected(self):
        return self.__client.is_connected()

    def reconnect(self) -> bool:
        try:
            if self.__autorise:
                _LOGGER.info(f"Re-connecting to MQTT Broker {self.__mqtt_info.url}:{self.__mqtt_info.port}")
                self.__client.loop_stop(True)
                self.__client.reconnect()
                self.__client.loop_start()
                return True
            else:
                _LOGGER.info(f"No reconnection to MQTT Broker {self.__mqtt_info.url}:{self.__mqtt_info.port} -> Not authorised ")
                self.stop()
                if self.__error_count >= 10 :
                    self.__error_count = 0
                    self.__autorise = True
                return True

        except Exception as e:
            _LOGGER.error(e)
            return False

    def on_connect(self, client, userdata, flags, rc):
        match rc:
            case 0:
                self.__client.loop_start()
                topics = []
                for (sn, device) in self.__devices.items():
                    _LOGGER.debug(f"Add Topics for  {sn}")

                    if device.device_info.data_topic:
                        topics.append((device.device_info.data_topic, 1))
                    if device.device_info.set_topic:
                        topics.append((device.device_info.set_topic, 1))
                    if device.device_info.set_reply_topic:
                        topics.append((device.device_info.set_reply_topic, 1))
                    if device.device_info.status_topic:
                        topics.append((device.device_info.status_topic, 1))

                self.__client.subscribe(topics)
                _LOGGER.info(f"Subscribed to MQTT topics {topics}")
            case -1:
                _LOGGER.error(f"Failed to connect to MQTT: connection timed out ({self.__mqtt_info.client_id})")
            case 1:
                _LOGGER.error(f"Failed to connect to MQTT: incorrect protocol version ({self.__mqtt_info.client_id})")
                self.__autorise = False
            case 2:
                _LOGGER.error(f"Failed to connect to MQTT: invalid client identifier ({self.__mqtt_info.client_id})")
                self.__autorise = False
            case 3:
                _LOGGER.error(f"Failed to connect to MQTT: server unavailable ({self.__mqtt_info.client_id})")
            case 4:
                _LOGGER.error(f"Failed to connect to MQTT: bad username or password ({self.__mqtt_info.client_id})")
                self.__autorise = False
            case 5:
                _LOGGER.error(f"Failed to connect to MQTT: not authorised ({self.__mqtt_info.client_id}) - {userdata}")
                self.__autorise = False
            case _:
                _LOGGER.error(f"Failed to connect to MQTT: another error occured: {rc} ({self.__mqtt_info.client_id})")

        if not self.__autorise:
            _LOGGER.error(f"Authorisation:False / rc: {rc} ({self.__mqtt_info.client_id})")
            self.stop()

        return client

    def on_socket_close(self, client, userdata, socket):
        _LOGGER.error(f"Unexpected MQTT Socket disconnection : {str(socket)}")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self.__error_count = self.__error_count+1
            _LOGGER.error(f"Unexpected MQTT disconnection: {rc} (Error count {self.__error_count}). Will auto-reconnect")
            time.sleep(15)
            if self.__error_count % 1000 :
                self.__error_count = 0 # reinit de temps en temps

    def on_message(self, client, userdata, message):
        try:
            message_sn = None
            for (sn, device) in self.__devices.items():
                TOPICS = [device.device_info.data_topic, device.device_info.set_topic, device.device_info.set_reply_topic, 
                          device.device_info.get_topic, device.device_info.get_reply_topic,  device.device_info.status_topic]
                match message.topic:
                    case item if item in TOPICS:
                        message_sn=sn
                        break
                    case _:
                        pass
            if message_sn:
                _LOGGER.debug(f"Message for {message_sn} and Topic {message.payload}")
                self.__devices[message_sn].update_data(message.payload, message.topic)
            else:
                _LOGGER.warn(f"No device for Topic {message.topic}")
        except UnicodeDecodeError as error:
            _LOGGER.error(f"UnicodeDecodeError: {error}. Ignoring message and waiting for the next one.")

    message_id = 999900000 + random.randint(10000, 99999)

    def __prepare_payload(self, command: dict):
        self.message_id += 1
        payload = {"from": "HomeAssistant",
                   "id": f"{self.message_id}",
                   "version": "1.0"}
        payload.update(command)
        return payload

    def __send(self, topic: str, message: str):
        try:
            info = self.__client.publish(topic, message, 1)
            _LOGGER.debug("Sending " + message + " :" + str(info) + "(" + str(info.is_published()) + ")")
        except RuntimeError as error:
            _LOGGER.error(error, "Error on topic " + topic + " and message " + message)
        except Exception as error:
            _LOGGER.debug(error, "Error on topic " + topic + " and message " + message)

    def send_get_message(self, device_sn: str, command: dict):
        payload = self.__prepare_payload(command)
        self.__send(self.__devices[device_sn].device_info.get_topic, json.dumps(payload))

    def send_set_message(self, device_sn: str, mqtt_state: dict[str, Any], command: dict):
        self.__devices[device_sn].data.update_to_target_state(mqtt_state)
        payload = self.__prepare_payload(command)
        self.__send(self.__devices[device_sn].device_info.set_topic, json.dumps(payload))

    def stop(self):
        self.__client.loop_stop()
        self.__client.disconnect()
