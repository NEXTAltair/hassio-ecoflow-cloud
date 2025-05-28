## **完了** 問題の概要

EcoFlow Delta Pro 3 から MQTT メッセージを `scripts/mqtt_capture_dp3_debug.py` スクリプトで受信できない。
デバイスはオンラインであり、公式アプリからの接続・操作は可能。スクリプトは MQTT ブローカーへの接続、トピック購読、およびデータ取得要求メッセージの送信まではエラーなく実行できているように見えるが、デバイスからの応答 (状態更新など) が一切ない。

**完了**
次の課題は送受信したメッセージのデコード

## これまでの主な試行錯誤と経緯

**参照コードベース:** 主に `ioBroker.ecoflow-mqtt` (特に `lib/dict_data/ef_deltapro3_data.js`, `lib/ecoflow_utils.js`, `main.js`)

1.  **初期の MQTT 接続問題 (RC:128):**

    - 当初、MQTT ブローカー接続後すぐに `RC:128` (Unspecified error) で切断される問題が発生していた。
    - クライアント ID の形式を `ANDROID_{UUID}_{USER_ID}` に変更したことなどにより、この即時切断エラーは解消。現在は PINGREQ/PINGRESP の交換も確認でき、接続自体は安定している。

2.  **`ecopacket_pb2.py` (Protobuf 定義ファイル) の準備:**

    - 当初欠損していたが、[`ef_deltapro3_data.js`](../../ioBroker.ecoflow-mqtt/lib/dict_data/ef_deltapro3_data.js) 内の `protoSource` を抽出し、`scripts/ef_dp3_iobroker.proto` として保存。
    - `uv add grpcio-tools` で `protoc` を導入し、`protoc --python_out=. scripts/ef_dp3_iobroker.proto` コマンドで `scripts/ecopacket_pb2.py` を再生成。これにより、スクリプト内での `setHeader` や `setMessage` などの型参照に関するリンターエラーは(一時的に)解消されたように見えたが、依然としてリンターは型を認識できていない状態が続いている(実行時エラーは発生していない)。

3.  **データ取得要求メッセージの送信トピックと `setHeader` フィールド内容の試行錯誤:**

    - MQTT 接続・トピック購読完了後、デバイスからのデータ送信を促すためにメッセージを送信。
    - 当初は `ecopacket_pb2.setMessage` (内部に `ecopacket_pb2.setHeader` をラップ) を使用。
    - 送信先トピックを `/app/{USER_ID}/{DEVICE_SN}/thing/property/get` から `/app/{USER_ID}/{DEVICE_SN}/thing/property/set` に変更。
    - `setHeader` のフィールド内容について、ioBroker の実装を参考に多フィールド版とシンプル版（`src`, `dest`, `seq`, `from` のみ）を試行。`pdata` の有無、`dest` の値修正、`seq` の 32 ビット整数化なども試したが、いずれも応答なし。

4.  **購読トピック:**
    - `config.json` に基づき、`set`, `set_reply`, `get`, `get_reply`, `update`, `delete`, `delete_reply` およびハートビートトピック (`/app/device/property/{DEVICE_SN}`) などを購読。

## 最新の実行結果と分析 (2025-05-28 `setattr` 修正後)

- **データ取得要求メッセージの送信成功:**
  - `scripts/mqtt_capture_dp3_debug.py` の `on_connect` 関数内で、データ取得要求のトップレベルメッセージを `ecopacket_pb2.setMessage` から `ecopacket_pb2.Header` に変更。
  - `Header` メッセージの `from` フィールドへのアクセスを `setattr(message_to_send, "from", "ios")` に修正。
  - これにより、以前発生していた `AttributeError: Protocol message Header has no "from_"` エラーは解消され、データ取得要求メッセージ (`Header` 型) が MQTT ブローカーへ正常に送信され、`PUBACK` も受信している。
