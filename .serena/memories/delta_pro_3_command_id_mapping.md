# Delta Pro 3 コマンドID対応関係

このドキュメントはDelta Pro 3のMQTTコマンドIDとその用途の対応関係をまとめたものです。

## データ受信用メッセージタイプ (cmdFunc/cmdId)

Delta Pro 3は複数の異なるメッセージタイプを受信します。これらは `_decode_message_by_type` メソッドで処理されます。

### 受信メッセージ

| cmdFunc | cmdId | メッセージタイプ | プロトコルバッファ定義 | 説明 |
|---------|-------|------------------|----------------------|------|
| 254 | 21 | DisplayPropertyUpload | DisplayPropertyUpload | ディスプレイプロパティ（表示情報） |
| 32 | 2 | cmdFunc32_cmdId2_Report | cmdFunc32_cmdId2_Report | EMS（エネルギー管理システム）情報 |
| 32 | 50 | RuntimePropertyUpload | RuntimePropertyUpload | ランタイムプロパティ（実行時情報） |
| 254 | 22 | RuntimePropertyUpload | RuntimePropertyUpload | ランタイムプロパティ（頻繁更新データ） |
| 254 | 23 | cmdFunc254_cmdId23_Report | cmdFunc254_cmdId23_Report | タイムスタンプ付きレポート |

## 設定コマンドID (送信用)

Delta Pro 3の各エンティティは特定のコマンドIDを使用して設定を送信します。

### Numbers (数値設定)

| エンティティ | フィールド名 | コマンドID | パラメータ名 | 範囲 | 説明 |
|------------|------------|-----------|------------|------|------|
| Max Charge Level | cms_max_chg_soc | 49 | cmsMaxChgSoc | 50-100% | 最大充電レベル |
| Min Discharge Level | cms_min_dsg_soc | 51 | cmsMinDsgSoc | 0-30% | 最小放電レベル |
| AC Charging Power | plug_in_info_ac_in_chg_pow_max | 69 | plugInInfoAcInChgPowMax | 200-3000W | AC充電電力 |

### Switches (スイッチ)

| エンティティ | フィールド名 | コマンドID | パラメータ名 | 説明 |
|------------|------------|-----------|------------|------|
| Beeper | en_beep | 38 | enBeep | ブザー音の有効/無効 |
| AC HV Output Enabled | cfg_hv_ac_out_open | 66 | cfgHvAcOutOpen | AC高電圧出力の有効/無効 |
| AC LV Output Enabled | cfg_lv_ac_out_open | 66 | cfgLvAcOutOpen | AC低電圧出力の有効/無効 |
| 12V DC Output Enabled | cfg_dc_12v_out_open | 81 | cfgDc12vOutOpen | 12V DC出力の有効/無効 |
| 24V DC Output Enabled | cfg_dc_24v_out_open | 81 | cfgDc24vOutOpen | 24V DC出力の有効/無効 |
| X-Boost Enabled | xboost_en | 66 | xboostEn | X-Boost機能の有効/無効 |
| AC Energy Saving Enabled | ac_energy_saving_open | 95 | acEnergySavingOpen | AC省エネモードの有効/無効 |
| GFCI Protection Enabled | llc_gfci_flag | 153 | llcGFCIFlag | GFCI保護の有効/無効 |

### Selects (選択肢)

| エンティティ | フィールド名 | コマンドID | パラメータ名 | 説明 |
|------------|------------|-----------|------------|------|
| Screen Timeout | screen_off_time | 39 | screenOffTime | 画面オフタイムアウト |
| AC Timeout | ac_standby_time | 10 | acStandbyTime | ACスタンバイタイムアウト |
| DC Timeout | dc_standby_time | 33 | dcStandbyTime | DCスタンバイタイムアウト |
| AC Output Type | plug_in_info_ac_out_type | 59 | plugInInfoAcOutType | AC出力タイプ (HV+LV/HV Only/LV Only) |

## プロトコルバッファ `set_dp3` メッセージ内の全コマンドID

`set_dp3` メッセージには以下のコマンドIDが定義されています（一部は未実装）:

| コマンドID | パラメータ名 | 説明 | 実装状況 |
|-----------|------------|------|---------|
| 3 | cfgPowerOff | 電源オフ設定 | 未実装 |
| 9 | enBeep | ブザー音 | 実装済 (ID: 38) |
| 10 | acStandbyTime | ACスタンバイタイム | 実装済 |
| 11 | dcStandbyTime | DCスタンバイタイム | 実装済 (ID: 33) |
| 12 | screenOffTime | 画面オフタイム | 実装済 (ID: 39) |
| 13 | devStandbyTime | デバイススタンバイタイム | 未実装 |
| 14 | lcdLight | LCD輝度 | 未実装 |
| 15 | cfgHvAcOutOpen | AC高電圧出力 | 実装済 (ID: 66) |
| 16 | cfgLvAcOutOpen | AC低電圧出力 | 実装済 (ID: 66) |
| 18 | cfgDc12vOutOpen | 12V DC出力 | 実装済 (ID: 81) |
| 25 | xboostEn | X-Boost | 実装済 (ID: 66) |
| 33 | cmsMaxChgSoc | 最大充電SOC | 実装済 (ID: 49) |
| 34 | cmsMinDsgSoc | 最小放電SOC | 実装済 (ID: 51) |
| 52 | plugInInfoPvLDcAmpMax | PV低電圧DC最大電流 | 未実装 |
| 53 | plugInInfoPvHDcAmpMax | PV高電圧DC最大電流 | 未実装 |
| 54 | plugInInfoAcInChgPowMax | AC入力充電最大電力 | 実装済 (ID: 69) |
| 56 | plugInfo_5p8ChgPowMax | 5P8充電最大電力 | 未実装 |
| 58 | cmsOilSelfStart | 発電機自動起動 | 未実装 |
| 59 | cmsOilOnSoc | 発電機起動SOC | 未実装 |
| 60 | cmsOilOffSoc | 発電機停止SOC | 未実装 |
| 61 | llc_GFCIFlag | GFCI保護 | 実装済 (ID: 153) |
| 99 | acEnergySavingOpen | AC省エネモード | 実装済 (ID: 95) |
| 100 | multiBpChgDsgMode | マルチバッテリーパック充放電モード | 未実装 |
| 102 | lowDischargeLimitCmd | 低放電制限コマンド (非EF-API) | 未実装 |
| 167 | unknown167 | 不明 | 未実装 |

## コマンド送信フォーマット

すべての設定コマンドは以下の形式で送信されます:

```python
{
    "moduleType": 0,
    "operateType": "TCP",
    "params": {
        "id": <コマンドID>,
        "<パラメータ名>": <値>
    }
}
```

## 注意点

1. **コマンドIDの重複**: 複数のパラメータが同じコマンドIDを共有する場合があります（例: ID 66 は cfgHvAcOutOpen, cfgLvAcOutOpen, xboostEn を含む）
2. **XORデコード**: encType == 1 かつ src != 32 の場合、ペイロードデータはseq値でXORデコードされます
3. **Base64エンコード**: 一部のデータはBase64エンコードされている場合があります
4. **未実装機能**: プロトコルバッファに定義されているが、Home Assistantインテグレーションには実装されていない機能が多数あります

## 参考ファイル

- Protobuf定義: `custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto`
- 実装: `custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py`
- 設定メッセージ定義: `set_dp3` および `setReply_dp3` in proto file
