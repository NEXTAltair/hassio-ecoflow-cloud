# DP3 コマンド送信実装タスク

## 1. 概要

Delta Pro 3のデバイス制御コマンド送信機能を実装する。
Home Assistantのスイッチ、ナンバー、セレクトエンティティからの操作を、DP3が理解できるProtobuf形式のコマンドに変換し、MQTT経由で送信する機能を構築する。

## 2. 前提条件

### **依存コンポーネント**
- [ ] **delta_pro3.py実装**: メインデバイスクラス完成
- [ ] **エンティティ定義実装**: 各種エンティティ定義完成
- [ ] **Protobufスキーマ**: コマンド送信用.protoファイル完成

### **技術要件**
- [ ] **MQTT送信**: EcoflowApiClient経由でのコマンド送信
- [ ] **Protobuf生成**: コマンド用Protobufメッセージ生成
- [ ] **エラーハンドリング**: コマンド失敗時の適切な処理

## 3. Phase 1: 基本コマンド構造実装

### **3.1 コマンド基盤クラス**

#### **DP3CommandBuilder クラス**
```python
# custom_components/ecoflow_cloud/devices/internal/dp3_commands.py

from __future__ import annotations
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass

import delta_pro3_pb2

_LOGGER = logging.getLogger(__name__)

@dataclass
class DP3CommandResult:
    """DP3コマンド実行結果"""
    success: bool
    command_type: str
    parameters: Dict[str, Any]
    error_message: Optional[str] = None
    protobuf_data: Optional[bytes] = None

class DP3CommandBuilder:
    """DP3用コマンドビルダー"""

    def __init__(self, device_sn: str):
        self.device_sn = device_sn
        self._logger = _LOGGER.getChild(f"DP3Command[{device_sn}]")

    def _create_base_command(self, cmd_func: int, cmd_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        DP3用基本コマンド構造生成

        Args:
            cmd_func (int): コマンド機能番号
            cmd_id (int): コマンドID
            params (Dict[str, Any]): パラメータ

        Returns:
            Dict[str, Any]: コマンド構造
        """
        command = {
            "sn": self.device_sn,
            "cmdId": cmd_id,
            "dirDest": 1,
            "dirSrc": 1,
            "cmdFunc": cmd_func,
            "dest": 2,
            "params": params
        }

        self._logger.debug(f"Created base command: func={cmd_func}, id={cmd_id}, params={params}")
        return command

    def _create_protobuf_command(self, command_request: delta_pro3_pb2.DeltaPro3CommandRequest) -> bytes:
        """
        Protobufコマンドメッセージ生成

        Args:
            command_request: Protobufコマンドリクエスト

        Returns:
            bytes: シリアライズされたProtobufデータ
        """
        try:
            protobuf_data = command_request.SerializeToString()
            self._logger.debug(f"Generated protobuf command: {len(protobuf_data)} bytes")
            return protobuf_data
        except Exception as e:
            self._logger.error(f"Failed to serialize protobuf command: {e}")
            raise
```

### **3.2 出力制御コマンド**

