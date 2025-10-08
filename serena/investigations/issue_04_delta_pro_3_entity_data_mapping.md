# Issue 04: Delta Pro 3 エンティティから値を取得できない問題

## 問題の概要

EcoFlow Delta Pro 3 (`delta_pro_3.py`) の現在の実装では、エンティティから正しい値を取得できていない。Home Assistant でセンサーエンティティは作成されているが、データが表示されない状態が発生している。

### 現在確認されている問題

1. **Protobuf インポートエラー**: `ef_dp3_iobroker_pb2` モジュールが見つからない
2. **型互換性エラー**: センサーエンティティの型が `BaseSensorEntity` と互換性がない
3. **データマッピング不整合**: ioBroker のフィールド名と Home Assistant 実装のフィールド名が一致していない
4. **Protobuf デコード問題**: メッセージデコードが正常に動作していない可能性
5. **🚨 実装パターンの不整合**: 調査用スクリプト `ecoflow_mqtt_parser` の影響で、他の `internal` デバイスと実装パターンが大きく異なっている

## 実装パターンの比較分析

### 🔍 正しい内部デバイス実装パターン（delta_pro.py, delta2.py）

```python
# 標準的なインポート構造
from custom_components.ecoflow_cloud.api import EcoflowApiClient
from custom_components.ecoflow_cloud.devices import const, BaseDevice
from custom_components.ecoflow_cloud.entities import BaseSensorEntity, BaseNumberEntity, BaseSwitchEntity, BaseSelectEntity
from custom_components.ecoflow_cloud.sensor import LevelSensorEntity, WattsSensorEntity, RemainSensorEntity, TempSensorEntity

class DeltaPro(BaseDevice):
    def sensors(self, client: EcoflowApiClient) -> list[BaseSensorEntity]:
        return [
            # シンプルな命名パターン
            LevelSensorEntity(client, self, "bmsMaster.soc", const.MAIN_BATTERY_LEVEL),
            WattsSensorEntity(client, self, "pd.wattsInSum", const.TOTAL_IN_POWER),
            WattsSensorEntity(client, self, "pd.wattsOutSum", const.TOTAL_OUT_POWER),
            # チェインメソッドでの属性追加
            .attr("bmsMaster.designCap", const.ATTR_DESIGN_CAPACITY, 0)
        ]
```

### ❌ 現在の delta_pro_3.py の問題実装

```python
# 調査用スクリプトの影響を受けた実装
import logging
import struct
from typing import Any
from google.protobuf.message import DecodeError

# 複雑すぎるProtobufデコード処理
DELTA_PRO_3_MESSAGE_DECODERS = {
    2: {32: "cmdFunc32_cmdId2_Report"},
    21: {254: "DisplayPropertyUpload"},
    # ...
}

class DeltaPro3(BaseDevice):
    def flat_json(self) -> bool:
        """Delta Pro 3 uses protobuf messages, not flat JSON"""
        return False

    def _xor_decode_pdata(self, pdata: bytes, seq: int) -> bytes:
        # 複雑なXORデコード処理...

    def _decode_protobuf_message(self, cmd_id: int, cmd_func: int, pdata: bytes) -> dict[str, Any]:
        # 複雑なProtobufデコード処理...

    def _prepare_data(self, raw_data) -> dict[str, Any]:
        # 複雑なデータ準備処理...

    def sensors(self, client: EcoflowApiClient) -> list[BaseSensorEntity]:
        return [
            # 間違ったフィールド名
            WattsSensorEntity(client, self, "powGetSum", const.TOTAL_OUT_POWER),  # ❌ 実際は powOutSumW
            InWattsSensorEntity(client, self, "powInSum", const.TOTAL_IN_POWER),  # ❌ 実際は powInSumW
        ]
```

## 🔥 根本的な問題

### 1. 実装アプローチの根本的誤り

**問題**: Delta Pro 3 を「特殊な Protobuf デバイス」として実装しているが、他のデバイスも内部的には protobuf を使用しており、特別扱いする必要はない。

**正解**: `BaseDevice` の標準的な `_prepare_data` メソッドを使用し、protobuf デコードはインフラレイヤーで処理すべき。

### 2. 責務の境界違反

