# Delta Pro 3 不明エンティティ調査記録

## 調査日時
2025-10-14

## 対象エンティティ（不明なもの）
1. **Cycles** (診断センサー)
2. **Total Charge Energy** (センサー)
3. **Total Discharge Energy** (センサー)

## 現在の実装状況

### センサー定義（delta_pro_3.py）
```python
# 69行目
CyclesSensorEntity(client, self, "cycles", const.CYCLES),

# 175-177行目
InEnergySensorEntity(client, self, "accu_chg_energy", "Total Charge Energy"),

# 178-180行目
OutEnergySensorEntity(client, self, "accu_dsg_energy", "Total Discharge Energy"),
```

### Protobuf定義（ef_dp3_iobroker.proto）
```protobuf
message BMSHeartBeatReport {
  optional uint32 cycles = 14;                  // サイクル数
  optional uint32 accu_chg_energy = 79;         // 累積充電エネルギー (Wh)
  optional uint32 accu_dsg_energy = 80;         // 累積放電エネルギー (Wh)
}
```

### デコードロジック（delta_pro_3.py: 634-645行目）
```python
elif (cmd_func == 3 and cmd_id in [1, 2, 30, 50]) or \
     (cmd_func == 254 and cmd_id in [24, 25, 26, 27, 28, 29, 30]) or \
     (cmd_func == 32 and cmd_id in [1, 3, 51, 52]):
    # BMSHeartBeatReport
    try:
        msg = pb2.BMSHeartBeatReport()
        msg.ParseFromString(pdata)
        _LOGGER.info(f"✅ Successfully decoded BMSHeartBeatReport: cmdFunc={cmd_func}, cmdId={cmd_id}")
        return self._protobuf_to_dict(msg)
    except Exception as e:
        _LOGGER.debug(f"Failed to decode as BMSHeartBeatReport (cmdFunc={cmd_func}, cmdId={cmd_id}): {e}")
```

**問題**: 複数のcmdFunc/cmdId候補を試行しているが、正しい組み合わせが不明

## 対比: 動作しているBMSエンティティ

以下のBMS関連エンティティは正常に動作している：

| エンティティ | フィールド名 | 値 | メッセージソース |
|---|---|---|---|
| Main Battery Level | `bms_batt_soc` | 4.44% | DisplayPropertyUpload |
| State of Health | `bms_batt_soh` | 100% | DisplayPropertyUpload |
| Max Charge SOC | `cms_max_chg_soc` | 100% | DisplayPropertyUpload |
| Min Discharge SOC | `cms_min_dsg_soc` | 0% | DisplayPropertyUpload |
| Battery Temperature | `bms_max_mos_temp` | 29°C | DisplayPropertyUpload |
| Max Cell Temp | `bms_max_cell_temp` | 28°C | DisplayPropertyUpload |
| Charge Remaining Time | `bms_chg_rem_time` | 341m | DisplayPropertyUpload |
| Discharge Remaining Time | `bms_dsg_rem_time` | 0m | DisplayPropertyUpload |

**重要**: これらは全て**DisplayPropertyUpload** (cmdFunc=254, cmdId=21)から取得されている！

## 仮説

### 仮説1: BMSHeartBeatReportが送信されていない
Delta Pro 3がBMSHeartBeatReportメッセージを送信していない可能性。
- DisplayPropertyUploadのみ送信している
- BMSHeartBeatReportは特定条件下でのみ送信される

**検証方法**: MQTTメッセージキャプチャで全メッセージタイプを確認

### 仮説2: cycles/accu_*_energyがDisplayPropertyUploadに含まれている
これらのフィールドがBMSHeartBeatReportではなく、DisplayPropertyUploadに含まれている可能性。

**検証方法**: DisplayPropertyUploadのprotobuf定義を確認

<function_calls>
<invoke name="Bash">
<parameter name="command">grep -A5 -B5 "message DisplayPropertyUpload" custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto | head -30