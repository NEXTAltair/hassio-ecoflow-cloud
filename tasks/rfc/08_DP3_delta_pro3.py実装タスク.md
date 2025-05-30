# DP3 delta_pro3.py 実装タスク

## 1. 概要

Delta Pro 3 用のメインデバイスクラス `DeltaPro3` を実装する。
このクラスは、XOR デコード処理、Protobuf パース、Home Assistant エンティティ生成を統合し、DP3 の完全な Home Assistant 統合を実現する。

## 2. 前提条件

### **依存コンポーネント**

- [ ] **XOR デコード実装**: `DP3_XORデコード実装タスク.md` 完了
- [ ] **Protobuf スキーマ**: `DP3_Protobufスキーマ解析作成タスク.md` 完了
- [ ] **既存構造理解**: `DeltaPro_Delta2Max_定義構造調査タスク.md` 完了

### **技術要件**

- [ ] **Python 3.8+**: 型ヒント、async/await 対応
- [ ] **Home Assistant Core**: BaseDevice 継承
- [ ] **Protobuf**: delta_pro3_pb2.py 生成済み

## 3. Phase 1: クラス基本構造実装

### **3.1 DeltaPro3 クラス定義**

#### **基本クラス構造**

```python
# custom_components/ecoflow_cloud/devices/internal/delta_pro3.py

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity

from ...api import EcoflowApiClient
from ...entities import (
    BaseSensorEntity,
    BaseNumberEntity,
    BaseSwitchEntity,
    BaseSelectEntity,
)
from . import BaseDevice
from .const import *
from .xor_decoder import DP3XORDecoder

_LOGGER = logging.getLogger(__name__)

class DeltaPro3(BaseDevice):
    """Delta Pro 3デバイスクラス"""

    def __init__(self, device_info: dict, client: EcoflowApiClient):
        super().__init__(device_info, client)

        # DP3専用XORデコーダー
        self.xor_decoder = DP3XORDecoder(
            enable_cache=True,
            enable_learning=True
        )

        # デバイス固有情報
        self.device_type = "DELTA_PRO_3"
        self.supports_heartbeat = True
        self.supports_commands = True
        # MQTT接続・切断処理、メッセージ受信コールバック登録 - 2025/05/29 完了
        # データ取得要求メッセージ送信 - 2025/05/29 完了
        # 受信メッセージの解析とデコード - 2025/05/29 完了

        _LOGGER.info(f"Initialized Delta Pro 3: {device_info.get('device_sn', 'Unknown')}")
```

#### **デバイス判定ロジック**

```python
    @classmethod
    def is_device_supported(cls, device_info: dict) -> bool:
        """
        デバイス情報からDP3対応可否を判定

        Args:
            device_info (dict): デバイス情報

        Returns:
            bool: DP3として対応可能な場合True
        """
        device_type = device_info.get("device_type", "")
        device_sn = device_info.get("device_sn", "")
        product_type = device_info.get("product_type", "")

        # DP3判定条件
        dp3_indicators = [
            "DELTA_PRO_3" in device_type.upper(),
            "DP3" in device_sn.upper(),
            product_type == "DELTA_PRO_3",
            device_sn.startswith("DP3"),
        ]

        is_supported = any(dp3_indicators)

        if is_supported:
            _LOGGER.info(f"Detected Delta Pro 3: {device_sn}")

        return is_supported
```

### **3.2 データ処理実装**

#### **\_prepare_data メソッド（XOR デコード統合）**

