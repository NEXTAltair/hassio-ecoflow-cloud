#!/usr/bin/env python3
"""
Delta Pro 3 _prepare_data プロセッサー
Issue 05 Phase 2.5: 実データテスト用

Phase 2で実装・検証済みのロジックを実用版として移植
"""

import logging
from typing import Any


# Protobuf定義ファイルのインポート
from custom_components.ecoflow_cloud.devices.internal.proto import (
    ef_dp3_iobroker_pb2 as pb2,
)

logger = logging.getLogger(__name__)


class DeltaPro3PrepareDataProcessor:
    """Delta Pro 3専用の_prepare_dataロジック実装"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def prepare_data(self, raw_data: bytes) -> dict[str, Any]:
        """
        Delta Pro 3用のメインデータ準備メソッド

        Args:
            raw_data: MQTTから受信した生バイナリデータ

        Returns:
            dict: Home Assistant用に変換されたデータ
        """
        try:
            self.logger.debug(f"Processing {len(raw_data)} bytes of raw data")

            # 1. HeaderMessageのデコード
            header_info = self._decode_header_message(raw_data)
            if not header_info:
                self.logger.warning("HeaderMessage decoding failed")
                return {}

            # 2. ペイロードデータの抽出
            pdata = self._extract_payload_data(header_info.get("header_obj"))
            if not pdata:
                self.logger.warning("No payload data found")
                return {}

            # 3. XORデコード (必要に応じて)
            decoded_pdata = self._perform_xor_decode(pdata, header_info)

            # 4. Protobufメッセージのデコード
            decoded_data = self._decode_message_by_type(decoded_pdata, header_info)
            if not decoded_data:
                self.logger.warning("Message decoding failed")
                return {}

            # 5. HAフィールド形式への変換
            transformed_data = self._transform_data_fields(decoded_data, header_info)

            self.logger.info(
                f"Successfully processed data: {len(transformed_data)} fields"
            )
            return transformed_data

        except Exception as e:
            self.logger.error(f"Data processing failed: {e}", exc_info=True)
            return {}

    def _decode_header_message(self, raw_data: bytes) -> dict[str, Any] | None:
        """HeaderMessageをデコードしてヘッダー情報を抽出"""
        try:
            # Base64デコードを試行
            import base64

            try:
                decoded_payload = base64.b64decode(raw_data, validate=True)
                self.logger.debug("Base64 decode successful")
                raw_data = decoded_payload
            except Exception:
                self.logger.debug("Data is not Base64 encoded, using as-is")

            # HeaderMessageとしてデコード
            header_msg = pb2.HeaderMessage()
            header_msg.ParseFromString(raw_data)

            if not header_msg.header:
                self.logger.warning("No headers found in HeaderMessage")
                return None

            # 最初のヘッダーを使用 (通常は1つ)
            header = header_msg.header[0]
            header_info = {
                "src": getattr(header, "src", 0),
                "dest": getattr(header, "dest", 0),
                "dSrc": getattr(header, "d_src", 0),
                "dDest": getattr(header, "d_dest", 0),
                "encType": getattr(header, "enc_type", 0),
                "checkType": getattr(header, "check_type", 0),
                "cmdFunc": getattr(header, "cmd_func", 0),
                "cmdId": getattr(header, "cmd_id", 0),
                "dataLen": getattr(header, "data_len", 0),
                "needAck": getattr(header, "need_ack", 0),
                "seq": getattr(header, "seq", 0),
                "productId": getattr(header, "product_id", 0),
                "version": getattr(header, "version", 0),
                "payloadVer": getattr(header, "payload_ver", 0),
                "header_obj": header,
            }

            self.logger.debug(
                f"Header decoded: cmdFunc={header_info['cmdFunc']}, cmdId={header_info['cmdId']}"
            )
            return header_info

        except Exception as e:
            self.logger.error(f"Header message decode error: {e}")
            return None

    def _extract_payload_data(self, header_obj: Any) -> bytes | None:
        """ヘッダーからペイロードデータを抽出"""
        try:
            pdata = getattr(header_obj, "pdata", b"")
            if pdata:
                self.logger.debug(f"Extracted {len(pdata)} bytes of payload data")
                return pdata
            else:
                self.logger.warning("No pdata found in header")
                return None
        except Exception as e:
            self.logger.error(f"Payload extraction error: {e}")
            return None

    def _perform_xor_decode(self, pdata: bytes, header_info: dict[str, Any]) -> bytes:
        """必要に応じてXORデコードを実行"""
        enc_type = header_info.get("encType", 0)
        src = header_info.get("src", 0)
        seq = header_info.get("seq", 0)

        # XOR decode condition: enc_type == 1 and src != 32
        if enc_type == 1 and src != 32:
            self.logger.debug(f"Performing XOR decode with seq={seq}")
            return self._xor_decode_pdata(pdata, seq)
        else:
            self.logger.debug("No XOR decoding needed")
            return pdata

    def _xor_decode_pdata(self, pdata: bytes, seq: int) -> bytes:
        """XORデコード処理"""
        if not pdata:
            return b""

        decoded_payload = bytearray()
        for byte_val in pdata:
            decoded_payload.append((byte_val ^ seq) & 0xFF)

        return bytes(decoded_payload)

    def _decode_message_by_type(
        self, pdata: bytes, header_info: dict[str, Any]
    ) -> dict[str, Any]:
        """cmdFunc/cmdIdに基づいてProtobufメッセージをデコード"""
        cmd_func = header_info.get("cmdFunc", 0)
        cmd_id = header_info.get("cmdId", 0)

        try:
            self.logger.debug(f"Decoding message: cmdFunc={cmd_func}, cmdId={cmd_id}")

            if cmd_func == 254 and cmd_id == 21:
                # DisplayPropertyUpload
                msg = pb2.DisplayPropertyUpload()
                msg.ParseFromString(pdata)
                return self._protobuf_to_dict(msg)

            elif cmd_func == 32 and cmd_id == 2:
                # cmdFunc32_cmdId2_Report
                msg = pb2.cmdFunc32_cmdId2_Report()
                msg.ParseFromString(pdata)
                return self._protobuf_to_dict(msg)

            elif cmd_func == 32 and cmd_id == 50:
                # cmdFunc50_cmdId30_Report
                msg = pb2.cmdFunc50_cmdId30_Report()
                msg.ParseFromString(pdata)
                return self._protobuf_to_dict(msg)

            elif cmd_func == 254 and cmd_id == 22:
                # RuntimePropertyUpload
                msg = pb2.RuntimePropertyUpload()
                msg.ParseFromString(pdata)
                return self._protobuf_to_dict(msg)

            else:
                self.logger.warning(
                    f"Unknown message type: cmdFunc={cmd_func}, cmdId={cmd_id}"
                )
                return {}

        except Exception as e:
            self.logger.error(f"Message decode error: {e}")
            return {}

    def _protobuf_to_dict(self, protobuf_obj: Any) -> dict[str, Any]:
        """Protobufオブジェクトを辞書に変換"""
        try:
            from google.protobuf.json_format import MessageToDict

            return MessageToDict(protobuf_obj, preserving_proto_field_name=True)
        except ImportError:
            # フォールバック: 手動変換
            return self._manual_protobuf_to_dict(protobuf_obj)

    def _manual_protobuf_to_dict(self, protobuf_obj: Any) -> dict[str, Any]:
        """手動でProtobufオブジェクトを辞書に変換"""
        result = {}
        for field, value in protobuf_obj.ListFields():
            if field.label == field.LABEL_REPEATED:
                result[field.name] = list(value)
            elif hasattr(value, "ListFields"):  # ネストしたメッセージ
                result[field.name] = self._manual_protobuf_to_dict(value)
            else:
                result[field.name] = value
        return result

    def _transform_data_fields(
        self, decoded_data: dict[str, Any], header_info: dict[str, Any]
    ) -> dict[str, Any]:
        """Home Assistant用のフィールド変換"""
        cmd_func = header_info.get("cmdFunc", 0)
        cmd_id = header_info.get("cmdId", 0)

        if cmd_func == 254 and cmd_id == 21:
            return self._transform_display_property(decoded_data)
        elif cmd_func == 32 and cmd_id == 2:
            return self._transform_cms_bms_summary(decoded_data)
        elif cmd_func == 32 and cmd_id == 50:
            return self._transform_bms_detailed(decoded_data)
        elif cmd_func == 254 and cmd_id == 22:
            return self._transform_runtime_property(decoded_data)
        else:
            return decoded_data

    def _transform_display_property(self, data: dict[str, Any]) -> dict[str, Any]:
        """DisplayPropertyUpload のフィールド変換"""
        result = {}

        # 基本電力情報
        if "powOutSumW" in data:
            result["pow_out_sum_w"] = data["powOutSumW"]
        if "powGetAcHvOut" in data:
            result["pow_get_ac_hv_out"] = data["powGetAcHvOut"]
        if "powGetBms" in data:
            result["pow_get_bms"] = data["powGetBms"]

        # 充電時間情報
        if "bmsChgRemTime" in data:
            result["bms_chg_rem_time"] = data["bmsChgRemTime"]
        if "cmsChgRemTime" in data:
            result["cms_chg_rem_time"] = data["cmsChgRemTime"]

        return result

    def _transform_cms_bms_summary(self, data: dict[str, Any]) -> dict[str, Any]:
        """cmdFunc32_cmdId2_Report のフィールド変換"""
        result = {}

        # msg32_2_1 からの主要データ抽出
        if "msg32_2_1" in data:
            msg1 = data["msg32_2_1"]

            if "volt4" in msg1:
                result["cms_batt_vol"] = msg1["volt4"]
            if "soc15" in msg1:
                result["cms_batt_soc"] = msg1["soc15"]
            if "maxChargeSoc7" in msg1:
                result["cms_max_chg_soc"] = msg1["maxChargeSoc7"]

        return result

    def _transform_bms_detailed(self, data: dict[str, Any]) -> dict[str, Any]:
        """cmdFunc50_cmdId30_Report のフィールド変換"""
        result = {}

        # BMS基本情報
        if "unknown7" in data:
            result["bms_batt_vol"] = data["unknown7"]
        if "unknown25" in data:
            result["bms_batt_soc"] = data["unknown25"]
        if "maxCellVol16" in data:
            result["bms_max_cell_vol"] = data["maxCellVol16"]
        if "cellVol33" in data:
            result["cell_vol"] = data["cellVol33"]

        return result

    def _transform_runtime_property(self, data: dict[str, Any]) -> dict[str, Any]:
        """RuntimePropertyUpload のフィールド変換"""
        # 基本的にはそのまま返す（必要に応じて変換ロジックを追加）
        return data


def create_processor() -> DeltaPro3PrepareDataProcessor:
    """プロセッサーインスタンスを作成"""
    return DeltaPro3PrepareDataProcessor()
