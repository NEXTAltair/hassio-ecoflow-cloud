# Delta Pro 3 MQTT メッセージ形式調査 詳細

このドキュメントは、EcoFlow Delta Pro 3 の MQTT メッセージ形式に関する詳細な調査結果を記録します。

## 調査目的

- Delta Pro 3 と MQTT ブローカー間で送受信されるメッセージの正確な形式を特定する。
- Home Assistant 連携機能の開発に必要なメッセージエンコード・デコード処理を明確にする。

## 調査対象・項目

- **メッセージヘッダー構造の解析:**
  - ヘッダーに含まれる各フィールド（長さ、コマンド ID、フラグ等）の意味と構造を特定する。
- **ペイロードのエンコード/デコード方式の解明:**
  - XOR デコード処理の詳細（キー、処理範囲など）を確認する。
  - `get_reply` メッセージの具体的な形式と内容を分析する。
- **Protobuf スキーマの検証と推測:**
  - `ioBroker.ecoflow-mqtt` の `ef_deltapro3_data.js` 内 `protoMsg` や `protoSource` から推測される Protobuf スキーマを、実際のキャプチャデータと照合し、検証・修正する。
  - 未知のコマンドやデータポイントに対応する Protobuf メッセージ構造を推測・定義する。
- **コマンド送信時のメッセージ構造:**
  - `scripts/mqtt_capture_dp3_debug.py` を用いて、特定の操作（充電開始/停止、AC 出力 ON/OFF など）を行った際の MQTT メッセージをキャプチャし、その構造を分析する。
  - `ioBroker.ecoflow-mqtt` の `prepareProtoCmd` 関数などを参考に、コマンド発行時のメッセージ構築方法を明らかにする。
- **定期的な状態更新メッセージの解析:**
  - デバイスから定期的に送信される状態情報（バッテリー残量、入出力電力など）のメッセージ形式を特定する。

## 調査方法

1.  **実機接続によるデータキャプチャ:**
    - `scripts/mqtt_capture_dp3_debug.py` を使用し、Delta Pro 3 と MQTT ブローカー間の通信をキャプチャする。
    - 様々な操作を行い、多様な種類のメッセージを収集する。
2.  **`ioBroker.ecoflow-mqtt` のコード解析:**
    - 特に `lib/dict_data/ef_deltapro3_data.js` を中心に、メッセージ処理に関連するロジックを詳細に分析する。
3.  **キャプチャデータの解析とスキーマ照合:**
    - キャプチャしたバイナリデータを、ヘッダー構造、XOR デコード、Protobuf スキーマに基づいて解析する。
    - 必要に応じてスキーマを修正・拡張する。

## 今後の進め方

- [ ] 実機を MQTT ブローカーに接続し、`scripts/mqtt_capture_dp3_debug.py` を用いてデータキャプチャ環境を構築する。
- [ ] 基本的な操作（電源 ON/OFF、情報取得など）を行い、対応する MQTT メッセージをキャプチャ・初期解析する。
- [ ] `ef_deltapro3_data.js` の `deviceCmd` や `protoMsg` で定義されているコマンドとメッセージについて、実際のデータとの整合性を確認する。

## 初期キャプチャ試行 (2025-05-27 13:00)

以前、AI エージェントが `uv run python scripts/mqtt_capture_dp3_debug.py` コマンドを実行した際にはスクリプトからの出力が確認できませんでした。しかし、ユーザーが PowerShell 上で同コマンドを実行したところ、以下のログが得られました。

**実行ログ (要約):**

```text
2025-05-27 04:08:17,432 - WARNING - [__main__] - ecopacket_pb2.py が見つかりません。ハートビートメッセージのXORデコードはスキップされます。生成された ecopacket_pb2.py を 'scripts' ディレクトリに配置するか、PYTHONPATH に追加してください。
2025-05-27 04:08:17,439 - INFO - [__main__] - === MQTTデバッグキャプチャスクリプト開始 ===
2025-05-27 04:08:17,439 - INFO - [__main__] - デバイスSN: MR51ZJS4PG6C0181
2025-05-27 04:08:17,439 - INFO - [__main__] - ユーザーID: 1807962518217633793
// ... (中略: トピック購読成功ログ) ...
2025-05-27 04:08:18,045 - INFO - [__main__] - MQTTブローカーに接続しました: mqtt-e.ecoflow.com
// ... (中略: トピック購読成功ログ) ...
2025-05-27 04:08:19,569 - WARNING - [__main__] - MQTTブローカーから切断されました。RC(int): 128, 理由: 'Unspecified error'. 受信メッセージ総数: 0.
2025-05-27 04:08:19,569 - ERROR - [__main__] - 予期せぬ切断が発生しました。
// ... (以降、接続と約1.5秒後の切断を繰り返す) ...
^C2025-05-27 04:08:25,721 - INFO - [__main__] - MQTTキャプチャスクリプトを停止しました。
```