```python
    def _prepare_data(self, raw_data: bytes) -> Optional[dict]:
        """
        DP3専用データ準備処理（XORデコード統合）

        Args:
            raw_data (bytes): MQTTメッセージの生データ

        Returns:
            Optional[dict]: パース済みデータ
        """
        try:
            # XORデコード実行
            decode_result = self.xor_decoder.decode(raw_data)

            if not decode_result['success']:
                _LOGGER.warning(
                    f"XOR decode failed for {self.device_sn}: {decode_result.get('error')}"
                )
                return None

            # cmdIdに基づくProtobufパース
            cmd_id = decode_result['cmd_id']
            decoded_pdata = decode_result['decoded_pdata']

            _LOGGER.debug(
                f"Processing DP3 message: cmdId={cmd_id}, "
                f"method={decode_result.get('method')}, "
                f"data_length={len(decoded_pdata)}"
            )

            # cmdId別パース処理
            if cmd_id == 1:
                return self._parse_app_heartbeat(decoded_pdata)
            elif cmd_id == 2:
                return self._parse_backend_heartbeat(decoded_pdata)
            elif cmd_id == 3:
                return self._parse_app_params(decoded_pdata)
            elif cmd_id == 4:
                return self._parse_battery_pack_info(decoded_pdata)
            elif cmd_id == 32:
                return self._parse_detailed_report(decoded_pdata)
            else:
                _LOGGER.debug(f"Unknown cmdId for DP3: {cmd_id}")
                return None

        except Exception as e:
            _LOGGER.error(f"Data preparation failed for {self.device_sn}: {e}")
            return None
```

#### **Protobuf パース処理**

```python
    def _parse_app_heartbeat(self, pdata: bytes) -> Optional[dict]:
        """
        cmdId=1: アプリ表示用ハートビートのパース

        Args:
            pdata (bytes): XORデコード済みペイロード

        Returns:
            Optional[dict]: パース済みデータ
        """
        try:
            import delta_pro3_pb2

            heartbeat = delta_pro3_pb2.AppShowHeartbeatReport()
            heartbeat.ParseFromString(pdata)

            # Home Assistant用データ構造に変換
            parsed_data = {}

            # バッテリー情報
            if heartbeat.HasField('bms_status'):
                bms = heartbeat.bms_status
                parsed_data.update({
                    'bmsBattSoc': bms.soc,
                    'bmsDesignCap': bms.design_cap,
                    'bmsFullCap': bms.full_cap,
                    'bmsRemainCap': bms.remain_cap,
                    'bmsSoh': bms.soh,
                    'bmsCycles': bms.cycles,
                    'bmsTemp': bms.temp,
                    'bmsMinCellTemp': bms.min_cell_temp,
                    'bmsMaxCellTemp': bms.max_cell_temp,
                    'bmsVol': bms.vol,
                    'bmsMinCellVol': bms.min_cell_vol,
                    'bmsMaxCellVol': bms.max_cell_vol,
                    'bmsAmp': bms.amp,
                })

                if bms.HasField('f32_show_soc'):
                    parsed_data['bmsBattSocF32'] = bms.f32_show_soc

            # インバータ情報
            if heartbeat.HasField('inverter_status'):
                inv = heartbeat.inverter_status
                parsed_data.update({
                    'invInputWatts': inv.input_watts,
                    'invOutputWatts': inv.output_watts,
                    'invAcInVol': inv.ac_in_vol,
                    'invOutVol': inv.inv_out_vol,
                    'invAcInFreq': inv.ac_in_freq,
                    'invOutFreq': inv.inv_out_freq,
                    'invCfgAcEnabled': inv.cfg_ac_enabled,
                    'invCfgAcXboost': inv.cfg_ac_xboost,
                    'invCfgSlowChgWatts': inv.cfg_slow_chg_watts,
                })

            # MPPT情報
            if heartbeat.HasField('mppt_status'):
                mppt = heartbeat.mppt_status
                parsed_data.update({
                    'mpptInWatts': mppt.in_watts,
                    'mpptInVol': mppt.in_vol,
                    'mpptInAmp': mppt.in_amp,
                    'mpptOutWatts': mppt.out_watts,
                    'mpptOutVol': mppt.out_vol,
                    'mpptCarState': mppt.car_state,
                    'mpptCarOutWatts': mppt.car_out_watts,
                })

            # PD情報
            if heartbeat.HasField('pd_status'):
                pd = heartbeat.pd_status
                parsed_data.update({
                    'pdWattsInSum': pd.watts_in_sum,
                    'pdWattsOutSum': pd.watts_out_sum,
                    'pdTypec1Watts': pd.typec1_watts,
                    'pdTypec2Watts': pd.typec2_watts,
                    'pdUsb1Watts': pd.usb1_watts,
                    'pdUsb2Watts': pd.usb2_watts,
                    'pdQcUsb1Watts': pd.qc_usb1_watts,
                    'pdQcUsb2Watts': pd.qc_usb2_watts,
                    'pdBeepState': pd.beep_state,
                    'pdLcdOffSec': pd.lcd_off_sec,
                })

            _LOGGER.debug(f"Parsed app heartbeat: {len(parsed_data)} fields")
            return parsed_data

        except Exception as e:
            _LOGGER.error(f"Failed to parse app heartbeat: {e}")
            return None

    def _parse_detailed_report(self, pdata: bytes) -> Optional[dict]:
        """
        cmdId=32: DP3詳細レポートのパース

        Args:
            pdata (bytes): XORデコード済みペイロード

        Returns:
            Optional[dict]: パース済みデータ
        """
        try:
            import delta_pro3_pb2

            report = delta_pro3_pb2.DeltaPro3DetailedReport()
            report.ParseFromString(pdata)

            parsed_data = {}

            # 詳細電力・電圧情報
            if report.HasField('voltage_68'):
                parsed_data['detailAcOutVol'] = report.voltage_68
            if report.HasField('current_69'):
                parsed_data['detailAcOutAmp'] = report.current_69
            if report.HasField('voltage_149'):
                parsed_data['detailDcOutVol'] = report.voltage_149
            if report.HasField('current_150'):
                parsed_data['detailDcOutAmp'] = report.current_150
            if report.HasField('voltage_244'):
                parsed_data['detailBattVol'] = report.voltage_244
            if report.HasField('current_245'):
                parsed_data['detailBattAmp'] = report.current_245
            if report.HasField('full_capacity_247'):
                parsed_data['detailFullCap'] = report.full_capacity_247
            if report.HasField('remain_capacity_249'):
                parsed_data['detailRemainCap'] = report.remain_capacity_249
            if report.HasField('min_cell_voltage_256'):
                parsed_data['detailMinCellVol'] = report.min_cell_voltage_256
            if report.HasField('max_cell_voltage_257'):
                parsed_data['detailMaxCellVol'] = report.max_cell_voltage_257
            if report.HasField('charge_limit_337'):
                parsed_data['detailChargeLimit'] = report.charge_limit_337
            if report.HasField('mppt_power_369'):
                parsed_data['detailMpptPower'] = report.mppt_power_369
            if report.HasField('mppt_voltage_377'):
                parsed_data['detailMpptVol'] = report.mppt_voltage_377

            _LOGGER.debug(f"Parsed detailed report: {len(parsed_data)} fields")
            return parsed_data

        except Exception as e:
            _LOGGER.error(f"Failed to parse detailed report: {e}")
            return None
```

