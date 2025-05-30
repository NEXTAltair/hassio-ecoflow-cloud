# Delta Pro 3 MQTT メッセージ形式調査 詳細

このドキュメントは、EcoFlow Delta Pro 3 の MQTT メッセージ形式に関する詳細な調査結果を記録します。

## 調査目的

- Delta Pro 3 と MQTT ブローカー間で送受信されるメッセージの正確な形式を特定する。
- Home Assistant 連携機能の開発に必要なメッセージエンコード・デコード処理を明確にする。

## 調査対象・項目

- **メッセージヘッダー構造の解析:**
  - ヘッダーに含まれる各フィールド(長さ、コマンド ID、フラグ等)の意味と構造を特定する。
- **ペイロードのエンコード/デコード方式の解明:**
  - XOR デコード処理の詳細(キー、処理範囲など)を確認する。
  - `get_reply` メッセージの具体的な形式と内容を分析する。
- **Protobuf スキーマの検証と推測:**
  - `ioBroker.ecoflow-mqtt` の `ef_deltapro3_data.js` 内 `protoMsg` や `protoSource` から推測される Protobuf スキーマを、実際のキャプチャデータと照合し、検証・修正する。
  - 未知のコマンドやデータポイントに対応する Protobuf メッセージ構造を推測・定義する。
- **コマンド送信時のメッセージ構造:**
  - `scripts/mqtt_capture_dp3_debug.py` を用いて、特定の操作(充電開始/停止、AC 出力 ON/OFF など)を行った際の MQTT メッセージをキャプチャし、その構造を分析する。
  - `ioBroker.ecoflow-mqtt` の `prepareProtoCmd` 関数などを参考に、コマンド発行時のメッセージ構築方法を明らかにする。
- **定期的な状態更新メッセージの解析:**
  - デバイスから定期的に送信される状態情報(バッテリー残量、入出力電力など)のメッセージ形式を特定する。

## 調査方法

1.  **実機接続によるデータキャプチャ:**
    - `scripts/mqtt_capture_dp3_debug.py` (現在は `scripts/ecoflow_mqtt_parser/` 配下のモジュール群) を使用し、Delta Pro 3 と MQTT ブローカー間の通信をキャプチャする。
    - 様々な操作を行い、多様な種類のメッセージを収集する。(実施済み、`captured_data.jsonl` に保存)
2.  **`ioBroker.ecoflow-mqtt` のコード解析:**
    - 特に `lib/dict_data/ef_deltapro3_data.js` を中心に、メッセージ処理に関連するロジックを詳細に分析する。(実施済み、主要な構造は `00_01_DP3_MQTTトピック構造詳細.md` に反映)
3.  **キャプチャデータの解析とスキーマ照合:**
    - キャプチャしたバイナリデータを、ヘッダー構造、XOR デコード、Protobuf スキーマに基づいて解析する。(実施済み、デコード処理は `message_handler.py` 等に実装)
    - 必要に応じてスキーマを修正・拡張する。(実施済み、`ef_dp3_iobroker.proto` をベースに利用)

## 今後の進め方

- [x] 実機を MQTT ブローカーに接続し、`scripts/mqtt_capture_dp3_debug.py` を用いてデータキャプチャ環境を構築する。 (2025-05-29 完了: `scripts/ecoflow_mqtt_parser/` として環境構築、接続成功)
- [x] 基本的な操作(電源 ON/OFF、情報取得など)を行い、対応する MQTT メッセージをキャプチャ・初期解析する。 (2025-05-29 完了: `/app/device/property/{SN}` トピックからの定期更新メッセージの受信とデコードに成功。`captured_data.jsonl` に保存。データ取得要求 (`cmdId:1, cmdFunc:20`) は送信成功するも、`get_reply` は未確認。)
- [x] `ef_deltapro3_data.js` の `deviceCmd` や `protoMsg` で定義されているコマンドとメッセージについて、実際のデータとの整合性を確認する。(2025-05-29 完了: `protoMsg` に基づく `protobuf_mapping.py` を作成し、受信メッセージの動的デコードに成功。`deviceCmd` は今後のコマンド送信機能実装時に詳細検証。)
- [ ] `get_reply` トピックで受信されるメッセージの完全な解析と対応。 (ioBroker の先頭バイト処理の検証など)
- [ ] 未解析の `cmdId`/`cmdFunc` の組み合わせに対するメッセージ内容の特定。
- [ ] コマンド送信機能の実装と、各コマンドに対応する `deviceCmd` の検証。

