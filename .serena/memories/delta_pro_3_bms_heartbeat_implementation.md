# Delta Pro 3 - BMSHeartBeatReport実装メモ

## 実装日: 2025-10-13

## 概要

Delta Pro 3で「不明」になっていた7つのエンティティのうち、3つ（cycles, accu_chg_energy, accu_dsg_energy）を解決するため、ioBrokerから取得した`BMSHeartBeatReport`メッセージをprotobufに追加しました。

## 実装内容

### 1. Protobuf定義追加

**ファイル**: `custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto`

**追加したメッセージ**: `BMSHeartBeatReport` (82フィールド)

**重要フィールド**:
- `cycles = 14` - サイクル数
- `input_watts = 26` - 入力電力 (W)
- `output_watts = 27` - 出力電力 (W)
- `accu_chg_energy = 79` - 累積充電エネルギー (Wh)
- `accu_dsg_energy = 80` - 累積放電エネルギー (Wh)

### 2. Protobuf再コンパイル

```bash
cd custom_components/ecoflow_cloud/devices/internal/proto
python3 -m grpc_tools.protoc --python_out=. --pyi_out=. --proto_path=. ef_dp3_iobroker.proto
```

**確認済み**: `BMSHeartBeatReport`クラスが正しく生成されました

### 3. デコードロジック追加

**ファイル**: `custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py`

**`_decode_message_by_type`メソッドに追加**:

```python
# BMSHeartBeatReport - Battery heartbeat with cycles and energy data
# Note: cmdFunc/cmdId mapping needs verification from actual MQTT logs
# Trying multiple potential combinations based on ioBroker implementation
elif (cmd_func == 3 and cmd_id in [1, 2, 30, 50]) or \
     (cmd_func == 254 and cmd_id in [24, 25, 26, 27, 28, 29, 30]) or \
     (cmd_func == 32 and cmd_id in [1, 3, 51, 52]):
    # BMSHeartBeatReport - contains cycles, input_watts, output_watts, accu_chg_energy, accu_dsg_energy
    try:
        msg = pb2.BMSHeartBeatReport()
        msg.ParseFromString(pdata)
        _LOGGER.info(f"✅ Successfully decoded BMSHeartBeatReport: cmdFunc={cmd_func}, cmdId={cmd_id}")
        return self._protobuf_to_dict(msg)
    except Exception as e:
        _LOGGER.debug(f"Failed to decode as BMSHeartBeatReport (cmdFunc={cmd_func}, cmdId={cmd_id}): {e}")
```

**重要**: cmdFunc/cmdIdの正確な値は実際のMQTTログから確認が必要。複数の候補を試行してログで確認できるようにしています。

### 4. センサー定義更新

**変更前（不明エンティティ）**:
```python
CyclesSensorEntity(client, self, "bms_cycles", const.CYCLES),  # ❌ 存在しない
InEnergySensorEntity(client, self, "pow_in_sum_energy", "Total Input Energy"),  # ❌
OutEnergySensorEntity(client, self, "pow_out_sum_energy", "Total Output Energy"),  # ❌
InEnergySensorEntity(client, self, "ac_in_energy_total", const.CHARGE_AC_ENERGY),  # ❌
OutEnergySensorEntity(client, self, "ac_out_energy_total", const.DISCHARGE_AC_ENERGY),  # ❌
InEnergySensorEntity(client, self, "pv_in_energy_total", const.SOLAR_IN_ENERGY),  # ❌
OutEnergySensorEntity(client, self, "dc_out_energy_total", const.DISCHARGE_DC_ENERGY),  # ❌
```

**変更後（BMSHeartBeatReportから取得）**:
```python
# Cycles from BMSHeartBeatReport
CyclesSensorEntity(client, self, "cycles", const.CYCLES),  # ✅ BMSHeartBeatReport

# Energy sensors from BMSHeartBeatReport
InEnergySensorEntity(client, self, "accu_chg_energy", "Total Charge Energy"),  # ✅
OutEnergySensorEntity(client, self, "accu_dsg_energy", "Total Discharge Energy"),  # ✅
```

## 解決されたエンティティ

