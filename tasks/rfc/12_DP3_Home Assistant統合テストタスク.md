# DP3 Home Assistant統合テストタスク

## 1. 概要

Delta Pro 3のHome Assistant統合実装の品質を保証するため、包括的なテスト計画を実行する。
実装されたエンティティ、コマンド送信、データ処理の各機能について、実際のHome Assistant環境での動作検証を行う。

## 2. 前提条件

### **依存コンポーネント**
- [ ] **delta_pro3.py実装**: メインデバイスクラス完成
- [ ] **エンティティ定義実装**: 全エンティティ実装完成
- [ ] **コマンド送信実装**: 全コマンド機能完成
- [ ] **XORデコード実装**: Protobuf処理基盤完成

### **テスト環境要件**
- [ ] **Home Assistant Core**: 最新安定版
- [ ] **開発環境**: カスタムコンポーネント開発環境
- [ ] **MQTT環境**: テスト用MQTTブローカー
- [ ] **DP3実機**: 実際のDelta Pro 3デバイス（推奨）

## 3. Phase 1: 単体テスト

### **3.1 XORデコード機能テスト**

#### **XORデコードテストケース**
```python
# tests/test_dp3_xor_decoder.py

import pytest
from unittest.mock import Mock, patch
from custom_components.ecoflow_cloud.devices.internal.xor_decoder import DP3XORDecoder

class TestDP3XORDecoder:
    """DP3 XORデコーダーテストクラス"""

    def setup_method(self):
        """テストセットアップ"""
        self.decoder = DP3XORDecoder(enable_cache=True, enable_learning=True)

        # テスト用サンプルデータ
        self.sample_seq = 12345
        self.sample_pdata = b'\x08\x01\x10\x02\x18\x03'
        self.encrypted_pdata = bytes(b ^ (self.sample_seq & 0xFF) for b in self.sample_pdata)

    def test_basic_xor_decode(self):
        """基本XORデコードテスト"""
        from custom_components.ecoflow_cloud.devices.internal.xor_decoder import xor_decode_pdata

        decoded = xor_decode_pdata(self.encrypted_pdata, self.sample_seq)
        assert decoded == self.sample_pdata

    def test_empty_data_handling(self):
        """空データ処理テスト"""
        from custom_components.ecoflow_cloud.devices.internal.xor_decoder import xor_decode_pdata

        with pytest.raises(ValueError, match="pdata cannot be empty"):
            xor_decode_pdata(b'', self.sample_seq)

    def test_negative_seq_handling(self):
        """負のseq値処理テスト"""
        from custom_components.ecoflow_cloud.devices.internal.xor_decoder import xor_decode_pdata

        with pytest.raises(ValueError, match="seq must be non-negative"):
            xor_decode_pdata(self.encrypted_pdata, -1)

    def test_protobuf_validity_check(self):
        """Protobuf妥当性チェックテスト"""
        from custom_components.ecoflow_cloud.devices.internal.xor_decoder import is_valid_protobuf

        valid_data = b'\x08\x01\x10\x02'  # field 1: varint 1, field 2: varint 2
        invalid_data = b'\xFF\xFF\xFF\xFF'  # 無効なProtobuf

        assert is_valid_protobuf(valid_data) == True
        assert is_valid_protobuf(invalid_data) == False

    def test_multiple_key_fallback(self):
        """複数キー候補フォールバックテスト"""
        from custom_components.ecoflow_cloud.devices.internal.xor_decoder import try_multiple_xor_keys

        decoded, key_type = try_multiple_xor_keys(self.encrypted_pdata, self.sample_seq)
        assert decoded == self.sample_pdata
        assert key_type == 'seq_low_byte'

    @patch('ecopacket_pb2.SendHeaderMsg')
    def test_full_message_decode(self, mock_header):
        """完全メッセージデコードテスト"""
        from custom_components.ecoflow_cloud.devices.internal.xor_decoder import decode_heartbeat_message

        # モックヘッダーの設定
        mock_msg = Mock()
        mock_msg.cmd_id = 1
        mock_msg.seq = self.sample_seq
        mock_msg.pdata = self.encrypted_pdata

        mock_header_instance = Mock()
        mock_header_instance.msg = mock_msg
        mock_header.return_value = mock_header_instance

        # テスト実行
        decoded_pdata, header_info = decode_heartbeat_message(b'dummy_raw_data')

        assert decoded_pdata == self.sample_pdata
        assert header_info['success'] == True
        assert header_info['cmd_id'] == 1
```