**問題**: デバイスクラス内で生の protobuf デコードを実装している

**正解**: デバイスクラスはエンティティ定義のみに集中し、データ変換は基盤クラスに委譲

### 3. 命名規則の不一致

**問題**: フィールド名が ioBroker の実際の名前と一致していない

**正解**: ioBroker の `ef_deltapro3_data.js` で定義されている正確なフィールド名を使用

## 現在の実装状況

### delta_pro_3.py の実装内容

```python
# 現在のセンサー定義例
LevelSensorEntity(client, self, "bmsBattSoc", const.MAIN_BATTERY_LEVEL)
CapacitySensorEntity(client, self, "bmsDesignCap", const.MAIN_DESIGN_CAPACITY, False)
WattsSensorEntity(client, self, "powGetSum", const.TOTAL_OUT_POWER)
InWattsSensorEntity(client, self, "powInSum", const.TOTAL_IN_POWER)
```

### ioBroker での実際のフィールド名 (ef_deltapro3_data.js)

```javascript
// 実際のフィールド名
bmsBattSoc: {  // バッテリーSOC
    min: 0, max: 100, unit_of_measurement: '%',
    entity_type: 'sensor', device_class: 'battery',
    name: 'SOC of the main battery'
},
bmsDesignCap: {  // バッテリー容量
    min: 0, max: 80000, unit_of_measurement: 'mAh',
    entity_type: 'sensor', device_class: 'capacity',
    name: 'Battery capacity'
},
powInSumW: {  // 総入力電力
    min: 0, max: 8000, unit_of_measurement: 'W',
    entity_type: 'sensor', device_class: 'power',
    name: 'Total input power'
},
powOutSumW: {  // 総出力電力
    min: 0, max: 8000, unit_of_measurement: 'W',
    entity_type: 'sensor', device_class: 'power',
    name: 'Total output power'
}
```

### フィールド名の不整合

| Home Assistant 実装 | ioBroker 実際名 | 状態      |
| ------------------- | --------------- | --------- |
| `powGetSum`         | `powOutSumW`    | ❌ 不一致 |
| `powInSum`          | `powInSumW`     | ❌ 不一致 |
| `bmsBattSoc`        | `bmsBattSoc`    | ✅ 一致   |
| `bmsDesignCap`      | `bmsDesignCap`  | ✅ 一致   |

## Protobuf ファイル確認結果

✅ **発見**: `core/config/custom_components/ecoflow_cloud/devices/internal/proto/` に以下のファイルが存在

- `ef_dp3_iobroker.proto` (25KB)
- `ef_dp3_iobroker_pb2.py` (49KB)
- `ef_dp3_iobroker_pb2.pyi` (71KB)

**インポートエラーの原因**: パス指定が間違っている

```python
# ❌ 現在（間違い）
from custom_components.ecoflow_cloud.devices.internal.proto import (
    ef_dp3_iobroker_pb2 as ecopacket_pb2,
)

# ✅ 正しい
from .proto import ef_dp3_iobroker_pb2 as ecopacket_pb2
```

## Linter Errors 詳細

### 1. Protobuf インポートエラー

```
"ef_dp3_iobroker_pb2" は不明なインポート シンボルです
```

**原因**: 相対インポートパスが間違っている

### 2. 型互換性エラー

```
型 "list[EcoFlowDictEntity | CapacitySensorEntity | ...]" の式は戻り値の型 "list[BaseSensorEntity]" と互換性がありません
```

**原因**: エンティティクラスの継承関係に問題がある

## 分析：ioBroker との実装差異

### 1. メッセージタイプマッピング

**ioBroker (ef_deltapro3_data.js)**:

```javascript
const deviceStatesDict = {
  deltapro3: {
    DisplayPropertyUpload: {
      bmsBattSoc: { entity: "number" },
      bmsDesignCap: { entity: "number" },
      powInSumW: { entity: "number" },
      powOutSumW: { entity: "number" },
    },
    RuntimePropertyUpload: {
      // 実行時データ
    },
    cmdFunc32_cmdId2_Report: {
      // コマンドレポート
    },
  },
};
```

**Home Assistant 現在実装**:

