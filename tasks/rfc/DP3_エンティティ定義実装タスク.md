# DP3 エンティティ定義実装タスク

## 1. 概要

Delta Pro 3のHome Assistant統合において、センサー、スイッチ、数値入力、セレクトの各エンティティを詳細に定義・実装する。
既存のDelta Pro/Delta 2 Maxの実装パターンを踏襲しつつ、DP3特有の機能・仕様に対応した包括的なエンティティセットを構築する。

## 2. 前提条件

### **依存コンポーネント**
- [ ] **delta_pro3.py実装**: `DP3_delta_pro3.py実装タスク.md` 完了
- [ ] **Protobufスキーマ**: DP3専用.protoファイル完成
- [ ] **既存構造理解**: Delta Pro/Delta 2 Maxエンティティ構造把握

### **技術要件**
- [ ] **Home Assistant Core**: Entity基底クラス対応
- [ ] **EcoFlow統合**: BaseSensorEntity等の活用
- [ ] **型安全性**: 完全な型ヒント対応

## 3. Phase 1: センサーエンティティ詳細実装

### **3.1 バッテリー関連センサー**

#### **基本バッテリーセンサー**
```python
def _battery_sensors(self, client: EcoflowApiClient) -> list[BaseSensorEntity]:
    """バッテリー関連センサーエンティティ"""
    return [
        # 基本残量情報
        BaseSensorEntity(
            client, self, "bmsBattSoc", MAIN_BATTERY_LEVEL, "%",
            attr={
                ATTR_DESIGN_CAPACITY: "bmsDesignCap",
                ATTR_FULL_CAPACITY: "bmsFullCap",
                ATTR_REMAIN_CAPACITY: "bmsRemainCap",
                ATTR_SOH: "bmsSoh",
                ATTR_CYCLES: "bmsCycles"
            }
        ),

        # 精密残量（float値）
        BaseSensorEntity(
            client, self, "bmsBattSocF32", MAIN_BATTERY_LEVEL_F32, "%",
            attr={
                "precision": "high",
                "data_source": "float32"
            }
        ),

        # 容量情報
        BaseSensorEntity(
            client, self, "bmsDesignCap", MAIN_DESIGN_CAPACITY, "mAh",
            attr={"capacity_type": "design"}
        ),
        BaseSensorEntity(
            client, self, "bmsFullCap", MAIN_FULL_CAPACITY, "mAh",
            attr={"capacity_type": "full_charge"}
        ),
        BaseSensorEntity(
            client, self, "bmsRemainCap", MAIN_REMAIN_CAPACITY, "mAh",
            attr={"capacity_type": "remaining"}
        ),

        # 健康状態
        BaseSensorEntity(
            client, self, "bmsSoh", SOH, "%",
            attr={"health_indicator": True}
        ),
        BaseSensorEntity(
            client, self, "bmsCycles", CYCLES, "回",
            attr={"wear_indicator": True}
        ),

        # 温度情報
        BaseSensorEntity(
            client, self, "bmsTemp", BATTERY_TEMP, "℃",
            attr={
                ATTR_MIN_CELL_TEMP: "bmsMinCellTemp",
                ATTR_MAX_CELL_TEMP: "bmsMaxCellTemp"
            }
        ),
        BaseSensorEntity(
            client, self, "bmsMinCellTemp", MIN_CELL_TEMP, "℃",
            attr={"temperature_type": "minimum_cell"}
        ),
        BaseSensorEntity(
            client, self, "bmsMaxCellTemp", MAX_CELL_TEMP, "℃",
            attr={"temperature_type": "maximum_cell"}
        ),

        # 電圧情報
        BaseSensorEntity(
            client, self, "bmsVol", BATTERY_VOLT, "mV",
            attr={
                ATTR_MIN_CELL_VOLT: "bmsMinCellVol",
                ATTR_MAX_CELL_VOLT: "bmsMaxCellVol"
            }
        ),
        BaseSensorEntity(
            client, self, "bmsMinCellVol", MIN_CELL_VOLT, "mV",
            attr={"voltage_type": "minimum_cell"}
        ),
        BaseSensorEntity(
            client, self, "bmsMaxCellVol", MAX_CELL_VOLT, "mV",
            attr={"voltage_type": "maximum_cell"}
        ),

        # 電流情報
        BaseSensorEntity(
            client, self, "bmsAmp", MAIN_BATTERY_CURRENT, "mA",
            attr={"current_direction": "charge_positive"}
        ),
    ]
```

