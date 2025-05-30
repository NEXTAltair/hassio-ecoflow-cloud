# DP3 Protobuf スキーマ解析・作成タスク

## 1. 概要

MQTT キャプチャ環境で収集した DP3 の実機データを解析し、正確な Protobuf スキーマ（`.proto`ファイル）を作成する。
これにより、DP3 の通信仕様を確定し、Home Assistant 統合実装の技術基盤を構築する。

## 2. 前提条件

### **必要な入力データ**

- [x] **MQTT キャプチャデータ**: `DP3_MQTTキャプチャ環境構築タスク.md`で収集済み - 2025/05/29 完了
- [x] **既存.proto ファイル**: コミュニティ提供のスキーマ定義 - 2025/05/29 完了
- [x] **操作ログ**: キャプチャ時の操作内容・デバイス状態記録 - 2025/05/29 完了

### **開発環境要件**

- [ ] **Python 3.8+**: protobuf, jsonpath_ng 等
- [ ] **protoc**: Protocol Buffers コンパイラ
- [ ] **解析ツール**: HEX/Base64 デコーダー、Protobuf デコーダー

## 3. Phase 1: データ前処理・分類

### **3.1 収集データの整理**

#### **データ分類**

- [x] **ハートビートデータ** (`app/device/property/<SN>`) - 2025/05/29 完了

  - cmdId 1: アプリ表示用ハートビート
  - cmdId 2: バックエンド記録用ハートビート
  - cmdId 3: アプリパラメータハートビート
  - cmdId 4: バッテリーパック情報
  - cmdId 32: 詳細電力・バッテリー情報（DP3/Ultra 系）

- [x] **コマンド送受信データ** (`set`/`set_reply`) - 2025/05/29 完了

  - AC 出力制御コマンド
  - 充電設定変更コマンド
  - X-Boost 制御コマンド
  - その他設定変更コマンド

- [x] **状態取得データ** (`get`/`get_reply`) - 2025/05/29 完了
  - 全状態取得応答
  - 部分状態取得応答

#### **データ品質確認**

- [x] **完整性チェック**: メッセージの切り捨て・破損確認 - 2025/05/29 完了
- [x] **重複除去**: 同一内容メッセージの除去 - 2025/05/29 完了
- [x] **時系列整理**: タイムスタンプ順でのソート - 2025/05/29 完了
- [x] **操作対応確認**: 操作ログとメッセージの対応付け - 2025/05/29 完了

### **3.2 基本構造解析**

#### **ecopacket.Header 構造の確認**

```python
# 基本ヘッダー解析スクリプト
import ecopacket_pb2
from binascii import unhexlify

def analyze_header(hex_data):
    """ecopacket.Headerの基本構造を解析"""
    try:
        raw_data = unhexlify(hex_data)
        header = ecopacket_pb2.SendHeaderMsg()
        header.ParseFromString(raw_data)

        return {
            'cmd_id': header.msg.cmd_id,
            'seq': header.msg.seq,
            'src': header.msg.src,
            'dest': header.msg.dest,
            'enc_type': header.msg.enc_type,
            'pdata_length': len(header.msg.pdata),
            'pdata_hex': header.msg.pdata.hex()
        }
    except Exception as e:
        return {'error': str(e)}

# 全ハートビートデータに対して実行
for sample in heartbeat_samples:
    result = analyze_header(sample['hex_data'])
    print(f"Sample: {sample['timestamp']}, cmdId: {result.get('cmd_id')}")
```

#### **cmdId 分布の確認**

- [x] **cmdId 頻度分析**: 各 cmdId の出現頻度 - 2025/05/29 完了
- [x] **cmdId 条件分析**: 特定条件での出現パターン - 2025/05/29 完了
- [x] **未知 cmdId 特定**: 既知以外の cmdId の発見 - 2025/05/29 完了

## 4. Phase 2: XOR デコード実装・検証

### **4.1 XOR デコード処理の実装**

#### **基本 XOR デコード関数**

```python
def xor_decode_pdata(pdata, seq):
    """
    ハートビートメッセージのpdataをXORデコード

    Args:
        pdata (bytes): 暗号化されたペイロードデータ
        seq (int): シーケンス番号（XORキーとして使用）

    Returns:
        bytes: デコードされたペイロードデータ
    """
    xor_key = seq & 0xFF  # seqの下位1バイトをXORキーとして使用
    decoded = bytearray()

    for byte in pdata:
        decoded.append(byte ^ xor_key)

    return bytes(decoded)

def analyze_xor_patterns(samples):
    """複数サンプルでXORパターンを分析"""
    patterns = {}

    for sample in samples:
        header = parse_header(sample['hex_data'])
        if header['cmd_id'] in [1, 2, 3, 4, 32]:  # ハートビート系
            decoded = xor_decode_pdata(header['pdata'], header['seq'])

            # デコード結果の妥当性チェック
            if is_valid_protobuf(decoded):
                patterns[sample['timestamp']] = {
                    'cmd_id': header['cmd_id'],
                    'seq': header['seq'],
                    'xor_key': header['seq'] & 0xFF,
                    'decoded_hex': decoded.hex(),
                    'valid': True
                }
            else:
                patterns[sample['timestamp']] = {
                    'cmd_id': header['cmd_id'],
                    'seq': header['seq'],
                    'valid': False
                }

    return patterns
```

