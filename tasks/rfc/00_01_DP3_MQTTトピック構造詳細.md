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

- **メッセージ送受信の一般的な流れ:**

  - **データ取得要求:**
    - クライアント (HA/App) は、特定の `cmdId` と `cmdFunc` を持つ `Header` 型 (Python スクリプトの場合、例: `cmdId:1, cmdFunc:20`) または `setMessage` 型 (ioBroker の場合、例: `cmdId:255, cmdFunc:2` を `setHeader` に設定) の Protobuf メッセージを構築し、シリアライズ後、トピック `app/<USER_ID>/<DEVICE_SN>/thing/property/set` に送信します。
  - **データ取得応答:**
    - デバイスは、上記要求に対し、トピック `app/<USER_ID>/<DEVICE_SN>/thing/property/get_reply` で応答します。ペイロードは `HeaderMessage` でラップされている可能性があり、内部の `Header` の `pdata` に要求されたデータが含まれます。このメッセージは通常 XOR デコード不要ですが、先頭バイトによって特殊な処理 (`setMessage`, `setReply` でのデコード) が必要な場合が ioBroker の実装に見られます (例: `0x01`, `0x02`)。
  - **定期更新メッセージ (ハートビート):**
    - デバイスは、トピック `app/device/property/<DEVICE_SN>` で定期的に状態を通知します。
    - このメッセージのペイロードは、多くの場合 Base64 エンコードされていません。
    - まず `HeaderMessage` 型としてデコードします。
    - 次に、`HeaderMessage` 内部の各 `Header` オブジェクトを取り出します。
    - 各 `Header` の `pdata` フィールドに対し、`enc_type == 1 && src != 32` (送信元がデバイスで暗号化有効) の条件を満たす場合、`Header` 内の `seq` (シーケンス番号) をキーとして XOR デコードを実行します。
    - XOR デコード後の `pdata` を、その `Header` の `cmd_id` と `cmd_func` の組み合わせに基づき、特定の Protobuf メッセージ型 (例: `DisplayPropertyUpload`, `RuntimePropertyUpload`) にデコードします。このマッピングは `ioBroker.ecoflow-mqtt` の `protoMsg` オブジェクトや、Python スクリプトの `protobuf_mapping.py` で定義されます。

- **ハートビートメッセージの XOR デコード:** (上記に統合)
  - トピック `app/device/property/<DEVICE_SN>` で受信する定期的状態更新(ハートビート)メッセージの `pdata` 部分は、そのままでは Protobuf としてデコードできません。
  - **ヘッダー内の `seq` (シーケンス番号) を使用して、`pdata` の各バイトを XOR デコードする必要があります** (主に `seq` の下位 1 バイトとの XOR)。
  - XOR デコード後に Protobuf としてパース可能になります。
- **`get_reply` メッセージ:** (上記に統合)
  - `app/<USER_ID>/<DEVICE_SN>/thing/property/get_reply` トピックで受信するメッセージは、通常 XOR デコードは不要で、直接 Protobuf としてデコード可能です。
  - 1 つの `get_reply` に複数の `cmdId` を持つ Protobuf メッセージが含まれることがあります。

### 2.1. 主要な `(cmdId, cmdFunc)` の組み合わせとメッセージ内容

以下は、ioBroker.ecoflow-mqtt や GitHub Issue、Python スクリプトでの解析情報を基にした、主要な `(cmdId, cmdFunc)` の組み合わせと、それに対応するメッセージ内容の概要です。実際のデコードには `ioBroker.ecoflow-mqtt` の `protoMsg` マッピングや Python 側の `protobuf_mapping.py` を参照してください。

| `cmdId` | `cmdFunc` | メッセージ概要/目的                               | ioBroker `protoSource` 内の型名 (例) | Python での対応型 (例)     | 主なトピック                                        |
| ------- | --------- | ------------------------------------------------- | ------------------------------------ | -------------------------- | --------------------------------------------------- |
| 1       | 20        | データ取得要求 (Python スクリプト側で使用)        | (`Header`)                           | `Header`                   | `.../thing/property/set`                            |
| 255     | 2         | データ取得要求 (ioBroker `getLastProtobufQuotas`) | `setMessage` (`setHeader`)           | `SetMessage` (`SetHeader`) | `.../thing/property/set`                            |
| 17      | 254       | 設定コマンド送信                                  | `set_dp3`                            | `SetDp3`                   | `.../thing/property/set`                            |
| 18      | 254       | 設定コマンド応答                                  | `setReply_dp3`                       | `SetReplyDp3`              | `.../thing/property/set_reply`                      |
| 21      | 254       | Display Property Upload                           | `DisplayPropertyUpload`              | `DisplayPropertyUpload`    | `app/device/property/{SN}` (XOR デコード後 `pdata`) |
| 22      | 254       | Runtime Property Upload                           | `RuntimePropertyUpload`              | `RuntimePropertyUpload`    | `app/device/property/{SN}` (XOR デコード後 `pdata`) |
| 23      | 254       | Report (タイムスタンプ等)                         | `cmdFunc254_cmdId23_Report`          | `CmdFunc254CmdId23_Report` | `app/device/property/{SN}` (XOR デコード後 `pdata`) |
| 30      | 50        | BMS 詳細情報 (ioBroker 定義)                      | `cmdFunc50_cmdId30_Report`           | `CmdFunc50CmdId30_Report`  | `app/device/property/{SN}` (XOR デコード後 `pdata`) |
| 2       | 32        | EMS 詳細情報 (ioBroker 定義)                      | `cmdFunc32_cmdId2_Report`            | `CmdFunc32CmdId2_Report`   | `app/device/property/{SN}` (XOR デコード後 `pdata`) |

**注意:**

- 上記の `cmdId`, `cmdFunc` の組み合わせや型名は、`ioBroker.ecoflow-mqtt` のバージョンや実際のデバイスのファームウェアによって異なる場合があります。
- `cmdId 1, 2, 3, 4` は、古いバージョンの情報や他のデバイスのものである可能性があり、Delta Pro 3 では上記 `(cmdId, cmdFunc)` の組み合わせでより具体的な型名が `ef_deltapro3_data.js` 内で定義されている点に注意が必要です。

### 2.2. `ioBroker.ecoflow-mqtt/lib/dict_data/ef_deltapro3_data.js` からの知見

このファイルは Delta Pro 3 の MQTT 通信におけるデータ構造とコマンド定義の核心情報を含んでいます。

- **`protoSource` (インライン Protobuf スキーマ):**
  - ここには、上記の表で触れた `DisplayPropertyUpload`, `RuntimePropertyUpload`, `cmdFunc50_cmdId30_Report` といったデバイス固有の Protobuf メッセージ型に加え、基本的な `Header`, `HeaderMessage`, `setMessage`, `setHeader`, `setValue` や、スケジュールタスク関連の enum (`TIME_TASK_MODE`, `TIME_TASK_TYPE` 等) とメッセージ (`TimeTaskItemV2` 等) が定義されています。
  - Python スクリプトでは、この `protoSource` を元に `ef_dp3_iobroker.proto` ファイルを作成し、`protoc` でコンパイルして `ef_dp3_iobroker_pb2.py` を生成して利用しています。
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
