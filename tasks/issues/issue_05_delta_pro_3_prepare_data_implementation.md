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
- **データトピック**: `/app/device/property/DEVICE_SN` (正常)

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

- [`ef_dp3_iobroker_pb2`](../../custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker_pb2.py) を使用したメッセージデコード
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

### **選択されたアプローチ: ローカル独立スクリプト開発**

`ecoflow_mqtt_parser` は MQTT 接続・認証・リアルタイム処理などの複雑性を持つため、**完全にローカルで動作する独立スクリプト**を作成して `_prepare_data` ロジックを開発・テストする。

### **利点**

- ✅ **高速開発**: HA 起動時間（数十秒〜数分）を回避
- ✅ **デバッグ容易**: 独立環境での即座なログ確認・エラー追跡
- ✅ **集中開発**: Protobuf 解析ロジックのみに専念
- ✅ **制御テスト**: 任意のモックデータでテストケース作成

### **開発フロー**

1. **ローカルスクリプトでロジック開発・検証**
2. **動作確認後、HA に統合**

## 作業項目

### **Phase 1: 独立テストスクリプトの作成**

- [x] 1. **テストスクリプト環境構築**

  ```bash
  scripts/delta_pro3_prepare_data_test/
  ├── [`test_prepare_data.py`](../../scripts/delta_pro3_prepare_data_test/test_prepare_data.py)           # メインテストスクリプト
  ├── [`mock_protobuf_data.py`](../../scripts/delta_pro3_prepare_data_test/mock_protobuf_data.py)          # モックデータ生成
  ├── [`prepare_data_implementation.py`](../../scripts/delta_pro3_prepare_data_test/prepare_data_implementation.py) # _prepare_data 実装
  └── test_cases/                    # テストケースデータ
  ```

- [x] 2. **Proto 定義ファイルのインポート確認**

  - ファイル: [`custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker_pb2.py`](../../custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker_pb2.py)
  - 確認項目: インポートパス、メッセージクラス、フィールド定義

- [x] 3. **モック Protobuf データの作成**
  - 実際の受信データ: `b'\n\x9b\x03\n\x83\x03\x08\x00\x10\x01\x18\x02 \x00(\xe9...'`
  - 各種パターンのテストデータ生成
  - XOR エンコード・デコードのテストケース

### **Phase 2: \_prepare_data ロジックの実装とテスト**

- [x] 4. **基本 Protobuf 解析処理の実装**

  - Protobuf メッセージのデコード
  - メッセージタイプの特定
  - フィールド値の抽出

- [x] 5. **XOR デコード処理の実装**

  - `seq` 値を使用した XOR デコード
  - エンコードタイプの判定
  - エラーハンドリング

- [x] 6. **データ変換処理の実装**

  - Protobuf フィールド → 辞書形式変換
  - フィールド名マッピング
  - データ型変換

- [x] 7. **包括的テストの実行**
  - 各種テストケースでの動作確認
  - エラーケースのハンドリング確認
  - パフォーマンス確認

### **Phase 2.5: 実データテスト (新規スクリプト作成)**

- [x] 7.1. **実データテスト用スクリプトの作成**

  ```bash
  scripts/delta_pro3_real_data_test/
  ├── [main.py](../../scripts/delta_pro3_real_data_test/main.py)                    # メインスクリプト (201行, 実装完了)
  ├── [mqtt_connection.py](../../scripts/delta_pro3_real_data_test/mqtt_connection.py)         # MQTT接続・認証 (256行, シンプル化完了)
  ├── [prepare_data_processor.py](../../scripts/delta_pro3_real_data_test/prepare_data_processor.py)  # _prepare_dataロジック (307行, Phase 2移植完了)
  ├── test_results/             # テスト結果保存ディレクトリ
  │   ├── [real_data_test.log](../../scripts/delta_pro3_real_data_test/test_results/real_data_test.log)      # 実行ログ
  │   ├── [raw_messages.jsonl](../../scripts/delta_pro3_real_data_test/test_results/raw_messages.jsonl)      # 受信メッセージ生ログ
  │   └── [processed_data.jsonl](../../scripts/delta_pro3_real_data_test/test_results/processed_data.jsonl)    # 処理済みデータ
  └── ([config.json](../../scripts/config.json): ../config.json を使用)
  ```

  **実装完了機能:**

  - ✅ シンプル MQTT 接続（ANDROID 固定、UUID 不使用）
  - ✅ Phase 2 実績ロジック移植
  - ✅ リアルタイムデータ処理・表示
  - ✅ JSONL 形式ログ保存
  - ✅ 統計情報表示
  - ✅ Ctrl+C 終了対応

