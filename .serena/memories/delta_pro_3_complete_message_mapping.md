# Delta Pro 3 完全メッセージマッピング対応表

このドキュメントは、EcoFlow Delta Pro 3のMQTTメッセージとProtobufメッセージタイプの完全な対応関係をまとめたものです。

## 概要

Delta Pro 3は複数の異なるProtobufメッセージタイプを使用してデータを送信します。**重要な発見: `BMSHeartBeatReport`メッセージが我々の実装に欠けており、これにcyclesとenergyフィールドが含まれています。**

## メッセージタイプ対応表

### 現在実装済みのメッセージ

| cmdFunc | cmdId | メッセージタイプ | protoメッセージ名 | 送信元 | 送信頻度 | 主な用途 | 実装状況 |
|---------|-------|------------------|-------------------|--------|----------|----------|----------|
| 254 | 21 | Display Property Upload | `DisplayPropertyUpload` | デバイス | 低頻度 | UI表示用データ、設定値 | ✅ 実装済 |
| 254 | 22 | Runtime Property Upload | `RuntimePropertyUpload` | デバイス | 高頻度 | リアルタイムデータ | ✅ 実装済 |
| 32 | 2 | EMS Heartbeat | `cmdFunc32_cmdId2_Report` | EMS (3) | 中頻度 | CMS/BMSサマリー情報 | ✅ 実装済 |
| 32 | 50 | BMS Detail Report | `cmdFunc50_cmdId30_Report` | BMS (3) | 中頻度 | BMS詳細データ | ✅ 実装済 |
| 254 | 23 | Timestamp Report | `cmdFunc254_cmdId23_Report` | デバイス | 低頻度 | タイムスタンプ付きレポート | ✅ 実装済 |

### ❌ 未実装の重要メッセージ

| cmdFunc | cmdId | メッセージタイプ | protoメッセージ名 | 送信元 | 送信頻度 | 主な用途 | 重要度 |
|---------|-------|------------------|-------------------|--------|----------|----------|--------|
| **?** | **?** | **BMS Heartbeat** | **`BMSHeartBeatReport`** | **BMS** | **高頻度** | **BMSハートビート（cycles, energy含む）** | **🔥 最高** |

**注意**: `BMSHeartBeatReport`の`cmdFunc/cmdId`は現時点で未確定。実際のMQTTログまたはioBrokerのデコードロジックから確認が必要。

## フィールド対応: 不明エンティティの解決

### 現在「不明」になっているエンティティ

| HAエンティティ名 | 現在の実装フィールド | 実際の送信元 | 正しいフィールド名 | メッセージタイプ |
|---|---|---|---|---|
| Battery Cycles | `bms_cycles` | ❌ 存在しない | `cycles` | `BMSHeartBeatReport` |
| Total Input Energy | `pow_in_sum_energy` | ❌ 存在しない | 計算または別フィールド | - |
| Total Output Energy | `pow_out_sum_energy` | ❌ 存在しない | 計算または別フィールド | - |
| Battery Charge Energy from AC | `ac_in_energy_total` | ❌ 存在しない | 計算または`accu_chg_energy` | `BMSHeartBeatReport` |
| Battery Discharge Energy to AC | `ac_out_energy_total` | ❌ 存在しない | 計算または`accu_dsg_energy` | `BMSHeartBeatReport` |
| Battery Discharge Energy to DC | `dc_out_energy_total` | ❌ 存在しない | 計算または含まれる | `BMSHeartBeatReport` |
| Solar In Energy | `pv_in_energy_total` | ❌ 存在しない | 計算が必要 | - |

## BMSHeartBeatReportの重要フィールド

ioBroker実装から確認された`BMSHeartBeatReport`の主要フィールド:

```protobuf
message BMSHeartBeatReport {
  optional uint32 num = 1;                      // バッテリーパック番号 (0/1/2)
  optional uint32 type = 2;                     // タイプ
  optional uint32 cell_id = 3;                  // セルID
  optional uint32 err_code = 4;                 // エラーコード
  optional uint32 sys_ver = 5;                  // システムバージョン
  
  // ⭐ 基本バッテリー情報
  optional uint32 soc = 6;                      // SOC (%)
  optional uint32 vol = 7;                      // 電圧 (mV)
  optional int32 amp = 8;                       // 電流 (mA)
  optional int32 temp = 9;                      // 温度 (°C)
  
  // ⭐ 容量情報
  optional uint32 design_cap = 11;              // 設計容量 (mAh)
  optional uint32 remain_cap = 12;              // 残容量 (mAh)
  optional uint32 full_cap = 13;                // 満充電容量 (mAh)
  
  // 🔥 重要: cyclesフィールド
  optional uint32 cycles = 14;                  // ⭐⭐⭐ サイクル数
  
  // ⭐ SOH情報
  optional uint32 soh = 15;                     // SOH (%)
  
  // ⭐ セル電圧
  optional uint32 max_cell_vol = 16;            // 最大セル電圧 (mV)
  optional uint32 min_cell_vol = 17;            // 最小セル電圧 (mV)
  
  // ⭐ 温度
  optional int32 max_cell_temp = 18;            // 最大セル温度 (°C)
  optional int32 min_cell_temp = 19;            // 最小セル温度 (°C)
  optional int32 max_mos_temp = 20;             // 最大MOS温度 (°C)
  optional int32 min_mos_temp = 21;             // 最小MOS温度 (°C)
  
  // フィールド22-25省略
  
  // 🔥 重要: 電力フィールド
  optional uint32 input_watts = 26;             // ⭐⭐⭐ 入力電力 (W)
  optional uint32 output_watts = 27;            // ⭐⭐⭐ 出力電力 (W)
  optional uint32 remain_time = 28;             // 残り時間 (min)
  
  // フィールド29-49省略
  
  // 🔥 重要: 累積容量・エネルギー
  optional uint32 accu_chg_cap = 50;            // 累積充電容量 (mAh)
  optional uint32 accu_dsg_cap = 51;            // 累積放電容量 (mAh)
  
  // フィールド52-78省略
  
  // 🔥 重要: 累積エネルギー
  optional uint32 accu_chg_energy = 79;         // ⭐⭐⭐ 累積充電エネルギー (Wh, mult:0.001でkWh)
  optional uint32 accu_dsg_energy = 80;         // ⭐⭐⭐ 累積放電エネルギー (Wh, mult:0.001でkWh)
  
  optional string pack_sn = 81;                 // バッテリーパックシリアル番号
  optional uint32 water_in_flag = 82;           // 浸水フラグ
}
```