### **3.2 コマンド生成機能テスト**

#### **コマンドビルダーテストケース**
```python
# tests/test_dp3_commands.py

import pytest
from custom_components.ecoflow_cloud.devices.internal.dp3_commands import DP3CommandBuilder

class TestDP3CommandBuilder:
    """DP3コマンドビルダーテストクラス"""

    def setup_method(self):
        """テストセットアップ"""
        self.device_sn = "DP3123456789"
        self.builder = DP3CommandBuilder(self.device_sn)

    def test_ac_output_command_generation(self):
        """AC出力コマンド生成テスト"""
        # AC出力ON
        result = self.builder.create_ac_output_command(True)
        assert result.success == True
        assert result.command_type == "ac_output_control"
        assert result.parameters["enabled"] == True

        # AC出力OFF
        result = self.builder.create_ac_output_command(False)
        assert result.success == True
        assert result.parameters["enabled"] == False

    def test_charge_limit_command_validation(self):
        """充電上限コマンド検証テスト"""
        # 正常値
        result = self.builder.create_charge_limit_command(80)
        assert result.success == True
        assert result.parameters["max_charge_soc"] == 80

        # 範囲外値（下限）
        result = self.builder.create_charge_limit_command(40)
        assert result.success == False
        assert "must be 50-100%" in result.error_message

        # 範囲外値（上限）
        result = self.builder.create_charge_limit_command(110)
        assert result.success == False
        assert "must be 50-100%" in result.error_message

    def test_ac_charge_power_command_rounding(self):
        """AC充電電力コマンド丸め処理テスト"""
        # 100W単位への丸め
        result = self.builder.create_ac_charge_power_command(1250)
        assert result.success == True
        assert result.parameters["ac_charge_watts"] == 1300  # 1250 → 1300

        result = self.builder.create_ac_charge_power_command(1230)
        assert result.success == True
        assert result.parameters["ac_charge_watts"] == 1200  # 1230 → 1200

    def test_timeout_command_mapping(self):
        """タイムアウトコマンドマッピングテスト"""
        # スクリーンタイムアウト
        result = self.builder.create_screen_timeout_command("5min")
        assert result.success == True
        assert result.parameters["timeout_seconds"] == 300

        # 無効な選択肢
        result = self.builder.create_screen_timeout_command("invalid")
        assert result.success == False
        assert "Invalid timeout option" in result.error_message
```

## 4. Phase 2: 統合テスト

### **4.1 デバイスクラス統合テスト**