#### **XOR デコード検証**

- [x] **デコード成功率**: 全サンプルでの成功率確認 - 2025/05/29 完了
- [x] **パターン一貫性**: 同一 cmdId での一貫性確認 - 2025/05/29 完了
- [x] **例外ケース**: デコード失敗ケースの分析 - 2025/05/29 完了

### **4.2 代替デコード方式の検証**

#### **複数 XOR キー候補の検証**

```python
def test_multiple_xor_keys(pdata, seq):
    """複数のXORキー候補でデコードを試行"""
    candidates = [
        seq & 0xFF,           # 下位1バイト（標準）
        (seq >> 8) & 0xFF,    # 上位1バイト
        seq & 0xFFFF,         # 下位2バイト
        seq,                  # 全体
        0x00,                 # XORなし
    ]

    results = {}
    for key in candidates:
        try:
            if isinstance(key, int) and key <= 0xFF:
                decoded = bytes(b ^ key for b in pdata)
            else:
                # 複数バイトキーの場合
                decoded = bytes(b ^ ((key >> (i % 4 * 8)) & 0xFF)
                              for i, b in enumerate(pdata))

            if is_valid_protobuf(decoded):
                results[f'key_{key:04x}'] = {
                    'decoded': decoded,
                    'valid': True
                }
        except:
            pass

    return results
```

## 5. Phase 3: 既存.proto ファイルでの検証

### **5.1 コミュニティ.proto ファイルの適用**

#### **既知.proto ファイルの検証**

- [x] **AppShowHeartbeatReport.proto** (cmdId 1) - 2025/05/29 完了
- [x] **BackendRecordHeartbeatReport.proto** (cmdId 2) - 2025/05/29 完了
- [x] **AppParaHeartbeatReport.proto** (cmdId 3) - 2025/05/29 完了
- [x] **BpInfoReport.proto** (cmdId 4) - 2025/05/29 完了

```python
# 各.protoファイルでの検証スクリプト例
import AppShowHeartbeatReport_pb2
import BackendRecordHeartbeatReport_pb2
import AppParaHeartbeatReport_pb2
import BpInfoReport_pb2

def verify_with_existing_proto(decoded_data, cmd_id):
    """既存.protoファイルでデコード検証"""
    try:
        if cmd_id == 1:
            msg = AppShowHeartbeatReport_pb2.AppShowHeartbeatReport()
            msg.ParseFromString(decoded_data)
            return extract_fields(msg), True

        elif cmd_id == 2:
            msg = BackendRecordHeartbeatReport_pb2.BackendRecordHeartbeatReport()
            msg.ParseFromString(decoded_data)
            return extract_fields(msg), True

        elif cmd_id == 3:
            msg = AppParaHeartbeatReport_pb2.AppParaHeartbeatReport()
            msg.ParseFromString(decoded_data)
            return extract_fields(msg), True

        elif cmd_id == 4:
            msg = BpInfoReport_pb2.BpInfoReport()
            msg.ParseFromString(decoded_data)
            return extract_fields(msg), True

        else:
            return {}, False

    except Exception as e:
        return {'error': str(e)}, False

def extract_fields(protobuf_msg):
    """Protobufメッセージからフィールド値を抽出"""
    fields = {}
    for field, value in protobuf_msg.ListFields():
        fields[field.name] = value
    return fields
```

#### **フィールド値の妥当性確認**

- [ ] **数値範囲チェック**: SOC (0-100%), 電力値の妥当性
- [ ] **データ型一貫性**: int32, float, string 等の型確認
- [ ] **必須フィールド**: 常に存在すべきフィールドの確認

### **5.2 未知フィールドの解析**

#### **フィールド候補の列挙**

- [x] **差分解析**: 既存.proto と実データの差分抽出 - 2025/05/29 完了
- [x] **関連情報収集**: コミュニティ情報・ドキュメント参照 - 2025/05/29 完了

#### **フィールド型・番号の推定**

- [x] **データ型推定**: 値の範囲・変動パターンから推定 - 2025/05/29 完了
- [x] **フィールド番号推定**: WireType・順序から推定 - 2025/05/29 完了
- [x] **検証**: 推定スキーマでのデコード検証 - 2025/05/29 完了

## 6. Phase 4: DP3 専用.proto ファイル作成

### **6.1 新規.proto ファイルの作成**

#### **メッセージ定義**

- [x] **cmdId 毎のメッセージ**: 各 cmdId に対応するメッセージ定義 - 2025/05/29 完了
- [x] **ネスト構造**: 必要に応じたネストメッセージ定義 - 2025/05/29 完了
- [x] **フィールド定義**: 型・番号・名前を明確に定義 - 2025/05/29 完了

#### **生成・検証**

- [x] **`protoc`でのコンパイル**: .py ファイルの生成 - 2025/05/29 完了
- [x] **Python スクリプト検証**: 生成コードでのデコード検証 - 2025/05/29 完了
- [x] **リンターチェック**: `mypy`等での型チェック - 2025/05/29 完了