### **3.2 電力関連センサー**

#### **AC電力センサー**
```python
def _ac_power_sensors(self, client: EcoflowApiClient) -> list[BaseSensorEntity]:
    """AC電力関連センサーエンティティ"""
    return [
        # AC入力
        BaseSensorEntity(
            client, self, "invInputWatts", AC_IN_POWER, "W",
            attr={
                "power_direction": "input",
                "power_type": "ac"
            }
        ),
        BaseSensorEntity(
            client, self, "invAcInVol", AC_IN_VOLT, "mV",
            attr={
                "voltage_type": "ac_input",
                "frequency": "invAcInFreq"
            }
        ),

        # AC出力
        BaseSensorEntity(
            client, self, "invOutputWatts", AC_OUT_POWER, "W",
            attr={
                "power_direction": "output",
                "power_type": "ac",
                "xboost_capable": "invCfgAcXboost"
            }
        ),
        BaseSensorEntity(
            client, self, "invOutVol", AC_OUT_VOLT, "mV",
            attr={
                "voltage_type": "ac_output",
                "frequency": "invOutFreq"
            }
        ),
    ]
```

### **3.3 USB/Type-C電力センサー**

#### **USB電力センサー**
```python
def _usb_power_sensors(self, client: EcoflowApiClient) -> list[BaseSensorEntity]:
    """USB/Type-C電力センサーエンティティ"""
    return [
        # Type-C出力
        BaseSensorEntity(
            client, self, "pdTypec1Watts", TYPEC_1_OUT_POWER, "W",
            attr={
                "power_direction": "output",
                "connector_type": "usb_type_c",
                "port_number": 1
            }
        ),
        BaseSensorEntity(
            client, self, "pdTypec2Watts", TYPEC_2_OUT_POWER, "W",
            attr={
                "power_direction": "output",
                "connector_type": "usb_type_c",
                "port_number": 2
            }
        ),

        # USB-A出力
        BaseSensorEntity(
            client, self, "pdUsb1Watts", USB_1_OUT_POWER, "W",
            attr={
                "power_direction": "output",
                "connector_type": "usb_a",
                "port_number": 1
            }
        ),
        BaseSensorEntity(
            client, self, "pdUsb2Watts", USB_2_OUT_POWER, "W",
            attr={
                "power_direction": "output",
                "connector_type": "usb_a",
                "port_number": 2
            }
        ),
    ]
```

## 4. Phase 2: スイッチエンティティ詳細実装

### **4.1 出力制御スイッチ**

#### **AC/DC出力スイッチ**
```python
def _output_switches(self, client: EcoflowApiClient) -> list[BaseSwitchEntity]:
    """出力制御スイッチエンティティ"""
    return [
        # AC出力制御
        BaseSwitchEntity(
            client, self, "invCfgAcEnabled", AC_ENABLED,
            lambda value, params: self._create_ac_output_command(value),
            attr={
                "output_type": "ac",
                "max_power": "invMaxOutputWatts",
                "xboost_available": True
            }
        ),

        # X-Boost制御
        BaseSwitchEntity(
            client, self, "invCfgAcXboost", XBOOST_ENABLED,
            lambda value, params: self._create_xboost_command(value),
            attr={
                "feature_type": "power_boost",
                "requires_ac_enabled": True,
                "max_boost_power": 3600
            }
        ),

        # DC出力制御
        BaseSwitchEntity(
            client, self, "mpptCarState", DC_ENABLED,
            lambda value, params: self._create_dc_output_command(value),
            attr={
                "output_type": "dc",
                "connector_types": ["cigarette_lighter", "anderson"]
            }
        ),
    ]
```