#### **DeltaPro3クラステスト**
```python
# tests/test_delta_pro3_integration.py

import pytest
from unittest.mock import Mock, patch, AsyncMock
from custom_components.ecoflow_cloud.devices.internal.delta_pro3 import DeltaPro3

class TestDeltaPro3Integration:
    """DeltaPro3統合テストクラス"""

    def setup_method(self):
        """テストセットアップ"""
        self.device_info = {
            "device_sn": "DP3123456789",
            "device_type": "DELTA_PRO_3",
            "product_type": "DELTA_PRO_3"
        }
        self.mock_client = Mock()
        self.device = DeltaPro3(self.device_info, self.mock_client)

    def test_device_identification(self):
        """デバイス識別テスト"""
        # DP3として認識されるケース
        assert DeltaPro3.is_device_supported(self.device_info) == True

        # DP3として認識されないケース
        other_device = {
            "device_sn": "DP2123456789",
            "device_type": "DELTA_PRO_2",
            "product_type": "DELTA_PRO_2"
        }
        assert DeltaPro3.is_device_supported(other_device) == False

    @patch('delta_pro3_pb2.AppShowHeartbeatReport')
    def test_app_heartbeat_parsing(self, mock_heartbeat):
        """アプリハートビートパーステスト"""
        # モックProtobufメッセージ設定
        mock_bms = Mock()
        mock_bms.soc = 75
        mock_bms.design_cap = 4000
        mock_bms.temp = 25

        mock_heartbeat_instance = Mock()
        mock_heartbeat_instance.HasField.return_value = True
        mock_heartbeat_instance.bms_status = mock_bms
        mock_heartbeat.return_value = mock_heartbeat_instance

        # テスト実行
        test_pdata = b'\x08\x4B\x10\xA0\x1F\x18\x19'  # サンプルデータ
        result = self.device._parse_app_heartbeat(test_pdata)

        assert result is not None
        assert result["bmsBattSoc"] == 75
        assert result["bmsDesignCap"] == 4000
        assert result["bmsTemp"] == 25

    def test_sensor_entity_generation(self):
        """センサーエンティティ生成テスト"""
        sensors = self.device.sensors(self.mock_client)

        # 基本センサーの存在確認
        sensor_keys = [sensor.mqtt_key for sensor in sensors]
        assert "bmsBattSoc" in sensor_keys
        assert "invInputWatts" in sensor_keys
        assert "invOutputWatts" in sensor_keys
        assert "mpptInWatts" in sensor_keys

        # センサー数の確認（最低限の数）
        assert len(sensors) >= 20

    def test_switch_entity_generation(self):
        """スイッチエンティティ生成テスト"""
        switches = self.device.switches(self.mock_client)

        # 基本スイッチの存在確認
        switch_keys = [switch.mqtt_key for switch in switches]
        assert "invCfgAcEnabled" in switch_keys
        assert "invCfgAcXboost" in switch_keys
        assert "mpptCarState" in switch_keys

        # スイッチ数の確認
        assert len(switches) >= 3

    def test_number_entity_generation(self):
        """ナンバーエンティティ生成テスト"""
        numbers = self.device.numbers(self.mock_client)

        # 基本ナンバーの存在確認
        number_keys = [number.mqtt_key for number in numbers]
        assert "bmsMaxChargeSoc" in number_keys
        assert "bmsMinDischargeSoc" in number_keys
        assert "invCfgSlowChgWatts" in number_keys

        # ナンバー数の確認
        assert len(numbers) >= 3
```

### **4.2 エンティティ動作テスト**

#### **エンティティ機能テスト**
```python
# tests/test_dp3_entities.py

import pytest
from unittest.mock import Mock, AsyncMock
from custom_components.ecoflow_cloud.entities import BaseSensorEntity, BaseSwitchEntity

class TestDP3Entities:
    """DP3エンティティテストクラス"""

    def setup_method(self):
        """テストセットアップ"""
        self.mock_client = Mock()
        self.mock_device = Mock()
        self.mock_device.device_sn = "DP3123456789"
        self.mock_device.data = Mock()

    def test_sensor_entity_value_update(self):
        """センサーエンティティ値更新テスト"""
        # バッテリー残量センサー
        sensor = BaseSensorEntity(
            self.mock_client, self.mock_device, "bmsBattSoc", "Battery Level", "%"
        )

        # データ更新シミュレーション
        self.mock_device.data.params = {"bmsBattSoc": 75}
        sensor._updated(self.mock_device.data)

        assert sensor.native_value == 75
        assert sensor.native_unit_of_measurement == "%"

    @pytest.mark.asyncio
    async def test_switch_entity_command_execution(self):
        """スイッチエンティティコマンド実行テスト"""
        # AC出力スイッチ
        switch = BaseSwitchEntity(
            self.mock_client, self.mock_device, "invCfgAcEnabled", "AC Output",
            lambda value, params: {"cfgAcEnabled": value}
        )

        # コマンド送信モック
        self.mock_client.send_set_message = AsyncMock()

        # スイッチON実行
        await switch.async_turn_on()

        # コマンド送信確認
        self.mock_client.send_set_message.assert_called_once()
        call_args = self.mock_client.send_set_message.call_args[0]
        assert call_args[1]["cfgAcEnabled"] == True
```