### **6.2 .proto ファイルの拡張・改善**

#### **フィールド意味の明確化**

- [x] **コメント追加**: 各フィールドへの説明コメント - 2025/05/29 完了
- [x] **命名規則統一**: フィールド名の一貫性確保 - 2025/05/29 完了

#### **スキーマバージョニング**

- [ ] **バージョン管理**: Git 等での変更履歴管理 (手動で実施)
- [ ] **互換性考慮**: 下位互換性を意識した変更

## 7. Phase 5: スキーマ最適化・完成

### **7.1 フィールド定義の精緻化**

#### **データ型の最適化**

- [ ] **int32 vs float**: 精度要件に基づく選択
- [ ] **mV vs V**: 単位統一の検討
- [ ] **enum 定義**: 状態値・エラーコードの列挙型化

#### **フィールド番号の最適化**

- [ ] **連続性**: フィールド番号の連続性確保
- [ ] **予約領域**: 将来拡張用の番号予約
- [ ] **互換性**: 既存.proto との番号重複回避

### **7.2 複数 cmdId の統合検討**

#### **共通フィールドの抽出**

```protobuf
// 共通メッセージの定義
message CommonBatteryStatus {
    int32 soc = 1;
    int32 voltage = 2;
    int32 current = 3;
    int32 temperature = 4;
}

// 各cmdIdで共通メッセージを利用
message AppShowHeartbeatReport {
    CommonBatteryStatus battery = 1;
    // cmdId 1固有のフィールド
}

message BackendRecordHeartbeatReport {
    CommonBatteryStatus battery = 1;
    // cmdId 2固有のフィールド
}
```

### **7.3 最終検証・ドキュメント化**

#### **全サンプルでの検証**

- [ ] **パース成功率**: 95%以上の成功率確保
- [ ] **フィールド網羅性**: 重要フィールドの漏れなし
- [ ] **値の妥当性**: アプリ表示値との一致確認

#### **スキーマドキュメント作成**

```markdown
# DP3 Protobuf スキーマ仕様書

## cmdId 1: AppShowHeartbeatReport

- **用途**: アプリ表示用の基本状態情報
- **更新頻度**: 約 5 秒間隔
- **主要フィールド**:
  - `bms_status.soc`: バッテリー残量 (0-100%)
  - `inverter_status.output_watts`: AC 出力電力 (W)
  - `mppt_status.in_watts`: ソーラー入力電力 (W)

## cmdId 32: DeltaPro3DetailedReport

- **用途**: 詳細な電力・バッテリー情報
- **更新頻度**: 約 1 秒間隔
- **主要フィールド**:
  - `voltage_244`: バッテリー電圧 (V)
  - `remain_capacity_249`: 残容量 (mAh)
  - `charge_limit_337`: 充電上限 (%)
```

## 8. 成果物・次ステップ

### **8.1 期待される成果物**

- [ ] **DP3 専用.proto ファイル**: `delta_pro3.proto`
- [ ] **生成 Python ファイル**: `delta_pro3_pb2.py`
- [ ] **フィールドマッピング表**: Protobuf ↔ アプリ表示値
- [ ] **XOR デコード実装**: 検証済みデコード関数
- [ ] **スキーマ仕様書**: 各 cmdId の詳細仕様

### **8.2 品質基準**

- [ ] **パース成功率**: 95%以上
- [ ] **フィールド精度**: アプリ表示値との誤差 5%以内
- [ ] **網羅性**: 主要機能の 90%以上をカバー
- [ ] **拡張性**: 将来機能追加に対応可能

### **8.3 次ステップへの引き継ぎ**

- [ ] **XOR デコード実装タスク**: 詳細実装・最適化
- [ ] **delta_pro3.py 実装タスク**: デバイスクラス実装
- [ ] **エンティティ定義実装タスク**: HA 統合実装

## 9. トラブルシューティング

### **9.1 解析問題**

- [ ] **XOR デコード失敗**: 代替キー・アルゴリズムの検証
- [ ] **Protobuf パースエラー**: フィールド定義・型の見直し
- [ ] **フィールド不一致**: サンプル数増加・条件変更

### **9.2 品質問題**

- [ ] **パース成功率低下**: スキーマ定義の見直し
- [ ] **値の不整合**: フィールドマッピングの再確認
- [ ] **未知フィールド**: 追加解析・コミュニティ情報収集

### **9.3 互換性問題**

- [ ] **既存.proto との競合**: フィールド番号の調整
- [ ] **バージョン差異**: 複数 FW バージョンでの検証
- [ ] **機種差異**: 他 DP3 バリエーションとの比較

---

## 備考

- **精度重視**: アプリ表示値との一致を最優先
- **拡張性**: 将来の機能追加・機種追加に対応
- **コミュニティ連携**: 成果の共有・フィードバック収集
- **継続改善**: 実装後の精度向上・最適化

このタスクの完了により、DP3 の正確な Protobuf 通信仕様が確定し、確実な Home Assistant 統合実装が可能になります。
