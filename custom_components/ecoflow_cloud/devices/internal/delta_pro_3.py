import logging
from typing import Any

from custom_components.ecoflow_cloud.api import EcoflowApiClient
from custom_components.ecoflow_cloud.devices import BaseDevice, const
from custom_components.ecoflow_cloud.devices.internal.proto import (
    ef_dp3_iobroker_pb2 as pb2,
)
from custom_components.ecoflow_cloud.entities import (
    BaseNumberEntity,
    BaseSelectEntity,
    BaseSensorEntity,
    BaseSwitchEntity,
)
from custom_components.ecoflow_cloud.number import (
    ChargingPowerEntity,
    MaxBatteryLevelEntity,
    MinBatteryLevelEntity,
)
from custom_components.ecoflow_cloud.select import (
    DictSelectEntity,
    TimeoutDictSelectEntity,
)
from custom_components.ecoflow_cloud.sensor import (
    AmpSensorEntity,
    CapacitySensorEntity,
    CyclesSensorEntity,
    InAmpSolarSensorEntity,
    InEnergySensorEntity,
    InMilliVoltSensorEntity,
    InVoltSolarSensorEntity,
    InWattsSensorEntity,
    InWattsSolarSensorEntity,
    LevelSensorEntity,
    MilliVoltSensorEntity,
    OutEnergySensorEntity,
    OutMilliVoltSensorEntity,
    OutVoltDcSensorEntity,
    OutWattsDcSensorEntity,
    OutWattsSensorEntity,
    QuotaStatusSensorEntity,
    RemainSensorEntity,
    TempSensorEntity,
    WattsSensorEntity,
)
from custom_components.ecoflow_cloud.switch import BeeperEntity, EnabledEntity


