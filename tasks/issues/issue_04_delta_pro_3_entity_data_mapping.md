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

- [ ] 実際の MQTT メッセージ受信状況確認
- [ ] `_prepare_data`メソッドでのデコード結果ログ出力
- [ ] `device_data`へのデータ格納状況確認

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