## 初期キャプチャ試行 (2025-05-27 13:00)

以前、AI エージェントが `uv run python scripts/mqtt_capture_dp3_debug.py` コマンドを実行した際にはスクリプトからの出力が確認できませんでした。しかし、ユーザーが PowerShell 上で同コマンドを実行したところ、ログが得られ、その後の改修でデータ受信に成功しました。

**判明した課題と解決経緯:**

1.  **`ecopacket_pb2.py` の欠落:** (2025-05-29 解決済み)
    - 当初、このファイルが存在せず、Protobuf メッセージのデコードができませんでした。
    - `ioBroker.ecoflow-mqtt` の `lib/dict_data/ef_deltapro3_data.js` 内の `protoSource` を抽出し、`scripts/ef_dp3_iobroker.proto` として保存。
    - `protoc` を使用して `ef_dp3_iobroker_pb2.py` を生成し、`scripts/ecoflow_mqtt_parser/` 配下に配置することで解決しました。
2.  **MQTT 接続後の即時切断 (RC: 128):** (2025-05-29 解消済み)
    - 初期には、MQTT ブローカー接続後約 1.5 秒で `Unspecified error (RC: 128)` で切断される問題が発生していました。
    - クライアント ID の形式変更 (`ANDROID_{UUID}_{USER_ID}`) や、Python 環境の整備 (`uv add paho-mqtt protobuf grpcio-tools`) などを行う過程で、この即時切断エラーは発生しなくなりました。直接的な原因特定には至っていませんが、現在は安定して接続できています。
3.  **アプリケーションレベルのメッセージ受信不可:** (2025-05-29 一部解決済み)
    - RC:128 エラー解消後も、当初はデバイスからの応答メッセージが受信できませんでした。
    - データ取得要求メッセージの送信トピック (`/app/{USER_ID}/{DEVICE_SN}/thing/property/set`) や `Header` の内容 (ioBroker の `latestQuotas` を参考に `src`, `dest`, `seq`, `from` のみ設定) を試行錯誤しました。
    - **現状 (2025-05-29):**
      - `/app/device/property/{DEVICE_SN}` トピックからの定期更新メッセージは受信・デコードに成功し、`captured_data.jsonl` に記録されています。
      - データ取得要求 (`cmdId:1, cmdFunc:20` を使用) は MQTT ブローカーに送信成功 (`PUBACK` 受信) していますが、対応する `/app/{USER_ID}/{DEVICE_SN}/thing/property/get_reply` トピックからの応答はまだ確認できていません。

### データ受信試行の経緯 (RC:128 エラー解消後、現在まで)

1.  **`ecopacket_pb2.py` の準備とリフレッシュ:** (2025-05-29 完了)

    - `ioBroker.ecoflow-mqtt` の `lib/dict_data/ef_deltapro3_data.js` の `protoSource` から `scripts/ef_dp3_iobroker.proto` を作成し、`protoc` で `ef_dp3_iobroker_pb2.py` を生成。
    - これにより、Python スクリプト (`ecoflow_mqtt_parser` モジュール群) 内での Protobuf 型参照が正しく行えるようになりました。

2.  **データ取得要求メッセージ (`get` リクエスト) の送信:** (2025-05-29 現在、応答待ち)

    - MQTT 接続・トピック購読完了後、デバイスからの全データ取得を促すため、`Header` 型のメッセージ (Python スクリプトでは `cmdId:1, cmdFunc:20` を設定) を `/app/{USER_ID}/{DEVICE_SN}/thing/property/set` トピックに送信しています。
    - メッセージ送信自体は成功し `PUBACK` も受信していますが、`get_reply` は未受信。