class DeltaPro3(BaseDevice):
    def sensors(self, client: EcoflowApiClient) -> list[BaseSensorEntity]:
        return [
            # Main Battery System - using actual protobuf field names
            LevelSensorEntity(client, self, "bms_batt_soc", const.MAIN_BATTERY_LEVEL)
            .attr("bms_design_cap", const.ATTR_DESIGN_CAPACITY, 0)
            .attr("bms_full_cap_mah", const.ATTR_FULL_CAPACITY, 0)
            .attr("bms_remain_cap_mah", const.ATTR_REMAIN_CAPACITY, 0),
            CapacitySensorEntity(
                client, self, "bms_design_cap", const.MAIN_DESIGN_CAPACITY, False
            ),
            CapacitySensorEntity(
                client, self, "bms_full_cap_mah", const.MAIN_FULL_CAPACITY, False
            ),
            CapacitySensorEntity(
                client, self, "bms_remain_cap_mah", const.MAIN_REMAIN_CAPACITY, False
            ),
            LevelSensorEntity(client, self, "bms_batt_soh", const.SOH),
            CyclesSensorEntity(client, self, "bms_cycles", const.CYCLES),
            # Battery Voltage and Current
            MilliVoltSensorEntity(
                client, self, "bms_batt_vol", const.BATTERY_VOLT, False
            )
            .attr("bms_min_cell_vol", const.ATTR_MIN_CELL_VOLT, 0)
            .attr("bms_max_cell_vol", const.ATTR_MAX_CELL_VOLT, 0),
            MilliVoltSensorEntity(
                client, self, "bms_min_cell_vol", const.MIN_CELL_VOLT, False
            ),
            MilliVoltSensorEntity(
                client, self, "bms_max_cell_vol", const.MAX_CELL_VOLT, False
            ),
            AmpSensorEntity(
                client, self, "bms_batt_amp", const.MAIN_BATTERY_CURRENT, False
            ),
            # Battery Temperature
            TempSensorEntity(
                client, self, "bms_max_cell_temp", const.MAX_CELL_TEMP, False
            ),
            TempSensorEntity(
                client, self, "bms_min_cell_temp", const.MIN_CELL_TEMP, False
            ),
            TempSensorEntity(client, self, "bms_max_mos_temp", const.BATTERY_TEMP)
            .attr("bms_min_cell_temp", const.ATTR_MIN_CELL_TEMP, 0)
            .attr("bms_max_cell_temp", const.ATTR_MAX_CELL_TEMP, 0),
            # Charge/Discharge Times
            RemainSensorEntity(
                client, self, "bms_chg_rem_time", const.CHARGE_REMAINING_TIME
            ),
            RemainSensorEntity(
                client, self, "bms_dsg_rem_time", const.DISCHARGE_REMAINING_TIME
            ),
            # Combined System Status
            LevelSensorEntity(
                client, self, "cms_batt_soc", const.COMBINED_BATTERY_LEVEL
            ),
            # Power Input/Output - using correct protobuf field names
            OutWattsSensorEntity(client, self, "pow_out_sum_w", const.TOTAL_OUT_POWER),
            InWattsSensorEntity(client, self, "pow_in_sum_w", const.TOTAL_IN_POWER),
            # AC Power System
            InWattsSensorEntity(client, self, "pow_get_ac_in", const.AC_IN_POWER),
            OutWattsSensorEntity(client, self, "pow_get_ac", const.AC_OUT_POWER),
            OutWattsSensorEntity(
                client, self, "pow_get_ac_hv_out", "AC HV Output Power"
            ),
            OutWattsSensorEntity(
                client, self, "pow_get_ac_lv_out", "AC LV Output Power"
            ),
            # AC Input Voltage/Current
            InMilliVoltSensorEntity(
                client, self, "plug_in_info_ac_in_vol", const.AC_IN_VOLT
            ),
            InAmpSolarSensorEntity(
                client, self, "plug_in_info_ac_in_amp", "AC Input Current"
            ),
            # DC Power System
            OutWattsDcSensorEntity(client, self, "pow_get_12v", "12V DC Output Power"),
            OutWattsDcSensorEntity(client, self, "pow_get_24v", "24V DC Output Power"),
            OutVoltDcSensorEntity(
                client, self, "pow_get_12v_vol", "12V DC Output Voltage"
            ),
            OutVoltDcSensorEntity(
                client, self, "pow_get_24v_vol", "24V DC Output Voltage"
            ),
            # Solar Input
            InWattsSolarSensorEntity(
                client, self, "pow_get_pv_h", "Solar High Voltage Input Power"
            ),
            InWattsSolarSensorEntity(
                client, self, "pow_get_pv_l", "Solar Low Voltage Input Power"
            ),
            InVoltSolarSensorEntity(
                client, self, "pow_get_pv_h_vol", "Solar HV Input Voltage"
            ),
            InVoltSolarSensorEntity(
                client, self, "pow_get_pv_l_vol", "Solar LV Input Voltage"
            ),
            InAmpSolarSensorEntity(
                client, self, "pow_get_pv_h_amp", "Solar HV Input Current"
            ),
            InAmpSolarSensorEntity(
                client, self, "pow_get_pv_l_amp", "Solar LV Input Current"
            ),
            # USB Ports
            OutWattsSensorEntity(
                client, self, "pow_get_qcusb1", const.USB_QC_1_OUT_POWER
            ),
            OutWattsSensorEntity(
                client, self, "pow_get_qcusb2", const.USB_QC_2_OUT_POWER
            ),
            OutWattsSensorEntity(
                client, self, "pow_get_typec1", const.TYPEC_1_OUT_POWER
            ),
            OutWattsSensorEntity(
                client, self, "pow_get_typec2", const.TYPEC_2_OUT_POWER
            ),
            # Power I/O and Extra Battery Ports
            OutWattsDcSensorEntity(
                client, self, "pow_get_5p8", "5P8 Power I/O Port Power"
            ),
            OutWattsDcSensorEntity(
                client, self, "pow_get_4p8_1", "4P8 Extra Battery Port 1 Power"
            ),
            OutWattsDcSensorEntity(
                client, self, "pow_get_4p8_2", "4P8 Extra Battery Port 2 Power"
            ),
            # System Frequencies
            OutWattsSensorEntity(client, self, "ac_out_freq", "AC Output Frequency"),
            # Power Management Status
            LevelSensorEntity(
                client, self, "cms_max_chg_soc", "Max Charge SOC Setting"
            ),
            LevelSensorEntity(
                client, self, "cms_min_dsg_soc", "Min Discharge SOC Setting"
            ),
            # Energy Counters
            InEnergySensorEntity(
                client, self, "pow_in_sum_energy", "Total Input Energy"
            ),
            OutEnergySensorEntity(
                client, self, "pow_out_sum_energy", "Total Output Energy"
            ),
            InEnergySensorEntity(
                client, self, "ac_in_energy_total", const.CHARGE_AC_ENERGY
            ),
            OutEnergySensorEntity(
                client, self, "ac_out_energy_total", const.DISCHARGE_AC_ENERGY
            ),
            InEnergySensorEntity(
                client, self, "pv_in_energy_total", const.SOLAR_IN_ENERGY
            ),
            OutEnergySensorEntity(
                client, self, "dc_out_energy_total", const.DISCHARGE_DC_ENERGY
            ),
            QuotaStatusSensorEntity(client, self),
        ]

    def numbers(self, client: EcoflowApiClient) -> list[BaseNumberEntity]:
        return [
            # Battery Management
            MaxBatteryLevelEntity(
                client,
                self,
                "cms_max_chg_soc",
                const.MAX_CHARGE_LEVEL,
                50,
                100,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 49, "cmsMaxChgSoc": value},
                },
            ),
            MinBatteryLevelEntity(
                client,
                self,
                "cms_min_dsg_soc",
                const.MIN_DISCHARGE_LEVEL,
                0,
                30,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 51, "cmsMinDsgSoc": value},
                },
            ),
            # AC Charging Power
            ChargingPowerEntity(
                client,
                self,
                "plug_in_info_ac_in_chg_pow_max",
                const.AC_CHARGING_POWER,
                200,
                3000,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 69, "plugInInfoAcInChgPowMax": value},
                },
            ),
        ]

    def switches(self, client: EcoflowApiClient) -> list[BaseSwitchEntity]:
        return [
            # Audio Control
            BeeperEntity(
                client,
                self,
                "en_beep",
                const.BEEPER,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 38, "enBeep": value},
                },
            ),
            # AC Output Control
            EnabledEntity(
                client,
                self,
                "cfg_hv_ac_out_open",
                "AC HV Output Enabled",
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 66, "cfgHvAcOutOpen": value},
                },
            ),
            EnabledEntity(
                client,
                self,
                "cfg_lv_ac_out_open",
                "AC LV Output Enabled",
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 66, "cfgLvAcOutOpen": value},
                },
            ),
            # DC Output Control
            EnabledEntity(
                client,
                self,
                "cfg_dc_12v_out_open",
                "12V DC Output Enabled",
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 81, "cfgDc12vOutOpen": value},
                },
            ),
            EnabledEntity(
                client,
                self,
                "cfg_dc_24v_out_open",
                "24V DC Output Enabled",
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 81, "cfgDc24vOutOpen": value},
                },
            ),
            # Xboost Control
            EnabledEntity(
                client,
                self,
                "xboost_en",
                const.XBOOST_ENABLED,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 66, "xboostEn": value},
                },
            ),
            # Energy Saving
            EnabledEntity(
                client,
                self,
                "ac_energy_saving_open",
                "AC Energy Saving Enabled",
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 95, "acEnergySavingOpen": value},
                },
            ),
            # GFCI Control
            EnabledEntity(
                client,
                self,
                "llc_gfci_flag",
                "GFCI Protection Enabled",
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"id": 153, "llcGFCIFlag": value},
                },
            ),
        ]

    def selects(self, client: EcoflowApiClient) -> list[BaseSelectEntity]:
        return [
            # Screen Timeout
            TimeoutDictSelectEntity(
                client,
                self,
                "screen_off_time",
                const.SCREEN_TIMEOUT,
                const.SCREEN_TIMEOUT_OPTIONS,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"screenOffTime": value, "id": 39},
                },
            ),
            # AC Standby Timeout
            TimeoutDictSelectEntity(
                client,
                self,
                "ac_standby_time",
                const.AC_TIMEOUT,
                const.AC_TIMEOUT_OPTIONS,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"acStandbyTime": value, "id": 153},
                },
            ),
            # DC Standby Timeout
            TimeoutDictSelectEntity(
                client,
                self,
                "dc_standby_time",
                "DC Timeout",
                const.UNIT_TIMEOUT_OPTIONS_LIMITED,
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"dcStandbyTime": value, "id": 33},
                },
            ),
            # AC Output Type
            DictSelectEntity(
                client,
                self,
                "plug_in_info_ac_out_type",
                "AC Output Type",
                {"HV+LV": 0, "HV Only": 1, "LV Only": 2},
                lambda value: {
                    "moduleType": 0,
                    "operateType": "TCP",
                    "params": {"plugInInfoAcOutType": int(value), "id": 153},
                },
            ),
        ]

    def _prepare_data(self, raw_data: bytes) -> dict[str, Any]:
        """
        Delta Pro 3専用のデータ準備メソッド
        Protobufバイナリデータをデコードして辞書形式に変換
        """
        _LOGGER = logging.getLogger(__name__)
        
        try:
            _LOGGER.debug(f"Processing {len(raw_data)} bytes of raw data")

            # 1. HeaderMessageのデコード
            header_info = self._decode_header_message(raw_data)
            if not header_info:
                _LOGGER.warning("HeaderMessage decoding failed")
                return {}

            # 2. ペイロードデータの抽出
            pdata = self._extract_payload_data(header_info.get("header_obj"))
            if not pdata:
                _LOGGER.warning("No payload data found")
                return {}

            # 3. XORデコード (必要に応じて)
            decoded_pdata = self._perform_xor_decode(pdata, header_info)

            # 4. Protobufメッセージのデコード
            decoded_data = self._decode_message_by_type(decoded_pdata, header_info)
            if not decoded_data:
                _LOGGER.warning("Message decoding failed")
                return {}

            # 5. HAフィールド形式への変換
            transformed_data = self._transform_data_fields(decoded_data, header_info)

            _LOGGER.debug(f"Successfully processed data: {len(transformed_data)} fields")
            return transformed_data

        except Exception as e:
            _LOGGER.error(f"Data processing failed: {e}", exc_info=True)
            return {}

    def _decode_header_message(self, raw_data: bytes) -> dict[str, Any] | None:
        """HeaderMessageをデコードしてヘッダー情報を抽出"""
        _LOGGER = logging.getLogger(__name__)
        
        try:
            # Base64デコードを試行
            import base64

            try:
                decoded_payload = base64.b64decode(raw_data, validate=True)
                _LOGGER.debug("Base64 decode successful")
                raw_data = decoded_payload
            except Exception:
                _LOGGER.debug("Data is not Base64 encoded, using as-is")

            # HeaderMessageとしてデコードを試行
            header_msg = pb2.HeaderMessage()
            header_msg.ParseFromString(raw_data)

            if not header_msg.header:
                _LOGGER.debug("No headers found in HeaderMessage")
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

            _LOGGER.debug(f"Header decoded: cmdFunc={header_info['cmdFunc']}, cmdId={header_info['cmdId']}")
            return header_info

        except Exception as e:
            _LOGGER.debug(f"HeaderMessage decode failed: {e}")
            return None

    def _extract_payload_data(self, header_obj: Any) -> bytes | None:
        """ヘッダーからペイロードデータを抽出"""
        _LOGGER = logging.getLogger(__name__)
        
        try:
            pdata = getattr(header_obj, "pdata", b"")
            if pdata:
                _LOGGER.debug(f"Extracted {len(pdata)} bytes of payload data")
                return pdata
            else:
                _LOGGER.warning("No pdata found in header")
                return None
        except Exception as e:
            _LOGGER.error(f"Payload extraction error: {e}")
            return None

    def _perform_xor_decode(self, pdata: bytes, header_info: dict[str, Any]) -> bytes:
        """必要に応じてXORデコードを実行"""
        _LOGGER = logging.getLogger(__name__)
        
        enc_type = header_info.get("encType", 0)
        src = header_info.get("src", 0)
        seq = header_info.get("seq", 0)

        # XOR decode condition: enc_type == 1 and src != 32
        if enc_type == 1 and src != 32:
            _LOGGER.debug(f"Performing XOR decode with seq={seq}")
            return self._xor_decode_pdata(pdata, seq)
        else:
            _LOGGER.debug("No XOR decoding needed")
            return pdata

    def _xor_decode_pdata(self, pdata: bytes, seq: int) -> bytes:
        """XORデコード処理"""
        if not pdata:
            return b""

        decoded_payload = bytearray()
        for byte_val in pdata:
            decoded_payload.append((byte_val ^ seq) & 0xFF)

        return bytes(decoded_payload)

    def _decode_message_by_type(self, pdata: bytes, header_info: dict[str, Any]) -> dict[str, Any]:
        """cmdFunc/cmdIdに基づいてProtobufメッセージをデコード"""
        _LOGGER = logging.getLogger(__name__)
        
        cmd_func = header_info.get("cmdFunc", 0)
        cmd_id = header_info.get("cmdId", 0)

        try:
            _LOGGER.debug(f"Decoding message: cmdFunc={cmd_func}, cmdId={cmd_id}")

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
                # RuntimePropertyUpload
                msg = pb2.RuntimePropertyUpload()
                msg.ParseFromString(pdata)
                return self._protobuf_to_dict(msg)

            else:
                _LOGGER.warning(f"Unknown message type: cmdFunc={cmd_func}, cmdId={cmd_id}")
                return {}

        except Exception as e:
            _LOGGER.error(f"Message decode error for cmdFunc={cmd_func}, cmdId={cmd_id}: {e}")
            return {}

    def _protobuf_to_dict(self, protobuf_obj: Any) -> dict[str, Any]:
        """Protobufオブジェクトを辞書に変換"""
        _LOGGER = logging.getLogger(__name__)
        
        try:
            from google.protobuf.json_format import MessageToDict
            result = MessageToDict(protobuf_obj, preserving_proto_field_name=True)
            _LOGGER.debug(f"MessageToDict result: {len(result)} fields")
            return result
        except ImportError:
            # フォールバック: 手動変換
            result = self._manual_protobuf_to_dict(protobuf_obj)
            _LOGGER.debug(f"Manual conversion result: {len(result)} fields")
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

    def _transform_data_fields(self, decoded_data: dict[str, Any], header_info: dict[str, Any]) -> dict[str, Any]:
        """Home Assistant用のフィールド変換"""
        _LOGGER = logging.getLogger(__name__)
        
        cmd_func = header_info.get("cmdFunc", 0)
        cmd_id = header_info.get("cmdId", 0)
        
        _LOGGER.debug(f"Transform data for cmdFunc={cmd_func}, cmdId={cmd_id}")

        if cmd_func == 254 and cmd_id == 21:
            return self._transform_display_property(decoded_data)
        elif cmd_func == 32 and cmd_id == 2:
            return self._transform_cms_bms_summary(decoded_data)
        elif cmd_func == 32 and cmd_id == 50:
            return self._transform_runtime_property(decoded_data)
        else:
            _LOGGER.debug("No specific transform, returning raw data")
            return decoded_data

    def _transform_display_property(self, data: dict[str, Any]) -> dict[str, Any]:
        """DisplayPropertyUpload のフィールド変換"""
        result = {}

        # 基本電力情報 (フィールド名はすでにsnake_case)
        if "pow_out_sum_w" in data:
            result["pow_out_sum_w"] = data["pow_out_sum_w"]
        if "pow_get_ac_hv_out" in data:
            result["pow_get_ac_hv_out"] = data["pow_get_ac_hv_out"]
        if "pow_get_bms" in data:
            result["pow_get_bms"] = data["pow_get_bms"]

        # 充電時間情報
        if "bms_chg_rem_time" in data:
            result["bms_chg_rem_time"] = data["bms_chg_rem_time"]
        if "cms_chg_rem_time" in data:
            result["cms_chg_rem_time"] = data["cms_chg_rem_time"]
            
        # その他のフィールド
        if "bms_min_mos_temp" in data:
            result["bms_min_mos_temp"] = data["bms_min_mos_temp"]

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

        return result

    def _transform_runtime_property(self, data: dict[str, Any]) -> dict[str, Any]:
        """RuntimePropertyUpload のフィールド変換 (cmdFunc=32, cmdId=50)"""
        result = {}

        # RuntimePropertyUpload のフィールドを直接マップ
        if "ac_phase_type" in data:
            result["ac_phase_type"] = data["ac_phase_type"]
        if "pcs_work_mode" in data:
            result["pcs_work_mode"] = data["pcs_work_mode"]
        if "plug_in_info_pv_l_vol" in data:
            result["plug_in_info_pv_l_vol"] = data["plug_in_info_pv_l_vol"]
        if "temp_pcs_dc" in data:
            result["temp_pcs_dc"] = data["temp_pcs_dc"]
        if "temp_pcs_ac" in data:
            result["temp_pcs_ac"] = data["temp_pcs_ac"]
        if "bms_batt_vol" in data:
            result["bms_batt_vol"] = data["bms_batt_vol"]
        if "bms_batt_amp" in data:
            result["bms_batt_amp"] = data["bms_batt_amp"]
        if "bms_remain_cap" in data:
            result["bms_remain_cap"] = data["bms_remain_cap"]
        if "bms_full_cap" in data:
            result["bms_full_cap"] = data["bms_full_cap"]

        return result
