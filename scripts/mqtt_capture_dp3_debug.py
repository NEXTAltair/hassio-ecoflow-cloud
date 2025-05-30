import json
import logging
import signal
import sys
import ctypes
import time
import ssl
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid

import base64
import binascii

from google.protobuf import json_format
import threading


import paho.mqtt.client as mqtt

# --- Protobuf (ユーザーがこのファイルを提供する必要があります) ---
import ef_dp3_iobroker_pb2 as ecopacket_pb2  # 直接インポートを試みる

# --- 設定 ---
CONFIG_FILE = Path(__file__).parent / "config.json"

# --- グローバル変数 ---
client: mqtt.Client | None = None
config: dict[str, Any] = {}
message_count = 0
last_activity_time = time.time()
last_message_received_time = time.time()
shutdown_event = threading.Event()

# --- ロギング設定 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger().setLevel(logging.DEBUG)  # ルートロガーのレベルをDEBUGに設定
logger = logging.getLogger(__name__)

# paho-mqttクライアントライブラリのデバッグログを有効化
mqtt_logger = logging.getLogger("paho.mqtt.client")
mqtt_logger.setLevel(logging.DEBUG)


# --- Protobufメッセージ型マッピング ---
# cmdFuncとcmdIdのタプルをキーとし、対応するProtobufメッセージ型を値とする
# PROTO_DECODERS: dict[tuple[int, int], type[Message]] = {
#     (254, 21): ecopacket_pb2.DisplayPropertyUpload, # 未確認
#     (32, 50): ecopacket_pb2.cmdFunc50_cmdId30_Report, # 未確認
#     (32, 2): ecopacket_pb2.cmdFunc32_cmdId2_Report, # 未確認
#     (254, 23): ecopacket_pb2.cmdFunc254_cmdId23_Report, # 未確認
# }


def xor_decode_pdata(pdata: bytes, seq: int) -> bytes:
    """ハートビートメッセージのpdataをXORデコードします。キーとしてseq全体を使用します。"""
    if not pdata:
        return b""
    decoded_payload = bytearray()
    for byte_val_int in pdata:  # pdata は bytes なので、各要素は既に int (0-255)
        # JavaScriptの number ^ number は、両者をビット列表現としてXORする。
        # Pythonでこれをエミュレートするには、byte_val_int と seq の下位8ビットのXORが妥当か、
        # もしくはseqをより大きな範囲で使うべきか。
        # ioBrokerのJSコード `array[i] ^ seq` は、array[i] (0-255の数値) と seq (大きな整数) のXOR。
        # JSのXORは32ビット整数として扱われる。結果も32ビット整数になるが、それをbyteにキャストする際、下位8ビットが使われる。
        # なので、Pythonでは (byte_val_int ^ seq) & 0xFF とする。
        decoded_payload.append((byte_val_int ^ seq) & 0xFF)
    return bytes(decoded_payload)


def decrypt_payload(encrypted_payload: bytes, key: bytes) -> bytes | None:
    """AES-128-ECBでペイロードを復号し、PKCS7パディングを解除する"""
    try:
        cipher = AES.new(key, AES.MODE_ECB)
        decrypted_data = cipher.decrypt(encrypted_payload)
        # 復号データが空、またはブロックサイズの倍数でない場合は、パディングエラーの可能性が高い
        if not decrypted_data:
            logger.warning("復号後のデータが空です。")
            return None  # もしくは encrypted_payload をそのまま返すか、エラーにするか

        try:
            # 常にアンパディングを試みる。データが実際にはパディングされていなければエラーになる。
            unpadded_payload = unpad(decrypted_data, AES.block_size, style="pkcs7")
            return unpadded_payload
        except ValueError as e_unpad:
            # パディングエラーはよく発生するので、警告レベルでログを出し、復号データ（パディング未処理）を返す
            logger.warning(
                f"PKCS7アンパディングエラー: {e_unpad}。復号データ（パディング未処理）を返します。データ: {decrypted_data.hex()}"
            )
            return decrypted_data
    except Exception as e:
        logger.error(f"復号中に予期せぬエラー: {e}", exc_info=True)
        return None