- [x] 7.2. **実データでの動作確認**

  ```bash
  # 実行手順
  cd scripts/delta_pro3_real_data_test
  python main.py
  ```

  **確認項目:**

  - MQTT 接続成功
  - メッセージ受信・デコード
  - フィールド抽出確認
  - データ品質検証
  - 主要なバッテリー・電力・状態情報が全ての該当メッセージで正しく抽出されていることを確認
  - unknown 系フィールドも含め、値の変動や安定性が時系列で観察できることを確認

- [x] 7.3. **統合テストの実行**
  - 複数メッセージタイプでの動作確認
  - 成功率の測定・分析
  - 問題点の特定・修正
  - [実データテストログ (real_data_test.log)](../../scripts/delta_pro3_real_data_test/test_results/real_data_test.log)
  - [生メッセージ (raw_messages.jsonl)](../../scripts/delta_pro3_real_data_test/test_results/raw_messages.jsonl)
  - [処理済みデータ (processed_data.jsonl)](../../scripts/delta_pro3_real_data_test/test_results/processed_data.jsonl)
  - **現象概要:**
    - 【2025-06-02 時点】ISSUE_06 での抜本的なロジック修正により、全ての主要メッセージ型でフィールド抽出・データ品質が大幅に改善し、空データ・欠損・unknown 系の取りこぼしも解消。
    - 詳細な定量・定性的な検証結果・サンプル出力例は [ISSUE_06_delta_pro3_prepare_data_decode_failure.md](../ISSUE_06_delta_pro3_prepare_data_decode_failure.md) の「6. 成功率・抽出フィールド数の改善を確認」セクションを参照。

### **Phase 3: HA への統合**

- [x] 8. **Delta Pro 3 クラスでの \_prepare_data メソッド実装**

  - ローカルスクリプトから本体への移植
  - インポートパスの調整
  - ログ設定の調整

  **関連ファイル:**

  - ローカル実装・検証用: [`scripts/delta_pro3_real_data_test/prepare_data_processor.py`](../../scripts/delta_pro3_real_data_test/prepare_data_processor.py)
  - 本体実装・編集先: [`custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py`](../../custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py)

  **統合結果:**

  - prepare_data_processor.py の flat 化・全フィールド抽出・unknown 系抽出ロジックを DeltaPro3 クラスに移植し、\_prepare_data メソッドを大幅刷新。
  - 返り値は Home Assistant 用 dict（ha_fields）・全フィールド（all_fields, flat）・unknown 系（unknown_fields, flat）を返す構造に統一。
  - 主要なバッテリー・電力・状態情報（cms_batt_vol_mv, bms_batt_vol, ac_out_freq_hz_config 等）も正しく抽出・マッピング。
  - フィールド名は ioBroker 実装に合わせて snake_case・flat 構造に統一。
  - 既存の他デバイス（delta*pro, delta_max, river_pro 等）との比較で、flat 化・フィールド名の違いが明確化。delta_pro_3 は bms*_/cms**/pow**等の flat 名、他は bmsMaster._/mppt.*/pd.*等のネスト名が多い。
  - 今後、他デバイスも flat 化・命名統一を進めることで、共通ロジック化・保守性向上が期待できる。

- [x] 9. **HA 環境でのテスト**

  - 実際の MQTT データでの動作確認を実施。
  - sensors メソッド経由で各エンティティが生成され、値が取得されることを確認。
  - ただし、現状は一部エンティティで「不明」や「0V」等の異常値が表示されるケースあり。
  - 原因は、flat 化後のフィールド名とエンティティ定義側の参照名のズレ、または変換ロジックの不一致が主。
  - データ取得自体は成功しているが、値のマッピング・変換ルールの精査・統一が今後の課題。
  - ログ・DEBUG 出力を活用し、どの時点で値が消失・変換ミスしているかを追跡中。
  - 他デバイスとのフィールド名対応表を作成し、ズレの吸収・共通化を進める予定。
  - ➡️ 詳細・今後の TODO は [issue_07_delta_pro_3_entity_mapping_and_flattening.md](issue_07_delta_pro_3_entity_mapping_and_flattening.md) を参照。

- [ ] 10. **最終検証に進むための追加タスク**

  - flat 化・命名統一のための変換ルールを整理し、変換ロジックを精査・修正
  - 変換後の dict（ha_fields, all_fields, unknown_fields）の内容を DEBUG ログで詳細出力し、どの時点で値が消失・変換ミスしているかを特定
  - エンティティ定義側の参照名と\_prepare_data 出力 dict のキー名のズレを解消

#### 【DeltaPro3.\_prepare_data にコマンド送信用 JSON が渡る問題の原因と修正内容】

- **原因:**

  - DeltaPro3.\_prepare_data は本来バイナリ Protobuf データ専用だが、update_data メソッドで get_topic/set_topic 等のコマンド送信系トピックでも同じメソッドが呼ばれ、JSON 文字列がバイナリデコーダに渡っていた。
  - そのため、DeltaPro3.\_prepare_data にコマンド送信用 JSON が渡ると空辞書{}しか返せず、値が消失する現象が発生していた。