```python
DELTA_PRO_3_MESSAGE_DECODERS = {
    2: {32: "cmdFunc32_cmdId2_Report"},
    21: {254: "DisplayPropertyUpload"},
    22: {254: "RuntimePropertyUpload"},
    23: {254: "cmdFunc254_cmdId23_Report"},
}
```

### 2. データ構造の違い

**ioBroker の階層構造**:

```
DisplayPropertyUpload/
├── bmsBattSoc
├── bmsDesignCap
├── powInSumW
└── powOutSumW
```

**Home Assistant 現在実装**:

```
直接フィールドアクセス: "bmsBattSoc", "powGetSum"
```

## 🎯 正しい修正方針

### Phase 0: 実装パターンの正規化

1. **Protobuf デコード処理の削除**

   - `_xor_decode_pdata`, `_decode_protobuf_message`, `_prepare_data` メソッドを削除
   - `DELTA_PRO_3_MESSAGE_DECODERS` を削除
   - `flat_json()` メソッドを削除

2. **標準的な BaseDevice パターンに戻す**

   ```python
   class DeltaPro3(BaseDevice):
       def sensors(self, client: EcoflowApiClient) -> list[BaseSensorEntity]:
           return [
               # 標準的なエンティティ定義のみ
           ]
   ```

3. **不必要なインポートの削除**
   - `logging`, `struct`, `google.protobuf` 関連
   - 複雑な protobuf 処理関連

### Phase 1: フィールド名修正

```python
# ✅ 修正後のセンサー定義
def sensors(self, client: EcoflowApiClient) -> list[BaseSensorEntity]:
    return [
        # 正しいフィールド名を使用
        LevelSensorEntity(client, self, "bmsBattSoc", const.MAIN_BATTERY_LEVEL),
        CapacitySensorEntity(client, self, "bmsDesignCap", const.MAIN_DESIGN_CAPACITY, False),
        InWattsSensorEntity(client, self, "powInSumW", const.TOTAL_IN_POWER),      # 修正
        OutWattsSensorEntity(client, self, "powOutSumW", const.TOTAL_OUT_POWER),   # 修正
    ]
```

## 調査すべき項目

### 1. Protobuf デコード検証

- [x] `ef_dp3_iobroker_pb2.py`の存在確認と生成 ✅ 存在確認済み
- [ ] プロトコル定義ファイル(`ef_dp3_iobroker.proto`)の確認
- [ ] メッセージタイプマッピングの検証

### 2. データフィールドマッピング検証

- [ ] 実際にデコードされたデータ構造の確認
- [ ] ioBroker と Home Assistant のフィールド名対応表作成
- [ ] 階層構造(例: `DisplayPropertyUpload.bmsBattSoc`)への対応

### 3. エンティティクラス型階層の修正

- [ ] `BaseSensorEntity`継承関係の確認
- [ ] 型アノテーション修正
- [ ] Linter エラー解決

### 4. MQTT データ受信確認

- [x] 4. MQTT データ受信の確認
  - ブレークポイント設定: `custom_components/ecoflow_cloud/devices/__init__.py:133`
  - 関数: `update_data(self, raw_data, data_type: str)`
  - 確認結果: ✅ `data_type` と `self.device_info.data_topic` は完全に一致
  - 確認結果: ✅ `raw_data` に Protobuf バイナリデータが正常に受信されている
  - 確認結果: ❌ **`BaseDevice._prepare_data`が JSON デコードを試みて失敗**
  - 根本原因: ✅ **Delta Pro 3 は Protobuf データなのに、BaseDevice は JSON を期待している**

## 想定される根本原因

### 1. フィールド名不整合

Home Assistant の実装で使用しているフィールド名が、実際に protobuf メッセージに含まれるフィールド名と一致していない。

### 2. データ階層の未対応

ioBroker では`DisplayPropertyUpload.bmsBattSoc`のような階層構造を使用しているが、Home Assistant では直接フィールドアクセスを想定している。

### 3. Protobuf メッセージタイプの不一致

`cmdId`/`cmdFunc`の組み合わせとメッセージタイプの対応が間違っている可能性。

### 4. XOR デコードの問題

Delta Pro 3 特有の XOR デコード処理に問題がある可能性。

