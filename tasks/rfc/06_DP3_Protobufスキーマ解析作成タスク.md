# DP3 Protobufスキーマ解析・作成タスク

## 1. 概要

MQTTキャプチャ環境で収集したDP3の実機データを解析し、正確なProtobufスキーマ（`.proto`ファイル）を作成する。
これにより、DP3の通信仕様を確定し、Home Assistant統合実装の技術基盤を構築する。

## 2. 前提条件

### **必要な入力データ**
- [ ] **MQTTキャプチャデータ**: `DP3_MQTTキャプチャ環境構築タスク.md`で収集済み
- [ ] **既存.protoファイル**: コミュニティ提供のスキーマ定義
- [ ] **操作ログ**: キャプチャ時の操作内容・デバイス状態記録

### **開発環境要件**
- [ ] **Python 3.8+**: protobuf, jsonpath_ng等
- [ ] **protoc**: Protocol Buffers コンパイラ
- [ ] **解析ツール**: HEX/Base64デコーダー、Protobufデコーダー

## 3. Phase 1: データ前処理・分類

### **3.1 収集データの整理**

#### **データ分類**
- [ ] **ハートビートデータ** (`app/device/property/<SN>`)
    - cmdId 1: アプリ表示用ハートビート
    - cmdId 2: バックエンド記録用ハートビート
    - cmdId 3: アプリパラメータハートビート
    - cmdId 4: バッテリーパック情報
    - cmdId 32: 詳細電力・バッテリー情報（DP3/Ultra系）

- [ ] **コマンド送受信データ** (`set`/`set_reply`)
    - AC出力制御コマンド
    - 充電設定変更コマンド
    - X-Boost制御コマンド
    - その他設定変更コマンド

- [ ] **状態取得データ** (`get`/`get_reply`)
    - 全状態取得応答
    - 部分状態取得応答

#### **データ品質確認**
- [ ] **完整性チェック**: メッセージの切り捨て・破損確認
- [ ] **重複除去**: 同一内容メッセージの除去
- [ ] **時系列整理**: タイムスタンプ順でのソート
- [ ] **操作対応確認**: 操作ログとメッセージの対応付け

### **3.2 基本構造解析**

#### **ecopacket.Header構造の確認**
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

#### **cmdId分布の確認**
- [ ] **cmdId頻度分析**: 各cmdIdの出現頻度
- [ ] **cmdId条件分析**: 特定条件での出現パターン
- [ ] **未知cmdId特定**: 既知以外のcmdIdの発見

## 4. Phase 2: XORデコード実装・検証

### **4.1 XORデコード処理の実装**

#### **基本XORデコード関数**
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

#### **XORデコード検証**
- [ ] **デコード成功率**: 全サンプルでの成功率確認
- [ ] **パターン一貫性**: 同一cmdIdでの一貫性確認
- [ ] **例外ケース**: デコード失敗ケースの分析

### **4.2 代替デコード方式の検証**

#### **複数XORキー候補の検証**
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

## 5. Phase 3: 既存.protoファイルでの検証

### **5.1 コミュニティ.protoファイルの適用**

#### **既知.protoファイルの検証**
- [ ] **AppShowHeartbeatReport.proto** (cmdId 1)
- [ ] **BackendRecordHeartbeatReport.proto** (cmdId 2)
- [ ] **AppParaHeartbeatReport.proto** (cmdId 3)
- [ ] **BpInfoReport.proto** (cmdId 4)

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
- [ ] **データ型一貫性**: int32, float, string等の型確認
- [ ] **必須フィールド**: 常に存在すべきフィールドの確認

### **5.2 未対応データの分析**

