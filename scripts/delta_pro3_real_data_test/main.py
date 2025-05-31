#!/usr/bin/env python3
"""
Delta Pro 3 実データテスト メインスクリプト
Issue 05 Phase 2.5: 実際のMQTTデータでの_prepare_dataロジック確認

ロジック確認特化・エラーハンドリング最小限
"""

import sys
import json
import logging
import signal
import time
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt


sys.path.append(str(Path.cwd().parent.parent))

from mqtt_connection import create_mqtt_client
from prepare_data_processor import create_processor

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("test_results/real_data_test.log"),
    ],
)

logger = logging.getLogger(__name__)


class DeltaPro3RealDataTester:
    """Delta Pro 3実データテスト実行クラス"""

    def __init__(self):
        self.mqtt_client = create_mqtt_client()
        self.data_processor = create_processor()
        self.message_count = 0
        self.success_count = 0
        self.running = True

        # 結果保存用
        self.results_dir = Path("test_results")
        self.results_dir.mkdir(exist_ok=True)

        self.raw_messages_file = self.results_dir / "raw_messages.jsonl"
        self.processed_data_file = self.results_dir / "processed_data.jsonl"

    def handle_mqtt_message(self, msg: mqtt.MQTTMessage) -> None:
        """MQTTメッセージを受信・処理"""
        self.message_count += 1

        logger.info(
            f"📥 Message {self.message_count}: topic={msg.topic}, length={len(msg.payload)}"
        )

        # 生メッセージを保存
        raw_data = {
            "message_id": self.message_count,
            "timestamp": time.time(),
            "topic": msg.topic,
            "payload_hex": msg.payload.hex(),
            "payload_length": len(msg.payload),
        }

        self._save_raw_message(raw_data)

        # データ処理実行
        try:
            processed_data = self.data_processor.prepare_data(msg.payload)

            if processed_data:
                self.success_count += 1
                logger.info(f"✅ Processing success: {len(processed_data)} fields")

                # 処理済みデータを保存
                result_data = {
                    "message_id": self.message_count,
                    "timestamp": time.time(),
                    "topic": msg.topic,
                    "processed_fields": processed_data,
                    "field_count": len(processed_data),
                }

                self._save_processed_data(result_data)
                self._print_processed_data(processed_data)

            else:
                logger.warning("❌ Processing failed: no data returned")

        except Exception as e:
            logger.error(f"❌ Processing error: {e}")

    def _save_raw_message(self, data: dict[str, Any]) -> None:
        """生メッセージをJSONL形式で保存"""
        with open(self.raw_messages_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def _save_processed_data(self, data: dict[str, Any]) -> None:
        """処理済みデータをJSONL形式で保存"""
        with open(self.processed_data_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def _print_processed_data(self, data: dict[str, Any]) -> None:
        """処理済みデータを見やすく表示"""
        logger.info("📊 Processed Data:")
        for key, value in data.items():
            logger.info(f"  {key}: {value}")

    def _setup_signal_handlers(self) -> None:
        """シグナルハンドラー設定"""

        def signal_handler(sig: int, frame: Any) -> None:
            logger.info(f"📋 Signal {sig} received. Shutting down...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def run(self) -> None:
        """メインテスト実行"""
        logger.info("🚀 Delta Pro 3 実データテスト開始")
        logger.info("Issue 05 Phase 2.5: _prepare_dataロジック確認")

        self._setup_signal_handlers()

        # MQTTコールバック設定
        self.mqtt_client.set_message_callback(self.handle_mqtt_message)

        # MQTT接続
        logger.info("🔌 MQTT接続中...")
        if not self.mqtt_client.connect():
            logger.error("❌ MQTT接続失敗")
            return

        # 接続待機
        if not self.mqtt_client.wait_for_connection(timeout=20):
            logger.error("❌ MQTT接続タイムアウト")
            return

        # バックグラウンドループ開始
        self.mqtt_client.start_loop()

        logger.info("👂 MQTTメッセージ待機中... (Ctrl+C で終了)")

        # メインループ
        try:
            while self.running and self.mqtt_client.is_connected():
                time.sleep(1)

                # 5秒ごとに統計表示
                if self.message_count > 0 and self.message_count % 5 == 0:
                    success_rate = (self.success_count / self.message_count) * 100
                    logger.info(
                        f"📈 統計: 受信={self.message_count}, 成功={self.success_count}, 成功率={success_rate:.1f}%"
                    )

        except KeyboardInterrupt:
            logger.info("🛑 Ctrl+C で終了")

        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        """終了処理"""
        logger.info("🧹 終了処理中...")

        self.mqtt_client.stop_loop()
        self.mqtt_client.disconnect()

        # 最終統計
        if self.message_count > 0:
            success_rate = (self.success_count / self.message_count) * 100
            logger.info("📊 最終統計:")
            logger.info(f"  総受信メッセージ数: {self.message_count}")
            logger.info(f"  処理成功数: {self.success_count}")
            logger.info(f"  成功率: {success_rate:.1f}%")
            logger.info(f"  生データログ: {self.raw_messages_file}")
            logger.info(f"  処理済みデータ: {self.processed_data_file}")
        else:
            logger.info("📭 メッセージを受信しませんでした")

        logger.info("✅ テスト終了")


def main() -> None:
    """メイン実行関数"""
    print("Delta Pro 3 実データテスト")
    print("Issue 05 Phase 2.5: _prepare_dataロジック確認")
    print("=" * 60)

    tester = DeltaPro3RealDataTester()
    tester.run()


if __name__ == "__main__":
    main()
