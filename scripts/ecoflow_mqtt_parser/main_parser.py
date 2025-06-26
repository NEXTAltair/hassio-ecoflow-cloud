import logging
import signal
import sys
import time
from pathlib import Path
from typing import Any

# --- モジュール検索パスに親ディレクトリ(scripts)を追加 ---
# これにより、ecoflow_mqtt_parser 内のモジュールが scripts 直下の
# ef_dp3_iobroker_pb2 や、ecoflow_mqtt_parser内の他のモジュールを
# `import common` や `import protobuf_mapping` のように直接インポートできるようになる。
# (poetry や pip install -e . などでパッケージとしてインストールしない場合の簡易的な対策)
current_dir = Path(__file__).resolve().parent  # ecoflow_mqtt_parser
scripts_dir = current_dir.parent  # scripts
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))
    print(f"Added to sys.path: {scripts_dir}")

# --- ローカルモジュールのインポート ---
# common, protobuf_mapping, mqtt_client_setup, message_handler は
# ecoflow_mqtt_parser ディレクトリ内にあるので、直接インポートできるはず。
import common
import protobuf_mapping  # noqa: E402, F401 (protobuf_mappingはmqtt_client_setup等から使われる)
from mqtt_client_setup import MQTTClient  # noqa: E402
from message_handler import MessageHandler  # noqa: E402

logger = logging.getLogger(__name__)

# グローバルなMQTTクライアントインスタンス (シグナルハンドラ用)
mqtt_client_instance: MQTTClient | None = None


def signal_handler(sig: int, frame: Any) -> None:
    global mqtt_client_instance
    logger.info(
        f"シグナル {signal.Signals(sig).name} ({sig}) を受信しました。シャットダウン処理を開始します..."
    )
    if mqtt_client_instance:
        mqtt_client_instance.shutdown_event = True


def main() -> None:
    global mqtt_client_instance

    common.setup_logging(
        logging.DEBUG
    )  # INFOレベルでロギング開始 -> DEBUGに変更して詳細確認

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        config_raw = common.load_config()
        logger.debug(f"Loaded raw config: {config_raw}")  # ★追加：load_config直後の状態

        # config.json の output_file 設定をログで確認
        if config_raw.get("output_file"):
            logger.info(
                f"処理結果はファイルに出力されます: {Path(config_raw['output_file']).resolve()}"
            )
        else:
            logger.info("処理結果のファイル出力は設定されていません。")

        # トピックプレースホルダーを解決
        config_resolved = common.resolve_topic_placeholders(config_raw.copy())
        logger.debug(
            f"Resolved config before MQTTClient init: {config_resolved}"
        )  # ★追加：resolve後
        logger.debug(
            f"  publish_topic in resolved_config: {config_resolved.get('publish_topic')}"
        )
        logger.debug(
            f"  subscribe_topics in resolved_config: {config_resolved.get('subscribe_topics')}"
        )

    except Exception as e:
        logger.error(
            f"設定の読み込みまたは初期化中にエラーが発生しました: {e}", exc_info=True
        )
        sys.exit(1)

    msg_handler = MessageHandler(config_resolved)  # 解決済みのconfigを使用
    mqtt_client_instance = MQTTClient(
        config_resolved,
        on_message_callback=msg_handler.handle_message,  # 解決済みのconfigを使用
    )

    try:
        logger.info("MQTTクライアント処理を開始します...")
        mqtt_client_instance.connect()  # 接続試行

        if mqtt_client_instance.client:  # clientが初期化されていれば
            mqtt_client_instance.loop_start()  # バックグラウンドループ開始
            logger.info("MQTTバックグラウンドループ開始。メインスレッド待機中...")
            while not mqtt_client_instance.shutdown_event:
                time.sleep(1)  # メインスレッドはシグナルを待つ
            logger.info("シャットダウン要求によりメインスレッド待機終了。")
        else:
            logger.error(
                "MQTTクライアントの初期化に失敗したため、ループを開始できませんでした。"
            )

    except Exception as e:
        if not (mqtt_client_instance and mqtt_client_instance.shutdown_event):
            # シャットダウン要求による終了でない場合のみエラーとしてログ
            logger.error(
                f"MQTT処理ループ中に予期せぬエラーが発生しました: {e}", exc_info=True
            )
    finally:
        logger.info("メイン処理を終了します。")
        if mqtt_client_instance:
            # loop_forever_with_reconnect から抜けた後、念のため再度disconnectを試みる
            # (通常は loop_forever_with_reconnect 内のfinallyで処理されているはず)
            # → 今回の修正でloop_forever_with_reconnectは使わないので、ここでstop/disconnectが重要
            logger.info("MQTTバックグラウンドループを停止し、切断します。")
            mqtt_client_instance.loop_stop()
            mqtt_client_instance.disconnect()


if __name__ == "__main__":
    main()