| エンティティ | 変更前フィールド | 変更後フィールド | メッセージ | 状態 |
|---|---|---|---|---|
| Battery Cycles | `bms_cycles` (❌) | `cycles` (✅) | BMSHeartBeatReport | 解決 |
| Total Charge Energy | `ac_in_energy_total` (❌) | `accu_chg_energy` (✅) | BMSHeartBeatReport | 解決 |
| Total Discharge Energy | `ac_out_energy_total` (❌) | `accu_dsg_energy` (✅) | BMSHeartBeatReport | 解決 |

## 依然として存在しないエンティティ

以下のエンティティはDelta Pro 3のどのprotobufメッセージにも存在しません:
- ❌ Total Input Energy (`pow_in_sum_energy`)
- ❌ Total Output Energy (`pow_out_sum_energy`)
- ❌ AC/DC/PV別のエネルギー累積値

**代替案**: これらは電力センサーに`.with_energy()`を追加してHome Assistant側で積算する必要があります。

## 次のステップ（必須）

### 1. cmdFunc/cmdIdの特定

`BMSHeartBeatReport`の正確な`cmdFunc/cmdId`を特定する必要があります:

**方法1: Home Assistantログ確認**
```bash
# Home Assistantを再起動後、ログを確認
tail -f /config/home-assistant.log | grep "BMSHeartBeatReport\|Unknown message type"
```

**期待されるログ**:
- 成功: `✅ Successfully decoded BMSHeartBeatReport: cmdFunc=X, cmdId=Y`
- 未知: `Unknown message type: cmdFunc=X, cmdId=Y`

**見つかったら**: 正確な`cmdFunc/cmdId`を`_decode_message_by_type`メソッドに追加

### 2. エンティティ動作確認

Home Assistant UIで以下を確認:
- Battery Cycles: 値が表示されるか
- Total Charge Energy: 値が表示されるか（kWh単位）
- Total Discharge Energy: 値が表示されるか（kWh単位）

### 3. 単位変換の確認

`accu_chg_energy`と`accu_dsg_energy`はWh単位で送信されます。
Home Assistantで自動的にkWh表示されることを確認してください。

## トラブルシューティング

### エンティティがまだ「不明」の場合

**原因1**: `BMSHeartBeatReport`の`cmdFunc/cmdId`が予想と異なる
- **解決**: ログで実際の値を確認して`_decode_message_by_type`を更新

**原因2**: フィールド名のマッピング違い
- **解決**: `_flatten_dict`の出力をログで確認し、フィールド名を調整

**原因3**: メッセージが送信されていない
- **解決**: MQTTキャプチャツールでメッセージを確認

### ログで確認すべき項目

```python
# delta_pro_3.pyに追加済みのログ
_LOGGER.debug(f"Decoding message: cmdFunc={cmd_func}, cmdId={cmd_id}")
_LOGGER.info(f"✅ Successfully decoded BMSHeartBeatReport: cmdFunc={cmd_func}, cmdId={cmd_id}")
_LOGGER.warning(f"Unknown message type: cmdFunc={cmd_func}, cmdId={cmd_id}")
```

## 参考情報

### ioBroker実装
- リポジトリ: https://github.com/foxthefox/ioBroker.ecoflow-mqtt
- ファイル: `lib/dict_data/ef_deltapro3_data.js`
- メッセージ定義: protoSource内のBMSHeartBeatReport

### 関連メモリ
- `delta_pro_3_command_id_mapping.md` - 全メッセージタイプのマッピング
- `delta_pro_3_complete_message_mapping.md` - BMSHeartBeatReport詳細

### 実装コミット
- Branch: dev
- Files:
  - `custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto`
  - `custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker_pb2.py` (generated)
  - `custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker_pb2.pyi` (generated)
  - `custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py`

## 期待される結果

- ✅ Battery Cyclesセンサーが正しい値を表示
- ✅ Total Charge Energyが累積値を表示（kWh）
- ✅ Total Discharge Energyが累積値を表示（kWh）
- ⚠️ 「不明」エンティティが7個 → 4個に減少（残り4個は別の方法で対応が必要）