## 5. Phase 3: Home Assistant環境テスト

### **5.1 設定フロー統合テスト**

#### **統合設定テスト**
```python
# tests/test_dp3_config_flow.py

import pytest
from unittest.mock import Mock, patch
from homeassistant.core import HomeAssistant
from custom_components.ecoflow_cloud.config_flow import EcoflowCloudConfigFlow

class TestDP3ConfigFlow:
    """DP3設定フローテストクラス"""

    @pytest.mark.asyncio
    async def test_dp3_device_discovery(self, hass: HomeAssistant):
        """DP3デバイス発見テスト"""
        config_flow = EcoflowCloudConfigFlow()
        config_flow.hass = hass

        # モックデバイス情報
        mock_devices = [
            {
                "device_sn": "DP3123456789",
                "device_type": "DELTA_PRO_3",
                "product_type": "DELTA_PRO_3",
                "device_name": "Delta Pro 3"
            }
        ]

        with patch.object(config_flow, '_get_devices', return_value=mock_devices):
            result = await config_flow.async_step_user()

            assert result["type"] == "form"
            assert "DP3123456789" in str(result["data_schema"])

    @pytest.mark.asyncio
    async def test_dp3_integration_setup(self, hass: HomeAssistant):
        """DP3統合セットアップテスト"""
        config_entry = Mock()
        config_entry.data = {
            "username": "test@example.com",
            "password": "password",
            "device_sn": "DP3123456789"
        }

        with patch('custom_components.ecoflow_cloud.async_setup_entry') as mock_setup:
            mock_setup.return_value = True

            from custom_components.ecoflow_cloud import async_setup_entry
            result = await async_setup_entry(hass, config_entry)

            assert result == True
```

### **5.2 エンティティ登録テスト**

#### **プラットフォーム統合テスト**
```python
# tests/test_dp3_platforms.py

import pytest
from unittest.mock import Mock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

class TestDP3Platforms:
    """DP3プラットフォームテストクラス"""

    @pytest.mark.asyncio
    async def test_sensor_platform_setup(self, hass: HomeAssistant):
        """センサープラットフォームセットアップテスト"""
        from custom_components.ecoflow_cloud.sensor import async_setup_entry

        config_entry = Mock()
        mock_add_entities = Mock()

        # モックデバイス
        mock_device = Mock()
        mock_device.sensors.return_value = [Mock(), Mock(), Mock()]  # 3つのセンサー

        with patch('custom_components.ecoflow_cloud.sensor.get_device_by_sn') as mock_get_device:
            mock_get_device.return_value = mock_device

            await async_setup_entry(hass, config_entry, mock_add_entities)

            # エンティティが追加されたことを確認
            mock_add_entities.assert_called_once()
            added_entities = mock_add_entities.call_args[0][0]
            assert len(added_entities) == 3

    @pytest.mark.asyncio
    async def test_switch_platform_setup(self, hass: HomeAssistant):
        """スイッチプラットフォームセットアップテスト"""
        from custom_components.ecoflow_cloud.switch import async_setup_entry

        config_entry = Mock()
        mock_add_entities = Mock()

        # モックデバイス
        mock_device = Mock()
        mock_device.switches.return_value = [Mock(), Mock()]  # 2つのスイッチ

        with patch('custom_components.ecoflow_cloud.switch.get_device_by_sn') as mock_get_device:
            mock_get_device.return_value = mock_device

            await async_setup_entry(hass, config_entry, mock_add_entities)

            # エンティティが追加されたことを確認
            mock_add_entities.assert_called_once()
            added_entities = mock_add_entities.call_args[0][0]
            assert len(added_entities) == 2
```

## 6. Phase 4: 実機テスト準備

### **6.1 実機テスト環境構築**

