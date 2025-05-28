# Delta Pro 3 MQTT トピック構造 詳細

このドキュメントは、EcoFlow Delta Pro 3 の MQTT 通信におけるトピック構造、メッセージ形式、主要なコマンド ID、および関連する Protobuf 定義に関する詳細な調査結果をまとめたものです。

## 1. 基本的な MQTT トピック構造

EcoFlow デバイスの MQTT トピックは、一般的に以下の形式に従います。

- **コマンド送信 (HA/App -> Device):**
  `app/<USER_ID>/<DEVICE_SN>/thing/property/set`
- **コマンド応答 (Device -> HA/App):**
  `app/<USER_ID>/<DEVICE_SN>/thing/property/set_reply`
- **状態取得要求 (HA/App -> Device):**
  `app/<USER_ID>/<DEVICE_SN>/thing/property/get`
- **状態取得応答 (Device -> HA/App):**
  `app/<USER_ID>/<DEVICE_SN>/thing/property/get_reply`
- **デバイスからの定期的状態更新/ハートビート (Device -> HA/App):**
  `app/device/property/<DEVICE_SN>`

ここで、

- `<USER_ID>`: EcoFlow アカウントのユーザー ID (通常 19 桁の数字)
- `<DEVICE_SN>`: Delta Pro 3 のシリアルナンバー

## 2. ペイロード形式と主要な Protobuf メッセージ

MQTT メッセージのペイロードは、すべて **Protobuf (Protocol Buffers)** 形式のバイナリデータです。

- **ハートビートメッセージの XOR デコード:**
  - トピック `app/device/property/<DEVICE_SN>` で受信する定期的状態更新(ハートビート)メッセージの `pdata` 部分は、そのままでは Protobuf としてデコードできません。
  - **ヘッダー内の `seq` (シーケンス番号) を使用して、`pdata` の各バイトを XOR デコードする必要があります** (主に `seq` の下位 1 バイトとの XOR)。
  - XOR デコード後に Protobuf としてパース可能になります。
- **`get_reply` メッセージ:**
  - `app/<USER_ID>/<DEVICE_SN>/thing/property/get_reply` トピックで受信するメッセージは、通常 XOR デコードは不要で、直接 Protobuf としてデコード可能です。
  - 1 つの `get_reply` に複数の `cmdId` を持つ Protobuf メッセージが含まれることがあります。

### 2.1. 主要な `cmdId` と予想される内容

以下は、ioBroker.ecoflow-mqtt や GitHub Issue の情報を基にした、主要な `cmdId` とそのメッセージ内容の推測です。

- **`cmdId 1`**: アプリ表示用ハートビート (充電状態、残り時間など基本的なステータス)
  - 対応 Protobuf メッセージ (推測): `AppShowHeartbeatReport`
- **`cmdId 2`**: バックエンド記録用ハートビート (より詳細な電力情報、電圧、電流など)
  - 対応 Protobuf メッセージ (推測): `BackendRecordHeartbeatReport`
- **`cmdId 3`**: アプリパラメータハートビート (デバイス設定値など)
  - 対応 Protobuf メッセージ (推測): `AppParaHeartbeatReport`
- **`cmdId 4`**: バッテリーパック情報
  - 対応 Protobuf メッセージ (推測): `BpInfoReport`
- **`cmdId 17`**: 設定コマンド (`set_dp3`)
  - デバイスの各種設定変更に使用されます。
  - 応答は `setReply_dp3` (`cmdId: 18`) で返されます。
- **`cmdId 21`**: Display Property Upload (`DisplayPropertyUpload`)
  - 主にディスプレイ表示に関連するプロパティや、ユーザーが設定可能な項目を含みます。
- **`cmdId 22`**: Runtime Property Upload (`RuntimePropertyUpload`)
  - デバイスのリアルタイムな動作状態、センサー値、内部ステータスなどを含みます。
- **`cmdId 23`**: Report (`cmdFunc254_cmdId23_Report`)
  - タイムスタンプなどを含むレポート。
- **`cmdId 32` (EMS 関連)**: Report (`cmdFunc32_cmdId2_Report`)
  - Energy Management System に関連する詳細な情報。
- **`cmdId 50` (BMS 関連)**: Report (`cmdFunc50_cmdId30_Report`)
  - Battery Management System に関連する詳細な情報 (セル電圧、温度など)。

コマンド送信 (`set` トピック) も、操作対象に応じた `cmdId` を持つ Protobuf メッセージが使用されます。