3.  **`Header` フィールド内容の試行錯誤:** (継続中)

    - 当初、`setMessage` (内部に `setHeader` をラップ) を使用し、ioBroker の多フィールド版ヘッダーを試行。
    - その後、ioBroker の `latestQuotas` 実装 (送信メッセージは `Header` 型で `src`, `dest`, `seq`, `from` のみ) を参考に、Python スクリプトも `Header` 型で同様のシンプル版フィールド (`from` は "ios" または "Android") を送信するように修正。
    - リンターエラーが出ていた `from` フィールドへのアクセスは `setattr(message_to_send, "from", "ios")` で解決 (ただし、現在の `ef_dp3_iobroker.proto` の `Header` には `from` フィールドは定義されていないため、送信時には設定していません)。

4.  **現在の主な課題と状況 (2025-05-29):**
    - `/app/device/property/{DEVICE_SN}` からの定期更新メッセージは受信・デコード成功 (`issue_02_response_decode_interpret_error.md` 参照)。
    - データ取得要求 (`cmdId:1, cmdFunc:20`) に対する `get_reply` が依然として受信できていない。
    - ioBroker の `latestQuotas` が使用する `cmdId:255, cmdFunc:2` での取得要求も試す価値あり。

### AI 実行時とユーザー実行時の差異について

AI エージェントによる前回実行時に出力が得られなかった原因としては、実行環境の微妙な差異(シェル、Python 仮想環境、`uv run`の解釈など)や、ツールによる出力キャプチャの限界が考えられます。

### データ取得要求メッセージの構造 (2025-05-29 更新)

`ioBroker.ecoflow-mqtt` の `latestQuotas` (全データ取得に相当) の実装や、Python スクリプトでの試行を踏まえ、データ取得要求の構造は以下のように考えられます。

1.  **メッセージ型の選択:**

    - `Header` 型 (ioBroker の `latestQuotas` での送信形式に近い)
    - または `setMessage` 型 (内部で `setHeader` を使用)

2.  **`Header` / `setHeader` の主要フィールド:**

    - `src`: 32 (クライアント側を示す)
    - `dest`: 32 (デバイス側を示す。ioBroker の `latestQuotas` ではこうなっているが、デバイスによっては `2` など他の値の場合もある)
    - `seq`: 現在時刻のミリ秒タイムスタンプ (32 ビット整数)
    - `from`: "ios" または "Android" (ioBroker の `latestQuotas` では "ios")
    - `cmd_id`:
      - `1` (Python スクリプトでの試行。`cmd_func: 20` とセット)
      - `255` (ioBroker の `latestQuotas`。`cmd_func: 2` とセット)
    - `cmd_func`:
      - `20` (Python スクリプトでの試行。`cmd_id: 1` とセット)
      - `2` (ioBroker の `latestQuotas`。`cmd_id: 255` とセット)
    - `pdata`: `latestQuotas` の場合は空、または非常に小さな固定ペイロード (例: `setValue` 型で特定の値)。

3.  **送信:**
    - 作成したメッセージオブジェクトを Protobuf でシリアライズする。
    - ターゲットトピック (`/app/{USER_ID}/{DEVICE_SN}/thing/property/set`) に送信する。

現在 Python スクリプトでは、`Header` 型で `cmdId:1, cmdFunc:20`、`src:32, dest:5, seq:(タイムスタンプ)` を設定して送信しています (`from` は未設定)。

### 今後の調査ステップ

