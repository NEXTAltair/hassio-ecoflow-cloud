## 問題の概要

EcoFlow Delta Pro 3 からの MQTT メッセージは `scripts/mqtt_capture_dp3_debug.py` スクリプトで受信できているものの、そのペイロードを正しくデコードし、Protobuf メッセージとして解釈することができない。
具体的には、`/app/device/property/{DEVICE_SN}` トピックなどでメッセージを受信するが、Base64 デコードに失敗したり、デコードに成功しても後続の Protobuf デシリアライズ処理が未実装または不適切なため、有効なデータとして利用できていない。

## 現在の状況とログ (ユーザー提供ログより)

- MQTT ブローカーへの接続、トピック購読は成功している。
- データ取得要求メッセージの送信も行われている。
- `/app/device/property/MR51ZJS4PG6C0181` トピックからメッセージを継続的に受信。
  - 受信メッセージのペイロードについて、Base64 デコードが試行される。
    - 例 1: `Length: 414` のメッセージで Base64 デコードに失敗し、「元のペイロードを処理試行します」とログ出力後、「未処理のトピック」となる。
    - 例 2: `Length: 117` のメッセージで Base64 デコードに成功 (デコード後 len: 15 や 39) するが、やはり「未処理のトピック」となる。
- 期待する `/app/{USER_ID}/{DEVICE_SN}/thing/property/get_reply` トピックでの全データ応答などは依然として確認できていないか、または正しく処理できていない。

```
# ユーザー提供ログの抜粋 (例)
2025-05-28 04:02:36,578 - INFO - [__main__] - メッセージ受信 (トピック: /app/device/property/MR51ZJS4PG6C0181, QoS: 0, Retain: False, MID: 0, Length: 414)
2025-05-28 04:02:36,579 - WARNING - [__main__] -   Base64デコード失敗。元のペイロードを処理試行します。
2025-05-28 04:02:36,579 - INFO - [__main__] -   未処理のトピック: /app/device/property/MR51ZJS4PG6C0181

2025-05-28 04:02:36,666 - INFO - [__main__] - メッセージ受信 (トピック: /app/device/property/MR51ZJS4PG6C0181, QoS: 0, Retain: False, MID: 0, Length: 117)
2025-05-28 04:02:36,666 - INFO - [__main__] -   Base64デコード成功 (len: 15)
2025-05-28 04:02:36,666 - INFO - [__main__] -   未処理のトピック: /app/device/property/MR51ZJS4PG6C0181
```

## 主な課題

1.  **`/app/device/property/{DEVICE_SN}` トピックメッセージのエンコード形式特定:**
    - このトピックから受信するメッセージのペイロードが常に Base64 エンコードされているのか、あるいはされていない場合もあるのかを明確にする必要がある。現状、デコード失敗と成功が混在しているように見える。
    - ioBroker の実装 (`pstreamDecode`) では Base64 デコードを前提としているように見えるが、実際のデバイス挙動との整合性を確認する必要がある。
2.  **Protobuf メッセージ型の特定とデコード処理の実装:**
    - Base64 デコード後 (あるいはデコード不要な場合、生のペイロード) のデータが、どの Protobuf メッセージ型 (`HeaderMessage`, `Header`, `set_dp3`, `get_dp3` など) に対応するのかを特定し、正しくデシリアライズする処理を実装する必要がある。
    - 特に `HeaderMessage` の場合、内部に複数の `Header` を含み、さらにその `pdata` が XOR デコードや特定の `cmdId`/`cmdFunc` に基づく別の Protobuf 型へのデコードを必要とする場合がある。この複雑な構造の解析処理が `mqtt_capture_dp3_debug.py` には不足している。
3.  **`get_reply` トピックのメッセージフォーマット:**
    - データ取得要求に対する応答が期待される `/app/{USER_ID}/{DEVICE_SN}/thing/property/get_reply` トピックでメッセージを受信した場合の、正しいデコード・解釈方法が確立されていない。
    - `issue_01` で言及のあった「ペイロード先頭バイトが `0x0a`」のケースなど、具体的なフォーマットの調査が必要。
4.  **動的な Protobuf 型特定とデコードロジックの欠如:**
    - ioBroker のように、受信した `Header` の `cmdId` や `cmdFunc` フィールド値に基づいて、`pdata` をどの Protobuf 型 (`battery_info_reply`, `inverter_heartbeat`, etc.) として解釈するかを動的に決定する仕組みが必要。

