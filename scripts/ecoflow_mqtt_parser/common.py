import json
import logging
import sys
from pathlib import Path
from typing import Any

# --- 設定 ---
CONFIG_FILE_NAME = "config.json"  # 設定ファイル名は固定

# --- ロギング設定 ---
logger = logging.getLogger(__name__)


def setup_logging(log_level: int = logging.INFO) -> None:
    """基本的なロギング設定を行います。"""
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # ルートロガーのレベルを設定 (必要に応じて)
    # logging.getLogger().setLevel(logging.DEBUG)

    # paho-mqttクライアントライブラリのデバッグログを有効化 (必要に応じて)
    # mqtt_logger = logging.getLogger("paho.mqtt.client")
    # mqtt_logger.setLevel(logging.DEBUG)


def load_config() -> dict[str, Any]:
    """
    JSONファイルから設定を読み込みます。
    設定ファイルはスクリプトと同じディレクトリにある config.json を想定します。
    """
    config_path = (
        Path(__file__).parent / CONFIG_FILE_NAME
    )  # common.py (このファイル) と同じディレクトリの config.json を指すように変更
    if not config_path.exists():
        logger.error(f"設定ファイルが見つかりません: {config_path}")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        try:
            conf = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"{config_path} からのJSONデコードエラー: {e}")
            sys.exit(1)

    # MQTT接続に最低限必要なキー
    required_mqtt_connect_keys = [
        "mqtt_broker",
        "mqtt_port",
        "mqtt_username",
        "mqtt_password",
    ]
    missing_keys = [
        key for key in required_mqtt_connect_keys if key not in conf or not conf[key]
    ]
    if missing_keys:
        logger.error(
            f"{config_path} にMQTT接続のための基本キーと有効な値が必要です: {', '.join(missing_keys)}"
        )
        sys.exit(1)

    # トピック生成に必要な可能性のあるキー (resolve_topic_placeholdersで詳細チェック)
    # app_user_id と device_sn はテンプレートの内容によって必須性が変わる
    if "app_user_id" not in conf or not conf["app_user_id"]:
        logger.warning(
            f"{config_path} に app_user_id が設定されていません。一部トピックが生成できない可能性があります。"
        )
        conf["app_user_id"] = (
            ""  # 空文字でプレースホルダー置換時にエラーにならないようにする
        )

    if "device_sn" not in conf or not conf["device_sn"]:
        logger.warning(
            f"{config_path} に device_sn が設定されていません。一部トピックが生成できない可能性があります。"
        )
        conf["device_sn"] = ""

    # subscribe_topics_templates の処理
    if "subscribe_topics_templates" not in conf:
        logger.warning(
            f"'subscribe_topics_templates' が {config_path} にありません。空のリストとして扱います。"
        )
        conf["subscribe_topics_templates"] = []
    elif not isinstance(conf.get("subscribe_topics_templates"), list):
        logger.error(
            f"'subscribe_topics_templates' は {config_path} 内で文字列のリストである必要があります。"
        )
        sys.exit(1)

    # publish_topic_template は resolve_topic_placeholders で処理・検証

    # その他のオプションキーのデフォルト値設定
    conf.setdefault("client_id_type", "ANDROID")
    conf.setdefault("monitor_interval_seconds", 30)
    conf.setdefault("no_message_timeout_seconds", 120)
    conf.setdefault("reconnect_delay_seconds", 10)
    conf.setdefault("mqtt_keepalive", 60)
    conf.setdefault("output_file", None)
    conf.setdefault("get_reply_topic_template", None)  # デフォルトはNone
    conf.setdefault("heartbeat_topic_template", None)  # デフォルトはNone

    return conf


def xor_decode_pdata(pdata: bytes, seq: int) -> bytes:
    """pdataをXORデコードします。キーとしてseq全体を使用します。"""
    if not pdata:
        return b""
    decoded_payload = bytearray()
    for byte_val_int in pdata:
        decoded_payload.append((byte_val_int ^ seq) & 0xFF)
    return bytes(decoded_payload)