#### **AC出力制御**
```python
    def create_ac_output_command(self, enabled: bool) -> DP3CommandResult:
        """
        AC出力制御コマンド生成

        Args:
            enabled (bool): AC出力有効/無効

        Returns:
            DP3CommandResult: コマンド実行結果
        """
        try:
            # JSON形式コマンド（従来方式）
            json_command = self._create_base_command(
                cmd_func=254,
                cmd_id=17,
                params={"cfgAcEnabled": enabled}
            )

            # Protobuf形式コマンド（新方式）
            command_request = delta_pro3_pb2.DeltaPro3CommandRequest()
            command_request.ac_output.enabled = enabled
            protobuf_data = self._create_protobuf_command(command_request)

            return DP3CommandResult(
                success=True,
                command_type="ac_output_control",
                parameters={"enabled": enabled},
                protobuf_data=protobuf_data
            )

        except Exception as e:
            self._logger.error(f"Failed to create AC output command: {e}")
            return DP3CommandResult(
                success=False,
                command_type="ac_output_control",
                parameters={"enabled": enabled},
                error_message=str(e)
            )

    def create_xboost_command(self, enabled: bool) -> DP3CommandResult:
        """
        X-Boost制御コマンド生成

        Args:
            enabled (bool): X-Boost有効/無効

        Returns:
            DP3CommandResult: コマンド実行結果
        """
        try:
            json_command = self._create_base_command(
                cmd_func=254,
                cmd_id=17,
                params={"cfgAcXboost": enabled}
            )

            command_request = delta_pro3_pb2.DeltaPro3CommandRequest()
            command_request.xboost.enabled = enabled
            protobuf_data = self._create_protobuf_command(command_request)

            return DP3CommandResult(
                success=True,
                command_type="xboost_control",
                parameters={"enabled": enabled},
                protobuf_data=protobuf_data
            )

        except Exception as e:
            self._logger.error(f"Failed to create X-Boost command: {e}")
            return DP3CommandResult(
                success=False,
                command_type="xboost_control",
                parameters={"enabled": enabled},
                error_message=str(e)
            )

    def create_dc_output_command(self, enabled: bool) -> DP3CommandResult:
        """
        DC出力制御コマンド生成

        Args:
            enabled (bool): DC出力有効/無効

        Returns:
            DP3CommandResult: コマンド実行結果
        """
        try:
            json_command = self._create_base_command(
                cmd_func=254,
                cmd_id=17,
                params={"cfgDcEnabled": enabled}
            )

            command_request = delta_pro3_pb2.DeltaPro3CommandRequest()
            command_request.dc_output.enabled = enabled
            protobuf_data = self._create_protobuf_command(command_request)

            return DP3CommandResult(
                success=True,
                command_type="dc_output_control",
                parameters={"enabled": enabled},
                protobuf_data=protobuf_data
            )

        except Exception as e:
            self._logger.error(f"Failed to create DC output command: {e}")
            return DP3CommandResult(
                success=False,
                command_type="dc_output_control",
                parameters={"enabled": enabled},
                error_message=str(e)
            )
```

### **3.3 充電制御コマンド**

#### **充電設定コマンド**
```python
    def create_charge_limit_command(self, max_soc: int) -> DP3CommandResult:
        """
        充電上限設定コマンド生成

        Args:
            max_soc (int): 充電上限SOC (50-100%)

        Returns:
            DP3CommandResult: コマンド実行結果
        """
        try:
            # 入力値検証
            if not 50 <= max_soc <= 100:
                raise ValueError(f"Invalid charge limit: {max_soc}% (must be 50-100%)")

            json_command = self._create_base_command(
                cmd_func=254,
                cmd_id=17,
                params={"cfgMaxChargeSoc": max_soc}
            )

            command_request = delta_pro3_pb2.DeltaPro3CommandRequest()
            command_request.charge_setting.max_charge_soc = max_soc
            protobuf_data = self._create_protobuf_command(command_request)

            return DP3CommandResult(
                success=True,
                command_type="charge_limit_setting",
                parameters={"max_charge_soc": max_soc},
                protobuf_data=protobuf_data
            )

        except Exception as e:
            self._logger.error(f"Failed to create charge limit command: {e}")
            return DP3CommandResult(
                success=False,
                command_type="charge_limit_setting",
                parameters={"max_charge_soc": max_soc},
                error_message=str(e)
            )

    def create_discharge_limit_command(self, min_soc: int) -> DP3CommandResult:
        """
        放電下限設定コマンド生成

        Args:
            min_soc (int): 放電下限SOC (0-30%)

        Returns:
            DP3CommandResult: コマンド実行結果
        """
        try:
            if not 0 <= min_soc <= 30:
                raise ValueError(f"Invalid discharge limit: {min_soc}% (must be 0-30%)")

            json_command = self._create_base_command(
                cmd_func=254,
                cmd_id=17,
                params={"cfgMinDischargeSoc": min_soc}
            )

            command_request = delta_pro3_pb2.DeltaPro3CommandRequest()
            command_request.charge_setting.min_discharge_soc = min_soc
            protobuf_data = self._create_protobuf_command(command_request)

            return DP3CommandResult(
                success=True,
                command_type="discharge_limit_setting",
                parameters={"min_discharge_soc": min_soc},
                protobuf_data=protobuf_data
            )

        except Exception as e:
            self._logger.error(f"Failed to create discharge limit command: {e}")
            return DP3CommandResult(
                success=False,
                command_type="discharge_limit_setting",
                parameters={"min_discharge_soc": min_soc},
                error_message=str(e)
            )

    def create_ac_charge_power_command(self, power_watts: int) -> DP3CommandResult:
        """
        AC充電電力設定コマンド生成

        Args:
            power_watts (int): AC充電電力 (400-2900W)

        Returns:
            DP3CommandResult: コマンド実行結果
        """
        try:
            if not 400 <= power_watts <= 2900:
                raise ValueError(f"Invalid AC charge power: {power_watts}W (must be 400-2900W)")

            # 100W単位に丸める
            power_watts = round(power_watts / 100) * 100

            json_command = self._create_base_command(
                cmd_func=254,
                cmd_id=17,
                params={"cfgAcChargePower": power_watts}
            )

            command_request = delta_pro3_pb2.DeltaPro3CommandRequest()
            command_request.charge_setting.ac_charge_watts = power_watts
            protobuf_data = self._create_protobuf_command(command_request)

            return DP3CommandResult(
                success=True,
                command_type="ac_charge_power_setting",
                parameters={"ac_charge_watts": power_watts},
                protobuf_data=protobuf_data
            )

        except Exception as e:
            self._logger.error(f"Failed to create AC charge power command: {e}")
            return DP3CommandResult(
                success=False,
                command_type="ac_charge_power_setting",
                parameters={"ac_charge_watts": power_watts},
                error_message=str(e)
            )
```

