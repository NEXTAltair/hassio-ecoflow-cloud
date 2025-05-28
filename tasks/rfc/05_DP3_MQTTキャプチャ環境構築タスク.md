# DP3 MQTTデータキャプチャ環境構築タスク

## 1. 概要

Delta Pro 3実機からMQTTデータをキャプチャし、Protobuf通信仕様を解析するための環境構築計画。
実機データの収集により、DP3の正確な通信仕様を確定し、Home Assistant統合の実装基盤を構築する。

## 2. 前提条件・必要機材

### **ハードウェア要件**
- [ ] **EcoFlow Delta Pro 3実機** (動作確認済み)
- [ ] **WiFiネットワーク環境** (DP3とキャプチャ環境が同一ネットワーク)
- [ ] **キャプチャ用PC/サーバー** (Linux/Windows/macOS)

### **ソフトウェア要件**
- [ ] **MQTTクライアントツール** (複数選択肢)
- [ ] **データ解析ツール** (HEX/Base64デコーダー等)
- [ ] **開発環境** (Python, protoc等)

## 3. Phase 1: MQTT認証情報取得

### **3.1 EcoFlow認証情報の準備**
- [ ] **EcoFlowアカウント情報**
    - メールアドレス
    - パスワード
    - デバイスSN (DP3のシリアル番号)

### **3.2 MQTT認証情報取得方法の選択**

#### **方法A: ecoflow_get_mqtt_login.sh スクリプト使用**
```bash
# GitHub: mmiller7/ecoflow-withoutflow
curl -O https://raw.githubusercontent.com/mmiller7/ecoflow-withoutflow/main/cloud-mqtt/ecoflow_get_mqtt_login.sh
chmod +x ecoflow_get_mqtt_login.sh
./ecoflow_get_mqtt_login.sh
```
- [ ] スクリプトダウンロード・実行
- [ ] 認証情報の取得・記録