def load_config(config_path: Path) -> dict[str, Any]:
    """JSONファイルから設定を読み込みます。"""
    if not config_path.exists():
        logger.error(f"設定ファイルが見つかりません: {config_path}")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        try:
            conf = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"{config_path} からのJSONデコードエラー: {e}")
            sys.exit(1)

    # APIを使用しない前提のため、MQTT接続情報が必須
    required_direct_mqtt_keys = [
        "mqtt_broker",
        "mqtt_port",
        "mqtt_username",
        "mqtt_password",
        "user_id",
        "device_sn",
        # subscribe_topics, publish_topic_template, heartbeat_topic_template は
        # resolve_topic_placeholders で処理されるため、ここでは必須としない。
        # ただし、これらが config.json に存在することは期待される。
    ]
    missing_keys = [
        key for key in required_direct_mqtt_keys if key not in conf or not conf[key]
    ]
    if missing_keys:
        logger.error(
            f"config.json に以下のキーと有効な値が必要です: {', '.join(missing_keys)}"
        )
        sys.exit(1)

    # device_sn はトピック解決に必要なので存在を保証
    conf["device_sn"] = conf.get("device_sn", "")
    # user_id もトピック解決に必要なので存在を保証
    conf["user_id"] = conf.get("user_id", "")

    # subscribe_topics がリストであることを確認 (空のリストも許可)
    if "subscribe_topics" in conf and not isinstance(conf["subscribe_topics"], list):
        logger.error(
            "'subscribe_topics' は config.json 内で文字列のリストである必要があります。"
        )
        sys.exit(1)
    elif "subscribe_topics" not in conf:
        logger.warning(
            "'subscribe_topics' が config.json にありません。空のリストとして扱います。"
        )
        conf["subscribe_topics"] = []

    return conf


def resolve_topic_placeholders(conf: dict[str, Any]) -> dict[str, Any]:
    """設定内のトピック文字列のプレースホルダーを解決します。"""
    current_device_sn = conf.get("device_sn", "")
    current_user_id = conf.get("user_id", "")

    subscribe_topics_conf = conf.get("subscribe_topics", [])
    if isinstance(subscribe_topics_conf, list):
        processed_topics = []
        for topic_template_str in subscribe_topics_conf:
            if isinstance(topic_template_str, str):
                # USER_ID と DEVICE_SN の両方のプレースホルダーを置換 (大文字・小文字対応)
                topic = topic_template_str
                if current_user_id:
                    topic = topic.replace("{USER_ID}", current_user_id)
                    topic = topic.replace("{user_id}", current_user_id)
                if current_device_sn:
                    topic = topic.replace("{DEVICE_SN}", current_device_sn)
                    topic = topic.replace("{device_sn}", current_device_sn)
                processed_topics.append(topic)
            # 文字列でない要素は無視 (load_configでチェック済みのはずだが念のため)
        conf["subscribe_topics"] = processed_topics

    if "heartbeat_topic_template" in conf and isinstance(
        conf["heartbeat_topic_template"], str
    ):
        heartbeat_template = conf["heartbeat_topic_template"]
        if current_user_id and current_device_sn:  # 必須情報がある場合のみ生成
            topic = heartbeat_template
            topic = topic.replace("{USER_ID}", current_user_id)
            topic = topic.replace("{user_id}", current_user_id)
            topic = topic.replace("{DEVICE_SN}", current_device_sn)
            topic = topic.replace("{device_sn}", current_device_sn)
            conf["heartbeat_topic"] = topic
        else:
            conf.pop("heartbeat_topic", None)
            logger.debug(
                "heartbeat_topic_templateは存在するが、USER_IDまたはDEVICE_SNが不足しているためheartbeat_topicは生成されません。"
            )
    else:
        conf.pop("heartbeat_topic", None)  # template自体がない場合

    if "publish_topic_template" in conf and isinstance(
        conf["publish_topic_template"], str
    ):
        publish_template = conf["publish_topic_template"]
        if current_user_id and current_device_sn:  # 必須情報がある場合のみ生成
            topic = publish_template
            topic = topic.replace("{USER_ID}", current_user_id)
            topic = topic.replace("{user_id}", current_user_id)
            topic = topic.replace("{DEVICE_SN}", current_device_sn)
            topic = topic.replace("{device_sn}", current_device_sn)
            conf["publish_topic"] = topic
        else:
            conf.pop("publish_topic", None)
            logger.debug(
                "publish_topic_templateは存在するが、USER_IDまたはDEVICE_SNが不足しているためpublish_topicは生成されません。"
            )
    else:
        conf.pop("publish_topic", None)  # template自体がない場合

    logger.debug(f"プレースホルダー解決後の設定: {conf}")
    return conf