### 5. **🚨 実装アプローチの根本的誤り**

調査用スクリプトのロジックをそのままデバイスクラスに移植してしまい、Home Assistant 統合の標準パターンから逸脱している。

## 次のアクション

### Phase 0: 実装正規化（最優先）

1. **delta_pro_3.py の完全リファクタリング**
   - 他の internal デバイスと同じパターンに修正
   - 複雑な protobuf デコード処理を削除
   - 標準的な BaseDevice パターンを採用

### Phase 1: 即座に実行すべき調査

1. **実際の MQTT データ確認**

   ```bash
   python scripts/mqtt_capture_dp3_debug.py
   ```

   - 受信データの構造確認
   - デコード結果のログ出力

2. **Protobuf ファイル生成確認**

   ```bash
   find . -name "*dp3*.proto" -o -name "*dp3*pb2.py"
   ```

3. **ioBroker フィールド名との対応確認**
   - `ef_deltapro3_data.js`の全フィールドリスト作成
   - Home Assistant 実装での使用フィールド名リスト作成

### Phase 2: 修正実装

1. **Protobuf インポート修正**
2. **フィールド名マッピング修正**
3. **型エラー修正**
4. **階層データアクセス対応**

### Phase 3: 検証

1. **エンティティ値取得テスト**
2. **Home Assistant 統合テスト**
3. **長期動作確認**

## 関連ファイル

- `core/config/custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py`
- `core/config/custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker_pb2.py` ✅ 存在確認済み
- `ioBroker.ecoflow-mqtt/lib/dict_data/ef_deltapro3_data.js`
- `scripts/mqtt_capture_dp3_debug.py`
- `scripts/ef_dp3_iobroker.proto`

## 参考 Issue

- `issue_01_dp3_mqtt_no_response.md` - MQTT 通信基盤
- `issue_02_response_decode_interpret_error.md` - デコード問題
- `issue_03_data_analysis_and_mapping_update.md` - データマッピング問題

## 🚨 **真の問題点が判明**

### **Protobuf は正常動作、問題はフィールド名の不一致**

protobuf ファイル `ef_dp3_iobroker_pb2.py` を詳細確認した結果：

- ✅ Protobuf インポートは正常
- ✅ メッセージクラスは正常に定義されている
- ❌ **フィールド名が delta_pro_3.py の期待値と完全に異なる**

## 📊 **フィールド名の不一致例**

### delta_pro_3.py で期待しているフィールド名：

```python
"bmsBattSoc"      # バッテリー残量
"bmsDesignCap"    # 設計容量
"powGetSum"       # 総出力電力
"powInSum"        # 総入力電力
```

### 実際の protobuf フィールド名：

```python
"bms_batt_soc"    # アンダースコア区切り
"bms_design_cap"  # アンダースコア区切り
"pow_out_sum_w"   # 異なる名前 + アンダースコア
"pow_in_sum_w"    # 異なる名前 + アンダースコア
```

## 🔍 **具体的な修正が必要な箇所**

### 1. **バッテリー関連**

| delta_pro_3.py | protobuf 実際        | 修正必要 |
| -------------- | -------------------- | -------- |
| `bmsBattSoc`   | `bms_batt_soc`       | ✅       |
| `bmsDesignCap` | `bms_design_cap`     | ✅       |
| `bmsFullCap`   | `bms_full_cap_mah`   | ✅       |
| `bmsRemainCap` | `bms_remain_cap_mah` | ✅       |
| `bmsBattSoh`   | `bms_batt_soh`       | ✅       |

### 2. **電力関連**

| delta_pro_3.py | protobuf 実際   | 修正必要 |
| -------------- | --------------- | -------- |
| `powGetSum`    | `pow_out_sum_w` | ✅       |
| `powInSum`     | `pow_in_sum_w`  | ✅       |
| `powGetAc`     | `pow_get_ac`    | ✅       |
| `powGetAcIn`   | `pow_get_ac_in` | ✅       |

### 3. **温度関連**

| delta_pro_3.py   | protobuf 実際       | 修正必要 |
| ---------------- | ------------------- | -------- |
| `bmsMaxCellTemp` | `bms_max_cell_temp` | ✅       |
| `bmsMinCellTemp` | `bms_min_cell_temp` | ✅       |
| `bmsMaxMosTemp`  | `bms_max_mos_temp`  | ✅       |