## 4. Phase 2: システム設定コマンド

### **4.1 タイムアウト設定コマンド**

#### **タイムアウト制御**
```python
    def create_screen_timeout_command(self, timeout_option: str) -> DP3CommandResult:
        """
        スクリーンタイムアウト設定コマンド生成

        Args:
            timeout_option (str): タイムアウト選択肢

        Returns:
            DP3CommandResult: コマンド実行結果
        """
        try:
            # タイムアウト値マッピング
            timeout_mapping = {
                "Never": 0,
                "10sec": 10,
                "30sec": 30,
                "1min": 60,
                "5min": 300,
                "30min": 1800
            }

            if timeout_option not in timeout_mapping:
                raise ValueError(f"Invalid timeout option: {timeout_option}")

            timeout_seconds = timeout_mapping[timeout_option]

            json_command = self._create_base_command(
                cmd_func=254,
                cmd_id=17,
                params={"cfgLcdOffSec": timeout_seconds}
            )

            return DP3CommandResult(
                success=True,
                command_type="screen_timeout_setting",
                parameters={"timeout_option": timeout_option, "timeout_seconds": timeout_seconds}
            )

        except Exception as e:
            self._logger.error(f"Failed to create screen timeout command: {e}")
            return DP3CommandResult(
                success=False,
                command_type="screen_timeout_setting",
                parameters={"timeout_option": timeout_option},
                error_message=str(e)
            )

    def create_unit_timeout_command(self, timeout_option: str) -> DP3CommandResult:
        """
        ユニットタイムアウト設定コマンド生成

        Args:
            timeout_option (str): タイムアウト選択肢

        Returns:
            DP3CommandResult: コマンド実行結果
        """
        try:
            timeout_mapping = {
                "Never": 0,
                "30min": 30,
                "1hr": 60,
                "2hr": 120,
                "6hr": 360,
                "12hr": 720
            }

            if timeout_option not in timeout_mapping:
                raise ValueError(f"Invalid timeout option: {timeout_option}")

            timeout_minutes = timeout_mapping[timeout_option]

            json_command = self._create_base_command(
                cmd_func=254,
                cmd_id=17,
                params={"cfgStandbyMin": timeout_minutes}
            )

            return DP3CommandResult(
                success=True,
                command_type="unit_timeout_setting",
                parameters={"timeout_option": timeout_option, "timeout_minutes": timeout_minutes}
            )

        except Exception as e:
            self._logger.error(f"Failed to create unit timeout command: {e}")
            return DP3CommandResult(
                success=False,
                command_type="unit_timeout_setting",
                parameters={"timeout_option": timeout_option},
                error_message=str(e)
            )
```

