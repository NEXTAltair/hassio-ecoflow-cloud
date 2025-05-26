# DP3 XORデコード実装タスク

## 1. 概要

Delta Pro 3のMQTTハートビートメッセージに適用されているXOR暗号化を解除する処理を実装する。
これは、DP3のProtobuf通信処理の基盤となる重要なコンポーネントであり、全てのデータ解析・デバイス制御の前提となる。

## 2. 技術背景

### **XOR暗号化の仕組み**
- **対象**: ハートビートメッセージ（`app/device/property/<DEVICE_SN>`）のpdata部分
- **暗号化方式**: ecopacket.Header内の`seq`フィールドを使用したXOR暗号化
- **キー**: 通常は`seq`の下位1バイト（`seq & 0xFF`）
- **適用cmdId**: 1, 2, 3, 4, 32等のハートビート系メッセージ

### **処理フロー**
```
MQTTメッセージ → ecopacket.Header解析 → seq抽出 → XORデコード → Protobufパース
```

## 3. Phase 1: 基本XORデコード実装

### **3.1 コア関数の実装**

#### **基本XORデコード関数**
```python
def xor_decode_pdata(pdata: bytes, seq: int) -> bytes:
    """
    ハートビートメッセージのpdataをXORデコード

    Args:
        pdata (bytes): 暗号化されたペイロードデータ
        seq (int): シーケンス番号（XORキーとして使用）

    Returns:
        bytes: デコードされたペイロードデータ

    Raises:
        ValueError: 入力データが無効な場合
    """
    if not pdata:
        raise ValueError("pdata cannot be empty")

    if seq < 0:
        raise ValueError("seq must be non-negative")

    # seqの下位1バイトをXORキーとして使用
    xor_key = seq & 0xFF

    # 各バイトをXORキーでデコード
    decoded = bytearray()
    for byte in pdata:
        decoded.append(byte ^ xor_key)

    return bytes(decoded)
```

#### **ヘッダー解析統合関数**
```python
import ecopacket_pb2
from typing import Tuple, Optional

def decode_heartbeat_message(raw_data: bytes) -> Tuple[Optional[bytes], dict]:
    """
    MQTTハートビートメッセージを完全デコード

    Args:
        raw_data (bytes): MQTTメッセージの生データ

    Returns:
        Tuple[Optional[bytes], dict]: (デコード済みpdata, ヘッダー情報)
    """
    try:
        # ecopacket.Headerの解析
        header = ecopacket_pb2.SendHeaderMsg()
        header.ParseFromString(raw_data)

        header_info = {
            'cmd_id': header.msg.cmd_id,
            'seq': header.msg.seq,
            'src': header.msg.src,
            'dest': header.msg.dest,
            'enc_type': header.msg.enc_type,
            'pdata_length': len(header.msg.pdata),
            'success': True
        }

        # ハートビート系メッセージの場合はXORデコード
        if header.msg.cmd_id in [1, 2, 3, 4, 32]:
            decoded_pdata = xor_decode_pdata(header.msg.pdata, header.msg.seq)
            return decoded_pdata, header_info
        else:
            # 非ハートビート系はそのまま返す
            return header.msg.pdata, header_info

    except Exception as e:
        return None, {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }
```

### **3.2 デコード検証機能**

#### **Protobuf妥当性チェック**
```python
def is_valid_protobuf(data: bytes) -> bool:
    """
    バイト列がProtobufとして妥当かチェック

    Args:
        data (bytes): チェック対象のバイト列

    Returns:
        bool: Protobufとして妥当な場合True
    """
    if not data:
        return False

    try:
        # 基本的なProtobuf構造チェック
        pos = 0
        while pos < len(data):
            # varint読み取り（フィールド番号+ワイヤタイプ）
            varint, new_pos = read_varint(data, pos)
            if new_pos == pos:  # 読み取り失敗
                return False

            field_number = varint >> 3
            wire_type = varint & 0x7

            # フィールド番号の妥当性（1-536870911）
            if field_number < 1 or field_number > 536870911:
                return False

            # ワイヤタイプの妥当性（0-5）
            if wire_type > 5:
                return False

            # 次のフィールドへ移動
            pos = skip_field(data, new_pos, wire_type)
            if pos == -1:  # スキップ失敗
                return False

        return True

    except:
        return False

def read_varint(data: bytes, pos: int) -> Tuple[int, int]:
    """varint値を読み取り"""
    result = 0
    shift = 0

    while pos < len(data):
        byte = data[pos]
        result |= (byte & 0x7F) << shift
        pos += 1

        if (byte & 0x80) == 0:
            return result, pos

        shift += 7
        if shift >= 64:  # varintが長すぎる
            break

    return 0, pos  # 失敗

def skip_field(data: bytes, pos: int, wire_type: int) -> int:
    """指定されたワイヤタイプのフィールドをスキップ"""
    if wire_type == 0:  # varint
        _, new_pos = read_varint(data, pos)
        return new_pos
    elif wire_type == 1:  # 64-bit
        return pos + 8 if pos + 8 <= len(data) else -1
    elif wire_type == 2:  # length-delimited
        length, new_pos = read_varint(data, pos)
        return new_pos + length if new_pos + length <= len(data) else -1
    elif wire_type == 5:  # 32-bit
        return pos + 4 if pos + 4 <= len(data) else -1
    else:
        return -1  # 未対応のワイヤタイプ
```