**分析と判明した課題:**

1.  **`ecopacket_pb2.py` の欠落:** (解決済み)
    - ~~警告メッセージ `ecopacket_pb2.py が見つかりません` が出力されており、ハートビートメッセージの XOR デコードがスキップされています。このファイルは Protobuf の定義から生成される Python ファイルと思われます。~~
    - **更新 (2025-05-27):** ユーザーにより `custom_components/ecoflow_cloud/devices/internal/proto/ecopacket_pb2.py` が `scripts` ディレクトリにコピーされ、`protobuf` が依存関係に追加された結果、この警告は解消されました。
2.  **MQTT 接続後の即時切断 (RC: 128):** (継続中の課題 → **最新ログでは解消、ただし根本原因は未特定**)
    - MQTT ブローカー (`mqtt-e.ecoflow.com:8883`) への接続とトピック購読には成功していますが、その後約 1.5 秒で `Unspecified error (RC: 128)` という理由で切断され、これが繰り返されています。
    - 結果として、メッセージを一切受信できていません。
    - **更新 (ユーザー提供ログ 2025-05-27 05:11 時点):** 最新の実行ログでは、この `RC: 128` エラーは発生しておらず、MQTT ブローカーへの接続およびトピック購読は成功し、PINGREQ/PINGRESP の交換も確認できています。しかし、依然としてアプリケーションレベルのメッセージは受信できていません。この変更は、クライアント ID の形式変更 (`ANDROID_` + UUID + `_` + `user_id`) や、`paho-mqtt` のバージョンアップ (`uv run` 環境) など、以前の実行環境との差異に起因する可能性があります。RC:128 エラーが再現しなくなったものの、メッセージ受信に至らない根本原因の特定は引き続き必要です。
    - **対応:** この `RC: 128` エラーの原因を特定する必要があります。EcoFlow 側の MQTT ブローカーが特定の認証情報やクライアントの振る舞いを期待している可能性があります。あるいは、クライアント ID の重複や、特定の初期メッセージの送信が必要なのかもしれません。

### データ受信試行の経緯 (RC:128 エラー解消後、現在まで)

RC:128 エラーによる即時切断問題が解消された後も、依然として EcoFlow デバイスからのアプリケーションレベルの MQTT メッセージ(状態更新やコマンド応答)を受信できていないため、以下の試行錯誤を行っています。

1.  **`ecopacket_pb2.py` の準備とリフレッシュ:**

    - 当初欠損していた `ecopacket_pb2.py` は、まず類似プロジェクトからコピーして使用しました。
    - その後、`ioBroker.ecoflow-mqtt` の `lib/dict_data/ef_deltapro3_data.js` ファイル内に記述されている `protoSource` (Protobuf スキーマ定義) を抽出。
    - この `protoSource` を `scripts/ef_dp3_iobroker.proto` というファイルに保存。
    - `uv add grpcio-tools` により `protoc` コンパイラを含むツールを Python 環境に導入。
    - `protoc --python_out=. scripts/ef_dp3_iobroker.proto` コマンドを実行し、`scripts/ecopacket_pb2.py` を最新のスキーマ定義に基づいて再生成しました。
    - これにより、Python スクリプト (`mqtt_capture_dp3_debug.py`) 内での `setHeader` や `setMessage` といった Protobuf メッセージ型への参照に関するリンターエラーは解消されました。

2.  **データ取得要求メッセージ (`get` リクエスト) の送信:**

    - MQTT ブローカーへの接続とトピック購読が正常に完了した後、デバイスからのデータ送信を促すため、トピック `/app/{USER_ID}/{DEVICE_SN}/thing/property/get` に対して `setMessage` (内部に `setHeader` を持つ) 型のメッセージを送信しています。
    - このメッセージ送信自体は成功し、MQTT ブローカーから `PUBACK` も受信しており、メッセージ形式自体はサーバーに受け入れられています。

3.  **`setHeader` フィールド内容の試行錯誤:**

    - **初期試行:** `ioBroker.ecoflow-mqtt` の `deviceCmd` 定義や `protoSource` 内のヘッダー定義を参考に、`cmd_id`, `cmd_func`, `product_id`, `version`, `payload_ver`, `device_sn`, `data_len` などのフィールドを設定。`from` フィールドは `"Android"` を使用。
    - **`ioBroker.ecoflow-mqtt` の実装詳細調査:** `lib/dict_data/ef_deltapro3_data.js` 内の `prepareProtoCmd` 関数を詳細に確認した結果、`state === 'latestQuotas'` (全データ取得に相当するリクエスト) の場合、`ioBroker.ecoflow-mqtt` が送信するヘッダーは非常にシンプルであることが判明しました。具体的には、`src: 32`, `dest: 32`, `seq: (ミリ秒タイムスタンプ)`, `from: 'ios'` のみが設定され、`cmd_id` や `product_id` といった他の多くのフィールドは設定されていませんでした。
    - **現在の方針:** 上記 ioBroker の実装に合わせ、Python スクリプトから送信する `get` 要求のヘッダーフィールドを `src`, `dest`, `seq`, `from="ios"` のみに限定する修正を次に適用予定です。これにより、デバイスが期待するリクエスト内容との合致を目指します。