def on_connect(
    mqtt_client: mqtt.Client,
    userdata: Any,
    flags: dict[str, Any],
    rc: Any,
    properties: Any | None = None,
) -> None:
    """MQTTブローカーに接続したときに呼び出されます。"""
    global last_activity_time
    last_activity_time = time.time()

    connect_rc_int: int
    connect_reason_str: str

    if hasattr(rc, "id"):
        connect_rc_int = rc.id
        connect_reason_str = str(rc)
    elif isinstance(rc, int):
        connect_rc_int = rc
        connect_reason_str = mqtt.connack_string(rc)
    else:
        # 予期しない型の場合 (フォールバック)
        connect_rc_int = -1  # 不明なエラーとして扱う
        connect_reason_str = f"不明な接続結果タイプ: {type(rc)}"
        logger.warning(connect_reason_str)

    if connect_rc_int == 0:
        logger.info(
            f"MQTTブローカーに接続成功: {config.get('mqtt_broker')}:{config.get('mqtt_port')}"
        )
        try:
            subscribe_topics_with_qos = [
                (topic, 0) for topic in config["subscribe_topics"]
            ]
            result, mid = mqtt_client.subscribe(subscribe_topics_with_qos)
            if result == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"以下のトピックを購読します: {subscribe_topics_with_qos}")
            else:
                logger.error(f"トピック購読失敗: {result}")
                # 必要であればここで再接続処理やエラー通知を行う

            # データ取得要求メッセージの送信 (latestQuotas相当)
            message_to_send = ecopacket_pb2.Header()
            message_to_send.src = 32  # device_app
            message_to_send.dest = 32  # device_iot (ioBrokerは32を使用)
            # 32ビット符号付き整数に収める
            message_to_send.seq = ctypes.c_int32(int(time.time() * 1000)).value
            setattr(message_to_send, "from", "ios")

            # cmd_id, cmd_func を設定 (ioBrokerのlatestQuotas送信時)
            message_to_send.cmd_id = 255
            message_to_send.cmd_func = 2

            # pdata に空のbytesを設定
            message_to_send.pdata = b""
            message_to_send.data_len = len(message_to_send.pdata)

            serialized_message = message_to_send.SerializeToString()
            logger.info(
                f"データ取得要求メッセージをトピック '{config['publish_topic']}' に送信します。"
            )
            logger.debug(f"送信メッセージ (protobuf): {message_to_send}")
            logger.debug(
                f"送信ペイロード (bytes, {len(serialized_message)} bytes): {serialized_message.hex()}"
            )

            result, mid = mqtt_client.publish(
                config["publish_topic"],
                payload=serialized_message,
                qos=1,
            )
            logger.debug(
                "メッセージ送信完了 (MID: ...)"
            )  # MIDはpublishの戻り値で取得可能だが一旦省略

        except Exception as e:
            logger.error(f"on_connect内でのエラー: {e}", exc_info=True)
    else:
        error_message = (
            f"MQTTブローカー接続失敗: {connect_reason_str} (RC: {connect_rc_int})"
        )
        logger.error(error_message)
        # 接続エラーコードの具体的なハンドリング (paho-mqtt v1.x と v2.x の定数を考慮)
        # v1.x: mqtt.MQTT_ERR_CONN_REFUSED (5 for bad creds, 4 for not authorized)
        # v2.x: ReasonCodesオブジェクトで詳細な理由が提供されるが、ここでは汎用的に
        if connect_rc_int == 5:  # 一般的な「認証情報不正」または「接続拒否 - 認証情報」
            logger.error(
                "認証情報 (ユーザー名/パスワード) が正しくないか、クライアントIDが拒否された可能性があります。"
            )
        elif (
            connect_rc_int == 4
        ):  # 一般的な「認証失敗」または「接続拒否 - 認証されていない」
            logger.error(
                "クライアントが認証されていません (ブローカー設定またはクライアントIDの問題の可能性)。"
            )

        global shutdown_event
        shutdown_event.set()


