import logging
import ssl
import time
import uuid
import ctypes
from typing import Any, Callable

import paho.mqtt.client as mqtt

# from . import protobuf_mapping as pm # 同じディレクトリ内のモジュールをインポート
# from . import common # 同じディレクトリ内の common をインポート
# 相対インポートが linter でエラーになる場合、main_parser.py で sys.path を調整することを想定
import protobuf_mapping as pm
import common

logger = logging.getLogger(__name__)


class MQTTClient:
    def __init__(
        self,
        config: dict[str, Any],
        on_message_callback: Callable[[mqtt.MQTTMessage], None],
    ):
        self.config = common.resolve_topic_placeholders(
            config.copy()
        )  # 設定を解決・保持
        self.client: mqtt.Client | None = None
        self.on_message_callback = on_message_callback
        self.shutdown_event = False  # 簡単なシャットダウンフラグ
        self._validate_config()

    def _validate_config(self) -> None:
        """必要な設定キーが存在するか検証"""
        required_for_connect = [
            "mqtt_broker",
            "mqtt_port",
            "mqtt_username",
            "mqtt_password",
            "subscribe_topics",
            "publish_topic",
        ]
        missing = [
            k
            for k in required_for_connect
            if k not in self.config or self.config[k] is None
        ]
        if missing:
            msg = f"MQTTClientの初期化に必要な設定が不足しています: {missing}"
            logger.error(msg)
            raise ValueError(msg)

        if not isinstance(self.config["subscribe_topics"], list):
            msg = "subscribe_topicsはリストである必要があります。"
            logger.error(msg)
            raise TypeError(msg)

    def _get_client_id(self) -> str:
        client_id_type = self.config.get("client_id_type", "ANDROID")

        # config.json に "mqtt_client_id" が直接指定されていればそれを最優先で使用
        if "mqtt_client_id" in self.config and self.config["mqtt_client_id"]:
            logger.info(
                f"config.json から直接 mqtt_client_id を使用します: {self.config['mqtt_client_id']}"
            )
            return str(self.config["mqtt_client_id"])

        # app_user_id を取得。分割前の挙動に合わせて、空ならデフォルト値 "unknown_user" を使う
        app_user_id_for_client = self.config.get(
            "app_user_id"
        )  # common.pyで空文字列がデフォルトの場合あり
        if not app_user_id_for_client:  # 空文字列やNoneの場合
            app_user_id_for_client = "unknown_user"  # 分割前のデフォルトに合わせる
            logger.debug(
                f"'app_user_id' が空または未設定のため、クライアントIDサフィックスにデフォルト値 '{app_user_id_for_client}' を使用します。"
            )

        user_id_suffix = f"_{app_user_id_for_client}"

        if client_id_type == "ANDROID":
            return f"ANDROID_{str(uuid.uuid4())}{user_id_suffix}"
        elif client_id_type == "WEB":
            return f"WEB_{str(uuid.uuid4())}{user_id_suffix}"
        elif client_id_type == "IOS":
            return f"IOS_{str(uuid.uuid4())}{user_id_suffix}"

        # GENERATED_STATIC やその他のカスタム client_id のケースも考慮。
        # 分割前のコードには GENERATED_STATIC があったので、同様のロジックをコメントアウトで残しておく。
        # elif client_id_type == "GENERATED_STATIC":
        #     return self.config.get("static_client_id", f"DEFAULT_STATIC_{str(uuid.uuid4())}{user_id_suffix}")

        logger.warning(
            f"未知の client_id_type: {client_id_type} または 'mqtt_client_id' が未指定。デフォルト形式で生成します。"
        )
        return f"custom_client_{str(uuid.uuid4())}{user_id_suffix}"

    def _on_connect(
        self,
        mqtt_client: mqtt.Client,
        userdata: Any,
        flags: dict[str, Any],
        rc: Any,
        properties: Any = None,
    ) -> None:
        connect_rc_int: int
        connect_reason_str: str

        if isinstance(rc, int):
            connect_rc_int = rc
            connect_reason_str = mqtt.connack_string(rc)
        else:
            connect_rc_int = -1
            connect_reason_str = f"不明な接続結果タイプ: {type(rc)}"

        if connect_rc_int == 0:
            logger.info(
                f"MQTTブローカーに接続成功: {self.config['mqtt_broker']}:{self.config['mqtt_port']}"
            )
            try:
                subscribe_topics_with_qos = [
                    (topic, 0) for topic in self.config["subscribe_topics"]
                ]
                if subscribe_topics_with_qos:
                    result, mid = mqtt_client.subscribe(subscribe_topics_with_qos)
                    if result == mqtt.MQTT_ERR_SUCCESS:
                        logger.info(
                            f"以下のトピックを購読します: {subscribe_topics_with_qos}"
                        )
                    else:
                        logger.error(f"トピック購読失敗: {mqtt.error_string(result)}")
                else:
                    logger.info("購読するトピックはありません。")

                self.publish_get_all_data_request()

            except Exception as e:
                logger.error(f"on_connect内でのエラー: {e}", exc_info=True)
        else:
            error_message = (
                f"MQTTブローカー接続失敗: {connect_reason_str} (RC: {connect_rc_int})"
            )
            logger.error(error_message)
            if connect_rc_int == 5:
                logger.error("認証情報が正しくない可能性があります。")
            elif connect_rc_int == 4:
                logger.error("クライアントが認証されていません。")
            self.shutdown_event = True

    def _on_message(
        self, mqtt_client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage
    ) -> None:
        try:
            self.on_message_callback(msg)
        except Exception as e:
            logger.error(f"on_messageコールバック処理中にエラー: {e}", exc_info=True)

    def _on_disconnect(
        self,
        client_obj: mqtt.Client,
        userdata: Any,
        rc: Any = None,
        properties: Any = None,
        *args: Any,
    ) -> None:
        reason_code_int: int
        reason_string: str
        if rc is None:
            reason_code_int = 0
            reason_string = "Normal disconnection"
        elif isinstance(rc, int):
            reason_code_int = rc
            if rc == 0:
                reason_string = "Normal disconnection"
            else:
                reason_string = f"Disconnect RC: {rc}"
        else:
            reason_code_int = -1
            reason_string = f"Unknown disconnect reason type: {type(rc)}"

        logger.info(
            f"MQTTブローカーから切断されました。理由: {reason_string} (RC: {reason_code_int})"
        )
        if reason_code_int != 0 and not self.shutdown_event:
            logger.warning(
                "予期せぬ切断です。メインループで再接続が試行されるかもしれません。"
            )
        elif self.shutdown_event:
            logger.info("シャットダウン中のため、再接続は行いません。")

    def _on_log_mqtt(
        self, log_client: mqtt.Client, userdata: Any, level: int, buf: str
    ) -> None:
        mqtt_paho_logger = logging.getLogger("paho.mqtt.client")
        if level == mqtt.MQTT_LOG_INFO or level == mqtt.MQTT_LOG_NOTICE:
            mqtt_paho_logger.info(buf)
        elif level == mqtt.MQTT_LOG_WARNING:
            mqtt_paho_logger.warning(buf)
        elif level == mqtt.MQTT_LOG_ERR:
            mqtt_paho_logger.error(buf)
        elif level == mqtt.MQTT_LOG_DEBUG:
            mqtt_paho_logger.debug(buf)
        else:
            mqtt_paho_logger.debug(f"MQTT Log (Level {level}): {buf}")

    def connect(self) -> None:
        if self.client and self.client.is_connected():
            logger.info("既に接続済みです。")
            return

        client_id = self._get_client_id()
        logger.info(f"使用するクライアントID: {client_id}")

        try:
            if hasattr(mqtt, "CallbackAPIVersion"):
                self.client = mqtt.Client(
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION1,  # type: ignore
                    client_id=client_id,
                    protocol=mqtt.MQTTv311,
                    transport="tcp",
                )
            else:
                self.client = mqtt.Client(
                    client_id=client_id, protocol=mqtt.MQTTv311, transport="tcp"
                )
        except TypeError as e:
            logger.warning(
                f"Paho MQTT Client初期化中にTypeError: {e}。フォールバック試行。"
            )
            self.client = mqtt.Client(client_id=client_id)  # type: ignore

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.on_log = self._on_log_mqtt

        self.client.tls_set(
            ca_certs=None,
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_NONE,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )
        self.client.tls_insecure_set(True)
        self.client.username_pw_set(
            self.config["mqtt_username"], self.config["mqtt_password"]
        )

        try:
            logger.info(
                f"MQTTブローカー ({self.config['mqtt_broker']}:{self.config['mqtt_port']}) に接続試行中..."
            )
            self.client.connect(
                self.config["mqtt_broker"],
                self.config["mqtt_port"],
                self.config.get("mqtt_keepalive", 60),
            )
            logger.info(f"Paho client.connect() 呼び出し完了。例外なし。")
        except Exception as e:
            logger.error(f"MQTT接続中にエラー: {e}", exc_info=True)

    def publish_message(
        self, topic: str, payload: bytes | str, qos: int = 1, retain: bool = False
    ) -> bool:
        if not self.client or not self.client.is_connected():
            logger.error("MQTT未接続のためメッセージを送信できません。")
            return False
        try:
            result, mid = self.client.publish(topic, payload, qos, retain)
            if result == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"メッセージ送信成功 (トピック: {topic}, MID: {mid})")
                return True
            else:
                logger.error(
                    f"メッセージ送信失敗: {mqtt.error_string(result)} (トピック: {topic})"
                )
                return False
        except Exception as e:
            logger.error(
                f"メッセージ送信中にエラー: {e} (トピック: {topic})", exc_info=True
            )
            return False

    def publish_get_all_data_request(self) -> None:
        """全データ取得要求メッセージ (空のHeader) を送信します。"""
        if not self.config.get("publish_topic"):
            logger.warning(
                "publish_topicが設定されていないため、データ取得要求を送信できません。"
            )
            return

        header_msg = pm.Header()  # protobuf_mapping から Header を使用

        # src と from (from_field) をここで直接設定
        # これらの値はEcoFlowのプロトコルや送信元のアプリタイプに基づいて決定されるべき
        # ここでは一般的な例として設定 (ioBrokerの実装なども参考に調整可能)
        header_msg.src = 1  # 例: 送信元ID (例: クライアントアプリケーション)
        # setattr(header_msg, "from", 2)  # 例: 送信元種別 (例: Android = 2)
        # header_msg.from_ = 2 # Pythonの予約語 'from' を避けるため 'from_' を使用。Linterエラーのためコメントアウト

        # その他のパラメータは protobuf_mapping.py の定義から取得
        header_params_def = pm.get_all_header_params_for_request()  # 辞書コピーを取得

        header_msg.dest = header_params_def.get("dest", 32)  # デフォルトも考慮
        header_msg.cmd_func = header_params_def.get("cmd_func", 20)
        header_msg.cmd_id = header_params_def.get("cmd_id", 1)

        header_msg.seq = ctypes.c_int32(int(time.time() * 1000)).value

        pdata = header_params_def.get("pdata", b"")  # 通常は空のはず
        if not isinstance(pdata, bytes):
            pdata = b""  # 念のためbytes型に
        header_msg.pdata = pdata
        header_msg.data_len = len(pdata)

        serialized_message = header_msg.SerializeToString()
        logger.info(
            f"データ取得要求メッセージをトピック '{self.config['publish_topic']}' に送信します。"
        )
        logger.debug(f"送信メッセージ (protobuf): {header_msg}")
        logger.debug(
            f"送信ペイロード (bytes, {len(serialized_message)} bytes): {serialized_message.hex()}"
        )

        self.publish_message(self.config["publish_topic"], serialized_message, qos=1)

    def loop_start(self) -> None:
        if self.client:
            self.client.loop_start()
            logger.info(
                "MQTTメッセージループを開始しました (バックグラウンドスレッド)。"
            )
        else:
            logger.error(
                "MQTTクライアントが初期化されていません。ループを開始できません。"
            )

    def loop_stop(self) -> None:
        if self.client:
            self.client.loop_stop()
            logger.info("MQTTメッセージループを停止しました。")

    def disconnect(self) -> None:
        self.shutdown_event = True  # 先にフラグを立てる
        if self.client and self.client.is_connected():
            logger.info("MQTTブローカーから切断しています...")
            self.client.disconnect()
        else:
            logger.info(
                "MQTTクライアントは既に切断されているか、初期化されていません。"
            )

    def loop_forever_with_reconnect(self) -> None:
        """接続と再接続を試みながらフォアグラウンドでループします。"""
        # まず最初に接続を試みる (self.client が None の場合、ここでインスタンス化される)
        if not self.client or not self.client.is_connected():
            logger.info("初期接続を試みます...")
            self.connect()

        # connect() 後に self.client が初期化されたか、または接続試行中にシャットダウンされていないか確認
        if self.shutdown_event:  # connect()中にシャットダウンされた場合
            logger.info(
                "初期接続試行中にシャットダウンが要求されたため、ループを開始しません。"
            )
            self.disconnect()  # 念のため
            return

        if (
            not self.client
        ):  # self.connect() が Paho Client を生成できなかった場合 (configエラー等)
            logger.error(
                "MQTTクライアントのインスタンス生成に失敗しました。loop_forever_with_reconnect を開始できません。"
            )
            return

        reconnect_delay = self.config.get("reconnect_delay_seconds", 10)
        logger.info(f"MQTTループを開始します。切断時の再接続遅延: {reconnect_delay}秒")

        while not self.shutdown_event:
            try:
                if not self.client.is_connected():
                    logger.info("MQTT再接続試行...")
                    # self.connect() は既に上で呼ばれているので、ここでは再接続を試みる Paho の機能を使うか、
                    # または再度 self.connect() を呼ぶ。ここではシンプルに再度 self.connect() を呼ぶ。
                    # より堅牢にするなら、Paho の reconnect() メソッドの使用も検討。
                    self.connect()  # 再接続
                    if self.shutdown_event:  # 接続試行中にシャットダウンされた場合
                        break
                    if not self.client.is_connected():  # 再接続に失敗した場合
                        logger.warning(
                            f"再接続に失敗しました。{reconnect_delay}秒後に再試行します。"
                        )
                        time.sleep(reconnect_delay)
                        continue  # ループの先頭に戻って再試行

                # 接続が確立されたらループ開始
                self.client.loop_start()  # バックグラウンドでネットワークループを開始
                logger.info(
                    "MQTTクライアントループがバックグラウンドで開始されました。メインスレッドは待機します。"
                )
                while not self.shutdown_event and self.client.is_connected():
                    time.sleep(0.5)  # 0.5秒ごとに状態確認 (より短くした)

                self.client.loop_stop()  # 接続が切れたかシャットダウン要求

                if self.shutdown_event:
                    logger.info("シャットダウン要求により内部ループを終了します。")
                    break  # 外側の while ループも抜ける

                # 接続が切れた場合 (shutdown_eventがFalseのままここまで来た場合)
                if (
                    not self.client.is_connected()
                ):  # このチェックはほぼ常にTrueになるはず
                    logger.warning(
                        f"MQTT接続が切れました。{reconnect_delay}秒後に再接続を試みます。"
                    )
                    # time.sleep(reconnect_delay) # 再接続は次のループの冒頭で行われる

            except KeyboardInterrupt:
                logger.info("Ctrl+C受信。シャットダウンします。")
                self.shutdown_event = True
            except AttributeError as e_attr:
                if "NoneType" in str(e_attr) and "is_connected" in str(e_attr):
                    logger.error(
                        f"MQTTクライアントが予期せずNoneになりました。致命的なエラー: {e_attr}",
                        exc_info=True,
                    )
                    self.shutdown_event = True  # 復旧不能なのでシャットダウン
                else:
                    logger.error(
                        f"MQTTループ中にAttributeError: {e_attr}", exc_info=True
                    )
                logger.info(f"{reconnect_delay}秒後に再試行します...")
                time.sleep(reconnect_delay)
            except Exception as e:
                logger.error(f"MQTTループ中に予期せぬエラー: {e}", exc_info=True)
                logger.info(f"{reconnect_delay}秒後に再試行します...")
                time.sleep(reconnect_delay)

        self.disconnect()
        logger.info("MQTTクライアントのループ処理を終了しました。")
