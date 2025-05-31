# Issue 05: Delta Pro 3 の `_prepare_data` メソッド実装

## 問題の概要

Issue 04 で特定した根本原因を解決するため、Delta Pro 3 に **Protobuf データ専用の `_prepare_data` メソッド**をオーバーライド実装する。

## Issue 04 からの継続事項

### **特定された根本原因**

Delta Pro 3 で `_prepare_data` メソッドがオーバーライドされておらず、BaseDevice の JSON パーサーが Protobuf バイナリデータに対して実行されて失敗している。

### **受信データの詳細**

- **データ形式**: Protobuf バイナリデータ
- **データサイズ**: 約 400 バイト
- **データ例**: `b'\n\x9b\x03\n\x83\x03\x08\x00\x10\x01\x18\x02 \x00(\xe9...'`
- **データトピック**: `/app/device/property/MR51ZJS4PG6C0181` (正常)

### **現在の失敗処理**

```python
# BaseDevice._prepare_data での失敗
def _prepare_data(self, raw_data) -> dict[str, any]:
    try:
        payload = raw_data.decode("utf-8", errors="ignore")  # ❌ Protobuf に UTF-8 デコード
        return json.loads(payload)                           # ❌ JSON パース試行で失敗
    except Exception as error1:
        _LOGGER.error(f"constant: {error1}. Ignoring message...")  # ❌ エラーで処理中断
```

## 実装要件

### **1. Protobuf デコード処理**

- `ef_dp3_iobroker_pb2` を使用したメッセージデコード
- XOR デコード処理（必要に応じて）
- エラーハンドリング

### **2. 出力データ形式**

```python
# 期待される出力形式（辞書）
{
    "bms_batt_soc": 85,           # バッテリー SOC
    "pow_out_sum_w": 1250,        # 総出力電力
    "pow_in_sum_w": 0,            # 総入力電力
    "bms_design_cap": 3600,       # 設計容量
    # ... その他のフィールド
}
```

### **3. フィールド名マッピング**

Protobuf で定義されている実際のフィールド名を使用:

- `bms_batt_soc` (バッテリー SOC)
- `pow_out_sum_w` (総出力電力)
- `pow_in_sum_w` (総入力電力)
- `bms_design_cap` (設計容量)
- その他、proto ファイルで定義されたフィールド

## 実装方針

### **Option A: 最小限の実装**

既存のプロトコル解析ロジックを流用して、最小限の `_prepare_data` メソッドを実装

### **Option B: 完全なリファクタリング**

調査用スクリプトから移植された複雑な処理を整理し、標準的なパターンに修正

## 作業項目

### **Phase 1: 既存コードの分析**

- [ ] 1. 調査用スクリプトの `_prepare_data` 相当処理の確認

  - ファイル: `scripts/ecoflow_mqtt_parser.py` (またはそれに相当するファイル)
  - 確認項目: XOR デコード、Protobuf デコード、メッセージタイプ判定

- [ ] 2. Delta Pro 3 の protobuf 定義確認

  - ファイル: `custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto`
  - 確認項目: メッセージタイプ、フィールド定義、階層構造

- [ ] 3. 他の internal デバイスの `_prepare_data` 実装確認
  - 比較対象: Delta Pro, Delta 2 等の実装パターン
  - 確認項目: Protobuf を使用している場合の処理方法

### **Phase 2: 実装**

- [ ] 4. Delta Pro 3 の `_prepare_data` メソッド実装

  - 機能: Protobuf バイナリデータをデコードして辞書を返す
  - エラーハンドリング: デコード失敗時の適切な例外処理
  - ログ出力: デバッグ用の適切なログ

- [ ] 5. テスト実装
  - 単体テスト: 実際の受信データでのデコード確認
  - 統合テスト: Home Assistant でのエンティティ値表示確認

### **Phase 3: 検証**

- [ ] 6. sensors メソッド実行確認

  - ブレークポイント: `def sensors(self, client: EcoflowApiClient)`
  - 確認項目: メソッドが正常に呼ばれるか

- [ ] 7. エンティティ値表示確認

  - Home Assistant UI でのセンサー値確認
  - Developer Tools での状態確認

- [ ] 8. ログエラーの解消確認
  - `home-assistant.log` でのエラーメッセージ確認
  - 継続的な動作の確認

## 技術的考慮事項

### **Protobuf メッセージタイプの特定**

```python
# 受信データからのメッセージタイプ判定が必要
# 例: DisplayPropertyUpload, RuntimePropertyUpload など
```

### **XOR デコード処理**

```python
# Delta Pro 3 特有の XOR エンコーディングへの対応
# seq 値を使用したデコード処理
```

### **エラーハンドリング**

```python
# デコード失敗時の適切な処理
# 部分的なデータでも可能な限り処理を継続
```

## 期待される効果

### **直接的な効果**

1. ✅ sensors メソッドが正常に実行される
2. ✅ Home Assistant でエンティティ値が表示される
3. ✅ MQTT データが正常にデコードされる

### **間接的な効果**

1. ✅ 他の Protobuf デバイスへの実装パターン確立
2. ✅ Delta Pro 3 の完全な機能利用
3. ✅ 保守性・可読性の向上

## 関連ファイル

### **実装対象**

- `custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py`

### **参考ファイル**

- `custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker_pb2.py`
- `custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto`
- `scripts/ecoflow_mqtt_parser.py` (調査用スクリプト)

### **テスト対象**

- Home Assistant UI (センサー値表示)
- `home-assistant.log` (エラーログ)

## 前提条件

- Issue 04 で特定した根本原因の理解
- Protobuf ファイルの存在確認 (✅ 完了)
- デバイス認識の正常動作確認 (✅ 完了)
- MQTT データ受信の正常動作確認 (✅ 完了)

---

**次のアクション**: Phase 1 の既存コード分析から開始