### **4.2 システム制御コマンド**

#### **ビープ音・その他設定**
```python
    def create_beep_command(self, enabled: bool) -> DP3CommandResult:
        """
        ビープ音制御コマンド生成

        Args:
            enabled (bool): ビープ音有効/無効

        Returns:
            DP3CommandResult: コマンド実行結果
        """
        try:
            json_command = self._create_base_command(
                cmd_func=254,
                cmd_id=17,
                params={"cfgBeepEnabled": enabled}
            )

            return DP3CommandResult(
                success=True,
                command_type="beep_control",
                parameters={"enabled": enabled}
            )

        except Exception as e:
            self._logger.error(f"Failed to create beep command: {e}")
            return DP3CommandResult(
                success=False,
                command_type="beep_control",
                parameters={"enabled": enabled},
                error_message=str(e)
            )
```

## 5. Phase 3: コマンド送信統合

### **5.1 DeltaPro3クラス統合**

#### **コマンド送信メソッド統合**
```python
# custom_components/ecoflow_cloud/devices/internal/delta_pro3.py に追加

class DeltaPro3(BaseDevice):
    """Delta Pro 3デバイスクラス"""

    def __init__(self, device_info: dict, client: EcoflowApiClient):
        super().__init__(device_info, client)
        # ... 既存の初期化コード ...

        # コマンドビルダー初期化
        self.command_builder = DP3CommandBuilder(self.device_sn)

    # AC出力制御
    def _create_ac_output_command(self, enabled: bool) -> dict:
        """AC出力制御コマンド生成（エンティティ用）"""
        result = self.command_builder.create_ac_output_command(enabled)
        if result.success:
            return result.parameters
        else:
            _LOGGER.error(f"AC output command failed: {result.error_message}")
            return {}

    def _create_xboost_command(self, enabled: bool) -> dict:
        """X-Boost制御コマンド生成（エンティティ用）"""
        result = self.command_builder.create_xboost_command(enabled)
        if result.success:
            return result.parameters
        else:
            _LOGGER.error(f"X-Boost command failed: {result.error_message}")
            return {}

    def _create_dc_output_command(self, enabled: bool) -> dict:
        """DC出力制御コマンド生成（エンティティ用）"""
        result = self.command_builder.create_dc_output_command(enabled)
        if result.success:
            return result.parameters
        else:
            _LOGGER.error(f"DC output command failed: {result.error_message}")
            return {}

    # 充電制御
    def _create_charge_limit_command(self, max_soc: int) -> dict:
        """充電上限設定コマンド生成（エンティティ用）"""
        result = self.command_builder.create_charge_limit_command(max_soc)
        if result.success:
            return result.parameters
        else:
            _LOGGER.error(f"Charge limit command failed: {result.error_message}")
            return {}

    def _create_discharge_limit_command(self, min_soc: int) -> dict:
        """放電下限設定コマンド生成（エンティティ用）"""
        result = self.command_builder.create_discharge_limit_command(min_soc)
        if result.success:
            return result.parameters
        else:
            _LOGGER.error(f"Discharge limit command failed: {result.error_message}")
            return {}

    def _create_ac_charge_power_command(self, power_watts: int) -> dict:
        """AC充電電力設定コマンド生成（エンティティ用）"""
        result = self.command_builder.create_ac_charge_power_command(power_watts)
        if result.success:
            return result.parameters
        else:
            _LOGGER.error(f"AC charge power command failed: {result.error_message}")
            return {}

    # システム設定
    def _create_screen_timeout_command(self, timeout_option: str) -> dict:
        """スクリーンタイムアウト設定コマンド生成（エンティティ用）"""
        result = self.command_builder.create_screen_timeout_command(timeout_option)
        if result.success:
            return result.parameters
        else:
            _LOGGER.error(f"Screen timeout command failed: {result.error_message}")
            return {}

    def _create_unit_timeout_command(self, timeout_option: str) -> dict:
        """ユニットタイムアウト設定コマンド生成（エンティティ用）"""
        result = self.command_builder.create_unit_timeout_command(timeout_option)
        if result.success:
            return result.parameters
        else:
            _LOGGER.error(f"Unit timeout command failed: {result.error_message}")
            return {}

    def _create_beep_command(self, enabled: bool) -> dict:
        """ビープ音制御コマンド生成（エンティティ用）"""
        result = self.command_builder.create_beep_command(enabled)
        if result.success:
            return result.parameters
        else:
            _LOGGER.error(f"Beep command failed: {result.error_message}")
            return {}
```