### 2.2. `ioBroker.ecoflow-mqtt/lib/dict_data/ef_deltapro3_data.js` からの知見

このファイルは Delta Pro 3 の MQTT 通信におけるデータ構造とコマンド定義の核心情報を含んでいます。

- **`protoSource` (インライン Protobuf スキーマ):**
  - `RuntimePropertyUpload` (cmdId 22, cmdFunc 254): デバイスのランタイム状態 (センサー値、内部ステータス等)。
  - `DisplayPropertyUpload` (cmdId 21, cmdFunc 254): 表示関連プロパティ、ユーザー設定項目。
  - `cmdFunc50_cmdId30_Report` (cmdId 50, cmdFunc 32): BMS 詳細情報。
  - `cmdFunc32_cmdId2_Report` (cmdId 2, cmdFunc 32): EMS 詳細情報。
  - `cmdFunc254_cmdId23_Report` (cmdId 23, cmdFunc 254): タイムスタンプ等を含むレポート。
  - `set_dp3` (cmdId 17, cmdFunc 254): 設定コマンド送信用メッセージ。
  - `setReply_dp3` (cmdId 18, cmdFunc 254): 設定コマンド応答用メッセージ。
  - `setHeader`: MQTT コマンドメッセージの共通ヘッダー構造。
  - `setMessage`: `setHeader` を含む包括的なコマンドメッセージ構造。
  - スケジュールタスク関連の enum (`TIME_TASK_MODE`, `TIME_TASK_TYPE` 等) とメッセージ (`TimeTaskItemV2` 等)。
- **`deviceStates` / `deviceStatesDict`:**
  - Delta Pro 3 が持つ全ての状態と設定可能な項目を網羅的に定義しています。
  - `DisplayPropertyUpload`, `RuntimePropertyUpload`, `setDp3` などのカテゴリ別に、プロパティ名、データ型 (`number`, `string`, `switch`, `level`, `diagnostic`, `icon`, `array`)、単位、役割などが詳細に記述されています。
  - これは、Home Assistant でエンティティを定義する際の基礎情報となります。
- **`deviceCmd`:**
  - 各設定項目 (`setDp3` や `DisplayPropertyUpload` 内の操作可能項目) を変更する際の MQTT コマンドメッセージの具体的な構造 (`dest`, `cmdFunc`, `cmdId`, `dataLen`) を定義しています。
  - コマンド送信機能を実装する上で非常に重要です。
- **`protoMsg`:**
  - 受信した MQTT メッセージのヘッダー情報 (`cmdId` と `cmdFunc`) から、どの Protobuf メッセージ型でデコードすべきかを判断するためのマッピング情報です。
- **`prepareProtoCmd` 関数:**
  - 送信するコマンド名と値から、`protoSource` と `deviceCmd` を参照して、エンコード済みの Protobuf メッセージ (Buffer) を生成するロジックを提供します。
- **`storeProtoPayload` 関数:**
  - 受信した Protobuf ペイロードをデコードし、`deviceStatesDict` を参照して状態を更新するロジックの例を示しています。
- **`officialapi` オブジェクト:**
  - EcoFlow 公式アプリ等で利用可能な主要コマンドの送信パラメータ例 (`sn`, `cmdId`, `cmdFunc`, `params` 等) を提供しており、コマンド実装の参考になります。

## 3. 参考情報源

- **`ioBroker.ecoflow-mqtt` リポジトリ (特に `lib/dict_data/ef_deltapro3_data.js`)**: 最重要情報源。
  - `main.js`: アダプターのメイン処理ファイル。トピック購読、メッセージ受信処理、コマンド送信処理。
  - `lib/ecoflow_utils.js`: 通信・データ処理ユーティリティ。XOR デコード、Protobuf パース、コマンドペイロード生成。
  - `lib/ecoflow_data.js` (旧構造の参考): デバイスごとのデータポイント定義、`cmdId`とフィールドのマッピング。
- **`hassio-ecoflow-cloud` GitHub Issues:**
  - Issue #193 (Delta Pro Ultra): `michaelahern` 氏提供の `.proto` ファイルやデコードに関するコメント。
  - Issue #270 (Delta Pro 3): DP3 固有の情報、サンプルデータ、フィールド解析。
- **オンライン Protobuf デコーダー:**
  - `protobuf-decoder.netlify.app`

詳細なフィールドリストや具体的なコマンドパラメータについては、上記の情報源、特に `ef_deltapro3_data.js` 内の `deviceStatesDict` および `officialapi` オブジェクトを参照してください。
