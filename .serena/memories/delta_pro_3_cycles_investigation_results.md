# Delta Pro 3 - Cycles/Energy エンティティ調査結果

## 調査日: 2025-10-14

## 背景

前回のコミット後、UTF-8デコードエラーが発生し、BaseDeviceをupstream状態に復元しました。復元後、41/44エンティティが動作していますが、以下の3つが依然として利用不可：

- Cycles (サイクル数)
- Total Charge Energy (累積充電エネルギー)
- Total Discharge Energy (累積放電エネルギー)

これらは`BMSHeartBeatReport`メッセージの以下のフィールドから取得する想定：
- `cycles` (field 14)
- `accu_chg_energy` (field 79)
- `accu_dsg_energy` (field 80)

## 調査方法

1. `/config/configuration.yaml`にデバッグログ設定を追加
2. Home Assistantを再起動してMQTTメッセージを収集
3. 約5分間のログを分析

## 調査結果

### 受信しているMQTTメッセージ

デバッグログから特定した全cmdFunc/cmdId組み合わせ：

| cmdFunc | cmdId | 送信頻度 | フィールド数 | 主なフィールド | メッセージタイプ（推定） |
|---------|-------|---------|-------------|---------------|---------------------|
| 254 | 21 | 約2秒 | 28 | soc, soh, max_chg_soc, min_dsg_soc | DisplayPropertyUpload ✅ |
| 254 | 22 | 1分 | 5-8 | pow_get_l1, pow_get_l2, llc_bat_cur | 不明 |
| 32 | 2 | 10秒 | 28 | cms_batt_soc, cms_batt_vol_mv, cms_max_chg_soc | 不明 |
| 32 | 50 | 10秒 | 3 | ac_phase_type, pcs_work_mode, plug_in_info_pv_l_vol | 不明 |

### 重要な発見

**BMSHeartBeatReportは受信されていない**

現在の`_decode_message_by_type`メソッドでは、以下の条件でBMSHeartBeatReportをデコードしようとしています：

```python
elif (cmd_func == 3 and cmd_id in [1, 2, 30, 50]) or \
     (cmd_func == 254 and cmd_id in [24, 25, 26, 27, 28, 29, 30]) or \
     (cmd_func == 32 and cmd_id in [1, 3, 51, 52]):
```

しかし、実際に受信している`cmdFunc=32`のメッセージは`cmdId=2`と`cmdId=50`であり、これらの条件に一致しません。

### cmdFunc=32, cmdId=2 の詳細

このメッセージは最も有望な候補でしたが、詳細分析の結果：

**デコード結果例**:
```python
{
  'msg32_2_1': {
    'cms_batt_soc': 55.110126,
    'cms_batt_vol_mv': 27085,
    'cms_max_chg_soc': 100,
    'cms_min_dsg_soc': 5,
    'cms_chg_rem_time': 255,
    'cms_dsg_rem_time': 5939,
    # ... 他のフィールド
  },
  'msg32_2_2': {
    'cms_status_misc13': 0,
    # ...
  }
}
```

**結論**: `cycles`, `accu_chg_energy`, `accu_dsg_energy` は含まれていません。

## 考えられる原因

### 原因1: BMSHeartBeatReportは特定の条件でのみ送信される

可能性のあるトリガー条件：
- 充電開始/終了時
- 放電開始/終了時
- バッテリー状態の大きな変化
- 定期的な長い間隔（例：1時間、1日）
- デバイスの再起動時

**検証方法**: 
- 充電を開始してログを監視
- より長時間（数時間〜1日）ログを収集

### 原因2: ファームウェアがこれらのフィールドを送信しない

Delta Pro 3のファームウェアバージョンによって：
- 古いファームウェア：cycles/accu_*_energyを送信しない
- 新しいファームウェア：送信する
- または、このデータはクラウドAPI経由でのみ利用可能

**検証方法**:
- EcoFlowアプリでこれらの値が表示されるか確認
- 公式APIでこれらのフィールドが利用可能か確認

### 原因3: cmdFunc/cmdIdの誤解

BMSHeartBeatReportは異なるcmdFunc/cmdIdで送信されているが、現在のprotobuf定義と一致しない。

**検証方法**:
- すべての不明なメッセージタイプをBMSHeartBeatReportとしてデコード試行
- 特に`cmdFunc=32, cmdId=2`を試す

## 次のステップ

### オプションA: 長時間監視（推奨）

```bash
# 24時間ログを収集
tail -f /config/home-assistant.log | grep -E "(cmdFunc|BMSHeartBeatReport)" > /tmp/mqtt_24h.log &
```

1日後、ログを分析して新しいcmdFunc/cmdIdが出現するか確認。

### オプションB: 充電トリガーテスト

1. 現在の充電を停止
2. ログ監視を開始
3. 充電を再開
4. ログで新しいメッセージタイプが出現するか確認

### オプションC: 代替フィールドマッピング

`cmdFunc=32, cmdId=2`をBMSHeartBeatReportとして強制的にデコードしてみる：

```python
# delta_pro_3.pyの_decode_message_by_typeに追加
elif cmd_func == 32 and cmd_id == 2:
    try:
        msg = pb2.BMSHeartBeatReport()
        msg.ParseFromString(pdata)
        _LOGGER.info(f"✅ Decoded cmdFunc=32/cmdId=2 as BMSHeartBeatReport")
        return self._protobuf_to_dict(msg)
    except Exception as e:
        _LOGGER.warning(f"Failed to decode cmdFunc=32/cmdId=2 as BMSHeartBeatReport: {e}")
        # 既存のデコードにフォールバック
```

### オプションD: EcoFlowアプリ確認

EcoFlowアプリで以下を確認：
- Battery Cycles値が表示されるか？
- Total Charge/Discharge Energyが表示されるか？

表示される場合 → データはクラウド側に存在
表示されない場合 → ハードウェア/ファームウェアが対応していない

### オプションE: ユーザーにコミット提案

現在の状態（41/44エンティティ動作、93.2%成功率）で一旦コミットし、残りの3エンティティは将来の調査課題とする。

## 推奨アクション

**段階的アプローチ**:

1. **即座に**: 現在の修正（UTF-8エラー解決、BaseDevice復元）をコミット
2. **短期**: オプションCを試す（cmdFunc=32/cmdId=2をBMSHeartBeatReportとして試行）
3. **中期**: オプションAを実行（24時間監視）
4. **長期**: EcoFlowアプリ/公式APIでデータ可用性を確認

## ファイル情報

### 調査に使用したログファイル
- `/tmp/ha_debug_new.log` - Home Assistant起動ログ（約10分）
- `/config/configuration.yaml` - デバッグログ設定

### 関連コードファイル
- `custom_components/ecoflow_cloud/devices/__init__.py` - BaseDevice（upstream復元済み）
- `custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py` - DeltaPro3Device
- `custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto` - BMSHeartBeatReport定義

### 関連メモリ
- `delta_pro_3_bms_heartbeat_implementation.md` - 実装メモ
- `delta_pro_3_entity_status_after_utf8_fix.md` - 現在のエンティティ状態

## 結論

**BMSHeartBeatReportメッセージは現在のMQTT通信では受信されていません。**

これは以下のいずれかを意味します：
1. 特定の条件（充電中など）でのみ送信される
2. ファームウェアバージョンがこの機能に対応していない
3. cmdFunc/cmdIdマッピングが完全に間違っている

**推奨**: 現在の修正をコミットし、残りの3エンティティは段階的に調査を続ける。93.2%のエンティティが動作しているため、統合は十分に機能的です。