## 調査方針・解決策案

1.  **`/app/device/property/{DEVICE_SN}` トピックのメッセージ解析強化:**
    - **Base64 デコード処理の見直し:**
      - トピック名やペイロードの特性 (例: 先頭バイトなど) に基づいて Base64 デコードを試みるか否かを判断するロジックを導入する。常にデコードを試行するのではなく、より確実な場合にのみ実行する。
      - デコード失敗時には、元のバイナリデータのまま後続の Protobuf デコード処理を試みるフォールバックを検討する。
    - **Protobuf デコード試行:**
      - 受信したペイロード (Base64 デコード後または生データ) を、まず `ecopacket_pb2.HeaderMessage` としてデコード試行する。
      - 失敗した場合、または `HeaderMessage` が適切でないと判断される場合、`ecopacket_pb2.Header` としてデコード試行する。
      - デコード成功時には、どの型で成功したかと、デコードされたフィールド内容を詳細にログ出力する。
    - **ioBroker の `parseMessage` および `syncDevice` 関数のロジック移植:**
      - ioBroker の `main.js` 内のこれらの関数が、どのようにして `/app/device/property/{DEVICE_SN}` からのメッセージを処理しているかを詳細に再レビューする。
      - 特に、`HeaderMessage` -> `Header` -> `pdata` (XOR デコード) -> 各種ステータス用 Protobuf 型へのデコード、という一連の流れを Python で再現する。
      - `cmdId` と `cmdFunc` に基づいて `pdata` をデコードする際の型マッピング (ioBroker の `DEVICE_COMMANDS` や `ParamPath`) を Python 側でも利用できるようにする。
2.  **`get_reply` トピックのメッセージ解析:**
    - データ取得要求 (`Header` メッセージを `/thing/property/set` に送信) 後に `/thing/property/get_reply` トピックでメッセージを受信した場合、そのペイロード構造を調査する。
    - ioBroker の `main.js` で `get_reply` がどのように処理されているかを確認し、同様のデコード処理を試みる。
    - `issue_01` での調査結果「ペイロード先頭バイトが `0x0a`」のメッセージについて、これが Protobuf の標準的なエンコーディング (Length-delimited field type) の一部である可能性を考慮し、`ecopacket_pb2.setMessage` や関連する型でデコードを試す。
3.  **XOR デコード処理の実装と適用:**
    - `mqtt_capture_dp3_debug.py` に ioBroker と同様の XOR デコード関数 (`xor_decode_pdata`) は存在するが、これが適切なタイミングで `Header` 内の `pdata` に適用されているか確認し、必要であれば修正する。
    - XOR デコードが必要な条件 (特定の `cmdId` や `cmdFunc` など) を ioBroker のコードから特定する。
4.  **エラーハンドリングとロギングの強化:**
    - デコード処理の各ステップ (Base64, Protobuf 型ごとのデコード試行、XOR デコードなど) で、成功・失敗だけでなく、試行した型やキーとなったフィールド値などを詳細にログ出力する。
    - Protobuf デコードエラー発生時には、具体的なエラー内容 (例: `ParseError: Error parsing message`) と共に、デコード対象となったバイト列 (一部分でも可) をログに出力するとデバッグが容易になる。
5.  **`ecopacket_pb2.py` の再検証 (補助的):**
    - 現在のデコード問題の主因ではない可能性が高いが、ioBroker の `.proto` から生成した `ecopacket_pb2.py` が、実際のデバイス通信で使われる全てのメッセージ型とフィールドを網羅しているか、軽微な不整合がないかを再度確認する。

## 期待される成果

- `/app/device/property/{DEVICE_SN}` トピックから受信するメッセージを、高い成功率で正しい Protobuf 型にデコードし、その内容 (デバイスのステータス情報など) を人間が読める形でログ出力または保存できるようになる。
- データ取得要求に対する応答 (`get_reply` など) を正しく解釈し、デバイスの全パラメータを取得できるようになる。
- スクリプトが EcoFlow デバイスからの MQTT メッセージを安定して処理できるようになり、Home Assistant 連携などの次のステップに進むための基盤が整う。

## 具体的なタスクリスト