#### **cmdId 32の詳細解析**
```python
def analyze_cmdid32_structure(decoded_samples):
    """cmdId 32の構造を詳細解析"""
    field_patterns = {}

    for sample in decoded_samples:
        if sample['cmd_id'] == 32:
            # protoscope等でraw解析
            raw_analysis = analyze_raw_protobuf(sample['decoded'])

            # フィールド番号と値の抽出
            for field_num, field_value in raw_analysis.items():
                if field_num not in field_patterns:
                    field_patterns[field_num] = []
                field_patterns[field_num].append({
                    'timestamp': sample['timestamp'],
                    'value': field_value,
                    'type': detect_field_type(field_value)
                })

    return field_patterns

def detect_field_type(value):
    """フィールド値から型を推測"""
    if isinstance(value, int):
        if 0 <= value <= 100:
            return 'percentage'
        elif value > 1000000:
            return 'timestamp_or_large_int'
        else:
            return 'int32'
    elif isinstance(value, float):
        return 'float'
    elif isinstance(value, str):
        return 'string'
    else:
        return 'unknown'
```

## 6. Phase 4: DP3専用.protoファイル作成

### **6.1 フィールドマッピングの確定**

#### **アプリ表示値との突き合わせ**
```python
def correlate_with_app_display(protobuf_fields, app_display_log):
    """Protobufフィールドとアプリ表示値の相関分析"""
    correlations = {}

    for timestamp, fields in protobuf_fields.items():
        app_data = find_closest_app_data(timestamp, app_display_log)

        if app_data:
            # SOC値の相関
            for field_name, field_value in fields.items():
                if 'soc' in field_name.lower():
                    if abs(field_value - app_data['soc']) < 2:  # 2%以内の誤差
                        correlations[field_name] = 'battery_soc'

                # 電力値の相関
                elif 'watt' in field_name.lower() or 'power' in field_name.lower():
                    for app_power_key in ['ac_input', 'ac_output', 'dc_output']:
                        if abs(field_value - app_data[app_power_key]) < 10:  # 10W以内
                            correlations[field_name] = app_power_key

                # 電圧値の相関
                elif 'volt' in field_name.lower():
                    for app_volt_key in ['battery_voltage', 'ac_voltage']:
                        if abs(field_value - app_data[app_volt_key]) < 1:  # 1V以内
                            correlations[field_name] = app_volt_key

    return correlations
```

#### **フィールド命名規則の策定**
- [ ] **一貫性のある命名**: 既存デバイスとの統一性
- [ ] **意味の明確性**: フィールド名から用途が分かる
- [ ] **拡張性**: 将来の機能追加に対応

### **6.2 .protoファイルの作成**