- **デバイスからの応答状況:**
  - データ取得要求メッセージ送信後も、期待する `get_reply` トピックでの全データなどの応答は依然として受信できていない。
  - `/app/device/property/{DEVICE_SN}` トピックからは継続してメッセージを受信。
    - これらのメッセージペイロードは Base64 デコードに失敗することが多い。成功時もデータ長は様々。
    - スクリプト内ではこれらのメッセージは「未処理のトピック」として扱われ、Protobuf としてのデコードや解釈は行われていない。
  - `/app/{USER_ID}/{DEVICE_SN}/thing/property/get_reply` トピックから、データ取得要求送信とは無関係に 1 件メッセージ (Length: 2498 bytes) を受信したが、ペイロード先頭バイトが `0x0a` であったため、「未対応のメッセージフォーマットバイト」として処理された。

**ログ抜粋 (2025-05-27 16:21 時点の `setMessage` での送信試行時のもの。現在は `Header` で送信):**

```
python scripts/mqtt_capture_dp3_debug.py
2025-05-27 16:21:47,865 - INFO - [__main__] - config.jsonの直接指定されたMQTT認証情報を使用します。
... (接続成功、トピック購読成功) ...
2025-05-27 16:21:48,447 - INFO - [__main__] - データ取得要求メッセージをトピック 'app/1807962518217633793/MR51ZJS4PG6C0181/thing/property/set' に送信します。
2025-05-27 16:21:48,447 - DEBUG - [__main__] - 送信メッセージ (protobuf): header {
  src: 32
  dest: 32
  seq: 311218975
  from: "ios"
}
2025-05-27 16:21:48,448 - DEBUG - [paho.mqtt.client] - Sending PUBLISH (d0, q1, r0, m2), 'b'app/1807962518217633793/MR51ZJS4PG6C0181/thing/property/set'', ... (24 bytes)
2025-05-27 16:21:48,720 - DEBUG - [paho.mqtt.client] - Received PUBACK (Mid: 2)
2025-05-27 16:21:50,381 - DEBUG - [paho.mqtt.client] - Received PUBLISH (d0, q0, r0, m0), '/app/device/property/MR51ZJS4PG6C0181', ...  (53 bytes)
... (同様のメッセージ受信と未処理のログが続く) ...
```

## 現在の主な課題と疑問点

- **デバイスからの期待される応答が得られない:** データ取得要求 (`Header` メッセージ) を送信後も、期待する `get_reply` や `set_reply` トピックでの応答がない。
- **`/app/device/property/{DEVICE_SN}` トピックのメッセージ解析:** このトピックから受信するメッセージのペイロード形式、エンコード方式（Base64 か否か）、具体的な Protobuf 型が不明。
- **正しい「データ取得要求」の方法が依然として不明:**
  - 送信先トピック (`/thing/property/set`)、`Header` の内容 (現在は `src`, `dest`, `seq`, `from` のみ) が Delta Pro 3 に有効か確証がない。
  - `pdata` に空でないペイロードが必要な可能性も残る。
- **EcoFlow サーバー側の期待するシーケンスが不明:** 単発のリクエストだけでなく、特定の初期化シーケンスや、他のメッセージとの組み合わせが必要な可能性。
- **リンターエラーと実行時挙動の不一致:** `ecopacket_pb2.py` 内の型がリンターに認識されていない（実行時エラーとは別問題）。
- **`ecopacket_pb2.py` の型定義の正確性:** ioBroker の `.proto` ファイルから生成したものが、実際の通信で使用されるべき型を正確に反映しているか。

## 根本原因分析とこれまでの調査詳細

### 1. データ取得要求メッセージのトップレベル Protobuf 型の不一致 (修正済み)

- 当初、Python スクリプトは `ecopacket_pb2.setMessage` を使用していたが、ioBroker は `Header` 型を直接使用。これがデバイスがメッセージを解釈できない根本原因と推測された。
- **対応:** Python スクリプトも `ecopacket_pb2.Header()` を使用するよう修正。

### 2. `AttributeError: module 'ecopacket_pb2' has no attribute 'Header'` (修正済み)