def resolve_topic_placeholders(conf: dict[str, Any]) -> dict[str, Any]:
    """設定内のトピック文字列のプレースホルダーを解決し、最終的なトピックを生成します。"""
    # load_configで空文字が設定されるため、Noneチェックは不要
    current_device_sn = conf.get("device_sn", "")
    current_app_user_id = conf.get("app_user_id", "")

    # subscribe_topics を生成
    subscribe_templates = conf.get("subscribe_topics_templates", [])
    processed_subscribe_topics = []
    for topic_template_str in subscribe_templates:
        if isinstance(topic_template_str, str):
            topic = topic_template_str
            if "{USER_ID}" in topic and not current_app_user_id:
                logger.warning(
                    f"購読トピックテンプレート '{topic_template_str}' に {{USER_ID}} がありますが、app_user_idが未設定です。"
                )
            topic = topic.replace("{USER_ID}", current_app_user_id).replace(
                "{user_id}", current_app_user_id
            )
            if "{DEVICE_SN}" in topic and not current_device_sn:
                logger.warning(
                    f"購読トピックテンプレート '{topic_template_str}' に {{DEVICE_SN}} がありますが、device_snが未設定です。"
                )
            topic = topic.replace("{DEVICE_SN}", current_device_sn).replace(
                "{device_sn}", current_device_sn
            )
            processed_subscribe_topics.append(topic)
    conf["subscribe_topics"] = processed_subscribe_topics  # 最終的な購読トピックリスト

    # publish_topic を生成
    publish_template = conf.get("publish_topic_template")
    if isinstance(publish_template, str):
        topic = publish_template
        publish_topic_generated = True
        if "{USER_ID}" in topic:
            if not current_app_user_id:
                logger.error(
                    f"publish_topic_template '{publish_template}' に {{USER_ID}} が必須ですが、app_user_idが未設定です。"
                )
                publish_topic_generated = False
            else:
                topic = topic.replace("{USER_ID}", current_app_user_id).replace(
                    "{user_id}", current_app_user_id
                )
        if "{DEVICE_SN}" in topic:
            if not current_device_sn:
                logger.error(
                    f"publish_topic_template '{publish_template}' に {{DEVICE_SN}} が必須ですが、device_snが未設定です。"
                )
                publish_topic_generated = False
            else:
                topic = topic.replace("{DEVICE_SN}", current_device_sn).replace(
                    "{device_sn}", current_device_sn
                )

        if publish_topic_generated:
            conf["publish_topic"] = topic
        else:
            logger.error(f"publish_topicの生成に失敗しました。値はNoneになります。")
            conf["publish_topic"] = None  # 生成失敗

    elif "publish_topic_template" not in conf:  # templateキー自体がない
        logger.warning(
            "config.jsonに 'publish_topic_template' が設定されていません。publish_topicはNoneになります。"
        )
        conf["publish_topic"] = None
    # publish_topicキーが元から存在する場合は何もしない（直接設定されているケース）

    # get_reply_topic を生成
    get_reply_template = conf.get("get_reply_topic_template")
    if isinstance(get_reply_template, str):
        topic = get_reply_template
        get_reply_topic_generated = True
        if "{USER_ID}" in topic:
            if not current_app_user_id:
                logger.warning(  # こちらは警告レベル
                    f"get_reply_topic_template '{get_reply_template}' に {{USER_ID}} がありますが、app_user_idが未設定です。"
                )
                # get_reply_topic_generated = False # USER_IDなしでもDEVICE_SNだけで機能する場合もあるかもしれないので生成は続ける
            topic = topic.replace("{USER_ID}", current_app_user_id).replace(
                "{user_id}", current_app_user_id
            )
        if "{DEVICE_SN}" in topic:
            if not current_device_sn:
                logger.warning(  # こちらは警告レベル
                    f"get_reply_topic_template '{get_reply_template}' に {{DEVICE_SN}} がありますが、device_snが未設定です。"
                )
                # get_reply_topic_generated = False
            topic = topic.replace("{DEVICE_SN}", current_device_sn).replace(
                "{device_sn}", current_device_sn
            )

        # if get_reply_topic_generated: # 警告のみなので、常に生成を試みる
        conf["get_reply_topic"] = topic
        # else:
        #     conf["get_reply_topic"] = None

    elif "get_reply_topic_template" not in conf:
        # logger.warning("get_reply_topic_templateが設定されていません。get_reply_topicはNoneのままです。")
        conf["get_reply_topic"] = None  # キーがなければNone

    # device_property_topic (旧heartbeat_topic) を生成
    device_property_template = conf.get(
        "heartbeat_topic_template"
    )  # configではheartbeat_topic_template
    if isinstance(device_property_template, str):
        topic = device_property_template
        if "{DEVICE_SN}" in topic:
            if not current_device_sn:
                logger.warning(
                    f"heartbeat_topic_template '{device_property_template}' に {{DEVICE_SN}} がありますが、device_snが未設定です。"
                )
            topic = topic.replace("{DEVICE_SN}", current_device_sn).replace(
                "{device_sn}", current_device_sn
            )
        conf["device_property_topic"] = topic
    elif "heartbeat_topic_template" not in conf:
        # logger.warning("heartbeat_topic_templateが設定されていません。device_property_topicはNoneのままです。")
        conf["device_property_topic"] = None

    logger.debug(f"プレースホルダー解決後の最終設定: {conf}")
    return conf