4.  **現在の主な課題:**
    - `uv run python scripts/mqtt_capture_dp3_debug.py` コマンドにより、スクリプトは依存関係エラーなく実行可能。
    - MQTT 接続、トピック購読、`get` 要求メッセージの送信、およびサーバーからの `PUBACK` 受信までは正常に動作。
    - しかし、依然としてデバイスからの応答メッセージ（例: `get_reply` トピックや、定期的な状態更新が行われる `app/device/property/{DEVICE_SN}` トピックへのメッセージ）は一切受信できていない状況です。

### AI 実行時とユーザー実行時の差異について

AI エージェントによる前回実行時に出力が得られなかった原因としては、実行環境の微妙な差異（シェル、Python 仮想環境、`uv run`の解釈など）や、ツールによる出力キャプチャの限界が考えられます。

### データ取得要求メッセージの構造 (2025-05-27 更新)

`ioBroker.ecoflow-mqtt` の `latestQuotas` (全データ取得に相当) の実装、および `scripts/ecopacket_pb2.py` の内容を分析した結果、データ取得要求は以下の構造で送信されるべきと判断される。

1.  **`setHeader` メッセージの構築:**

    - `src`: 32 (固定値)
    - `dest`: 32 (固定値)
    - `seq`: 現在時刻のミリ秒タイムスタンプ (下位 32 ビット)
    - `from`: "Android" または "ios"
    - その他フィールド (`cmd_id`, `cmd_func` など) は、`latestQuotas` の場合は設定不要の可能性が高い。

2.  **`setMessage` メッセージの構築:**

    - `header` フィールド: 上記で作成した `setHeader` オブジェクトを `CopyFrom` で設定する。

3.  **送信:**
    - 作成した `setMessage` オブジェクトを Protobuf でシリアライズする。
    - ターゲットトピック (例: `/app/{USER_ID}/{DEVICE_SN}/thing/property/get`) に送信する。

この修正を `scripts/mqtt_capture_dp3_debug.py` の `on_connect` 関数および `status_monitor` スレッド内のデータ取得要求送信部分に適用済み。

### 今後の調査ステップ

- [x] **`ecopacket_pb2.py` の調査と配置:** (完了)
  - [x] ~~このファイルがプロジェクト内のどこで生成されるか、あるいは外部から取得する必要があるかを確認する。~~
  - [x] ~~スクリプトが期待通りに `ecopacket_pb2.py` を利用できるようにする。~~
- [ ] **MQTT 切断エラー (RC: 128) の原因調査:**
  - [ ] EcoFlow の MQTT プロトコルに関する既知情報（フォーラム、類似プロジェクトなど）で、このエラーコードに関する情報がないか調査する。
  - [ ] `scripts/mqtt_capture_dp3_debug.py` の認証情報（ユーザー ID、シリアル番号、パスワードなど）が正確かつ最新であることを再確認する。特に、`get_device_key()` で取得される `secret_key` や、MQTT 接続に使用されるユーザー名・パスワードが正しいか。
  - [ ] クライアント ID (`ANDROID_...`) が EcoFlow のサーバー側で問題を引き起こしていないか検討する。（例：他のセッションで同じクライアント ID が使用されている、EcoFlow 側で想定外のクライアント ID 形式であるなど）
  - [ ] `ioBroker.ecoflow-mqtt` アダプタが接続時に行っている初期シーケンスや、送信している可能性のある特別なメッセージ（例えば、特定のトピックへの初期 PUBLISH など）がないか、再度コード (`main.js`, `lib/ecoflow_utils.js` 等) を確認する。
  - [ ] スクリプトの Paho MQTT クライアントのログレベルをさらに詳細に設定し、切断直前の通信内容に手がかりがないか確認する（現状でも DEBUG レベルのログは出ていますが、より詳細なトレースが可能か確認）。
  - [ ] `mqtt_capture_dp3_debug.py` の `client.username_pw_set(username, password)` で設定しているユーザー名とパスワードが、EcoFlow の MQTT ブローカーが期待するものと一致しているか確認する。（`get_device_key()` で取得したキーをどのようにユーザー名・パスワードに加工しているか詳細確認）
- [ ] **デバイス操作によるメッセージ誘発（上記切断問題解決後）:**
- [ ] スクリプト実行中に、EcoFlow アプリなどから Delta Pro 3 に対して何らかの操作（例: AC オン/オフ、設定変更）を行い、メッセージが発行されるか試す。