- **修正内容:**
  - update_data 内で「data_topic（実データ受信）」の場合のみ DeltaPro3.\_prepare_data を呼び、それ以外（get/set 系）は BaseDevice のデフォルト（JSON デコード）を使うように分岐を明確化。
  - DeltaPro3.\_prepare_data 内にも「JSON 文字列が来た場合は即 return」する防御ロジックを追加し、誤ったデータ流入時の影響を最小化。
  - これにより、DeltaPro3.\_prepare_data には必ず「バイナリ Protobuf データ」のみが渡るようになり、flat 化・命名統一後の dict 内容が安定して Home Assistant 側に流れるようになる。
  - 併せて、DEBUG ログで「どのトピックでどんなデータが来ているか」「変換後の dict 内容」を詳細出力し、今後のズレ検証・命名統一のトラブルシュートを容易にする。

## 技術的考慮事項

### **ローカルスクリプトでの検証項目**

```python
# 1. Protobuf メッセージタイプの特定
message_types = [
    "DisplayPropertyUpload",
    "RuntimePropertyUpload",
    # ... その他
]

# 2. XOR デコード処理
def xor_decode_test(data: bytes, seq: int) -> bytes:
    # 実装とテスト

# 3. フィールド抽出処理
def extract_fields_test(decoded_message) -> dict:
    # 実装とテスト
```

### **エラーハンドリング戦略**

```python
# 段階的フォールバック処理
try:
    # 1. XORデコード試行
    # 2. Protobufデコード試行
    # 3. フィールド抽出試行
except SpecificError:
    # 特定エラーに対する処理
except Exception:
    # 汎用エラー処理
```

## 期待される効果

### **開発効率の向上**

1. ✅ **即座のフィードバック**: ローカル実行による高速開発サイクル
2. ✅ **独立デバッグ**: HA 環境の複雑さを排除した集中開発
3. ✅ **確実な動作**: 十分なテスト後の HA 統合

### **最終的な効果**

1. ✅ sensors メソッドが正常に実行される
2. ✅ Home Assistant でエンティティ値が表示される
3. ✅ MQTT データが正常にデコードされる

## 関連ファイル

### **新規作成ファイル**

- [`scripts/delta_pro3_prepare_data_test/test_prepare_data.py`](../../scripts/delta_pro3_prepare_data_test/test_prepare_data.py)
- [`scripts/delta_pro3_prepare_data_test/mock_protobuf_data.py`](../../scripts/delta_pro3_prepare_data_test/mock_protobuf_data.py)
- [`scripts/delta_pro3_prepare_data_test/prepare_data_implementation.py`](../../scripts/delta_pro3_prepare_data_test/prepare_data_implementation.py)

### **実装対象**

- [`custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py`](../../custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py)

### **参考ファイル**

- [`custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker_pb2.py`](../../custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker_pb2.py)
- [`custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto`](../../custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto)

### **テスト対象**

- Home Assistant UI (センサー値表示)
- `home-assistant.log` (エラーログ) (パスが特定できないためリンクなし)

## 前提条件

- Issue 04 で特定した根本原因の理解 (✅ 完了)
- Protobuf ファイルの存在確認 (✅ 完了)
- デバイス認識の正常動作確認 (✅ 完了)
- MQTT データ受信の正常動作確認 (✅ 完了)

---

** 未完了**: Delta Pro 3 の `_prepare_data` メソッド実装を実装したが複合処理がほとんどできていない

## 【2024-06-01 現状：一部修正済み・追加調査中】

### 現状まとめ

- 一部のメッセージ（cmdFunc=32, cmdId=50）は安定してデコード・フィールド抽出できている。
- しかし、cmdFunc=32, cmdId=2 や cmdFunc=254, cmdId=21 など多くのメッセージで、MessageToDict でフィールドは得られているのに最終出力が 0 件、またはごく一部しか抽出されない現象が継続。
- 主要なバッテリー情報や電力情報が安定して抽出できない場合が多い。
- 失敗時の詳細な値・型・内容がログに出ていないため、どこで除外されているか不明瞭。

### 次のアクション

- MessageToDict 直後の全フィールド・値・型を詳細ログ出力するよう修正し、どこで値が消えるか特定する。
- 変換・フィルタロジックを一時的に緩和し、全フィールドを出力してみる。
- 失敗例の raw/payload/MessageToDict 内容をサンプル保存し、どこで値が消えるか特定。
- cmdFunc/cmdId ごとのフィールドマッピング・変換ルールを再整理。
- 必要に応じて ioBroker JS 実装の該当箇所を再調査。

---