#### **テスト環境設定**
```yaml
# tests/fixtures/dp3_test_config.yaml
test_environment:
  home_assistant:
    version: "2024.1.0"
    config_dir: "/config"

  ecoflow_integration:
    username: "${ECOFLOW_USERNAME}"
    password: "${ECOFLOW_PASSWORD}"

  dp3_device:
    device_sn: "${DP3_DEVICE_SN}"
    mqtt_broker: "mqtt.ecoflow.com"
    mqtt_port: 1883

  test_scenarios:
    - name: "basic_functionality"
      description: "基本機能テスト"
      tests:
        - entity_discovery
        - data_reception
        - command_execution

    - name: "stress_test"
      description: "負荷テスト"
      tests:
        - continuous_data_processing
        - rapid_command_execution
        - error_recovery
```

### **6.2 実機テストスクリプト**

#### **自動テストスクリプト**
```python
# tests/integration/test_dp3_real_device.py

import pytest
import asyncio
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant

class TestDP3RealDevice:
    """DP3実機テストクラス"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_device_data_reception(self, hass: HomeAssistant):
        """実機データ受信テスト"""
        # 実機接続確認
        device = await self._get_dp3_device(hass)
        assert device is not None

        # データ受信待機
        initial_time = datetime.now()
        timeout = timedelta(minutes=2)

        while datetime.now() - initial_time < timeout:
            if device.data.last_received_time:
                break
            await asyncio.sleep(1)

        # データ受信確認
        assert device.data.last_received_time is not None
        assert device.data.params is not None
        assert len(device.data.params) > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_device_command_execution(self, hass: HomeAssistant):
        """実機コマンド実行テスト"""
        device = await self._get_dp3_device(hass)

        # AC出力状態取得
        initial_ac_state = device.data.params.get("invCfgAcEnabled", False)

        # AC出力切り替えコマンド実行
        new_state = not initial_ac_state
        command_result = device.command_builder.create_ac_output_command(new_state)
        assert command_result.success == True

        # コマンド送信
        await device.client.send_set_message(device.device_sn, command_result.parameters)

        # 状態変化確認（最大30秒待機）
        for _ in range(30):
            await asyncio.sleep(1)
            current_state = device.data.params.get("invCfgAcEnabled")
            if current_state == new_state:
                break

        assert device.data.params.get("invCfgAcEnabled") == new_state

        # 元の状態に戻す
        restore_result = device.command_builder.create_ac_output_command(initial_ac_state)
        await device.client.send_set_message(device.device_sn, restore_result.parameters)

    async def _get_dp3_device(self, hass: HomeAssistant):
        """DP3デバイス取得ヘルパー"""
        # 統合からDP3デバイスを取得
        # 実装は実際のHA統合構造に依存
        pass
```

## 7. 成果物・次ステップ

### **7.1 期待される成果物**
- [ ] **単体テストスイート**: XORデコード・コマンド生成テスト
- [ ] **統合テストスイート**: デバイスクラス・エンティティテスト
- [ ] **HA統合テスト**: 設定フロー・プラットフォームテスト
- [ ] **実機テスト環境**: 自動テストスクリプト・設定
- [ ] **テストレポート**: 品質評価・課題特定

### **7.2 品質基準**
- [ ] **テストカバレッジ**: 90%以上
- [ ] **単体テスト成功率**: 100%
- [ ] **統合テスト成功率**: 95%以上
- [ ] **実機テスト成功率**: 90%以上

### **7.3 次ステップへの引き継ぎ**
- [ ] **実機テスト実行**: 実際のDP3での動作検証
- [ ] **パフォーマンステスト**: 負荷・応答時間測定
- [ ] **ドキュメント更新**: テスト結果・使用方法の文書化

---

## 備考

- **段階的テスト**: 単体→統合→実機の順序でテスト実行
- **自動化重視**: CI/CDパイプラインでの自動テスト実行
- **品質保証**: 包括的なテストによる高品質確保
- **実機検証**: 実際の使用環境での動作確認

このタスクの完了により、DP3統合の品質が保証され、安定したリリースが可能になります。