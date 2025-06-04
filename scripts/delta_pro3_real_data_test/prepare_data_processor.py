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
        Returns:
            dict: {"all_fields": MessageToDict全フィールド, "unknown_fields": unknown系のみ, "ha_fields": Home Assistant用変換済み}
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

            # 6. unknown系フィールド抽出
            unknown_fields = self._extract_unknown_fields(decoded_data)

            self.logger.info(
                f"Successfully processed data: {len(transformed_data)} fields"
            )
            return {
                "all_fields": decoded_data,
                "unknown_fields": unknown_fields,
                "ha_fields": transformed_data,
            }

        except Exception as e:
            self.logger.error(f"Data processing failed: {e}", exc_info=True)
            return {}

    def _decode_header_message(self, raw_data: bytes) -> dict[str, Any] | None:
        """setMessage経由でHeaderMessageをデコードしてヘッダー情報を抽出"""
        try:
            # Base64デコードを試行
            import base64

            try:
                decoded_payload = base64.b64decode(raw_data, validate=True)
                self.logger.debug("Base64 decode successful")
                raw_data = decoded_payload
            except Exception:
                self.logger.debug("Data is not Base64 encoded, using as-is")

            # まずHeaderMessageとしてデコードを試行 (これが主要なパス)
            header_info = self._try_decode_as_headermessage(raw_data)
            if header_info:
                return header_info

            # HeaderMessageで失敗した場合、setMessageとしてデコードを試行
            header_info = self._try_decode_as_setmessage(raw_data)
            if header_info:
                return header_info

            # 両方失敗した場合、詳細ログを出力
            self.logger.error(
                f"Failed to decode data as both setMessage and HeaderMessage. Data length: {len(raw_data)}"
            )
            self.logger.error(
                f"First 32 bytes: {raw_data[:32].hex() if len(raw_data) >= 32 else raw_data.hex()}"
            )
            return None

        except Exception as e:
            self.logger.error(f"Header message decode error: {e}", exc_info=True)
            return None

    def _try_decode_as_setmessage(self, raw_data: bytes) -> dict[str, Any] | None:
        """setMessage型としてデコードを試行"""
        try:
            # setMessageとしてデコード
            set_msg = pb2.setMessage()
            set_msg.ParseFromString(raw_data)

            if not hasattr(set_msg, "header") or not set_msg.header:
                self.logger.debug("No header found in setMessage")
                return None

            header = set_msg.header
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
                f"setMessage decoded: cmdFunc={header_info['cmdFunc']}, cmdId={header_info['cmdId']}"
            )
            return header_info

        except Exception as e:
            self.logger.debug(f"setMessage decode failed: {e}")
            return None

    def _try_decode_as_headermessage(self, raw_data: bytes) -> dict[str, Any] | None:
        """HeaderMessage型としてデコードを試行（フォールバック）"""
        try:
            # HeaderMessageとしてデコード
            header_msg = pb2.HeaderMessage()
            header_msg.ParseFromString(raw_data)

            if not header_msg.header:
                self.logger.debug("No headers found in HeaderMessage")
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
                f"HeaderMessage decoded: cmdFunc={header_info['cmdFunc']}, cmdId={header_info['cmdId']}"
            )
            return header_info

        except Exception as e:
            self.logger.debug(f"HeaderMessage decode failed: {e}")
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
                # RuntimePropertyUpload (based on successful decode test)
                msg = pb2.RuntimePropertyUpload()
                msg.ParseFromString(pdata)
                return self._protobuf_to_dict(msg)

            elif cmd_func == 254 and cmd_id == 22:
                # RuntimePropertyUpload (need to verify correct message type)
                msg = pb2.RuntimePropertyUpload()
                msg.ParseFromString(pdata)
                return self._protobuf_to_dict(msg)

            else:
                self.logger.warning(
                    f"Unknown message type: cmdFunc={cmd_func}, cmdId={cmd_id}"
                )
                return {}

        except Exception as e:
            self.logger.error(
                f"Message decode error for cmdFunc={cmd_func}, cmdId={cmd_id}: {e}"
            )
            self.logger.debug(
                f"Pdata length: {len(pdata)}, first 32 bytes: {pdata[:32].hex() if len(pdata) >= 32 else pdata.hex()}"
            )
            return {}

    def _protobuf_to_dict(self, protobuf_obj: Any) -> dict[str, Any]:
        """Protobufオブジェクトを辞書に変換"""
        try:
            from google.protobuf.json_format import MessageToDict

            result = MessageToDict(protobuf_obj, preserving_proto_field_name=True)
            self.logger.debug(f"MessageToDict result: {len(result)} fields")

            def _log_fields(d, prefix=""):  # 再帰的にネストも出力
                for k, v in d.items():
                    if isinstance(v, dict):
                        self.logger.debug(f"{prefix}{k}: <dict> ({type(v).__name__})")
                        _log_fields(v, prefix=prefix + k + ".")
                    elif isinstance(v, list):
                        self.logger.debug(
                            f"{prefix}{k}: <list, len={len(v)}> ({type(v).__name__})"
                        )
                        for idx, item in enumerate(v):
                            if isinstance(item, dict):
                                self.logger.debug(f"{prefix}{k}[{idx}]: <dict>")
                                _log_fields(item, prefix=f"{prefix}{k}[{idx}].")
                            else:
                                self.logger.debug(
                                    f"{prefix}{k}[{idx}]: {item} ({type(item).__name__})"
                                )
                    else:
                        self.logger.debug(f"{prefix}{k}: {v} ({type(v).__name__})")

            _log_fields(result)
            return result
        except ImportError:
            # フォールバック: 手動変換
            result = self._manual_protobuf_to_dict(protobuf_obj)
            self.logger.debug(f"Manual conversion result: {len(result)} fields")
            return result

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

        self.logger.debug(f"Transform data for cmdFunc={cmd_func}, cmdId={cmd_id}")
        self.logger.debug(f"Available fields: {list(decoded_data.keys())}")

        if cmd_func == 254 and cmd_id == 21:
            return self._transform_display_property(decoded_data)
        elif cmd_func == 32 and cmd_id == 2:
            return self._transform_cms_bms_summary(decoded_data)
        elif cmd_func == 32 and cmd_id == 50:
            return self._transform_bms_detailed(decoded_data)
        elif cmd_func == 254 and cmd_id == 22:
            return self._transform_runtime_property(decoded_data)
        else:
            self.logger.debug("No specific transform, returning raw data")
            return decoded_data

    def _transform_display_property(self, data: dict[str, Any]) -> dict[str, Any]:
        """DisplayPropertyUpload のフィールド変換: 主要フィールドをリネーム・型/単位変換して抽出"""
        result = {}
        if "pow_out_sum_w" in data:
            result["pow_out_sum_w"] = data["pow_out_sum_w"]
        if "pow_get_ac_hv_out" in data:
            result["pow_get_ac_hv_out"] = data["pow_get_ac_hv_out"]
        if "pow_get_bms" in data:
            result["pow_get_bms"] = data["pow_get_bms"]
        if "bms_chg_rem_time" in data:
            result["bms_chg_rem_time_min"] = data["bms_chg_rem_time"]
        if "cms_chg_rem_time" in data:
            result["cms_chg_rem_time_min"] = data["cms_chg_rem_time"]
        if "bms_min_mos_temp" in data:
            result["bms_min_mos_temp_c"] = data["bms_min_mos_temp"]
        # unknown系もflat出力
        for k, v in data.items():
            if k.startswith("unknown") and k not in result:
                result[k] = v
        return result

    def _transform_cms_bms_summary(self, data: dict[str, Any]) -> dict[str, Any]:
        """cmdFunc32_cmdId2_Report のフィールド変換: msg32_2_1, msg32_2_2配下の全フィールドをflat dictで出力し、主要フィールドはリネーム・型/単位変換して抽出"""
        result = {}
        # msg32_2_1配下の全フィールドをflat化
        if "msg32_2_1" in data and isinstance(data["msg32_2_1"], dict):
            d1 = data["msg32_2_1"]
            # 主要フィールドのリネーム・型変換
            if "cms_batt_vol_mv" in d1:
                result["cms_batt_vol_v"] = d1["cms_batt_vol_mv"] / 1000.0  # mV→V
            if "cms_batt_soc_percent" in d1:
                result["cms_batt_soc_percent"] = d1["cms_batt_soc_percent"]
            if "cms_max_chg_soc_percent" in d1:
                result["cms_max_chg_soc_percent"] = d1["cms_max_chg_soc_percent"]
            if "cms_min_dsg_soc_percent" in d1:
                result["cms_min_dsg_soc_percent"] = d1["cms_min_dsg_soc_percent"]
            if "ac_out_freq_hz_config" in d1:
                result["ac_out_freq_hz"] = d1["ac_out_freq_hz_config"]
            if "cms_chg_rem_time_min" in d1:
                result["cms_chg_rem_time_min"] = d1["cms_chg_rem_time_min"]
            if "cms_dsg_rem_time_min" in d1:
                result["cms_dsg_rem_time_min"] = d1["cms_dsg_rem_time_min"]
            if "cms_chg_dsg_state" in d1:
                result["cms_chg_dsg_state"] = d1["cms_chg_dsg_state"]
            if "bms_is_conn_state" in d1:
                result["bms_is_conn_state"] = d1["bms_is_conn_state"]
            if "cms_oil_off_soc_percent" in d1:
                result["cms_oil_off_soc_percent"] = d1["cms_oil_off_soc_percent"]
            # unknown系もflat出力
            for k, v in d1.items():
                if k.startswith("unknown") and f"msg32_2_1.{k}" not in result:
                    result[f"msg32_2_1.{k}"] = v
        # msg32_2_2配下の全フィールドをflat化
        if "msg32_2_2" in data and isinstance(data["msg32_2_2"], dict):
            d2 = data["msg32_2_2"]
            for k, v in d2.items():
                result[f"msg32_2_2.{k}"] = v
        return result

    def _transform_bms_detailed(self, data: dict[str, Any]) -> dict[str, Any]:
        """cmdFunc50_cmdId30_Report (BMS詳細ランタイム) のフィールド変換: 主要フィールドをリネーム・型/単位変換して抽出"""
        result = {}
        # 主要フィールド例
        if "bms_batt_vol" in data:
            result["bms_batt_vol_v"] = data["bms_batt_vol"] / 1000.0  # mV→V
        if "bms_batt_amp" in data:
            result["bms_batt_amp_a"] = data["bms_batt_amp"] / 1000.0  # mA→A
        if "bms_batt_soc_percent_float1" in data:
            result["bms_batt_soc_percent"] = data["bms_batt_soc_percent_float1"]
        if "bms_batt_soh_percent_float" in data:
            result["bms_batt_soh_percent"] = data["bms_batt_soh_percent_float"]
        if "bms_chg_rem_time_min" in data:
            result["bms_chg_rem_time_min"] = data["bms_chg_rem_time_min"]
        if "bms_dsg_rem_time_min" in data:
            result["bms_dsg_rem_time_min"] = data["bms_dsg_rem_time_min"]
        if "cell_vol_mv" in data:
            result["cell_vol_v_array"] = [v / 1000.0 for v in data["cell_vol_mv"]]
        if "cell_temp_c" in data:
            result["cell_temp_c_array"] = data["cell_temp_c"]
        # unknown系もflat出力
        for k, v in data.items():
            if k.startswith("unknown") and k not in result:
                result[k] = v
        return result

    def _transform_runtime_property(self, data: dict[str, Any]) -> dict[str, Any]:
        """RuntimePropertyUpload のフィールド変換"""
        # 基本的にはそのまま返す（必要に応じて変換ロジックを追加）
        return data

    def _extract_unknown_fields(self, decoded_data: dict[str, Any]) -> dict[str, Any]:
        """unknown, 未定義, unknownXX_s1/s2 などを抽出"""
        result = {}

        def _recurse(d, prefix=""):
            for k, v in d.items():
                if "unknown" in k:
                    result[prefix + k] = v
                elif isinstance(v, dict):
                    _recurse(v, prefix + k + ".")

        _recurse(decoded_data)
        return result


def create_processor() -> DeltaPro3PrepareDataProcessor:
    """プロセッサーインスタンスを作成"""
    return DeltaPro3PrepareDataProcessor()