- [x] **`ecopacket_pb2.py` の調査と配置:** (2025-05-29 完了: `ioBroker.ecoflow-mqtt` の `protoSource` から生成し配置済み)
- [x] **MQTT 切断エラー (RC: 128) の原因調査:** (2025-05-29 解消済み: 直接原因は不明だが、環境整備により発生しなくなった)
- [ ] **データ取得要求 (`get`) に対する応答 (`get_reply`) が受信できない問題の解決:**

  - [x] ioBroker が `latestQuotas` で使用している `cmdId:255, cmdFunc:2` の組み合わせでデータ取得要求を送信してみる。
        **分析結果サマリー（2025-05-29 08:30 実行ログより更新）**

    1.  **接続とデータ取得要求の送信:**

        - MQTT ブローカーへの接続、トピック購読、および `cmdId: 255, cmdFunc: 2` を使用したデータ取得要求メッセージの送信は成功しています。`PUBACK` も受信しています。

    2.  **メッセージ受信と処理:**

        - **大きな進展:** 今回のログでは、`2025-05-29 08:31:17,047` に **`/app/1807962518217633793/MR51ZJS4PG6C0181/thing/property/get_reply`** トピックからメッセージを**受信しています。**
          - ペイロード長は 2490 bytes です。
          - スクリプトは Base64 デコードに成功し、デコード後のデータ長は 128 bytes でした。
          - しかし、その後の処理で `メッセージフォーマットバイト: 0x3c` となり、スクリプトは `get_reply: 未対応のメッセージフォーマットバイト: 0x3c` という警告を出力しています。これは、スクリプトが期待するフォーマット (`0x01` または `0x02`) と異なるため、それ以降の `setMessage` としてのデコード処理に進めていないことを示します。
        - `/app/device/property/MR51ZJS4PG6C0181` トピックからも引き続き多数のメッセージを受信しています。
          - これらのメッセージに対する Base64 デコードの成否はまちまちです。
          - 前回同様、これらのメッセージはスクリプトのトピック処理の条件分岐の問題により、「未処理のトピック」として扱われています。

    3.  **スクリプトの終了:**
        - ユーザーが Ctrl+C でスクリプトを停止し、正常にシャットダウンしています。

    **結論と次のステップへの影響**

    - **最大の収穫:** `cmdId:255, cmdFunc:2` でのデータ取得要求に対し、ついに **`get_reply` トピックからの応答を受信できました。** これは非常に重要な進展です。
    - **新たな課題:** 受信した `get_reply` メッセージの先頭バイト (メッセージフォーマットバイト) が `0x3c` であり、これは ioBroker のコードやこれまでの想定 (`0x01` または `0x02`) と異なります。この `0x3c` が何を意味するのか、どのようにデコードすべきかを調査する必要があります。
      - ioBroker のコードで `0x3c` に関連する処理がないか再確認する。
      - 他の EcoFlow デバイスの MQTT プロトコル情報で同様のフォーマットバイトが使用されていないか調査する。
      - ペイロード (Base64 デコード後の 128 bytes) の内容を直接バイナリエディタなどで確認し、既知の Protobuf メッセージ構造（例えば `Header` や `setMessage` の一部）と部分的にでも一致するかどうかを比較検討する。
    - `/app/device/property/MR51ZJS4PG6C0181` からのメッセージについては、依然としてスクリプトのトピック処理ロジックの修正が必要です。

- [x] **`/app/device/property/{DEVICE_SN}` からのメッセージ解析深化:** (`issue_03_data_analysis_and_mapping_update.md` で進行中)
  - [x] 受信したメッセージ (`HeaderMessage` -> `Header` -> `pdata`) のデコード処理を実装。(2025-05-29 完了: `message_handler.py`, `protobuf_mapping.py` 等で実装。
        **2025-05-29 08:42 実行ログ分析:**
    - MQTT ブローカーへの接続、トピック購読、データ取得要求メッセージ (`cmdId:1, cmdFunc:20`, `src:1, dest:32`) の送信成功を確認。
    - `/app/device/property/MR51ZJS4PG6C0181` トピックから多数のメッセージを受信。
    - 各メッセージは `HeaderMessage` としてデコード成功。
    - `pdata` は以下の組み合わせでデコード成功:
      - `cmdId:21, cmdFunc:254` -> `DisplayPropertyUpload` (複数回確認)
      - `cmdId:50, cmdFunc:32` (seq:0, encType:0, src:3) -> `cmdFunc50_cmdId30_Report` (複数回確認)
      - `cmdId:2, cmdFunc:32` -> `cmdFunc32_cmdId2_Report` (複数回確認)
      - `cmdId:23, cmdFunc:254` -> `cmdFunc254_cmdId23_Report` (1 回確認)
    - ペイロードの Base64 デコードは試行されるが失敗。スクリプトは元のバイナリデータで後続処理を継続しており、これは期待通りの動作。
    - 今回の実行ログでは、送信したデータ取得要求 (`cmdId:1, cmdFunc:20`) に対する `/app/.../get_reply` トピックからの応答は確認されなかった。これは、前回 `cmdId:255, cmdFunc:2` で応答があったことと整合する。)
  - [x] デコードされた各フィールドの意味を `ioBroker.ecoflow-mqtt/doc/devices/deltapro3.md` と照合して特定し、`.proto` ファイルやマッピング情報を更新する。