- `Header` 型への変更後、このエラーが発生しメッセージ送信不可に。
- **原因:** `.proto` ファイルの `Header` メッセージ内の `from` フィールド (Python 予約語) へのアクセス方法の問題。
- **対応:** [Protobuf 公式ドキュメント](https://protobuf.dev/reference/python/python-generated/#names-which-conflict-with-python-keywords) に従い、`setattr(message, "from", "ios")` を使用するよう修正し、エラー解消。

### 3. 送信メッセージの `pdata` の扱いに関する潜在的課題

- `.proto` の `setHeader.pdata` 型は `setValue` だが、ioBroker では `Header.pdata` (型 `bytes`) にコマンドペイロードを格納。
- 現在のデータ取得要求 (ioBroker `latestQuotas` 相当) では `pdata` は空のため問題ないが、今後他のコマンド送信時に考慮が必要。

### 4. ioBroker 実装の詳細分析結果

- [`ef_deltapro3_data.js`](../../ioBroker.ecoflow-mqtt/lib/dict_data/ef_deltapro3_data.js)の分析完了
- [`main.js`](../../ioBroker.ecoflow-mqtt/main.js)の MQTT 接続・初期化シーケンス分析 (詳細は @issue_01_ioBroker.ecoflow-mqtt_Sequence.md に記載)
- [`ecoflow_utils.js`](../../ioBroker.ecoflow-mqtt/lib/ecoflow_utils.js)の`prepareStreamCmd`と`getLastProtobufQuotas`関数の詳細分析 (詳細は [`issue_01_ecoflow_utils_analysis.md`](./issue_01_ecoflow_utils_analysis.md) に記載)

### 5. 現在のスクリプト問題点の特定とレビュー結果 (2025-05-28)

- **[`mqtt_capture_dp3_debug.py`](../../scripts/mqtt_capture_dp3_debug.py)の詳細レビュー:**
  - **`on_connect` でのデータ取得要求:**
    - (修正済み) 送信メッセージ (`setMessage` > `setHeader`) のペイロードを Base64 エンコードして送信していた。ioBroker では直接シリアライズ。→ 現在は `Header` を直接シリアライズして送信。
  - **`on_message` での受信処理:**
    - **Base64 デコード:** `/app/device/property/{SN}` からのメッセージは Base64 エンコードされているという ioBroker の `pstreamDecode` と整合するが、`get_reply` トピックのメッセージも同様に Base64 デコードを前提としている点の明確な根拠が ioBroker 側に見当たらない。
    - **`get_reply` トピック (`/app/{UID}/{SN}/thing/property/get_reply`):**
      - メッセージ先頭 1 バイト (`0x01` または `0x02`) に基づくデコード分岐の根拠が不明。
      - **提案:** 先頭バイトをスキップせずペイロード全体を `setMessage` (または `Header` / `HeaderMessage`) でデコードするか、ioBroker の `pstreamDecode` のように Base64 デコード → `HeaderMessage` デコード → 内部 `Header` 処理のロジックに近づける。
    - **`/app/device/property/{DEVICE_SN}` トピック (ハートビート/ストリーム):**
      - Base64 デコード → `HeaderMessage` (失敗時 `Header`) でデコードする流れは ioBroker と整合。
      - `HeaderMessage` 内の各 `Header` の `pdata` に対する XOR デコードと、その後の `cmdId`/`cmdFunc` に基づく具体的な Protobuf 型への動的デコード処理が未実装 (TODO コメント多数)。
      - **提案:** ioBroker 同様の条件での XOR デコードと、`cmdId`/`cmdFunc` と `ecopacket_pb2.py` (または専用マッピング) を用いた動的型特定・デコード処理を実装する。
  - **`xor_decode_pdata` 関数:**
    - 実装は ioBroker の挙動を正しく模倣していると考えられ、問題なさそう。
  - **全体:**
    - `ecopacket_pb2.py` が最新かつ正確であるかの再確認が重要。
    - デコード処理の複雑化に伴い、より詳細なエラーログがデバッグに有効。
- **[`ecopacket_pb2.py`](../../scripts/ecopacket_pb2.py)の Protobuf 定義の検証:**
  - `scripts/ecopacket_pb2.py` は、`scripts/ef_dp3_iobroker.proto` から正しく生成されており、メッセージ定義やフィールド定義のレベルでは大きな不整合は見られない。
  - **送信メッセージの `pdata` の扱いに関する潜在的課題:** (上記 3.参照)
  - **リンターエラーについて:** 開発環境設定に起因する可能性が高く、MQTT 応答なし問題の直接原因である可能性は低い。
- **現在のメッセージ送信ロジックと期待される形式の比較:**
  - **トップレベルのメッセージ型:** (上記 1.参照、修正済み)
  - **ヘッダーフィールド (`cmdId`, `cmdFunc`):** ioBroker `latestQuotas` では明示設定なし。Python も同様。
  - **ペイロード (`pdata`):** ioBroker `latestQuotas` では空。Python も同様。

## 今後の調査方針案 (優先度順)

1.  **`/app/device/property/{DEVICE_SN}` トピックから受信するメッセージの解析と処理実装:**
    - **最優先:** このトピックのメッセージペイロードが Base64 エンコードされているか否かを明確に判断する。ioBroker の実装や他のリファレンスを確認し、通常エンコードされていないのであれば、スクリプトの Base64 デコード処理を修正する(例: このトピックの場合はデコードを試みない)。
    - 受信したペイロードを `ecopacket_pb2.HeaderMessage` または `ecopacket_pb2.Header` (場合によってはさらに内部の `pdata` を `ecopacket_pb2.set_dp3` や `ecopacket_pb2.get_dp3` など適切な型) でデコードすることを試みる。
    - ioBroker の `main.js` で、この種のトピックでメッセージを受信した際に、どの Protobuf 型でパースし、どのようにデータを処理しているか (`syncDevice`, `parseMessage` 関数など) を詳細に確認し、Python スクリプトに同様の処理を実装する。
2.  **データ取得要求メッセージの再検討 (上記と並行または後):**
    - 受信メッセージ解析を進めてもなお期待する応答が得られない場合、再度データ取得要求 (`Header` メッセージ) の内容を見直す。
    - `src`, `dest`, `seq`, `from` 以外のフィールド (ioBroker の `latestQuotas` では設定されていないように見える `cmd_id`, `cmd_func` など) の要否や、`pdata` に特定の情報を入れる必要があるかなどを再調査する。
3.  **`ioBroker.ecoflow-mqtt` の `main.js` におけるデバイス接続確立後の初期メッセージ交換シーケンスの徹底的な再調査:**
    - `mqttClient.on('connect', ...)` ハンドラ内で、トピック購読後、具体的にどのトピックに、どのような構造のメッセージを、どの順番で送信しているか。特に `ef.getLastProtobufQuotas(this, id);` 以外の初期呼び出しがないか。
    - `DeltaPro3` (または類似の最新デバイス) の場合に特有の処理がないか。
4.  **公式アプリの通信内容の解析 (可能であれば):**
    - mitmproxy などを使用して、公式スマートフォンアプリがデバイスと通信する際の MQTT メッセージをキャプチャし、特に全データ取得時や操作時のリクエストトピック、ヘッダー、ペイロードを分析する。これが最も確実な情報源となる可能性が高い。
5.  **`setHeader` の `cmd_id` と `cmd_func` の再検討:**
    - [`ef_deltapro3_data.js`](../../ioBroker.ecoflow-mqtt/lib/dict_data/ef_deltapro3_data.js) の `deviceCmd` オブジェクトには、`latestQuotas: { cmdId: 255, cmdFunc: 2, ... }` 以外にも多数のコマンドが定義されている。これらのうち、「全データ取得」に近い意味合いを持つ別のコマンド ID が存在しないか確認する。もし該当するものがあれば、それを設定してデータ取得要求を送信してみる。
    - `product_id` と `version` が、デバイス情報と一致している必要があるか検討する。
6.  **異なる `from` の値の試行:** `"ios"`, `"Android"` 以外に、例えば空文字列や、他の一般的なクライアントを示す文字列を試す。
7.  **応答トピックの再確認:** `get_reply` や `/app/device/property/{DEVICE_SN}` 以外に、デバイスが応答を返す可能性のある購読トピックがないか、ioBroker のコードから再度洗い出す。