#### **DP3専用メッセージ定義**
```protobuf
// delta_pro3.proto
syntax = "proto3";

package ecoflow.delta_pro3;

// cmdId 1: アプリ表示用ハートビート
message AppShowHeartbeatReport {
    // バッテリー関連
    BmsStatus bms_status = 1;

    // インバータ関連
    InverterStatus inverter_status = 2;

    // MPPT関連
    MpptStatus mppt_status = 3;

    // PD関連
    PdStatus pd_status = 4;
}

message BmsStatus {
    int32 soc = 1;                    // バッテリー残量 (%)
    float f32_show_soc = 2;           // 精密残量 (%)
    int32 design_cap = 3;             // 設計容量 (mAh)
    int32 full_cap = 4;               // フル容量 (mAh)
    int32 remain_cap = 5;             // 残容量 (mAh)
    int32 soh = 6;                    // SOH (%)
    int32 cycles = 7;                 // サイクル数
    int32 temp = 8;                   // バッテリー温度 (℃)
    int32 min_cell_temp = 9;          // 最小セル温度 (℃)
    int32 max_cell_temp = 10;         // 最大セル温度 (℃)
    int32 vol = 11;                   // バッテリー電圧 (mV)
    int32 min_cell_vol = 12;          // 最小セル電圧 (mV)
    int32 max_cell_vol = 13;          // 最大セル電圧 (mV)
    int32 amp = 14;                   // バッテリー電流 (mA)
}

message InverterStatus {
    int32 input_watts = 1;            // AC入力電力 (W)
    int32 output_watts = 2;           // AC出力電力 (W)
    int32 ac_in_vol = 3;              // AC入力電圧 (mV)
    int32 inv_out_vol = 4;            // AC出力電圧 (mV)
    int32 ac_in_freq = 5;             // AC入力周波数 (Hz)
    int32 inv_out_freq = 6;           // AC出力周波数 (Hz)
    bool cfg_ac_enabled = 7;          // AC出力有効
    bool cfg_ac_xboost = 8;           // X-Boost有効
    int32 cfg_slow_chg_watts = 9;     // AC充電電力 (W)
}

message MpptStatus {
    int32 in_watts = 1;               // ソーラー入力電力 (W)
    int32 in_vol = 2;                 // ソーラー入力電圧 (V)
    int32 in_amp = 3;                 // ソーラー入力電流 (A)
    int32 out_watts = 4;              // DC出力電力 (W)
    int32 out_vol = 5;                // DC出力電圧 (V)
    bool car_state = 6;               // DC出力状態
    int32 car_out_watts = 7;          // シガーソケット出力 (W)
}

message PdStatus {
    int32 watts_in_sum = 1;           // 合計入力電力 (W)
    int32 watts_out_sum = 2;          // 合計出力電力 (W)
    int32 typec1_watts = 3;           // Type-C1出力 (W)
    int32 typec2_watts = 4;           // Type-C2出力 (W)
    int32 usb1_watts = 5;             // USB1出力 (W)
    int32 usb2_watts = 6;             // USB2出力 (W)
    int32 qc_usb1_watts = 7;          // QC USB1出力 (W)
    int32 qc_usb2_watts = 8;          // QC USB2出力 (W)
    bool beep_state = 9;              // ビープ音状態
    int32 lcd_off_sec = 10;           // LCD オフ時間 (秒)
}

// cmdId 2: バックエンド記録用ハートビート
message BackendRecordHeartbeatReport {
    // 詳細な電力・電圧・電流データ
    DetailedPowerStatus power_status = 1;
    DetailedBatteryStatus battery_status = 2;
}

// cmdId 32: DP3/Ultra系詳細情報
message DeltaPro3DetailedReport {
    // フィールド番号68-400の範囲で定義
    float voltage_68 = 68;            // AC出力電圧 (V)
    float current_69 = 69;            // AC出力電流 (A)
    float voltage_149 = 149;          // DC出力電圧 (V)
    float current_150 = 150;          // DC出力電流 (A)
    float voltage_244 = 244;          // バッテリー電圧 (V)
    float current_245 = 245;          // バッテリー電流 (A)
    int32 full_capacity_247 = 247;    // フル容量 (mAh)
    int32 remain_capacity_249 = 249;  // 残容量 (mAh)
    int32 min_cell_voltage_256 = 256; // 最小セル電圧 (mV)
    int32 max_cell_voltage_257 = 257; // 最大セル電圧 (mV)
    float charge_limit_337 = 337;     // 充電上限 (%)
    float mppt_power_369 = 369;       // MPPT出力電力 (W)
    float mppt_voltage_377 = 377;     // MPPT電圧 (V)

    // 他のフィールドは解析結果に基づいて追加
}
```

#### **コマンド送信用メッセージ定義**
```protobuf
// コマンド送信用メッセージ
message DeltaPro3CommandRequest {
    oneof command {
        AcOutputCommand ac_output = 1;
        ChargeSettingCommand charge_setting = 2;
        XBoostCommand xboost = 3;
        DcOutputCommand dc_output = 4;
    }
}

message AcOutputCommand {
    bool enabled = 1;
}

message ChargeSettingCommand {
    int32 max_charge_soc = 1;         // 充電上限 (%)
    int32 min_discharge_soc = 2;      // 放電下限 (%)
    int32 ac_charge_watts = 3;        // AC充電電力 (W)
}

message XBoostCommand {
    bool enabled = 1;
}

message DcOutputCommand {
    bool enabled = 1;
}
```

### **6.3 .protoファイルの検証**

#### **protoc コンパイル検証**
```bash
# .protoファイルのコンパイル
protoc --python_out=. delta_pro3.proto

# 生成されたPythonファイルの確認
ls -la *_pb2.py
```