0.  [ ] **既存実装の調査:**

    1.  [x] `custom_components/ecoflow_cloud` フォルダ内の既存コード調査:
        - [x] MQTT 関連処理 (接続、購読、メッセージ送受信、デコード等) の有無と内容確認。
          - `custom_components/ecoflow_cloud/api/ecoflow_mqtt.py` の `EcoflowMQTTClient` クラスが担当。
          - Paho MQTT の `AsyncMQTTClient` を利用。
          - 接続、再接続、購読、メッセージ送受信の基本的な処理を実装。
          - **デコード処理:** `_on_message` 内で受信メッセージを `device.update_data(payload, topic)` に渡す。直接的な Base64/Protobuf デコード処理はこのファイルにはない。`UnicodeDecodeError` のみの基本的なエラー処理。
        - [x] Protobuf 関連処理の有無と内容確認。
          - Protobuf の定義ファイル (`.proto`) 及びそれから生成された Python コード (`_pb2.py`) は `custom_components/ecoflow_cloud/devices/internal/proto/` ディレクトリ内に存在する (例: `powerstream.proto`, `powerstream_pb2.py`, `ecopacket.proto`, `ecopacket_pb2.py` など)。
          - **デシリアライズ処理の実装例:** `custom_components/ecoflow_cloud/devices/internal/powerstream.py` の `_prepare_data` メソッドでは、`ecopacket_pb2.SendHeaderMsg` を用いて受信ペイロードからヘッダー情報をパースし、その `msg.cmd_id` (例: `1` の場合) に基づいて `msg.pdata` を対応する Protobuf メッセージ型 (例: `powerstream_pb2.InverterHeartbeat`) でデシリアライズする処理が実装されている。
          - **汎用的なデコード処理の不在:** `BaseDevice._prepare_data` のデフォルト実装では、依然として UTF-8 デコードと JSON パースのみが試行される。PowerStream のようなデバイス固有の `_prepare_data` オーバーライドがない場合、Protobuf メッセージは処理されない。
          - `EcoflowDataHolder` クラスは、デコード済みの Python 辞書を前提としている。
          - **結論:** `/app/device/property/{DEVICE_SN}` からのメッセージを処理するためには、PowerStream の実装を参考に、Delta Pro 3 (およびその他のデバイス) 用に `_prepare_data` をオーバーライドし、適切な `cmd_id` の判別、Base64 デコード (必要な場合)、XOR デコード (必要な場合)、および対応する Protobuf 型でのデシリアライズ処理を実装する必要がある。
    2.  [x] `ioBroker.ecoflow-mqtt` プロジェクトの詳細再調査:
        - [x] `main.js` におけるメッセージ受信・解析処理 (`on('message')`, `parseMessage`, `syncDevice` 等) のロジックフローの再確認。
          - **`onReady` 関数内の MQTT メッセージ処理 (`this.client.on('message', ...)`):**
            - 受信トピックからデバイス ID (`topic`) とメッセージ種別 (`msgtype`) を抽出。
            - デバイス種別 (`devtype`) に基づき、Protobuf メッセージか JSON メッセージかを判断。
            - **Protobuf メッセージ処理の場合:**
              - `devtype` が `pstream`, `plug`, `deltaproultra`, `powerocean`, `panel2`, `alternator`, `deltapro3`, `delta3`, `delta3plus`, `river3`, `river3plus` のいずれか。
              - `ef.pstreamDecode(this, message, '', topic, msgtype, this.protoSource[devtype], this.protoMsg[devtype], logged)` を呼び出してデコード。
                - `message`: 生の MQTT ペイロード (Buffer)。
                - `this.protoSource[devtype]`: デバイス固有の Protobuf 型定義。
                - `this.protoMsg[devtype]`: デバイス固有の `cmdId`/`cmdFunc` と Protobuf 型のマッピング。
              - `pstreamDecode` の結果 (`msgdecode`) を `this.storeProtoPayload[devtype](this, this.pdevicesStatesDict[origdevtype], this.pdevicesStates[origdevtype], topic, msgdecode, devtype, haEnable, logged)` に渡して状態を更新。
                - `this.pdevicesStatesDict[origdevtype]`: 状態定義辞書。
                - `this.pdevicesStates[origdevtype]`: 状態オブジェクト。
            - **JSON メッセージ処理の場合:**
              - 上記以外の `devtype`。
              - `JSON.parse(message.toString())` でデコードし、デバイス種別に応じた `ef.storeStationPayload` や `ef.storePowerkitPayload` などを呼び出して状態更新。
        - [x] `lib/ecoflow_utils.js` におけるデータ整形・デコード関連関数 (`pstreamDecode`, `decodeLatestQuotas` 等) の詳細分析。
          - **`pstreamDecode` 関数の解析結果 (抜粋):**
            - **入力:** MQTT ペイロード (`payload`、Base64 文字列を期待)、`topic`、`msgtype` (通常は `HeaderMessage` を期待)、`protoSourceDevice` (デバイス固有 proto 定義)、`protoMsg` (デバイス固有の cmdId/cmdFunc と型名のマッピング)。
            - **Base64 デコード:** 受信した MQTT ペイロードは、最初に Base64 デコードされる (`new Buffer.from(payload, 'base64')`)。
            - **`HeaderMessage` パース:** Base64 デコード後のデータは、汎用的な `HeaderMessage` 型としてデコードされる。この `HeaderMessage` は内部に `header` という `Header`オブジェクトの配列を持つ。
            - **各 `Header` の処理ループ:** 配列内の各 `Header` オブジェクトに対して以下の処理が行われる。
              - **`cmdId`, `cmdFunc`, `src`, `seq` の取得:** `Header` からこれらの制御情報を抽出。
              - **ペイロード型特定:** `protoMsg` オブジェクト (デバイス定義ファイル由来) を `cmdId` と `cmdFunc` をキーとして検索し、`pdata` をデコードするための具体的な Protobuf メッセージ型名 (`prototyp`) を特定する。特定できない場合は `prototyp` を `'undef'` とし、エラーログを出力。`Header.code == '-2'` の場合はオフラインを示す情報を結果に含める。
              - **XOR デコード:** `Header.encType === 1` かつ `Header.src !== 32` の場合、`Header.pdata` を `Header.seq` (シーケンス番号) をキーとして XOR デコードする。
              - **`pdata` デコード:** 特定された `prototyp` が `'undef'` でない場合、デバイス固有の `protoSourceDevice` を用いて、(必要なら XOR デコード済みの) `Header.pdata` を実際のデータ構造にデコードする。デコード結果は `prototyp` をキーとして結果オブジェクトに格納。
            - **結果オブジェクト:** `returnobj` には、キーがデコードされたメッセージの型名 (`prototyp`)、値がデコードされたメッセージオブジェクトとなる。
            - **全量データのキャッシュ:** デコード結果全体は `adapter.quotas[topic]` にも保存される。
            - **示唆:** `/app/device/property/{DEVICE_SN}` トピックのメッセージは `RuntimePropertyUpload` または `DisplayPropertyUpload` 型である可能性が高い。
          - **`getLastProtobufQuotas` (ecoflow_utils.js 内、ioBroker 状態トグル版) 関数の解析結果:**
            - **役割:** この関数は直接 MQTT メッセージを送信するのではなく、ioBroker 内部の状態 (`.action.latestQuotas`) をトグルする。
            - **トリガー:** この状態変更が、実際の MQTT 要求メッセージ送信処理 (おそらく`main.js`の`onStateChange`経由で、メッセージを構築する別の関数を呼び出す) のトリガーとなる。
            - **結論:** 送信すべき具体的な要求メッセージの内容 (cmdId, cmdFunc, pdata) は、この関数からは直接特定できない。トリガーによって呼び出されるメッセージ構築処理の特定が必要。
        - [x] Base64 デコード、XOR デコードの適用条件と具体的な処理内容の再確認。
          - **Base64 デコード:** `pstreamDecode` 関数の冒頭で、入力ペイロードは常に Base64 デコードされることが確認された。
          - **XOR デコード:** `pstreamDecode` 関数の解析により、`Header.encType === 1` かつ `Header.src !== 32` の場合に `Header.pdata` が対象となり、キーは `Header.seq` であることが確認された。
        - [x] `lib/dict_data/` 内のデバイス別定義ファイル (特に `ef_deltapro3_data.js`) におけるコマンド ID (`cmdId`), 関数 ID (`cmdFunc`), Protobuf 型マッピングの再確認。
          - **`deviceCmd` オブジェクト (抜粋):**
            - ioBroker の内部状態名と、それを操作するための送信メッセージヘッダー情報 (`dest`, `cmdFunc`, `cmdId`, `dataLen`) をマッピング。
            - 主にコマンド送信時に利用される。
            - 例: `action.latestQuotas` (全データ取得要求) は `cmdFunc: 20, cmdId: 1` を使用。
          - **`protoMsg` オブジェクト (抜粋):**
            - 受信した `Header` の `cmdId` と `cmdFunc` の値から、`pdata` をデコードすべき Protobuf メッセージ型名を特定するためのマッピング。
            - `pstreamDecode` 関数内で利用される。
            - **重要なマッピング例 (DeltaPro3):**
              - `cmdId: 22, cmdFunc: 254` → `RuntimePropertyUpload`
              - `cmdId: 21, cmdFunc: 254` → `DisplayPropertyUpload`
              - `cmdId: 18, cmdFunc: 254` → `setReply_dp3`
              - `cmdId: 17, cmdFunc: 254` → `set_dp3`
            - **`protoSource` オブジェクト (確定):**
              - `ef_deltapro3_data.js` 内にインラインで Protobuf スキーマ定義 (例: `message RuntimePropertyUpload { ... }`) が文字列として直接記述されている。これに基づき、実行時に Protobuf パーサーが動的に生成・利用される。
              - このスキーマ定義は、`ioBroker.ecoflow-mqtt/doc/devices/deltapro3.md` に、各メッセージ型 (`RuntimePropertyUpload`, `DisplayPropertyUpload` など) とそのフィールドの意味が人間可読な形でまとめられている。
            - **`storeProtoPayload` (ef_deltapro3_data.js 内) 関数の解析結果 (抜粋):**
              - **入力:** `pstreamDecode` でデコードされたペイロードオブジェクト (キーが Protobuf メッセージ型名、値がデコード済みデータオブジェクト)。
              - **処理対象チャネル (Protobuf メッセージ型名):**
                - `RuntimePropertyUpload`, `DisplayPropertyUpload`: デバイスからの状態・表示情報。ペイロード内の各プロパティを `stateDictObj` の同名チャネル定義を参照して状態更新。