## 6. Phase 4: エラーハンドリング・検証

### **6.1 コマンド検証機能**

#### **入力値検証**
```python
class DP3CommandValidator:
    """DP3コマンド検証クラス"""

    @staticmethod
    def validate_soc_range(soc: int, min_val: int, max_val: int, param_name: str) -> None:
        """SOC値の範囲検証"""
        if not isinstance(soc, int):
            raise TypeError(f"{param_name} must be an integer")
        if not min_val <= soc <= max_val:
            raise ValueError(f"{param_name} must be between {min_val}% and {max_val}%")

    @staticmethod
    def validate_power_range(power: int, min_val: int, max_val: int, step: int = 1) -> int:
        """電力値の範囲検証・正規化"""
        if not isinstance(power, int):
            raise TypeError("Power must be an integer")
        if not min_val <= power <= max_val:
            raise ValueError(f"Power must be between {min_val}W and {max_val}W")

        # ステップサイズに合わせて正規化
        if step > 1:
            power = round(power / step) * step

        return power

    @staticmethod
    def validate_timeout_option(option: str, valid_options: list[str]) -> None:
        """タイムアウト選択肢の検証"""
        if not isinstance(option, str):
            raise TypeError("Timeout option must be a string")
        if option not in valid_options:
            raise ValueError(f"Invalid timeout option: {option}. Valid options: {valid_options}")
```

### **6.2 コマンド応答処理**

#### **応答メッセージ処理**
```python
class DP3CommandResponseHandler:
    """DP3コマンド応答処理クラス"""

    def __init__(self, device_sn: str):
        self.device_sn = device_sn
        self._logger = _LOGGER.getChild(f"DP3Response[{device_sn}]")

    def handle_command_response(self, response_data: dict) -> bool:
        """
        コマンド応答処理

        Args:
            response_data (dict): 応答データ

        Returns:
            bool: 処理成功可否
        """
        try:
            # 応答データの基本検証
            if not isinstance(response_data, dict):
                self._logger.error("Invalid response data format")
                return False

            # 成功/失敗判定
            success = response_data.get("success", False)
            error_code = response_data.get("error_code", 0)
            error_message = response_data.get("error_message", "")

            if success:
                self._logger.info("Command executed successfully")
                return True
            else:
                self._logger.warning(f"Command failed: code={error_code}, message={error_message}")
                return False

        except Exception as e:
            self._logger.error(f"Failed to handle command response: {e}")
            return False
```

## 7. 成果物・次ステップ

### **7.1 期待される成果物**
- [ ] **DP3CommandBuilder**: 包括的コマンド生成クラス
- [ ] **出力制御コマンド**: AC/DC/X-Boost制御
- [ ] **充電制御コマンド**: 上限/下限/電力設定
- [ ] **システム設定コマンド**: タイムアウト・ビープ音制御
- [ ] **検証・エラーハンドリング**: 堅牢なコマンド処理

### **7.2 品質基準**
- [ ] **入力値検証**: 全パラメータの範囲・型チェック
- [ ] **エラーハンドリング**: 例外ケースの適切な処理
- [ ] **ログ充実**: デバッグ・監視のための詳細ログ
- [ ] **型安全性**: 完全な型ヒント対応

### **7.3 次ステップへの引き継ぎ**
- [ ] **HA統合テスト**: 実際のHA環境でのコマンドテスト
- [ ] **実機テスト**: 実機でのコマンド動作検証
- [ ] **パフォーマンス最適化**: コマンド送信の高速化

---

## 備考

- **堅牢性重視**: エラーハンドリング・入力値検証の充実
- **拡張性**: 将来のコマンド追加に対応可能な設計
- **デバッグ支援**: 詳細なログ・エラーメッセージ
- **既存互換性**: 既存デバイスとの一貫性維持

このタスクの完了により、DP3の完全なデバイス制御機能が実現されます。