## 4. Phase 2: エンティティ生成メソッド実装

### **4.1 センサーエンティティ**

#### **sensors メソッド**

```python
    def sensors(self, client: EcoflowApiClient) -> list[BaseSensorEntity]:
        """
        DP3用センサーエンティティ生成

        Args:
            client (EcoflowApiClient): APIクライアント

        Returns:
            list[BaseSensorEntity]: センサーエンティティリスト
        """
        return [
            # バッテリー関連センサー
            BaseSensorEntity(client, self, "bmsBattSoc", MAIN_BATTERY_LEVEL, "%"),
            BaseSensorEntity(client, self, "bmsBattSocF32", MAIN_BATTERY_LEVEL_F32, "%"),
            BaseSensorEntity(client, self, "bmsDesignCap", MAIN_DESIGN_CAPACITY, "mAh",
                           attr={"design_capacity": "bmsDesignCap"}),
            BaseSensorEntity(client, self, "bmsFullCap", MAIN_FULL_CAPACITY, "mAh"),
            BaseSensorEntity(client, self, "bmsRemainCap", MAIN_REMAIN_CAPACITY, "mAh"),
            BaseSensorEntity(client, self, "bmsSoh", SOH, "%"),
            BaseSensorEntity(client, self, "bmsCycles", CYCLES, "回"),
            BaseSensorEntity(client, self, "bmsTemp", BATTERY_TEMP, "℃"),
            BaseSensorEntity(client, self, "bmsMinCellTemp", MIN_CELL_TEMP, "℃"),
            BaseSensorEntity(client, self, "bmsMaxCellTemp", MAX_CELL_TEMP, "℃"),
            BaseSensorEntity(client, self, "bmsVol", BATTERY_VOLT, "mV"),
            BaseSensorEntity(client, self, "bmsMinCellVol", MIN_CELL_VOLT, "mV"),
            BaseSensorEntity(client, self, "bmsMaxCellVol", MAX_CELL_VOLT, "mV"),
            BaseSensorEntity(client, self, "bmsAmp", MAIN_BATTERY_CURRENT, "mA"),

            # 電力関連センサー
            BaseSensorEntity(client, self, "pdWattsInSum", TOTAL_IN_POWER, "W"),
            BaseSensorEntity(client, self, "pdWattsOutSum", TOTAL_OUT_POWER, "W"),
            BaseSensorEntity(client, self, "invInputWatts", AC_IN_POWER, "W"),
            BaseSensorEntity(client, self, "invOutputWatts", AC_OUT_POWER, "W"),
            BaseSensorEntity(client, self, "invAcInVol", AC_IN_VOLT, "mV"),
            BaseSensorEntity(client, self, "invOutVol", AC_OUT_VOLT, "mV"),

            # ソーラー関連センサー
            BaseSensorEntity(client, self, "mpptInWatts", SOLAR_IN_POWER, "W"),
            BaseSensorEntity(client, self, "mpptInVol", SOLAR_IN_VOLT, "V"),
            BaseSensorEntity(client, self, "mpptInAmp", SOLAR_IN_AMP, "A"),
            BaseSensorEntity(client, self, "mpptOutWatts", DC_OUT_POWER, "W"),
            BaseSensorEntity(client, self, "mpptOutVol", DC_OUT_VOLT, "V"),
            BaseSensorEntity(client, self, "mpptCarOutWatts", DC_CAR_OUT_POWER, "W"),

            # USB/Type-C関連センサー
            BaseSensorEntity(client, self, "pdTypec1Watts", TYPEC_1_OUT_POWER, "W"),
            BaseSensorEntity(client, self, "pdTypec2Watts", TYPEC_2_OUT_POWER, "W"),
            BaseSensorEntity(client, self, "pdUsb1Watts", USB_1_OUT_POWER, "W"),
            BaseSensorEntity(client, self, "pdUsb2Watts", USB_2_OUT_POWER, "W"),
            BaseSensorEntity(client, self, "pdQcUsb1Watts", USB_QC_1_OUT_POWER, "W"),
            BaseSensorEntity(client, self, "pdQcUsb2Watts", USB_QC_2_OUT_POWER, "W"),

            # 詳細情報センサー（cmdId=32から）
            BaseSensorEntity(client, self, "detailAcOutVol", "AC Output Voltage (Detail)", "V"),
            BaseSensorEntity(client, self, "detailAcOutAmp", "AC Output Current (Detail)", "A"),
            BaseSensorEntity(client, self, "detailDcOutVol", "DC Output Voltage (Detail)", "V"),
            BaseSensorEntity(client, self, "detailBattVol", "Battery Voltage (Detail)", "V"),
            BaseSensorEntity(client, self, "detailFullCap", "Full Capacity (Detail)", "mAh"),
            BaseSensorEntity(client, self, "detailRemainCap", "Remain Capacity (Detail)", "mAh"),
            BaseSensorEntity(client, self, "detailChargeLimit", "Charge Limit (Detail)", "%"),
            BaseSensorEntity(client, self, "detailMpptPower", "MPPT Power (Detail)", "W"),
            BaseSensorEntity(client, self, "detailMpptVol", "MPPT Voltage (Detail)", "V"),
        ]
```