1.  [ ] **`/app/device/property/{DEVICE_SN}` トピックメッセージ解析の実装:**
    1.  [ ] Base64 デコードロジック改善:
        - [ ] ペイロード特性に基づくデコード要否判断ロジックの導入。
        - [ ] デコード失敗時のフォールバック (生データでの Protobuf デコード試行) 実装。
    2.  [ ] Protobuf デコード処理実装:
        - [ ] `ecopacket_pb2.HeaderMessage` でのデコード試行。
        - [ ] `ecopacket_pb2.Header` でのデコード試行 (上記失敗時)。
        - [ ] デコード成功/失敗の詳細ログ出力強化。
    3.  [ ] ioBroker `parseMessage`/`syncDevice` ロジック移植:
        - [ ] `HeaderMessage` -> `Header` -> `pdata` (XOR) -> 具体的な Protobuf 型へのデコードフロー実装。
        - [ ] `cmdId`/`cmdFunc` と Protobuf 型のマッピング機構の確立。
2.  [ ] **`get_reply` トピックメッセージ解析の実装:**
    1.  [ ] ioBroker での `get_reply` 処理方法の調査・確認。
    2.  [ ] 確認した処理方法に基づき、Python スクリプトでのデコード処理実装。
    3.  [ ] 「先頭バイト `0x0a`」メッセージの `ecopacket_pb2.setMessage` 等でのデコード試行。
3.  [ ] **XOR デコード処理の適用:**
    1.  [ ] `xor_decode_pdata` 関数が `Header` 内 `pdata` に適用される条件の特定 (ioBroker コードベース)。
    2.  [ ] 特定した条件に基づき、スクリプト内での XOR デコード実行ロジックの修正・確認。
4.  [ ] **エラーハンドリングとロギングの全体的強化:**
    1.  [ ] デコード処理の各ステップでの詳細なログ出力 (試行型、キーフィールド値など)。
    2.  [ ] Protobuf デコードエラー時のエラー内容と対象バイト列のログ出力。
5.  [ ] **`ecopacket_pb2.py` の再検証 (必要に応じて):**
    1.  [ ] ioBroker の `.proto` ファイルとの比較、不足しているメッセージ型やフィールドがないか確認。
