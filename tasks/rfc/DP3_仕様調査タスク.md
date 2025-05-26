# Delta Pro3 仕様調査タスク

## 1. MQTT/Protobuf仕様調査
- [ ] MQTTブローカーの接続方式調査
    - 例: mqtt.ecoflow.com への接続方法、認証情報の取得方法
    - **参考: ioBroker.ecoflow-mqtt, GitHub issue #270**
    - EcoFlow公式MQTTブローカー(mqtt.ecoflow.com)に接続するには、以下の認証情報が必要:
        - UserName(例: app-xxxx...)
        - UserID(19桁の数字)
        - UserPassword(英数字)
        - ClientID(ANDROID_xxxx... で始まる文字列)
    - 認証情報の取得方法:
        1. [ecoflow-withoutflow/cloud-mqtt/ecoflow_get_mqtt_login.sh](https://github.com/mmiller7/ecoflow-withoutflow/blob/main/cloud-mqtt/ecoflow_get_mqtt_login.sh) スクリプトを使う
        2. [energychain.github.io/site_ecoflow_mqtt_credentials/](https://energychain.github.io/site_ecoflow_mqtt_credentials/) のWebサイトで取得
        3. ioBroker.ecoflow-mqttアダプタの「ボタンを押す」機能(EcoFlowアカウントのユーザー名・パスワードが必要)
    - MQTTブローカーのアドレスやポートは通常デフォルト(mqtt.ecoflow.com:1883)
    - 場合によってはWebサイト②で異なるブローカーアドレスが返ることもあるので注意
    - 取得した認証情報を使い、MQTTクライアント(Node-REDやioBroker等)で接続設定を行う
    - 参考: [ioBroker.ecoflow-mqtt README](https://github.com/foxthefox/ioBroker.ecoflow-mqtt#ef-credentials)
- [ ] Delta Pro3のMQTTトピック構造調査
    - 例: /app/xxxx/thing/property/get など、どのトピックでどんなデータが流れるか
    - **基本的なトピック構造:**
        - `app/<USER_ID>/<DEVICE_SN>/thing/property/set`: コマンド送信 (HA/App -> Device)
        - `app/<USER_ID>/<DEVICE_SN>/thing/property/set_reply`: コマンド応答 (Device -> HA/App)
        - `app/<USER_ID>/<DEVICE_SN>/thing/property/get`: 状態取得要求 (HA/App -> Device)
        - `app/<USER_ID>/<DEVICE_SN>/thing/property/get_reply`: 状態取得応答 (Device -> HA/App)
        - `app/device/property/<DEVICE_SN>`: デバイスからの定期的状態更新/ハートビート (Device -> HA/App)
    - **ペイロード形式:**
        - 全てProtobuf形式。
        - 特に `app/device/property/<DEVICE_SN>` からのメッセージは、ヘッダーの `seq` でXORデコードが必要な場合がある。
        - `get_reply` は複数の `cmdId` を持つProtobufメッセージを含むことがある。
    - **主な `cmdId` と予想される内容 (ioBroker.ecoflow-mqtt や GitHub Issue 参考):**
        - `cmdId 1, 2, 3, 4, 28` などが `get_reply` やハートビートに含まれる。
            - `cmdId 1`: アプリ表示用ハートビート (充電状態、残り時間など基本的なステータス)
            - `cmdId 2`: バックエンド記録用ハートビート (より詳細な電力情報、電圧、電流など)
            - `cmdId 3`: アプリパラメータハートビート (デバイス設定値など)
            - `cmdId 4`: バッテリーパック情報
            - `cmdId 28`: 空の場合がある
        - コマンド送信時 (`set` トピック) も、操作対象に応じた `cmdId` を持つProtobufメッセージが使用される。
    - **参考情報源:**
        - `ioBroker.ecoflow-mqtt` リポジトリ (特に `lib/ecoflow_data.js`、`.proto` ファイル群)
        - `hassio-ecoflow-cloud` GitHub Issue #193 (Delta Pro Ultra), #270 (Delta Pro 3)
        - `protobuf-decoder.netlify.app` (Protobufメッセージのデコード・解析ツール)
- [ ] Delta Pro3のMQTTメッセージ形式調査
    - 例: Protobuf形式かJSON形式か、バイナリかテキストか
    - **確定事項:** Delta Pro3のMQTTメッセージのペイロードは **Protobuf (Protocol Buffers)** 形式。
        - これはJSON形式ではなく、バイナリベースのシリアライズフォーマット。
        - Node-RED等で直接メッセージを見ると "Invalid JSON string" のように表示されるのはこのため。
    - **伝送形式:**
        - Protobufメッセージは通常、生の**バイナリデータ**としてMQTTペイロードに格納される。
        - 特殊なエンコーディング(Base64等)は通常行われない。
    - **メッセージ構造のヒント (PowerStream等の既存実装より類推):**
        - EcoFlow独自のヘッダー構造を持つ可能性が高い。
        - ヘッダーには `pdata` (Protobufペイロード)、`cmd_id`、`seq` (シーケンス番号)、`enc_type` などが含まれる。
    - **特に注意すべき点 (ハートビートメッセージ):**
        - トピック `app/device/property/<DEVICE_SN>` で受信する定期的状態更新(ハートビート)メッセージ (cmdId 1, 2, 3, 4, 28など) の `pdata` 部分は、そのままではProtobufとしてデコードできない。
        - **ヘッダー内の `seq` (シーケンス番号) を使用して、`pdata` の各バイトをXORデコードする必要がある** (主に `seq` の下位1バイトとのXOR)。
        - XORデコード後にProtobufとしてパース可能になる。
        - (参考: `hassio-ecoflow-cloud` GitHub Issue #193, `michaelahern` 氏のコメント)
    - **`get_reply` メッセージ:**
        - `app/<USER_ID>/<DEVICE_SN>/thing/property/get_reply` トピックで受信するメッセージは、通常XORデコードは不要で、直接Protobufとしてデコード可能。
        - 1つの `get_reply` に複数の `cmdId` を持つProtobufメッセージが含まれることがある。
    - **参考情報源:**
        - `ioBroker.ecoflow-mqtt` リポジトリ (特に `lib/parser.js` や `.proto` ファイル群)
        - `hassio-ecoflow-cloud` GitHub Issue #193 (Delta Pro Ultra, 特に `michaelahern` 氏の .proto ファイルやデコードに関するコメント)
        - `hassio-ecoflow-cloud` GitHub Issue #270 (Delta Pro 3)
- [ ] Protobufメッセージのサンプル収集
    - 例: Node-REDやioBroker等で実際の生データをキャプチャ
    - **目的:** Delta Pro3がMQTTで送受信する実際のProtobufメッセージの生データを収集し、後のスキーマ解析やデコード処理実装の基礎とする。
    - **準備するもの:**
        - EcoFlow Delta Pro 3 実機
        - MQTTブローカー接続情報 (アドレス、ポート、認証情報)
        - MQTTクライアントツール (以下いずれか、または複数):
            - **MQTT Explorer:** GUIでトピック購読、メッセージ表示・コピーが容易。
            - **Node-RED:** フローベース。MQTTノードで購読しファイル保存やデバッグ表示。
            - **ioBroker と `ioBroker.ecoflow-mqtt` アダプター:** 既存環境があればデバッグログ活用。
            - **コマンドラインMQTTクライアント (mosquitto_sub等):** CUIでの購読・保存。
    - **収集手順:**
        1.  **MQTTブローカーに接続:** 準備したツールと認証情報で接続する。
        2.  **対象トピックを購読:**
            - `app/device/property/<DEVICE_SN>` (ハートビート)
            - `app/<USER_ID>/<DEVICE_SN>/thing/property/get_reply` (状態取得応答)
            - `app/<USER_ID>/<DEVICE_SN>/thing/property/set` (コマンド送信)
            - `app/<USER_ID>/<DEVICE_SN>/thing/property/set_reply` (コマンド応答)
            - (SNとUserIDは自身のものに置き換える。必要に応じてワイルドカード `#` や `+` を使用)
        3.  **データ収集の実行:**
            -   **状態更新 (ハートビート):**
                -   `app/device/property/<DEVICE_SN>` をしばらく購読し、複数パターンのメッセージを収集。
                -   メッセージ生データに加え、ヘッダーの `cmdId`, `seq` も記録 (XORデコードに必要)。
            -   **状態取得 (`get_reply`):**
                -   可能であれば、`get` リクエストを送信し、対応する `get_reply` メッセージを収集。
                -   送信した `get` リクエストの内容も記録。
            -   **コマンド送受信 (`set`, `set_reply`):**
                -   EcoFlowアプリ等で様々な操作 (AC ON/OFF, 充電上限変更, 放電下限変更, 電源ON/OFF等) を行う。
                -   操作時に `set` トピックに送られるメッセージと、`set_reply` で返る応答をセットで収集。
                -   **行った操作内容を必ず記録する。** (例: 「AC出力をON」)
        4.  **記録・保存:**
            -   収集したデータはテキストファイル、CSV、JSONファイル等に保存する。
            -   各サンプルについて以下情報を推奨:
                -   **日時**
                -   **トピック名**
                -   **メッセージ生データ (HEX文字列 or バイト配列)**
                -   **ヘッダー情報 (判明すれば):** `cmdId`, `seq`, `src`, `dest`, `enc_type` 等
                -   **操作内容 (コマンドの場合)**
                -   **備考**
    - **収集量の目安:** 多様な操作、多様な状態でのメッセージをできるだけ多く。設定値の僅かな違いによるメッセージの変化も重要。
- [ ] Protobufスキーマ(.protoファイル)の入手・推測
    - 例: 既存リポジトリやissue、ioBroker.ecoflow-mqttの実装を参考にする
    - **最優先調査対象:**
        - **`foxthefox/ioBroker.ecoflow-mqtt` リポジトリ:**
            - `lib/` ディレクトリ配下や `doc/devices/` 配下に、Delta Pro 3 (DP3) または Delta Pro Ultra (DPU) 向けの `.proto` ファイル、あるいはそれらに関連するスキーマ定義が含まれている可能性が高い。
            - Changelog に "new Delta Pro 3 implementation" (v1.3.0), "preparations for DeltaPro3 decode" (v1.0.3) の記述あり。
            - 特に `lib/ecoflow_data.js` や `lib/parser.js`、`.proto` ファイル群を確認。
        - **`tolwi/hassio-ecoflow-cloud` GitHub Issue #193 (Delta Pro Ultra):**
            - `michaelahern` 氏が提供している以下の `.proto` ファイルおよび `pbdesc.txt` はDP3にも流用・応用できる可能性が高い:
                - `AppShowHeartbeatReport.proto` (cmdId 1)
                - `BackendRecordHeartbeatReport.proto` (cmdId 2)
                - `AppParaHeartbeatReport.proto` (cmdId 3)
                - `BpInfoReport.proto` (cmdId 4)
                - `pbdesc.txt` (上記 .proto を生成するための FileDescriptorSet)
            - これらのファイルは、収集したサンプルデータの `pdata` (XORデコード後) を解析する際に使用する。
    - **スキーマ構造のヒント:**
        - EcoFlowのProtobufメッセージは、共通のヘッダー構造と、`cmdId` ごとに異なるペイロード (`pdata`) 構造を持つことが多い。
        - `ioBroker.ecoflow-mqtt` で PowerStream 用に定義されているヘッダー構造も参考になる可能性がある。
    - **入手・推測の手順:**
        1.  上記リポジトリ・Issueから `.proto` ファイルやスキーマ定義をダウンロード・収集する。
        2.  収集したサンプルメッセージ (特にXORデコード済みの `pdata`) と照らし合わせ、対応する `cmdId` のスキーマを特定する。
        3.  オンラインのProtobufデコーダー (例: `protobuf-decoder.netlify.app`) やローカルツール (`protoc --decode_raw` 等) を使用し、収集したスキーマ定義を適用してメッセージが正しくデコードできるか検証する。
        4.  既存のスキーマでデコードできないフィールドや、DP3特有のフィールドがある場合は、サンプルデータの値の変動パターンからデータ型 (int32, float, string, bool, enum, nested message等) やフィールド番号を推測し、`.proto` ファイルを拡張・修正する。
        5.  コマンド送信 (`set` トピック) 用のメッセージスキーマも同様に、送信データと応答データから推測・定義する。
    - **スキーマ推測ツール (補助的利用):**
        - 生のバイナリデータからある程度スキーマを推測するツール (例: `protoscope`, `blackboxprotobuf`) も存在するが、完全なスキーマ生成は難しいため、あくまで補助的な手段として利用を検討。
    - **ドキュメント化:**
        - 特定・推測できたスキーマは、メッセージタイプごとに `.proto` ファイルとして保存・管理する。
        - 各フィールドの意味が判明次第、コメントとして追記する。
- [ ] 主要なフィールドと値の意味の特定
    - 例: バッテリー残量、AC出力、ソーラー入力など、どのフィールドが何を表すか
    - **参考情報源:**
        - [hassio-ecoflow-cloud Issue #193, #270](https://github.com/tolwi/hassio-ecoflow-cloud/issues/193)
        - [ioBroker.ecoflow-mqtt/lib/ecoflow_data.js](https://github.com/foxthefox/ioBroker.ecoflow-mqtt)
        - 実際のデバッグデータ例・コミュニティの推測
    - **代表的なcmdId: 1, 2, 3, 4, 32 など**
        - cmdId 1: アプリ表示用ハートビート(基本ステータス)
        - cmdId 2: バックエンド記録用ハートビート(詳細電力情報)
        - cmdId 3: アプリパラメータハートビート(設定値など)
        - cmdId 4: バッテリーパック情報
        - cmdId 32: 詳細な電力・バッテリー情報(DP3/Ultra系で多用)
    - **主要フィールド例(cmdId 32, foxthefox氏の推測より)**

        | フィールド名         | フィールド番号 | 型     | 意味・推定内容(例)                |
        |----------------------|---------------|--------|-------------------------------------|
        | voltage68            | 68            | float  | AC出力電圧(例: 119V)              |
        | current69            | 69            | float  | AC出力電流                          |
        | voltage149           | 149           | float  | DC出力電圧(例: 24V)               |
        | current150           | 150           | float  | DC出力電流                          |
        | voltage151           | 151           | float  | AC出力電圧(別系統?)              |
        | unknown169           | 169           | float  | 出力電力(W)?                     |
        | voltage197           | 197           | float  | AC出力電圧                          |
        | voltage244           | 244           | float  | バッテリー電圧(例: 52V)           |
        | unknown245           | 245           | float  | バッテリー電流?                    |
        | unknown247           | 247           | int32  | フル容量(例: 80000mAh)            |
        | unknown249           | 249           | int32  | 残容量(例: 26400mAh)              |
        | unknown256           | 256           | int32  | 最小セル電圧(例: 3309 → 3.309V)   |
        | unknown257           | 257           | int32  | 最大セル電圧(例: 3313 → 3.313V)   |
        | voltage264           | 264           | float  | バッテリー電圧                      |
        | voltage266           | 266           | float  | バッテリー電圧(別系統?)          |
        | unknown267           | 267           | float  | 充電上限/下限設定値?               |
        | unknown293           | 293           | int32  | 120000(容量?)                    |
        | unknown294           | 294           | int32  | 2000(容量?)                      |
        | unknown295           | 295           | int32  | 300000(容量?)                    |
        | unknown296           | 296           | int32  | 60000(容量?)                     |
        | voltage318           | 318           | float  | バッテリー電圧                      |
        | unknown337           | 337           | float  | 充電上限(%)?                     |
        | unknown340           | 340           | float  | バッテリー電流?                    |
        | voltage341           | 341           | float  | バッテリー電圧                      |
        | unknown369           | 369           | float  | MPPT出力電力(例: 400W)            |
        | unknown377           | 377           | float  | MPPT電圧(例: 57.25V)              |
        | unknown378           | 378           | float  | MPPT出力電力(例: 837W)            |
        | unknown385           | 385           | float  | バッテリー電圧                      |
        | unknown386           | 386           | float  | MPPT出力電力                        |

    - **具体的な値の例**
        - voltage68: 119.3 → AC出力電圧
        - voltage149: 24.0 → DC出力電圧
        - unknown249: 26400 → 残容量mAh
        - unknown337: 80 → 充電上限%?
        - unknown369: 400.9 → MPPT出力W
    - **備考:**
        - フィールド番号や型は、今後のサンプルデータ解析やアプリ画面との突き合わせでさらに確定・詳細化が必要。
        - 既存の .proto ファイル(例: AppShowHeartbeatReport.proto など)も参考にすること。
- [ ] コマンド送信時のメッセージ構造調査
    - 例: スイッチON/OFFや設定変更時の送信データの内容
    - **参考情報源:**
        - [hassio-ecoflow-cloud Issue #193, #270](https://github.com/tolwi/hassio-ecoflow-cloud/issues/193)
        - [ioBroker.ecoflow-mqtt/lib/ecoflow_data.js](https://github.com/foxthefox/ioBroker.ecoflow-mqtt)
        - 実際のデバッグデータ例(Node-RED, MQTT Explorer等で取得されたBase64/HEXデータ)
    - **送信トピック:**
        - `app/<USER_ID>/<DEVICE_SN>/thing/property/set` : コマンド送信(HA/App → Device)
        - `app/<USER_ID>/<DEVICE_SN>/thing/property/set_reply` : コマンド応答(Device → HA/App)
    - **メッセージ形式:**
        - いずれもProtobuf形式のバイナリデータ。
        - 通常、`set` 送信時はXORデコード不要。
        - `set`/`set_reply` どちらもcmdIdや操作内容に応じたペイロード構造。
    - **代表的なコマンド例と推定構造:**
        - **AC出力ON/OFF:**
            - cmdId: 32, もしくはコマンド種別ごとに異なる場合あり
            - 主要フィールド例: `ac_out_on` (bool/int), `ac_out_off` (bool/int)
        - **充電上限/下限変更:**
            - cmdId: 32, もしくは専用cmdId
            - 主要フィールド例: `chg_soc_max` (int), `chg_soc_min` (int)
        - **X-Boost切替:**
            - cmdId: 32, もしくは専用cmdId
            - 主要フィールド例: `xboost_enable` (bool/int)
        - **GFCI/RCD切替:**
            - cmdId: 32, もしくは専用cmdId
            - 主要フィールド例: `gfci_enable` (bool/int)
        - **DC/USB出力ON/OFF:**
            - cmdId: 32, もしくは専用cmdId
            - 主要フィールド例: `dc_out_on` (bool/int), `usb_out_on` (bool/int)
        - **AC充電速度/入力電流設定:**
            - cmdId: 32, もしくは専用cmdId
            - 主要フィールド例: `ac_chg_current` (int), `ac_chg_speed` (int)
        - **車載入力電流設定:**
            - cmdId: 32, もしくは専用cmdId
            - 主要フィールド例: `car_in_current` (int)
    - **実際のサンプルデータ例(Base64/HEX, debug logより):**
        - AC出力ON/OFF: `CioKA4ABABAgGAIgASgBOANA/gFIEVADWAFwwrmugwKAAROIAQG6AQNpb3M=`
        - X-Boost ON: `CioKA8gBARAgGAIgASgBOANA/gFIEVADWAFwk7HDgQKAAROIAQG6AQNpb3M=`
        - 充電上限変更: `CioKA4gCURAgGAIgASgBOANA/gFIEVADWAFwjZCZgQKAAROIAQG6AQNpb3M=`
        - 車載入力電流変更: `CioKA6ADBxAgGAIgASgBOANA/gFIEVADWAFw9anHgQKAAROIAQG6AQNpb3M=`
        - GFCI/RCD OFF: `CioKA+gDABAgGAIgASgBOANA/gFIEVADWAFws4/AgQKAAROIAQG6AQNpb3M=`
    - **コマンド送信時の流れ:**
        1. Home AssistantやEcoFlowアプリから操作(例: AC出力ON)
        2. `set`トピックに対応するProtobufメッセージを送信
        3. デバイスがコマンドを受信し、`set_reply`トピックで応答
        4. 応答メッセージには、操作結果や新しい状態が含まれる
    - **cmdId/フィールド番号の推定:**
        - 多くのコマンドはcmdId=32のメッセージで送信される傾向(DP3/Ultra系)
        - フィールド番号や型は、今後のサンプルデータ解析やアプリ画面との突き合わせでさらに確定・詳細化が必要
        - 既存の.protoファイル(例: AppShowHeartbeatReport.proto, BackendRecordHeartbeatReport.proto等)も参考にすること
    - **備考:**
        - コマンド送信時のメッセージ構造は、今後のサンプルデータ収集・解析でさらに詳細化・確定が必要
        - コマンド種別ごとにcmdIdやフィールド番号が異なる場合があるため、実際の操作とデータの突き合わせが重要
        - 参考: [protobuf-decoder.netlify.app](https://protobuf-decoder.netlify.app/) でサンプルデータのデコード・解析が可能

## 2. 既存定義・構造調査
- [ ] delta_pro.py, delta2_max.py など既存デバイス定義の項目一覧化
    - 例: センサー/スイッチ/スライダー/セレクトのリストアップ
    - **参考ファイル:**
        - custom_components/ecoflow_cloud/devices/internal/delta_pro.py
        - custom_components/ecoflow_cloud/devices/internal/delta2_max.py
    - **センサー(例: Delta Pro):**
        | 種別         | エンティティ名例                | 属性/説明                       |
        |--------------|-------------------------------|---------------------------------|
        | Level        | bmsMaster.soc                 | メインバッテリー残量            |
        | Level        | bmsMaster.f32ShowSoc          | メインバッテリー残量(float)     |
        | Capacity     | bmsMaster.designCap           | 設計容量                        |
        | Capacity     | bmsMaster.fullCap             | フル容量                        |
        | Capacity     | bmsMaster.remainCap           | 残容量                          |
        | Level        | bmsMaster.soh                 | SOH                             |
        | Level        | ems.lcdShowSoc                | 複合バッテリー残量              |
        | Watts        | pd.wattsInSum                 | 合計入力W                       |
        | Watts        | pd.wattsOutSum                | 合計出力W                       |
        | InWatts      | inv.inputWatts                | AC入力W                         |
        | OutWatts     | inv.outputWatts               | AC出力W                         |
        | InMilliVolt  | inv.acInVol                   | AC入力V                         |
        | OutMilliVolt | inv.invOutVol                 | AC出力V                         |
        | InWattsSolar | mppt.inWatts                  | ソーラー入力W                   |
        | InVoltSolar  | mppt.inVol                    | ソーラー入力V                   |
        | InAmpSolar   | mppt.inAmp                    | ソーラー入力A                   |
        | OutWattsDc   | mppt.outWatts                 | DC出力W                         |
        | OutVoltDc    | mppt.outVol                   | DC出力V                         |
        | ...          | ...                           | ...(他、多数)                 |
    - **スイッチ(例: Delta Pro):**
        | エンティティ名例           | 説明                      |
        |--------------------------|---------------------------|
        | pd.beepState             | ビーパーON/OFF            |
        | mppt.carState            | DC出力ON/OFF              |
        | inv.cfgAcEnabled         | AC出力ON/OFF              |
        | inv.cfgAcXboost          | X-Boost ON/OFF            |
        | pd.acautooutConfig       | AC常時出力ON/OFF          |
        | pd.watthisconfig         | バックアップ電源設定       |
    - **スライダー/ナンバー(例: Delta Pro):**
        | エンティティ名例           | 説明                      |
        |--------------------------|---------------------------|
        | ems.maxChargeSoc         | 充電上限(%)               |
        | ems.minDsgSoc            | 放電下限(%)               |
        | pd.bppowerSoc            | バックアップリザーブ(%)    |
        | ems.minOpenOilEbSoc      | 発電機自動起動しきい値(%)  |
        | ems.maxCloseOilEbSoc     | 発電機自動停止しきい値(%)  |
        | inv.cfgSlowChgWatts      | AC充電パワー(W)            |
    - **セレクト(例: Delta Pro):**
        | エンティティ名例           | 説明                      |
        |--------------------------|---------------------------|
        | mppt.cfgDcChgCurrent     | DC充電電流選択             |
        | pd.lcdOffSec             | LCDオフタイマー            |
        | pd.standByMode           | スタンバイモード           |
        | inv.cfgStandbyMin        | ACスタンバイタイマー       |
    - **Delta2 Maxも同様に多数のセンサー・スイッチ・スライダー・セレクトを持つ。**
        - センサー: bms_bmsStatus.soc, mppt.inWatts, inv.inputWatts, ...
        - スイッチ: pd.beepMode, pd.dcOutState, inv.cfgAcEnabled, ...
        - スライダー: bms_emsStatus.maxChargeSoc, bms_emsStatus.minDsgSoc, ...
        - セレクト: pd.lcdOffSec, inv.standbyMin, mppt.carStandbyMin, ...
    - **備考:**
        - 各エンティティは、`custom_components/ecoflow_cloud/devices/internal/` 配下の各.pyで `sensors`/`switches`/`numbers`/`selects` メソッドにより定義されている。
        - 実際の項目名・属性はconst.pyや各Entityクラスの定義も参照。
        - DP3対応時は、これら既存定義をベースに、DP3特有の項目追加・調整を行う。
- [ ] 既存デバイスのデータパース・エンティティ生成ロジック調査
    - 例: どのようにデータを受け取り、Home Assistantのエンティティに変換しているか
    - **全体フロー:**
        1. **MQTT受信**
            - `EcoflowMQTTClient`（`api/ecoflow_mqtt.py`）が各トピックでメッセージ受信。
            - 受信時、各デバイス（`BaseDevice`継承クラス）に `update_data(payload, topic)` を呼び出す。
        2. **データパース・格納**
            - `BaseDevice.update_data()` でトピック種別ごとに `_prepare_data()` でデータをパース。
            - デフォルトはJSONデコード。Protobuf対応デバイスは各デバイスでオーバーライドし、バイナリ→XOR→Protobufデコード等を実装。
            - パース後のデータは `EcoflowDataHolder`（`devices/data_holder.py`）の `params` 等に格納。
        3. **エンティティ生成**
            - 各デバイス（例: `DeltaPro`, `Delta2Max`）は `sensors()`/`switches()`/`numbers()`/`selects()` でエンティティリストを返す。
            - 各エンティティは `entities/__init__.py` の `EcoFlowDictEntity`/`BaseSensorEntity` などを継承。
        4. **Home Assistant連携**
            - 各プラットフォームの `async_setup_entry()` で `device.sensors(client)` などを呼び出し、エンティティを登録。
            - エンティティは `CoordinatorEntity` として `coordinator`（デバイスの `EcoflowDeviceUpdateCoordinator`）のデータ更新を購読。
        5. **値の更新・反映**
            - データ更新時、`_handle_coordinator_update()` → `_updated(data)` で `params` から値を抽出し、エンティティの状態を更新。
            - `mqtt_key` で `params` 内の値を `jsonpath_ng` で抽出。
            - 値が変化した場合、Home Assistantの状態が自動で更新される。
    - **主要クラス・関数:**
        - `EcoflowMQTTClient`（MQTT受信・publish）
        - `BaseDevice`（データパース・保持・エンティティ生成）
        - `EcoflowDataHolder`（データ保持・履歴管理）
        - `EcoFlowDictEntity`/`BaseSensorEntity` など（エンティティの値更新ロジック）
    - **備考:**
        - Protobuf対応時は `_prepare_data()` のオーバーライドが必須。
        - データ構造やパース処理はDP3対応時に再設計・拡張が必要な場合あり。

## 3. 参考情報・コミュニティ調査
- [ ] ioBroker.ecoflow-mqttのDelta Pro3対応状況調査
    - 例: 実装例やスキーマ、データマッピングの有無
    - **対応状況（2024年5月時点）:**
        - バージョン1.3.0で「Delta Pro 3 implementation」として公式に対応が追加。
        - [Changelog](https://github.com/foxthefox/ioBroker.ecoflow-mqtt#changelog)や[README](https://github.com/foxthefox/ioBroker.ecoflow-mqtt#implemented-devices--structure-with-datapoints)にもDelta Pro 3の記載あり。
        - デバイス追加時に「Delta Pro 3」を選択可能。
    - **データマッピング・スキーマ:**
        - Protobufベースでのデータ受信・コマンド送信に対応。
        - コミュニティ（GitHub Issue #193, #270）でcmdIdごとのフィールド解析が進行中。
        - [AppShowHeartbeatReport.proto](https://github.com/tolwi/hassio-ecoflow-cloud/files/14321255/AppShowHeartbeatReport.proto.txt) など、主要なcmdId(1,2,3,4)の.protoファイルが公開・流用可能。
        - Heartbeatやget_replyのデータはXORデコード後にProtobufでパース可能。
        - コマンド送信もProtobuf形式で、cmdId=32等でAC出力ON/OFFや設定変更が可能。
    - **実装例:**
        - [lib/ecoflow_data.js](https://github.com/foxthefox/ioBroker.ecoflow-mqtt/blob/main/lib/ecoflow_data.js)・[lib/parser.js](https://github.com/foxthefox/ioBroker.ecoflow-mqtt/blob/main/lib/parser.js)にDP3/Ultra系のデータパース・マッピング実装あり。
        - データポイント（state名・型・単位等）はadapter起動時に自動生成され、HAのMQTT Discovery経由でHome Assistantに連携。
    - **コミュニティ解析状況:**
        - [hassio-ecoflow-cloud Issue #193, #270](https://github.com/tolwi/hassio-ecoflow-cloud/issues/193)でDP3/Ultraのフィールド解析・サンプルデータ共有が活発。
        - XORデコード・Protobufパース・フィールド推測の手法が確立。
        - heartbeat(pdata)のXORデコード方法や、主要なフィールド番号・意味も議論・共有されている。
    - **備考:**
        - ioBroker.ecoflow-mqttのDP3対応実装は、hassio-ecoflow-cloudやコミュニティの解析成果を積極的に取り込んでいる。
        - 公式API/SDKは未公開のため、今後もサンプルデータ・フィールド推測の精度向上が期待される。
        - 実装・解析の進捗はGitHub IssueやChangelogを随時確認すること。
- [ ] GitHub issue #270等のコミュニティ解析情報収集
    - 例: 実際のデータ例、フィールド推測、既知の課題
    - **参考情報源:**
        - [hassio-ecoflow-cloud Issue #270 (Delta Pro 3)](https://github.com/tolwi/hassio-ecoflow-cloud/issues/270)
        - [hassio-ecoflow-cloud Issue #193 (Delta Pro Ultra)](https://github.com/tolwi/hassio-ecoflow-cloud/issues/193)
        - [ioBroker.ecoflow-mqtt](https://github.com/foxthefox/ioBroker.ecoflow-mqtt)
    - **実際のデータ例:**
        - コミュニティユーザーがNode-REDやMQTT Explorerで取得したDP3のMQTTメッセージ（HEX/BASE64形式）が多数共有されている。
        - 例: `debug 4`（get_reply/heartbeat）や `debug 5/6`（set/set_reply）など、コマンド操作時・状態取得時の生データ。
        - サンプル: `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`
        - コマンド送信時の例: `CioKA8gBARAgGAIgASgBOANA/gFIEVADWAFww+7SigKAAROIAQG6AQNpb3M=`
    - **フィールド推測・進捗:**
        - foxthefox氏らが、cmdId=32等のメッセージに対し、Protobufスキーマ（例: `message cmdFunc254_cmdId32_Report`）を作成し、フィールド番号ごとに値の意味を推測。
        - 例: `voltage68`(68): AC出力電圧, `current69`(69): AC出力電流, `voltage149`(149): DC出力電圧, `unknown249`(249): 残容量mAh, `unknown337`(337): 充電上限%? など。
        - 実際の値の変動やアプリ画面との突き合わせで、フィールドの意味が徐々に確定。
        - Heartbeatやget_replyのデータはXORデコード後にProtobufでパース可能。
    - **既知の課題・議論:**
        - データ長制限（Node-REDのdebugノードの最大長）により、長大なメッセージが途中で切れる問題。
        - 一部フィールドの意味が未確定（`unknownXXX`）であり、今後もサンプル収集・アプリ画面との比較が必要。
        - コマンド送信時のフィールド番号・型も、操作ごとに異なる場合があり、さらなる解析が進行中。
        - BLE経由の解析や、他のEcoFlow機種との共通性・差分も議論されている。
    - **コミュニティの進捗:**
        - 実機ユーザーが積極的にサンプルデータを投稿し、操作内容とデータの対応付けを進行。
        - foxthefox氏が中心となり、.protoファイルの作成・修正、データマッピングの精度向上を推進。
        - XORデコード・Protobufパース・フィールド推測の手法が確立しつつある。
    - **今後の方針:**
        - さらなるサンプルデータ収集と、アプリ画面・実機表示値との突き合わせによるフィールド確定。
        - コマンド送信時の詳細な構造解析と、.protoファイルの拡充。
        - BLEや他の通信経路でのデータ取得・解析も視野に入れる。
    - **備考:**
        - 最新の解析状況・サンプルデータ・.protoファイルは、上記IssueやioBroker.ecoflow-mqttリポジトリのChangelog/README/コードを随時参照すること。
- [ ] 他のオープンソース実装・フォーラムの調査
    - 例: 似たような解析・実装事例の有無
    - **海外コミュニティの逆向き解析・プロトコル分析事例:**
        - 代表的な事例・OSS:
            - [peuter/ecoflow (GitHub)](https://github.com/peuter/ecoflow)
                - Homie MQTT規格でEcoFlowデバイス（主にPowerStream/Delta Max等）を制御・監視するPython実装。
                - .envでEcoFlowアカウント情報を指定し、MQTT経由でデータ取得・コマンド送信。
                - Delta Pro 3への直接対応は未確認だが、MQTT/Protobuf/XORデコードの実装例として参考になる。
            - [v1ckxy/ecoflow-withoutflow (GitHub)](https://github.com/v1ckxy/ecoflow-withoutflow)
                - EcoFlowポータブル電源の「オフラインモード」通信（WiFi直結/ポート8055等）を逆向き解析。
                - バイトストリーム通信・既知ポート・Javaクラス名・バイト列変換ユーティリティ等の詳細な調査記録あり。
                - Delta Max中心だが、通信プロトコルやバイナリ解析の手法がDP3にも応用可能。
            - [nielsole/ecoflow-bt-reverse-engineering (GitHub)](https://github.com/nielsole/ecoflow-bt-reverse-engineering)
                - EcoFlow Delta 2等のBluetooth通信プロトコル逆向き解析。
                - BLEアトリビュート・RFCOMM/UDPパケット・ビルドログ取得手順・データ構造推測など、BLE経由の制御・状態取得の実験例。
                - DP3/Ultra系のBLE仕様調査にも参考になる。
        - **海外フォーラム:**
            - [DIY Solar Power Forum](https://diysolarforum.com/threads/how-to-add-the-ecoflow-delta-pro-3-to-home-assistant-with-iobroker-and-mqtt.104005/) などで、ioBrokerやHome Assistant連携、MQTT/Protobuf/XORデコードの実践例・議論が活発。
        - **総括:**
            - DP3/Ultra系の完全なプロトコル仕様は未公開だが、世界中のコミュニティでサンプルデータ収集・フィールド推測・.protoファイル作成・OSS実装が進行中。
            - BLEやWiFi直結モード、MQTT/Protobuf/XORデコードなど多様なアプローチが存在し、既存OSSやコミュニティ成果を積極的に参照・活用することが推奨される。

### 備考
- 各タスクは進捗や新たな発見に応じてさらに細分化・追記してください。
- サンプルデータの収集・解析が最初の重要ステップです。