### **4.2 スイッチエンティティ**

#### **switches メソッド**

```python
    def switches(self, client: EcoflowApiClient) -> list[BaseSwitchEntity]:
        """
        DP3用スイッチエンティティ生成

        Args:
            client (EcoflowApiClient): APIクライアント

        Returns:
            list[BaseSwitchEntity]: スイッチエンティティリスト
        """
        return [
            # ビープ音制御
            BaseSwitchEntity(
                client, self, "pdBeepState", BEEPER,
                lambda value, params: self._create_beep_command(value)
            ),

            # AC出力制御
            BaseSwitchEntity(
                client, self, "invCfgAcEnabled", AC_ENABLED,
                lambda value, params: self._create_ac_output_command(value)
            ),

            # X-Boost制御
            BaseSwitchEntity(
                client, self, "invCfgAcXboost", XBOOST_ENABLED,
                lambda value, params: self._create_xboost_command(value)
            ),

            # DC出力制御
            BaseSwitchEntity(
                client, self, "mpptCarState", DC_ENABLED,
                lambda value, params: self._create_dc_output_command(value)
            ),
        ]
```

## 5. Phase 3: コマンド送信実装

### **5.1 コマンド生成メソッド**

#### **基本コマンド構造**

```python
    def _create_base_command(self, cmd_func: int, cmd_id: int, params: dict) -> dict:
        """
        DP3用基本コマンド構造生成

        Args:
            cmd_func (int): コマンド機能番号
            cmd_id (int): コマンドID
            params (dict): パラメータ

        Returns:
            dict: コマンド構造
        """
        return {
            "sn": self.device_sn,
            "cmdId": cmd_id,
            "dirDest": 1,
            "dirSrc": 1,
            "cmdFunc": cmd_func,
            "dest": 2,
            "params": params
        }

    def _create_ac_output_command(self, enabled: bool) -> dict:
        """AC出力制御コマンド生成"""
        return self._create_base_command(
            cmd_func=254,
            cmd_id=17,
            params={"cfgAcEnabled": enabled}
        )

    def _create_xboost_command(self, enabled: bool) -> dict:
        """X-Boost制御コマンド生成"""
        return self._create_base_command(
            cmd_func=254,
            cmd_id=17,
            params={"cfgAcXboost": enabled}
        )

    def _create_dc_output_command(self, enabled: bool) -> dict:
        """DC出力制御コマンド生成"""
        return self._create_base_command(
            cmd_func=254,
            cmd_id=17,
            params={"cfgDcEnabled": enabled}
        )

    def _create_beep_command(self, enabled: bool) -> dict:
        """ビープ音制御コマンド生成"""
        return self._create_base_command(
            cmd_func=254,
            cmd_id=17,
            params={"cfgBeepEnabled": enabled}
        )
```