#### **方法B: Webサイト経由取得**
- [ ] [energychain.github.io/site_ecoflow_mqtt_credentials/](https://energychain.github.io/site_ecoflow_mqtt_credentials/) にアクセス
- [ ] EcoFlowアカウント情報を入力
- [ ] 認証情報の取得・記録

#### **方法C: hassio-ecoflow-cloud経由取得**
- [ ] 既存のHome Assistant統合から認証情報を抽出
- [ ] 設定ファイルまたはログから情報取得

### **3.3 取得すべき認証情報**
- [ ] **UserName** (例: app-xxxx...)
- [ ] **UserID** (19桁の数字)
- [ ] **UserPassword** (英数字)
- [ ] **ClientID** (ANDROID_xxxx... で始まる文字列)
- [ ] **MQTTブローカーアドレス** (通常: mqtt.ecoflow.com:1883)

## 4. Phase 2: MQTTキャプチャ環境構築

### **4.1 MQTTクライアントツールの選択・設定**

#### **推奨ツール: MQTT Explorer (GUI)**
- [ ] **インストール**
    ```bash
    # Windows: Chocolatey
    choco install mqtt-explorer

    # macOS: Homebrew
    brew install --cask mqtt-explorer

    # Linux: AppImage
    wget https://github.com/thomasnordquist/MQTT-Explorer/releases/latest/download/MQTT-Explorer-*.AppImage
    ```
- [ ] **接続設定**
    - Host: mqtt.ecoflow.com
    - Port: 1883
    - Username: 取得したUserName
    - Password: 取得したUserPassword
    - Client ID: 取得したClientID

#### **代替ツール: Node-RED (フロー型)**
- [ ] **インストール・設定**
    ```bash
    npm install -g node-red
    node-red
    # http://localhost:1880 でアクセス
    ```
- [ ] **MQTTノード設定**
    - MQTT in ノードで購読設定
    - Debug ノードでメッセージ表示
    - File out ノードでデータ保存

#### **代替ツール: mosquitto_sub (CLI)**
- [ ] **インストール・設定**
    ```bash
    # Ubuntu/Debian
    sudo apt-get install mosquitto-clients

    # macOS
    brew install mosquitto

    # Windows
    choco install mosquitto
    ```
- [ ] **購読コマンド例**
    ```bash
    mosquitto_sub -h mqtt.ecoflow.com -p 1883 \
      -u "取得したUserName" -P "取得したUserPassword" \
      -i "取得したClientID" \
      -t "app/device/property/DP3のSN" \
      -v > heartbeat_data.log
    ```

### **4.2 購読対象トピックの設定**

#### **必須トピック (DP3のSNに置き換え)**
- [ ] **ハートビート**: `app/device/property/<DEVICE_SN>`
- [ ] **状態取得応答**: `app/<USER_ID>/<DEVICE_SN>/thing/property/get_reply`
- [ ] **コマンド送信**: `app/<USER_ID>/<DEVICE_SN>/thing/property/set`
- [ ] **コマンド応答**: `app/<USER_ID>/<DEVICE_SN>/thing/property/set_reply`

#### **ワイルドカード購読 (全データ収集)**
- [ ] **全トピック**: `app/#`
- [ ] **デバイス特定**: `app/+/<DEVICE_SN>/#`
- [ ] **ユーザー特定**: `app/<USER_ID>/+/#`

## 5. Phase 3: データ収集実行

### **5.1 基本データ収集**

#### **ハートビートデータ (最重要)**
- [ ] **収集期間**: 最低30分間の連続収集
- [ ] **収集条件**:
    - DP3が通常動作中
    - 充電中・放電中の両方
    - AC出力ON/OFF状態の両方
- [ ] **記録項目**:
    - タイムスタンプ
    - トピック名
    - メッセージ生データ (HEX/Base64)
    - DP3の表示状態 (SOC, 入出力W等)

#### **状態取得データ**
- [ ] **get リクエスト送信**
    ```json
    # トピック: app/<USER_ID>/<DEVICE_SN>/thing/property/get
    {
      "id": 123456789,
      "version": "1.0",
      "params": {},
      "from": "app",
      "moduleType": 0,
      "timestamp": 1640995200000
    }
    ```
- [ ] **get_reply 応答収集**
- [ ] **複数回実行** (状態変化時の差分確認)

### **5.2 操作連動データ収集**

#### **AC出力制御**
- [ ] **操作前状態記録**
- [ ] **EcoFlowアプリでAC出力ON実行**
- [ ] **set/set_reply メッセージ収集**
- [ ] **操作後状態記録**
- [ ] **AC出力OFF実行** (同様の手順)

#### **充電上限変更**
- [ ] **現在設定値記録** (例: 80%)
- [ ] **EcoFlowアプリで充電上限変更** (例: 90%)
- [ ] **set/set_reply メッセージ収集**
- [ ] **変更後状態確認**

#### **その他重要操作**
- [ ] **X-Boost ON/OFF**
- [ ] **DC出力ON/OFF**
- [ ] **充電下限変更**
- [ ] **AC充電電力変更**
- [ ] **スクリーンタイムアウト変更**

### **5.3 多様な状態でのデータ収集**

#### **電力状態バリエーション**
- [ ] **アイドル状態** (入出力なし)
- [ ] **AC充電中** (様々な充電電力)
- [ ] **ソーラー充電中** (天候・時間帯による変動)
- [ ] **AC出力中** (様々な負荷)
- [ ] **DC出力中** (USB, シガーソケット等)
- [ ] **複合状態** (充電+出力同時)

#### **SOCバリエーション**
- [ ] **低SOC** (10-30%)
- [ ] **中SOC** (40-70%)
- [ ] **高SOC** (80-100%)
- [ ] **SOC変化時** (充放電による変動)

## 6. Phase 4: データ整理・保存

### **6.1 データ分類・整理**

#### **ファイル命名規則**
```
DP3_MQTT_<データ種別>_<日時>_<状態>.log

例:
DP3_MQTT_heartbeat_20241201_1400_charging.log
DP3_MQTT_set_reply_20241201_1405_ac_on.log
DP3_MQTT_get_reply_20241201_1410_idle.log
```

#### **メタデータ記録**
- [ ] **収集条件記録ファイル作成**
    ```yaml
    # DP3_MQTT_metadata_20241201.yaml
    device:
      model: "Delta Pro 3"
      serial: "DP3のSN"
      firmware: "ファームウェアバージョン"

    collection:
      start_time: "2024-12-01T14:00:00Z"
      end_time: "2024-12-01T16:00:00Z"
      conditions:
        - "AC充電中 (1200W)"
        - "SOC: 45% → 78%"
        - "AC出力: OFF"

    operations:
      - time: "14:05:00"
        action: "AC出力ON"
        app_display: "AC出力: 0W → 150W"
      - time: "14:10:00"
        action: "充電上限変更"
        before: "80%"
        after: "90%"
    ```

### **6.2 データ検証・品質確認**

#### **基本検証項目**
- [ ] **メッセージ完整性**: 切り捨てや文字化けなし
- [ ] **タイムスタンプ連続性**: 時系列順序正常
- [ ] **操作対応性**: 操作とメッセージの対応確認
- [ ] **重複除去**: 同一メッセージの重複排除

#### **サンプルデータ例**
```
# ハートビートメッセージ例
Topic: app/device/property/DP3123456789
Timestamp: 2024-12-01T14:05:23Z
Payload (HEX): 0A2A0A28080110011802200128013801400140014801500158016001680170017801800188019001980...
Payload (Base64): CioKKAgBEAEYAiABKAE4AUABQAFIAVABWAFgAWgBcAF4AYABiAGQAZgB...
Device State: SOC=67%, AC_IN=1200W, AC_OUT=0W, DC_OUT=25W
```

## 7. Phase 5: 初期解析・検証

### **7.1 XORデコード検証**

#### **ハートビートメッセージのXORデコード**
- [ ] **ecopacket.Header パース**
    ```python
    import ecopacket_pb2

    # HEXデータをバイト列に変換
    raw_data = bytes.fromhex("0A2A0A28080110011802...")

    # ヘッダーパース
    header = ecopacket_pb2.SendHeaderMsg()
    header.ParseFromString(raw_data)

    print(f"cmd_id: {header.msg.cmd_id}")
    print(f"seq: {header.msg.seq}")
    print(f"pdata length: {len(header.msg.pdata)}")
    ```

- [ ] **XORデコード実装**
    ```python
    def xor_decode_pdata(pdata, seq):
        """ハートビートのpdataをXORデコード"""
        xor_key = seq & 0xFF  # seqの下位1バイト
        decoded = bytearray()
        for byte in pdata:
            decoded.append(byte ^ xor_key)
        return bytes(decoded)

    # XORデコード実行
    decoded_pdata = xor_decode_pdata(header.msg.pdata, header.msg.seq)
    ```

### **7.2 既存.protoファイルでの検証**

#### **コミュニティ.protoファイル適用**
- [ ] **AppShowHeartbeatReport.proto (cmdId 1)**
- [ ] **BackendRecordHeartbeatReport.proto (cmdId 2)**
- [ ] **AppParaHeartbeatReport.proto (cmdId 3)**
- [ ] **BpInfoReport.proto (cmdId 4)**

#### **デコード検証**
```python
import AppShowHeartbeatReport_pb2

# cmdId=1の場合
if header.msg.cmd_id == 1:
    heartbeat = AppShowHeartbeatReport_pb2.AppShowHeartbeatReport()
    heartbeat.ParseFromString(decoded_pdata)

    print(f"SOC: {heartbeat.bms_bmsStatus.soc}")
    print(f"AC Input: {heartbeat.inv.inputWatts}")
    print(f"AC Output: {heartbeat.inv.outputWatts}")
```

### **7.3 フィールドマッピング確認**

#### **アプリ表示値との突き合わせ**
- [ ] **SOC値比較**: Protobufフィールド vs アプリ表示
- [ ] **電力値比較**: 入出力W vs アプリ表示
- [ ] **電圧値比較**: バッテリー電圧 vs アプリ表示
- [ ] **温度値比較**: バッテリー温度 vs アプリ表示

## 8. 成果物・次ステップ

### **8.1 期待される成果物**
- [ ] **生MQTTデータセット** (分類・整理済み)
- [ ] **XORデコード実装** (検証済み)
- [ ] **フィールドマッピング表** (アプリ表示値対応)
- [ ] **DP3通信仕様書** (暫定版)

### **8.2 次ステップへの引き継ぎ**
- [ ] **DP3用.protoファイル作成**
- [ ] **delta_pro3.py実装開始**
- [ ] **Home Assistant統合テスト**

## 9. トラブルシューティング

### **9.1 接続問題**
- [ ] **認証エラー**: 認証情報の再取得
- [ ] **ネットワークエラー**: ファイアウォール・プロキシ確認
- [ ] **タイムアウト**: keep-alive設定調整

### **9.2 データ問題**
- [ ] **メッセージ切り捨て**: バッファサイズ拡大
- [ ] **文字化け**: エンコーディング設定確認
- [ ] **重複メッセージ**: QoS設定調整

### **9.3 解析問題**
- [ ] **XORデコード失敗**: seq値・アルゴリズム再確認
- [ ] **Protobufパースエラー**: スキーマ定義見直し
- [ ] **フィールド不一致**: サンプル数増加・条件変更

---

## 備考

- **安全性**: 実機操作時は安全な範囲で実施
- **継続性**: 長期間のデータ収集も検討
- **共有**: コミュニティへの成果共有も検討
- **バックアップ**: 収集データの複数箇所保存

このタスクの完了により、DP3の正確な通信仕様が確定し、Home Assistant統合の実装基盤が確立されます。