def on_message(mqtt_client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
    global last_message_received_time, message_count, config
    last_message_received_time = time.time()
    message_count += 1
    logger.info(
        f"メッセージ受信 (トピック: {msg.topic}, QoS: {msg.qos}, Retain: {msg.retain}, "
        f"MID: {msg.mid}, Length: {len(msg.payload)})"
    )
    payload_hex_for_log = (
        msg.payload.hex() if isinstance(msg.payload, bytes) else str(msg.payload)
    )
    logger.debug(f"  生ペイロード (hex or str): {payload_hex_for_log}")

    output_data: dict[str, Any] = {
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        "timestamp_unix": time.time(),
        "topic": msg.topic,
        "qos": msg.qos,
        "retain": msg.retain,
        "mid": msg.mid,
        "payload_length": len(msg.payload),
        "message_seq_local": 0,
        "payload_raw_hex": "",
        "payload_base64_decoded_hex": None,
        "payload_xor_decoded_hex": None,
        "decoded_protobuf": None,
        "error": [],
        "message_format_byte_hex": None,
    }

    actual_payload_for_proto: bytes
    payload_after_base64_decode_success = False

    if isinstance(msg.payload, str):
        payload_bytes_for_b64 = msg.payload.encode("utf-8")
    else:
        payload_bytes_for_b64 = msg.payload

    try:
        # Base64デコードを試行
        decoded_payload = base64.b64decode(payload_bytes_for_b64)
        output_data["payload_base64_decoded_hex"] = (
            decoded_payload.hex()
            if len(decoded_payload) < 200
            else decoded_payload[:100].hex() + "..."
        )
        logger.info(f"  Base64デコード成功 (len: {len(decoded_payload)})")
        actual_payload_for_proto = decoded_payload
        payload_after_base64_decode_success = True
    except binascii.Error:
        logger.warning("  Base64デコード失敗。元のペイロードを処理試行します。")
        actual_payload_for_proto = payload_bytes_for_b64  # 元のバイト列を使用
        output_data["error"].append("Base64 decode failed, using original payload.")
    except Exception as e:
        logger.error(f"  Base64デコード中に予期せぬエラー: {e}")
        actual_payload_for_proto = payload_bytes_for_b64  # 元のバイト列を使用
        output_data["error"].append(f"Base64 unexpected error: {e}")

    if not actual_payload_for_proto:
        logger.warning("  処理対象のペイロードが空です。")
        output_data["error"].append("Payload is empty for processing.")
        if config.get("output_file"):
            try:
                with open(config["output_file"], "a", encoding="utf-8") as f:
                    json.dump(output_data, f, ensure_ascii=False)
                    f.write("\n")
            except Exception as e_write:
                logger.error(f"  デコード結果のファイル書き出し失敗: {e_write}")
        return

    # decoded_message_obj: Optional[Message] = None # Anyに変更
    decoded_message_obj: Any = None
    protobuf_type_name: str | None = "Unknown"

    # トピックに応じた処理分岐
    user_id = config.get("user_id")
    device_sn = config.get("device_sn")

    # トピック名を確実に取得するためにNoneチェックとデフォルト値
    get_reply_topic_template = config.get(
        "publish_topic_template_get_reply",
        "/app/{USER_ID}/{DEVICE_SN}/thing/property/get_reply",
    )
    heartbeat_topic_template = config.get(
        "heartbeat_topic_template", "/app/device/property/{DEVICE_SN}"
    )

    get_reply_topic = ""
    if user_id and device_sn:
        get_reply_topic = get_reply_topic_template.replace(
            "{USER_ID}", user_id
        ).replace("{DEVICE_SN}", device_sn)

    heartbeat_topic = ""
    if device_sn:
        heartbeat_topic = heartbeat_topic_template.replace("{DEVICE_SN}", device_sn)

    if get_reply_topic and msg.topic == get_reply_topic:
        logger.info(f"  トピック: {get_reply_topic} (データ取得応答)")
        if not payload_after_base64_decode_success:
            output_data["error"].append(
                "Expected Base64 payload for get_reply, but decode failed or was skipped."
            )

        current_msg_format_byte_int = actual_payload_for_proto[0]
        output_data["message_format_byte_hex"] = hex(current_msg_format_byte_int)  # type: ignore
        logger.info(
            f"    メッセージフォーマットバイト: {hex(current_msg_format_byte_int)}"
        )  # type: ignore

        if current_msg_format_byte_int == 0x01 or current_msg_format_byte_int == 0x02:
            try:
                set_msg = ecopacket_pb2.setMessage()
                set_msg.ParseFromString(actual_payload_for_proto[1:])
                protobuf_type_name = "setMessage (get_reply)"
                decoded_message_obj = set_msg
                logger.info(f"    {protobuf_type_name} としてデコード成功。")

                if hasattr(set_msg, "header") and set_msg.header:
                    inner_header = set_msg.header
                    pdata_for_final_decode: bytes | None = None  # 型を明示
                    pdata_bytes_for_xor: bytes | None = None  # 型を明示

                    if hasattr(inner_header, "pdata"):
                        if isinstance(
                            inner_header.pdata, bytes
                        ):  # pdataが既にbytesの場合 (protoスキーマ依存)
                            pdata_bytes_for_xor = inner_header.pdata
                        elif hasattr(
                            inner_header.pdata, "SerializeToString"
                        ):  # pdataがメッセージ型の場合
                            pdata_bytes_for_xor = inner_header.pdata.SerializeToString()

                        if pdata_bytes_for_xor:
                            output_data["get_reply_inner_header_pdata_raw_hex"] = (
                                pdata_bytes_for_xor.hex()
                            )
                            pdata_for_final_decode = (
                                pdata_bytes_for_xor  # デフォルトはXORなし
                            )

                            if (
                                hasattr(inner_header, "enc_type")
                                and inner_header.enc_type == 1
                                and hasattr(inner_header, "src")
                                and inner_header.src != 32
                                and hasattr(inner_header, "seq")
                            ):
                                logger.info(
                                    f"      pdataをXORデコードします (seq: {inner_header.seq})"
                                )
                                try:
                                    xored_pdata = xor_decode_pdata(
                                        pdata_bytes_for_xor, inner_header.seq
                                    )
                                    output_data["payload_xor_decoded_hex"] = (
                                        xored_pdata.hex()
                                    )
                                    pdata_for_final_decode = xored_pdata
                                    logger.debug(
                                        f"        XORデコード後 (hex): {xored_pdata.hex()}"
                                    )
                                except Exception as e_xor:
                                    output_data["error"].append(
                                        f"get_reply pdata XOR decode error: {e_xor}"
                                    )
                                    logger.error(
                                        f"      pdataのXORデコード中にエラー: {e_xor}"
                                    )

                        if pdata_for_final_decode:
                            # TODO: ここで pdata_for_final_decode を cmdFunc/cmdId に基づいて具体的な型にデコード
                            # 例: decoded_result = decode_using_cmd_id(pdata_for_final_decode, inner_header.cmdFunc, inner_header.cmdId)
                            # output_data["decoded_payload_meaningful"] = decoded_result
                            logger.info(
                                f"      最終的なpdata (hex, {len(pdata_for_final_decode)} bytes) をさらにデコードする必要があります (未実装)。"
                            )
                            output_data["get_reply_final_pdata_hex"] = (
                                pdata_for_final_decode.hex()
                            )
                        else:
                            logger.warning(
                                "      最終デコード対象のpdataがありません (元データなし or XOR後データなし)。"
                            )
                    else:
                        logger.warning(
                            "      setMessage.header に pdata フィールドが存在しません。"
                        )
                else:
                    logger.warning(
                        "      setMessage に header フィールドが存在しません。"
                    )

            except Exception as e_set_msg:
                output_data["error"].append(
                    f"get_reply setMessage decode error: {e_set_msg}"
                )
                logger.error(
                    f"    get_reply のsetMessageデコード中にエラー: {e_set_msg}"
                )
        else:
            output_data["error"].append(
                f"get_reply: Unexpected msg_format_byte {hex(current_msg_format_byte_int)}"
            )  # type: ignore
            logger.warning(
                f"    get_reply: 未対応のメッセージフォーマットバイト: {hex(current_msg_format_byte_int)}"
            )  # type: ignore

    elif heartbeat_topic and msg.topic == heartbeat_topic:
        logger.info(f"  トピック: {heartbeat_topic} (ハートビート/ストリーム)")
        if (
            payload_after_base64_decode_success
        ):  # 通常ハートビートはBase64でないことが多い
            output_data["error"].append(
                "Expected raw protobuf for heartbeat, but Base64 decode success?!"
            )

        try:
            hb_msg = ecopacket_pb2.HeaderMessage()
            hb_msg.ParseFromString(actual_payload_for_proto)
            protobuf_type_name = "HeaderMessage (Heartbeat)"
            decoded_message_obj = hb_msg
            logger.info(f"    {protobuf_type_name} としてデコード試行成功。")
            # TODO: HeaderMessage内部の各HeaderのpdataをXORデコードし、cmdFunc/cmdIdに基づいてさらにデコード
            if hasattr(hb_msg, "header_list") and hb_msg.header_list:
                for idx, header_item in enumerate(hb_msg.header_list):
                    logger.debug(
                        f"      Processing header item {idx} from HeaderMessage..."
                    )
                    # ここで各header_itemのpdata処理 (XOR, 個別デコード)
            elif hasattr(hb_msg, "header") and hb_msg.header:  # 単一Headerの場合
                logger.debug(
                    "      Processing single header item from HeaderMessage..."
                )
                # header_item = hb_msg.header; ここでpdata処理

        except Exception as e_hb:
            logger.warning(
                f"    HeaderMessageとしてのデコード失敗: {e_hb}。Headerとして試行します。"
            )
            try:
                h_msg = ecopacket_pb2.Header()
                h_msg.ParseFromString(actual_payload_for_proto)
                protobuf_type_name = "Header (Heartbeat Fallback)"
                decoded_message_obj = h_msg
                logger.info(f"    {protobuf_type_name} としてデコード試行成功。")
                # TODO: HeaderのpdataをXORデコードし、cmdFunc/cmdIdに基づいてさらにデコード
                if (
                    hasattr(h_msg, "pdata")
                    and isinstance(h_msg.pdata, bytes)
                    and hasattr(h_msg, "enc_type")
                    and h_msg.enc_type == 1
                    and hasattr(h_msg, "src")
                    and h_msg.src != 32
                    and hasattr(h_msg, "seq")
                ):
                    logger.info(
                        f"      Fallback HeaderのpdataをXORデコードします (seq: {h_msg.seq})"
                    )
                    try:
                        xored_pdata = xor_decode_pdata(h_msg.pdata, h_msg.seq)
                        output_data["payload_xor_decoded_hex"] = xored_pdata.hex()
                        logger.debug(
                            f"        XORデコード後 (hex): {xored_pdata.hex()}"
                        )
                        # TODO: xored_pdata を cmdFunc/cmdId に基づいてさらにデコード
                    except Exception as e_xor_h:
                        output_data["error"].append(
                            f"Heartbeat fallback Header pdata XOR decode error: {e_xor_h}"
                        )

            except Exception as e_h:
                output_data["error"].append(
                    f"Heartbeat direct Header decode error: {e_h}"
                )
                logger.error(f"    ハートビート系のメッセージデコードに失敗: {e_h}")
    else:
        logger.info(f"  未処理のトピック: {msg.topic}")
        # 必要に応じて他のトピックも処理 (例: set_replyなど)

    if decoded_message_obj:
        try:
            # MessageToJson だと bytes が Base64エンコード文字列になるので MessageToDict を使う
            decoded_json = json_format.MessageToDict(
                decoded_message_obj,
                preserving_proto_field_name=True,
                including_default_value_fields=True,
                # bytes_as_base64 = False # bytesをhexで出力したいが、そういうオプションはない
            )

            # bytes型フィールドをhexに変換する処理を追加
            def convert_bytes_to_hex_recursive(obj):
                if isinstance(obj, dict):
                    return {
                        k: convert_bytes_to_hex_recursive(v) for k, v in obj.items()
                    }
                elif isinstance(obj, list):
                    return [convert_bytes_to_hex_recursive(elem) for elem in obj]
                elif isinstance(obj, bytes):
                    return obj.hex()
                return obj

            decoded_json_with_hex_bytes = convert_bytes_to_hex_recursive(decoded_json)

            output_data["decoded_protobuf"] = {
                "type": protobuf_type_name,
                "data": decoded_json_with_hex_bytes,
            }
            # JSONが巨大になる可能性があるので、ログ出力は必要な部分だけか、長さを制限
            log_friendly_json_str = json.dumps(decoded_json_with_hex_bytes)
            if len(log_friendly_json_str) > 500:
                log_friendly_json_str = log_friendly_json_str[:500] + "..."
            logger.debug(
                f"  デコード結果 ({protobuf_type_name}): {log_friendly_json_str}"
            )

        except Exception as e_json:
            output_data["error"].append(f"Protobuf to JSON error: {e_json}")
            logger.error(
                f"  デコードされたProtobufメッセージのJSON変換中にエラー: {e_json}"
            )

    # ファイルへの書き出し
    if config.get("output_file"):
        try:
            with open(config["output_file"], "a", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False)
                f.write("\n")
        except Exception as e_write:
            logger.error(f"JSONファイルへの書き込み中にエラー: {e_write}")


def on_disconnect(
    client_obj: mqtt.Client,
    userdata: Any,
    rc: Any | None = None,
    properties: Any | None = None,
    *args: Any,
) -> None:
    """MQTTブローカーから切断されたときに呼び出されます。"""
    global last_activity_time, client
    last_activity_time = time.time()

    reason_code_int: int
    reason_string: str

    if rc is None:  # 通常の disconnect() 呼び出しなど
        reason_code_int = 0
        reason_string = "Normal disconnection"
    elif hasattr(rc, "id"):  # Paho MQTT v2.0+ (ReasonCode object)
        reason_code_int = rc.id
        reason_string = str(rc)
    elif isinstance(rc, int):  # Paho MQTT v1.x
        reason_code_int = rc
        # v1.xの場合、mqtt.connack_string() は接続用だが、同様の文字列を生成する関数はない。
        # paho.mqtt.client.disconnect_reason_string(rc) は存在しないため、手動でマッピングするか、RC値を直接表示。
        if rc == 0:
            reason_string = "Normal disconnection"
        elif rc == mqtt.MQTT_ERR_CONN_LOST:  # type: ignore
            reason_string = "Connection lost"
        # 他のRC値に対応する文字列を追加することも可能
        else:
            reason_string = f"Disconnect RC: {rc}"

    logger.info(
        f"MQTTブローカーから切断されました。理由: {reason_string} (RC: {reason_code_int})"
    )

    if reason_code_int != 0 and not shutdown_event.is_set():
        logger.warning("予期せぬ切断です。メインループで再接続が試行されます。")
    elif shutdown_event.is_set():
        logger.info("シャットダウン中のため、再接続は行いません。")


def on_log_mqtt(log_client: mqtt.Client, userdata: Any, level: int, buf: str) -> None:
    """Paho MQTTライブラリのログメッセージを処理します。"""
    # client変数との衝突を避けるため、引数名を log_client に変更
    if level == mqtt.MQTT_LOG_INFO or level == mqtt.MQTT_LOG_NOTICE:
        mqtt_logger.info(buf)
    elif level == mqtt.MQTT_LOG_WARNING:
        mqtt_logger.warning(buf)
    elif level == mqtt.MQTT_LOG_ERR:
        mqtt_logger.error(buf)
    elif level == mqtt.MQTT_LOG_DEBUG:
        mqtt_logger.debug(buf)
    else:
        mqtt_logger.debug(f"MQTT Log (Level {level}): {buf}")


def status_monitor():
    """定期的に接続状態とメッセージ受信状況を監視するスレッド関数。"""
    global last_activity_time, last_message_received_time, client, shutdown_event
    monitor_interval = config.get("monitor_interval_seconds", 30)
    no_message_timeout = config.get("no_message_timeout_seconds", 120)
    reconnect_delay = config.get("reconnect_delay_seconds", 10)

    logger.info(
        f"ステータスモニター開始 (監視間隔: {monitor_interval}秒, 無通信タイムアウト: {no_message_timeout}秒)"
    )

    while not shutdown_event.is_set():
        current_time = time.time()

        if client and client.is_connected():
            if current_time - last_message_received_time > no_message_timeout:
                logger.warning(
                    f"{no_message_timeout}秒以上メッセージを受信していません。接続に問題がある可能性があります。"
                )
                if client and client.is_connected() and config.get("publish_topic"):
                    logger.info("無通信のため、データ取得要求を再送信します。")
                    # 1. setHeader オブジェクトを作成して値を設定
                    header_info = ecopacket_pb2.Header()  # type: ignore
                    header_info.src = 32
                    header_info.dest = 32
                    current_time_ms = int(time.time() * 1000)
                    current_seq = current_time_ms & 0xFFFFFFFF
                    header_info.seq = current_seq
                    try:
                        setattr(header_info, "from", "ios")
                    except AttributeError:
                        pass  # on_connectで警告済みなのでここでは省略

                    # 2. setMessage オブジェクトを作成し、header フィールドに setHeader オブジェクトをセット
                    message_to_send = ecopacket_pb2.Header()  # type: ignore
                    message_to_send.CopyFrom(header_info)  # type: ignore

                    # 3. setMessage オブジェクトをシリアライズして送信
                    message_bytes = message_to_send.SerializeToString()
                    logger.debug(
                        f"ステータスモニターからのデータ取得要求 (再送) ペイロード (bytes, {len(message_bytes)} bytes): {message_bytes.hex()}"
                    )
                    result, mid = client.publish(
                        config["publish_topic"],
                        payload=message_bytes,  # Base64エンコードしない
                        qos=1,  # ioBrokerはQoS 1で送信している
                    )
                    if result == mqtt.MQTT_ERR_SUCCESS:
                        logger.debug(f"メッセージ再送信成功 (MID: {mid})")
                        last_message_received_time = (
                            current_time  # 再送したので、最後のメッセージ時刻を更新
                        )
                    else:
                        logger.error(
                            f"メッセージ再送信失敗: {mqtt.error_string(result)}"
                        )
        else:
            logger.warning(
                f"MQTTクライアントが接続されていません。{reconnect_delay}秒後に再接続を試みます。"
            )
            shutdown_event.wait(reconnect_delay)

        shutdown_event.wait(monitor_interval)

    logger.info("ステータスモニター終了。")


def signal_handler(sig: int, frame: Any) -> None:
    """Ctrl+Cなどのシグナルを処理します。"""
    global client, shutdown_event
    logger.info(f"シグナル {sig} を受信しました。シャットダウン処理を開始します...")
    shutdown_event.set()

    if client and client.is_connected():
        logger.info("MQTTブローカーから切断しています...")
        client.disconnect()
    logger.info("シャットダウン完了。")
    sys.exit(0)


def main() -> None:
    """メイン処理"""
    global client, config, last_message_received_time, shutdown_event

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    config = load_config(CONFIG_FILE)

    while not shutdown_event.is_set():
        # API認証フローを削除
        logger.info("config.jsonの直接指定されたMQTT認証情報を使用します。")
        config = resolve_topic_placeholders(config)  # load_config の後に呼び出す

        # 必須キーのチェック (load_configとresolve_topic_placeholders後)
        # publish_topic はデータ取得要求に必須、subscribe_topics は受信に必須
        final_required_keys = [
            "mqtt_broker",  # load_config でチェック済み
            "mqtt_port",  # load_config でチェック済み
            "mqtt_username",  # load_config でチェック済み
            "mqtt_password",  # load_config でチェック済み
            "user_id",  # load_config でチェック済み
            "device_sn",  # load_config でチェック済み
            "subscribe_topics",  # resolve_topic_placeholders で処理済み、内容は空かもしれない
            "publish_topic",  # resolve_topic_placeholders で生成されるかNone
            # "heartbeat_topic" はオプションなので必須リストからは除外
        ]
        missing_final_keys = []
        for key in final_required_keys:
            if (
                key not in config or config[key] is None
            ):  # 値がNoneの場合も不足とみなす (publish_topicなど)
                # subscribe_topics は空リストを許容するので、Noneでないことだけチェック
                if key == "subscribe_topics" and isinstance(config.get(key), list):
                    continue
                missing_final_keys.append(key)

        if missing_final_keys:
            logger.error(
                f"MQTT処理に必要な設定が不足しています: {', '.join(missing_final_keys)}。"
                f"config.jsonの内容を確認してください。"
            )
            retry_delay = config.get(
                "reconnect_delay_seconds", 10
            )  # API失敗時と同じ遅延を使う
            logger.info(f"{retry_delay}秒後に設定読み込みから再試行します...")
            shutdown_event.wait(retry_delay)
            if shutdown_event.is_set():
                break
            config = load_config(CONFIG_FILE)  # ループの最初に戻る前に再読み込み
            continue

        client_id_type = config.get("client_id_type", "ANDROID")
        user_id_for_client = config.get("user_id", "unknown_user")

        if client_id_type == "ANDROID":
            client_id = f"ANDROID_{str(uuid.uuid4())}_{user_id_for_client}"
        elif client_id_type == "WEB":
            client_id = f"WEB_{str(uuid.uuid4())}_{user_id_for_client}"
        elif client_id_type == "IOS":
            client_id = f"IOS_{str(uuid.uuid4())}_{user_id_for_client}"
        elif client_id_type == "GENERATED_STATIC":
            client_id = config.get(
                "static_client_id", f"DEFAULT_STATIC_{str(uuid.uuid4())}"
            )
        else:
            client_id = config.get("client_id", f"custom_client_{str(uuid.uuid4())}")

        logger.info(f"使用するクライアントID: {client_id}")

        try:
            # Paho MQTT v2.x.x との互換性のためのCallbackAPIVersion指定
            if hasattr(mqtt, "CallbackAPIVersion"):
                client = mqtt.Client(
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION1,  # type: ignore
                    client_id=client_id,
                    protocol=mqtt.MQTTv311,
                    transport="tcp",
                )
            else:  # 古いバージョン (v1.x.x) の場合
                client = mqtt.Client(
                    client_id=client_id, protocol=mqtt.MQTTv311, transport="tcp"
                )
        except TypeError as e:
            logger.warning(
                f"Paho MQTT Client初期化中にTypeError: {e}。フォールバック試行。"
            )
            # TypeErrorが発生した場合の最も基本的な初期化 (引数なしは不可なのでclient_idのみ)
            # ただし、上記 hasattr で分岐しているので、ここに来ることは通常ないはず
            client = mqtt.Client(client_id=client_id)  # type: ignore

        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        client.on_log = on_log_mqtt

        client.tls_set(
            ca_certs=None,
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_NONE,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )
        client.tls_insecure_set(True)

        # 設定ファイルでこれらのキーの存在は既にチェックされているが、型チェッカーのためにデフォルト値を提供
        mqtt_username = config.get("mqtt_username", "")
        mqtt_password = config.get("mqtt_password", "")
        client.username_pw_set(mqtt_username, mqtt_password)

        monitor_thread = threading.Thread(target=status_monitor, daemon=True)
        monitor_thread.start()
        last_message_received_time = time.time()

        try:
            logger.info(
                f"MQTTブローカー ({config.get('mqtt_broker')}:{config.get('mqtt_port')}) に接続試行中..."
            )
            # 設定ファイルでこれらのキーの存在は既にチェックされているが、型チェッカーのためにデフォルト値を提供
            mqtt_broker = config.get(
                "mqtt_broker", "localhost"
            )  # デフォルトは適切に変更してください
            mqtt_port = config.get(
                "mqtt_port", 1883
            )  # デフォルトは適切に変更してください
            mqtt_keepalive = config.get("mqtt_keepalive", 60)

            client.connect(
                mqtt_broker,
                mqtt_port,
                mqtt_keepalive,
            )
            client.loop_forever(retry_first_connection=False)

        except ConnectionRefusedError:
            logger.error(
                "MQTTブローカーへの接続が拒否されました。ホスト/ポートを確認してください。"
            )
        except TimeoutError:
            logger.error("MQTTブローカーへの接続がタイムアウトしました。")
        except mqtt.WebsocketConnectionError as e:
            logger.error(f"MQTT WebSocket接続エラー: {e}")
        except ssl.SSLError as e:
            logger.error(f"SSLエラーが発生しました: {e}. TLS設定を確認してください。")
            logger.error(
                "CA証明書がシステムにないか、ブローカーの証明書に問題がある可能性があります。"
            )
        except OSError as e:
            logger.error(f"OSエラー (ネットワーク関連): {e}")
        except Exception as e:
            if not shutdown_event.is_set():
                logger.error(f"MQTT接続/ループ中に予期せぬエラー: {e}", exc_info=True)

        if shutdown_event.is_set():
            logger.info("シャットダウンシグナルによりMQTTループを終了しました。")
            break

        logger.info(
            f"{config.get('reconnect_delay_seconds', 10)}秒後に再接続を試みます..."
        )
        shutdown_event.wait(config.get("reconnect_delay_seconds", 10))

    logger.info("スクリプトを終了します。")


if __name__ == "__main__":
    main()