### 単位変換

| フィールド | Proto単位 | ioBroker mult | 表示単位 | 備考 |
|---|---|---|---|---|
| `soc` | % (int) | 1 | % | 整数値 |
| `vol` | mV | 0.001 | V | 電圧 |
| `amp` | mA | 0.001 | A | 電流 |
| `temp` | °C | 1 | °C | 温度 |
| `cycles` | count | 1 | cycles | サイクル数 |
| `input_watts` | W | 1 | W | 入力電力 |
| `output_watts` | W | 1 | W | 出力電力 |
| `accu_chg_energy` | Wh | **0.001** | **kWh** | 累積充電エネルギー |
| `accu_dsg_energy` | Wh | **0.001** | **kWh** | 累積放電エネルギー |

## 複数バッテリーパック対応

Delta Pro 3は最大3つのバッテリーパックをサポート:
- **BMSHeartBeatReport0**: メインバッテリー (常に存在)
- **BMSHeartBeatReport1**: 追加バッテリー1 (オプション)
- **BMSHeartBeatReport2**: 追加バッテリー2 (オプション)

ioBroker実装では、各パックを別々のエンティティとして扱います。

## 実装上の課題

### 1. cmdFunc/cmdIdの特定

`BMSHeartBeatReport`がどの`cmdFunc/cmdId`で送信されるかが現時点で不明。以下の方法で確認が必要:

- **方法1**: 実際のMQTTログから確認
- **方法2**: ioBrokerのデコードロジックを詳細に解析
- **方法3**: 既知のcmdFunc/cmdIdで試行（可能性のある組み合わせ）:
  - `cmdFunc=3, cmdId=?`（BMSからの送信の可能性）
  - `cmdFunc=254, cmdId=24-30`（未使用のID範囲）
  - `cmdFunc=32, cmdId=1` または他の未使用ID

### 2. メッセージデコードの優先順位

現在の`_decode_message_by_type`メソッドは以下の順序でメッセージをデコード:

```python
if cmd_func == 254 and cmd_id == 21:      # DisplayPropertyUpload
elif cmd_func == 32 and cmd_id == 2:       # cmdFunc32_cmdId2_Report
elif cmd_func == 32 and cmd_id == 50:      # RuntimePropertyUpload
elif cmd_func == 254 and cmd_id == 22:     # RuntimePropertyUpload
elif cmd_func == 254 and cmd_id == 23:     # cmdFunc254_cmdId23_Report
# ⭐ BMSHeartBeatReportをここに追加する必要がある
```

### 3. エネルギーフィールドの統合

`BMSHeartBeatReport`には総エネルギー（`accu_chg_energy`/`accu_dsg_energy`）のみ存在。AC/DC/PV別のエネルギーは以下の方法で対応:

**オプション1: デバイス累積値のみ使用**
```python
InEnergySensorEntity(client, self, "accu_chg_energy", "Total Charge Energy")
OutEnergySensorEntity(client, self, "accu_dsg_energy", "Total Discharge Energy")
```

**オプション2: Home Assistant積算を併用**
```python
# デバイス累積値
InEnergySensorEntity(client, self, "accu_chg_energy", "Total Charge Energy (Device)")

# HA積算値（詳細内訳）
InWattsSensorEntity(client, self, "pow_get_ac_in", const.AC_IN_POWER).with_energy()
OutWattsSensorEntity(client, self, "pow_get_ac", const.AC_OUT_POWER).with_energy()
InWattsSolarSensorEntity(client, self, "pow_get_pv_h", "Solar HV Input Power").with_energy()
```

**推奨**: オプション2（両方実装）
- デバイス累積値: 長期的な正確性、デバイス再起動後も継続
- HA積算値: 詳細な内訳、リアルタイムデータ

## 次のステップ

1. **`BMSHeartBeatReport`の`cmdFunc/cmdId`を特定**
   - 実際のMQTTログを確認
   - ioBrokerのデコードロジックをさらに深く調査
   
2. **protobuf定義に`BMSHeartBeatReport`を追加**
   - `ef_dp3_iobroker.proto`に完全な定義を追加
   - `protoc`でコンパイル
   
3. **`delta_pro_3.py`の実装を更新**
   - `_decode_message_by_type`に`BMSHeartBeatReport`のケースを追加
   - センサー定義を更新（cycles, energy追加）
   - 不要なフィールド参照を削除
   
4. **複数バッテリーパック対応を検討**
   - 初期実装はメインパック（0）のみ
   - 将来的に追加パック（1,2）にも対応

## 参考資料

- ioBroker.ecoflow-mqtt: `lib/dict_data/ef_deltapro3_data.js`
- ioBroker protoSource: BMSHeartBeatReport完全定義
- issue_03: cmdFunc50_cmdId30_Reportの詳細解析
- issue_04: Delta Pro 3エンティティデータマッピング