## 🛠️ **修正方針**

### **命名規則の統一が必要**

他の internal デバイスと proto ファイルの命名規則を確認した結果、以下の規則に従う必要があることが判明：

#### **1. 他の internal デバイスの命名規則**

**Delta Pro (`delta_pro.py`)**:

```python
# ドット記法（階層構造）
"bmsMaster.soc"           # BMS Master の SOC
"bmsMaster.designCap"     # BMS Master の設計容量
"pd.wattsInSum"           # Power Delivery の入力電力合計
"pd.wattsOutSum"          # Power Delivery の出力電力合計
"inv.inputWatts"          # Inverter の入力電力
```

**Delta 2 (`delta2.py`)**:

```python
# アンダースコア + ドット記法
"bms_bmsStatus.soc"       # BMS Status の SOC
"bms_bmsStatus.designCap" # BMS Status の設計容量
"pd.wattsInSum"           # Power Delivery の入力電力合計
"pd.wattsOutSum"          # Power Delivery の出力電力合計
```

#### **2. Delta Pro 3 Proto ファイルの実際のフィールド名**

**DisplayPropertyUpload メッセージ**:

```proto
optional float pow_in_sum_w = 3;      # 総入力電力
optional float pow_out_sum_w = 4;     # 総出力電力
optional float bms_batt_soc = 242;    # バッテリー SOC
optional float bms_batt_soh = 243;    # バッテリー SOH
optional uint32 bms_design_cap = 248; # バッテリー設計容量
optional float pow_get_ac = 53;       # AC 出力電力
optional float pow_get_ac_in = 54;    # AC 入力電力
```

#### **3. 修正すべきフィールド名マッピング**

| 現在の delta_pro_3.py | Proto 実際値     | 正しい値        |
| --------------------- | ---------------- | --------------- |
| `"bmsBattSoc"`        | `bms_batt_soc`   | ✅ そのまま使用 |
| `"powGetSum"`         | `pow_out_sum_w`  | ✅ そのまま使用 |
| `"powInSum"`          | `pow_in_sum_w`   | ✅ そのまま使用 |
| `"powGetAc"`          | `pow_get_ac`     | ✅ そのまま使用 |
| `"powGetAcIn"`        | `pow_get_ac_in`  | ✅ そのまま使用 |
| `"bmsDesignCap"`      | `bms_design_cap` | ✅ そのまま使用 |

### **修正方針の結論**

1. **✅ Proto フィールド名をそのまま使用**: Delta Pro 3 は他の internal デバイスと異なり、protobuf の生のフィールド名を直接使用する
2. **❌ ドット記法は使用しない**: `bmsMaster.soc` のような階層構造ではなく、`bms_batt_soc` のようなフラット構造
3. **✅ アンダースコア区切りを維持**: `pow_in_sum_w`, `bms_batt_soc` など

### **即座に実行すべき修正**

1. `delta_pro_3.py` の全センサーエンティティのフィールド名を protobuf の実際のフィールド名に変更
2. 型エラーの修正（linter エラー解決）
3. 不要な複雑な protobuf デコード処理の簡素化

### **修正の優先度**

1. **最高優先**: フィールド名の修正（データ取得の根本解決）
2. **高優先**: 型エラーの修正（linter エラー解決）
3. **中優先**: protobuf デコード処理の最適化

## 📝 **次のアクション**

1. ✅ protobuf の全フィールド名を抽出してマッピング表を作成 **完了**
2. delta_pro_3.py の全エンティティ定義を正しいフィールド名に修正
3. 型エラーを修正
4. テスト実行

**これで根本原因が特定できました。フィールド名の不一致が主要な問題です。**

## 🔧 **デバッグ調査確認手順**

### **Phase 1: デバイス認識の確認**

- [x] 1. デバイスタイプマッピングの確認

  - ブレークポイント設定: `custom_components/ecoflow_cloud/devices/registry.py:35`
  - 関数: `get_device_by_type(device_type: str)`
  - 確認結果: ✅ `device_type` が `"DELTA_PRO_3"` で正しく登録されている
  - 確認結果: ✅ 戻り値が `internal_delta_pro_3.DeltaPro3` クラスで正常
  - 確認結果: ✅ registry.py のマッピングは完全に正常、デバイス認識に問題なし

