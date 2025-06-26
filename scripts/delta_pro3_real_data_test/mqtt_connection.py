#!/usr/bin/env python3
"""
Delta Pro 3 実データテスト用 MQTT接続
Issue 05 Phase 2.5: ecoflow_mqtt_parserから必要機能のみを流用・簡素化

シンプルなMQTT接続・認証・メッセージ受信機能
"""

import json
import logging
import ssl
import time
from pathlib import Path
from typing import Any, Callable

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class DeltaPro3MQTTClient:
    """Delta Pro 3テスト専用の簡素化MQTTクライアント"""

    def __init__(self, config_path: str | Path | None = None):
        """
        MQTTクライアントを初期化

        Args:
            config_path: 設定ファイルのパス (Noneの場合は scripts/config.json を使用)
        """
        self.client: mqtt.Client | None = None
        self.message_callback: Callable[[mqtt.MQTTMessage], None] | None = None
        self.connected = False
        self.logger = logging.getLogger(__name__)

        self.config = self._load_config(config_path)

        # 接続対象トピック (Device Property のみに集中)
        self.target_topic = f"/app/device/property/{self.config['device_sn']}"

    def _load_config(self, config_path: str | Path | None = None) -> dict[str, Any]:
        """設定ファイルを読み込み"""
        if config_path is None:
            # scripts/config.json をデフォルトとする
            config_path = Path(__file__).parent.parent / "config.json"

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 必須設定の確認
            required_keys = [
                "mqtt_broker",
                "mqtt_port",
                "mqtt_username",
                "mqtt_password",
                "mqtt_client_id",
                "device_sn",
            ]
            missing_keys = [key for key in required_keys if key not in config]
            if missing_keys:
                raise ValueError(f"Missing required config keys: {missing_keys}")

            self.logger.info(f"Config loaded from: {config_path}")
            return config

        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            raise

    def set_message_callback(
        self, callback: Callable[[mqtt.MQTTMessage], None]
    ) -> None:
        """メッセージ受信時のコールバック関数を設定"""
        self.message_callback = callback

    def connect(self) -> bool:
        """MQTTブローカーに接続"""
        try:
            # クライアントIDを生成
            client_id = self._generate_client_id()
            self.logger.info(f"Connecting with client ID: {client_id}")

            # MQTTクライアントを作成
            self.client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1,  # type: ignore
                client_id=client_id,
                protocol=mqtt.MQTTv311,
                transport="tcp",
            )

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message

            # SSL/TLS設定
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.client.tls_set_context(context)

            # 認証設定
            self.client.username_pw_set(
                self.config["mqtt_username"], self.config["mqtt_password"]
            )

            # 接続実行
            self.logger.info(
                f"Connecting to {self.config['mqtt_broker']}:{self.config['mqtt_port']}"
            )
            self.client.connect(
                self.config["mqtt_broker"],
                self.config["mqtt_port"],
                keepalive=60,
            )

            self.client.loop_forever(retry_first_connection=False)

            return True

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False

    def _generate_client_id(self) -> str:
        """クライアントIDをconfigから取得"""
        return self.config["mqtt_client_id"]

    def _on_connect(
        self, client: mqtt.Client, userdata: Any, flags: dict[str, Any], rc: int
    ) -> None:
        """接続成功時のコールバック"""
        if rc == 0:
            self.connected = True
            self.logger.info("Connected to MQTT broker successfully")

            # ターゲットトピックを購読
            result, mid = client.subscribe(self.target_topic, qos=0)
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Subscribed to: {self.target_topic}")
            else:
                self.logger.error(f"Failed to subscribe: {mqtt.error_string(result)}")

        else:
            self.connected = False
            self.logger.error(
                f"Connection failed with code {rc}: {mqtt.connack_string(rc)}"
            )
            if rc == 5:
                self.logger.error("Authentication failed - check username/password")

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        """切断時のコールバック"""
        self.connected = False
        if rc == 0:
            self.logger.info("Disconnected from MQTT broker")
        else:
            self.logger.warning(f"Unexpected disconnection: {rc}")

    def _on_message(
        self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage
    ) -> None:
        """メッセージ受信時のコールバック"""
        try:
            self.logger.debug(
                f"Message received: topic={msg.topic}, length={len(msg.payload)}"
            )

            # 設定されたコールバック関数を呼び出し
            if self.message_callback:
                self.message_callback(msg)
            else:
                self.logger.warning("No message callback set")

        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)

    def start_loop(self) -> None:
        """バックグラウンドでMQTTループを開始"""
        if self.client:
            self.client.loop_start()
            self.logger.info("MQTT loop started in background")
        else:
            self.logger.error("Client not initialized")

    def stop_loop(self) -> None:
        """MQTTループを停止"""
        if self.client:
            self.client.loop_stop()
            self.logger.info("MQTT loop stopped")

    def disconnect(self) -> None:
        """MQTTブローカーから切断"""
        if self.client:
            self.client.disconnect()
            self.connected = False
            self.logger.info("Disconnected from MQTT broker")

    def is_connected(self) -> bool:
        """接続状態を確認"""
        return self.connected

    def wait_for_connection(self, timeout: float = 10.0) -> bool:
        """接続完了まで待機"""
        start_time = time.time()
        while not self.connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)

        if self.connected:
            self.logger.info("Connection established")
            return True
        else:
            self.logger.error(f"Connection timeout after {timeout} seconds")
            return False

    def publish_get_data_request(self) -> bool:
        """データ取得要求を送信 (オプション機能)"""
        if not self.client or not self.connected:
            self.logger.error("Not connected to MQTT broker")
            return False

        try:
            # 簡単なpingメッセージを送信して通信を促進
            # (実際のデータ取得要求の実装は必要に応じて追加)
            publish_topic = f"/app/{self.config.get('user_id', '')}/{self.config['device_sn']}/thing/property/set"

            # 空のヘッダーメッセージ (最小限のping)
            from custom_components.ecoflow_cloud.devices.internal.proto import (
                ef_dp3_iobroker_pb2 as pb2,
            )

            header_msg = pb2.HeaderMessage()
            header = header_msg.header.add()
            header.dest = 32
            header.cmd_func = 20
            header.cmd_id = 1
            header.pdata = b""

            message_bytes = header_msg.SerializeToString()

            result = self.client.publish(publish_topic, message_bytes, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info("Data request sent")
                return True
            else:
                self.logger.error(
                    f"Failed to send request: {mqtt.error_string(result.rc)}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error sending data request: {e}")
            return False


def create_mqtt_client(config_path: str | Path | None = None) -> DeltaPro3MQTTClient:
    """MQTTクライアントインスタンスを作成"""
    return DeltaPro3MQTTClient(config_path)