## 5. Phase 3: 数値入力エンティティ詳細実装

### **5.1 充電制御ナンバー**

#### **充電設定ナンバー**
```python
def _charging_numbers(self, client: EcoflowApiClient) -> list[BaseNumberEntity]:
    """充電制御ナンバーエンティティ"""
    return [
        # 充電上限
        BaseNumberEntity(
            client, self, "bmsMaxChargeSoc", "Max Charge Level", "%",
            50, 100, 1,
            lambda value, params: self._create_charge_limit_command(int(value)),
            attr={
                "setting_type": "charge_limit",
                "safety_range": "50-100",
                "default_value": 80
            }
        ),

        # 放電下限
        BaseNumberEntity(
            client, self, "bmsMinDischargeSoc", "Min Discharge Level", "%",
            0, 30, 1,
            lambda value, params: self._create_discharge_limit_command(int(value)),
            attr={
                "setting_type": "discharge_limit",
                "safety_range": "0-30",
                "default_value": 10
            }
        ),

        # AC充電電力
        BaseNumberEntity(
            client, self, "invCfgSlowChgWatts", "AC Charging Power", "W",
            400, 2900, 100,
            lambda value, params: self._create_ac_charge_power_command(int(value)),
            attr={
                "setting_type": "charge_power",
                "power_type": "ac_input",
                "step_size": 100
            }
        ),
    ]
```

## 6. Phase 4: セレクトエンティティ詳細実装

### **6.1 タイムアウト設定セレクト**

#### **タイムアウト制御セレクト**
```python
def _timeout_selects(self, client: EcoflowApiClient) -> list[BaseSelectEntity]:
    """タイムアウト制御セレクトエンティティ"""
    return [
        # スクリーンタイムアウト
        BaseSelectEntity(
            client, self, "pdLcdOffSec", "Screen Timeout",
            ["Never", "10sec", "30sec", "1min", "5min", "30min"],
            lambda value, params: self._create_screen_timeout_command(value),
            attr={
                "setting_type": "display",
                "feature": "auto_off",
                "power_saving": True
            }
        ),

        # ユニットタイムアウト
        BaseSelectEntity(
            client, self, "pdStandbyMode", "Unit Timeout",
            ["Never", "30min", "1hr", "2hr", "6hr", "12hr"],
            lambda value, params: self._create_unit_timeout_command(value),
            attr={
                "setting_type": "power_management",
                "feature": "standby_mode",
                "power_saving": True
            }
        ),
    ]
```

## 7. 成果物・次ステップ

### **7.1 期待される成果物**
- [ ] **包括的センサーエンティティ**: 50+個のセンサー
- [ ] **完全なスイッチエンティティ**: 主要制御機能100%カバー
- [ ] **詳細ナンバーエンティティ**: 充電・バックアップ制御
- [ ] **豊富なセレクトエンティティ**: タイムアウト・モード設定
- [ ] **属性情報充実**: 各エンティティの詳細メタデータ

### **7.2 品質基準**
- [ ] **機能網羅性**: DP3主要機能95%以上カバー
- [ ] **型安全性**: 完全な型ヒント対応
- [ ] **属性充実**: 各エンティティに適切なメタデータ
- [ ] **命名一貫性**: 既存デバイスとの統一性

### **7.3 次ステップへの引き継ぎ**
- [ ] **コマンド送信実装**: 詳細コマンド処理
- [ ] **HA統合テスト**: 実際のHA環境でのテスト
- [ ] **実機テスト**: 実機での動作検証

---

## 備考

- **既存パターン踏襲**: Delta Pro/Delta 2 Maxとの一貫性
- **DP3特有機能**: 新機能への対応
- **属性充実**: 各エンティティの詳細情報
- **拡張性**: 将来の機能追加に対応

このタスクの完了により、DP3のHome Assistant統合エンティティが完成します。