- [x] 2. Internal DeltaPro3 クラスの実行確認

  - ブレークポイント設定: `custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py:43`
  - 位置: `class DeltaPro3(BaseDevice):` 行 → `numbers` メソッドの return 文
  - 確認結果: ✅ デバイスタイプ、名前、SN 入力後に`numbers`メソッドで正常に停止
  - 確認結果: ✅ `self.device_data.device_type`、`name`、`sn`に想定通りの値が格納されている
  - 確認結果: ✅ クラスのインスタンス化は正常に動作、セットアップフローに問題なし

- [x] 3. sensors メソッドの実行確認
  - ブレークポイント設定: `custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py:44`
  - 関数: `def sensors(self, client: EcoflowApiClient)`
  - 確認結果: ❌ **sensors メソッドに到達していない**
  - 確認結果: ❌ 代わりに`update_data`メソッドが繰り返し実行されている
  - 推測: センサーエンティティが作成されていない可能性、エンティティ作成フェーズでの問題

### **Phase 2: MQTT データフローの確認**

- [x] 4. MQTT データ受信の確認
  - ブレークポイント設定: `custom_components/ecoflow_cloud/devices/__init__.py:133`
  - 関数: `update_data(self, raw_data, data_type: str)`
  - 確認結果: ✅ `data_type` と `self.device_info.data_topic` は完全に一致
  - 確認結果: ✅ `raw_data` に Protobuf バイナリデータが正常に受信されている
  - 確認結果: ❌ **`BaseDevice._prepare_data`が JSON デコードを試みて失敗**
  - 根本原因: ✅ **Delta Pro 3 は Protobuf データなのに、BaseDevice は JSON を期待している**

## 🎯 **調査結果と根本原因の特定**

### **✅ 確認できたこと**

1. **デバイス認識**: registry.py でのマッピングは完全に正常
2. **クラスインスタンス化**: DeltaPro3 クラスは正常にインスタンス化される
3. **MQTT データ受信**: Protobuf バイナリデータは正常に受信されている
4. **データトピック**: `data_type` と `self.device_info.data_topic` は完全に一致

### **❌ 根本原因**

**Delta Pro 3 で `_prepare_data` メソッドがオーバーライドされていない**

#### **問題の詳細:**

1. Delta Pro 3 は **Protobuf バイナリデータ**を受信する
2. `BaseDevice._prepare_data` は **JSON データ**を期待してデコードを試行する
3. JSON パースが失敗し、例外発生または None 返却
4. `self.data.update_data(raw)` で空データまたは例外
5. エンティティ初期化が完了しない
6. **sensors メソッドが呼ばれない**

#### **具体的な失敗箇所:**

```python
# BaseDevice._prepare_data の処理
def _prepare_data(self, raw_data) -> dict[str, any]:
    try:
        payload = raw_data.decode("utf-8", errors="ignore")  # ❌ Protobuf に UTF-8 デコードを適用
        return json.loads(payload)                           # ❌ JSON パースを試行
    except Exception as error1:
        _LOGGER.error(f"constant: {error1}. Ignoring message...")  # ❌ エラーでNone返却
```

### **解決に必要な作業**

Delta Pro 3 に **Protobuf データ専用の `_prepare_data` メソッド**をオーバーライド実装する必要がある。

## 📋 **Issue 04 完了**

**調査目的**: Delta Pro 3 エンティティから値を取得できない問題の根本原因特定
**調査結果**: ✅ **根本原因特定完了**
**次のアクション**: `_prepare_data` メソッドのオーバーライド実装 → **Issue 05** で対応

---

**Issue 04 で特定した問題:** Delta Pro 3 で `_prepare_data` メソッドが実装されておらず、BaseDevice の JSON パーサーが Protobuf データに対して実行されて失敗している。

**次の Issue で解決すべき課題:** Delta Pro 3 専用の Protobuf デコード処理を `_prepare_data` メソッドとして実装する。