#### **実データでの検証**
```python
import delta_pro3_pb2

def verify_new_proto(decoded_data, cmd_id):
    """新しい.protoファイルでの検証"""
    try:
        if cmd_id == 1:
            msg = delta_pro3_pb2.AppShowHeartbeatReport()
            msg.ParseFromString(decoded_data)

            # フィールド値の妥当性確認
            if hasattr(msg, 'bms_status'):
                soc = msg.bms_status.soc
                if 0 <= soc <= 100:
                    print(f"SOC: {soc}% (valid)")
                else:
                    print(f"SOC: {soc}% (invalid range)")

            return True

    except Exception as e:
        print(f"Parse error: {e}")
        return False
```

## 7. Phase 5: スキーマ最適化・完成

### **7.1 フィールド定義の精緻化**

#### **データ型の最適化**
- [ ] **int32 vs float**: 精度要件に基づく選択
- [ ] **mV vs V**: 単位統一の検討
- [ ] **enum定義**: 状態値・エラーコードの列挙型化

#### **フィールド番号の最適化**
- [ ] **連続性**: フィールド番号の連続性確保
- [ ] **予約領域**: 将来拡張用の番号予約
- [ ] **互換性**: 既存.protoとの番号重複回避

### **7.2 複数cmdIdの統合検討**

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
# DP3 Protobufスキーマ仕様書

## cmdId 1: AppShowHeartbeatReport
- **用途**: アプリ表示用の基本状態情報
- **更新頻度**: 約5秒間隔
- **主要フィールド**:
  - `bms_status.soc`: バッテリー残量 (0-100%)
  - `inverter_status.output_watts`: AC出力電力 (W)
  - `mppt_status.in_watts`: ソーラー入力電力 (W)

## cmdId 32: DeltaPro3DetailedReport
- **用途**: 詳細な電力・バッテリー情報
- **更新頻度**: 約1秒間隔
- **主要フィールド**:
  - `voltage_244`: バッテリー電圧 (V)
  - `remain_capacity_249`: 残容量 (mAh)
  - `charge_limit_337`: 充電上限 (%)
```

## 8. 成果物・次ステップ

### **8.1 期待される成果物**
- [ ] **DP3専用.protoファイル**: `delta_pro3.proto`
- [ ] **生成Pythonファイル**: `delta_pro3_pb2.py`
- [ ] **フィールドマッピング表**: Protobuf ↔ アプリ表示値
- [ ] **XORデコード実装**: 検証済みデコード関数
- [ ] **スキーマ仕様書**: 各cmdIdの詳細仕様

### **8.2 品質基準**
- [ ] **パース成功率**: 95%以上
- [ ] **フィールド精度**: アプリ表示値との誤差5%以内
- [ ] **網羅性**: 主要機能の90%以上をカバー
- [ ] **拡張性**: 将来機能追加に対応可能

### **8.3 次ステップへの引き継ぎ**
- [ ] **XORデコード実装タスク**: 詳細実装・最適化
- [ ] **delta_pro3.py実装タスク**: デバイスクラス実装
- [ ] **エンティティ定義実装タスク**: HA統合実装

## 9. トラブルシューティング

### **9.1 解析問題**
- [ ] **XORデコード失敗**: 代替キー・アルゴリズムの検証
- [ ] **Protobufパースエラー**: フィールド定義・型の見直し
- [ ] **フィールド不一致**: サンプル数増加・条件変更

### **9.2 品質問題**
- [ ] **パース成功率低下**: スキーマ定義の見直し
- [ ] **値の不整合**: フィールドマッピングの再確認
- [ ] **未知フィールド**: 追加解析・コミュニティ情報収集

### **9.3 互換性問題**
- [ ] **既存.protoとの競合**: フィールド番号の調整
- [ ] **バージョン差異**: 複数FWバージョンでの検証
- [ ] **機種差異**: 他DP3バリエーションとの比較

---

## 備考

- **精度重視**: アプリ表示値との一致を最優先
- **拡張性**: 将来の機能追加・機種追加に対応
- **コミュニティ連携**: 成果の共有・フィードバック収集
- **継続改善**: 実装後の精度向上・最適化

このタスクの完了により、DP3の正確なProtobuf通信仕様が確定し、確実なHome Assistant統合実装が可能になります。