## 4. Phase 2: 高度なデコード機能

### **4.1 複数キー対応**

#### **代替XORキー検証**
```python
def try_multiple_xor_keys(pdata: bytes, seq: int) -> Tuple[Optional[bytes], str]:
    """
    複数のXORキー候補でデコードを試行

    Args:
        pdata (bytes): 暗号化されたペイロードデータ
        seq (int): シーケンス番号

    Returns:
        Tuple[Optional[bytes], str]: (成功時のデコード結果, 使用したキー種別)
    """
    # XORキー候補リスト
    key_candidates = [
        ('seq_low_byte', seq & 0xFF),           # 標準: 下位1バイト
        ('seq_high_byte', (seq >> 8) & 0xFF),   # 上位1バイト
        ('seq_low_word', seq & 0xFFFF),         # 下位2バイト
        ('seq_full', seq),                      # 全体
        ('no_xor', 0),                          # XORなし
        ('seq_inverted', (~seq) & 0xFF),        # 反転
        ('seq_rotated', ((seq << 1) | (seq >> 7)) & 0xFF),  # ローテート
    ]

    for key_name, key_value in key_candidates:
        try:
            if key_name == 'seq_low_word' or key_name == 'seq_full':
                # 複数バイトキーの場合
                decoded = decode_with_multi_byte_key(pdata, key_value)
            else:
                # 単一バイトキーの場合
                decoded = bytes(b ^ (key_value & 0xFF) for b in pdata)

            # Protobuf妥当性チェック
            if is_valid_protobuf(decoded):
                return decoded, key_name

        except Exception:
            continue

    return None, 'none'

def decode_with_multi_byte_key(pdata: bytes, key: int) -> bytes:
    """複数バイトキーでのXORデコード"""
    decoded = bytearray()
    key_bytes = key.to_bytes(4, 'little')  # 4バイトのキー

    for i, byte in enumerate(pdata):
        key_byte = key_bytes[i % 4]
        decoded.append(byte ^ key_byte)

    return bytes(decoded)
```

## 5. Phase 3: パフォーマンス最適化

### **5.1 高速化実装**

#### **NumPy活用版**
```python
import numpy as np

def xor_decode_numpy(pdata: bytes, seq: int) -> bytes:
    """
    NumPyを使用した高速XORデコード

    Args:
        pdata (bytes): 暗号化データ
        seq (int): シーケンス番号

    Returns:
        bytes: デコード結果
    """
    if not pdata:
        return b''

    # バイト配列をNumPy配列に変換
    data_array = np.frombuffer(pdata, dtype=np.uint8)

    # XORキー
    xor_key = np.uint8(seq & 0xFF)

    # ベクトル化XOR演算
    decoded_array = data_array ^ xor_key

    # バイト列に戻す
    return decoded_array.tobytes()
```

## 6. 成果物・次ステップ

### **6.1 期待される成果物**
- [ ] **基本XORデコード関数**: `xor_decode_pdata()`
- [ ] **統合デコード関数**: `decode_heartbeat_message()`
- [ ] **Protobuf妥当性チェック**: `is_valid_protobuf()`
- [ ] **複数キー対応**: `try_multiple_xor_keys()`
- [ ] **統合デコーダークラス**: `DP3XORDecoder`

### **6.2 品質基準**
- [ ] **デコード成功率**: 95%以上
- [ ] **処理速度**: 1メッセージあたり1ms以下
- [ ] **メモリ効率**: 不要なコピー最小化
- [ ] **エラーハンドリング**: 全例外ケース対応

### **6.3 次ステップへの引き継ぎ**
- [ ] **delta_pro3.py実装**: デバイスクラスへの統合
- [ ] **Protobufパース実装**: 各cmdIdの詳細パース
- [ ] **エンティティ実装**: Home Assistant統合

---

## 備考

- **パフォーマンス重視**: 高頻度処理のため最適化必須
- **拡張性**: 将来の暗号化方式変更に対応
- **テスト充実**: 実データでの徹底検証
- **ログ機能**: デバッグ・監視のための詳細ログ

このタスクの完了により、DP3の全てのProtobuf通信処理の基盤が確立されます。