## 6. 成果物・次ステップ

### **6.1 期待される成果物**

- [ ] **DeltaPro3 クラス**: 完全なデバイスクラス実装
- [ ] **XOR デコード統合**: \_prepare_data メソッド
- [ ] **Protobuf パース**: 各 cmdId 対応
- [ ] **エンティティ生成**: sensors/switches/numbers/selects
- [ ] **コマンド送信**: 基本制御コマンド対応

### **6.2 品質基準**

- [ ] **データパース成功率**: 95%以上
- [ ] **エンティティ生成**: 主要機能 100%カバー
- [ ] **コマンド送信**: 基本操作 100%対応
- [ ] **エラーハンドリング**: 全例外ケース対応

### **6.3 次ステップへの引き継ぎ**

- [ ] **エンティティ定義実装**: 詳細エンティティ実装
- [ ] **コマンド送信実装**: 高度なコマンド対応
- [ ] **HA 統合テスト**: 実際の HA 環境でのテスト

---

## 備考

- **既存コード活用**: Delta Pro/Delta 2 Max の実装パターン踏襲
- **拡張性**: 将来の機能追加・改善に対応
- [ ] **パフォーマンス**: 高頻度データ処理の最適化
- **ログ充実**: デバッグ・監視のための詳細ログ

このタスクの完了により、DP3 の Home Assistant 統合の中核が完成します。
