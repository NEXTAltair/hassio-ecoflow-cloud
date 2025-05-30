# 製品要求仕様書 (PRD)

## EcoFlow Delta Pro 3 MQTT プロトコル統合

### 概要

Home Assistant 向け EcoFlow Cloud カスタムコンポーネントにおける Delta Pro 3 デバイス対応のための製品要求仕様。本仕様は MQTT プロトコルベースの通信および Protocol Buffers を使用したメッセージ処理に基づく。

### cmdId/cmdFunc 対応表 (完全版)

以下は Delta Pro 3 デバイスで使用される MQTT メッセージの cmdId と cmdFunc の完全な対応表です。

#### 受信メッセージ (デバイス → Home Assistant)

| cmdFunc | cmdId | プロトコルバッファメッセージ型 | 送信元 | 機能概要 | 実装状況 |
|---------|-------|---------------------------|--------|----------|----------|
| `32` | `2` | `cmdFunc32_cmdId2_Report` | `3` (BMS) | CMS/BMS サマリー情報、充電制御関連データ | ✅ 実装済み |
| `50` | `30` | `cmdFunc50_cmdId30_Report` | `3` (BMS) | BMS 詳細ランタイムデータ (セル電圧、温度、SOH等) | ✅ 実装済み |
| `254` | `21` | `DisplayPropertyUpload` | デバイス | 表示用プロパティ (UI表示用の状態データ) | ✅ 実装済み |
| `254` | `22` | `RuntimePropertyUpload` | デバイス | ランタイムプロパティ (頻繁更新データ) | ✅ 実装済み |
| `254` | `23` | `cmdFunc254_cmdId23_Report` | デバイス | タイムスタンプ付きレポート | ✅ 実装済み |
| `2` | `255` | `setReply_dp3` | デバイス | SET コマンドに対する応答 | ✅ 実装済み |

#### 送信メッセージ (Home Assistant → デバイス)

| cmdFunc | cmdId | プロトコルバッファメッセージ型 | 送信先 | 機能概要 | 実装状況 |
|---------|-------|---------------------------|--------|----------|----------|
| `20` | `1` | (標準MQTT) | `32` (App) | 全プロパティ取得要求 (Get ALL Quotas) | ✅ 実装済み |
| `各種` | `各種` | `set_dp3` | デバイス | 設定変更コマンド (AC出力、充電上限等) | ✅ 実装済み |
| `調査中` | `調査中` | `RTCTimeSet` | デバイス | RTC時刻設定 | 🔄 調査中 |
| `調査中` | `調査中` | `ProductNameSet` | デバイス | 製品名設定 | 🔄 調査中 |

#### 未分類・追加実装予定

| cmdFunc | cmdId | プロトコルバッファメッセージ型 | 機能概要 | 実装優先度 |
|---------|-------|---------------------------|----------|------------|
| `調査中` | `調査中` | `EventRecordReport` | イベント・エラーログ通知 | 中 |
| `調査中` | `調査中` | `ProductNameGetAck` | 製品名取得応答 | 低 |
| `調査中` | `調査中` | `RTCTimeGetAck` | RTC時刻取得応答 | 低 |
| `調査中` | `調査中` | `SendMsgHart` | ハートビート | 高 |

### 主要メッセージの詳細仕様

#### cmdFunc32_cmdId2_Report (CMS/BMS サマリー)

**重要フィールド:**
- `volt4` (cms_batt_vol_mv): CMS バッテリー電圧 (mV)
- `maxChargeSoc7` (cms_max_chg_soc_percent): 充電上限 SOC (%)
- `soc15` (cms_batt_soc_percent): CMS バッテリー SOC (%)
- `bmsIsConnt16`: BMS 接続状態配列

#### cmdFunc50_cmdId30_Report (BMS 詳細データ)

**重要フィールド:**
- `remainCap12` (bms_remain_cap_mah): バッテリー残容量 (mAh)
- `maxCellTemp18` (bms_max_cell_temp_c): 最高セル温度 (°C)
- `minCellTemp19` (bms_min_cell_temp_c): 最低セル温度 (°C)
- `maxCellVol16` (max_cell_vol_mv): 最大セル電圧 (mV)
- `cellVol33` (cell_vol_mv): 各セル電圧配列 (mV)
- `soh54` (bms_batt_soh_percent_float): バッテリー SOH (%)

#### DisplayPropertyUpload (表示プロパティ)

**主要カテゴリ:**
- 電力関連: `pow_in_sum_w`, `pow_out_sum_w`
- バッテリー: `bms_batt_soc`, `cms_max_chg_soc`
- AC出力: `ac_out_freq_hz_config`, `xboost_en`
- 表示設定: `lcd_light`, `energy_backup_state`

### 実装要件

#### 必須機能
1. **リアルタイムデータ監視**: 全センサーデータの Home Assistant エンティティ化
2. **デバイス制御**: AC出力、充電設定、表示設定の制御
3. **エラーハンドリング**: 通信エラー、デバイスエラーの適切な処理
4. **設定永続化**: デバイス設定の保存・復元

#### パフォーマンス要件
- **メッセージ処理遅延**: < 100ms
- **MQTT接続維持**: 99.9% 可用性
- **メモリ使用量**: < 50MB (通常運用時)

#### セキュリティ要件
- **暗号化通信**: AES-128-ECB ペイロード復号化
- **認証情報保護**: アクセストークンの安全な保存
- **通信ログ**: センシティブデータのマスキング