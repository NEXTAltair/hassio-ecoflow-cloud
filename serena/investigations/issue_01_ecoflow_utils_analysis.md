# ioBroker.ecoflow-mqtt/lib/ecoflow_utils.js 分析

## 1. ファイル先頭部分 (1-534 行目程度)

このセクションには、Protobuf メッセージの基本的な型定義と、受信メッセージのデコードに関連するユーティリティ関数が含まれています。

### 1.1. `protoSource` (グローバル定数)

- **概要:**
  - MQTT 通信で使用される基本的な Protobuf メッセージのスキーマ定義が文字列として格納されています。
  - この定義は、Python スクリプト (`scripts/mqtt_capture_dp3_debug.py`) で `ecopacket_pb2.py` を生成するために使用した `scripts/ef_dp3_iobroker.proto` の内容とほぼ一致しています。
- **主要なメッセージ型:**
  - `Header`: メッセージの共通ヘッダー構造。`pdata` (ペイロード)、`src`, `dest`, `cmd_func`, `cmd_id`, `seq` など、多くのフィールドを含みます。
  - `HeaderMessage`: `Header` を複数含むことができるラッパーメッセージ。ストリームデータなどで使用されると推測されます。
  - `setMessage`: コマンド送信時に使用される型。`setHeader` 型の `header` フィールドを 1 つ持ちます。
  - `setHeader`: `setMessage` の内部で使用されるヘッダー型。`setValue` 型の `pdata` フィールドと、`src`, `dest`, `cmd_func`, `cmd_id`, `seq`, `from` などの制御フィールドを持ちます。`latestQuotas` リクエストの構築に直接関連します。
  - `setValue`: `setHeader` の `pdata` として使用される型。`optional int32 value = 1;` と `optional int32 value2 = 2;` を持ちますが、`latestQuotas` の場合は実際にはこの `pdata` は使用されないか、空である可能性が高いです。
  - その他、イベント通知 (`EventRecordItem`, `EventRecordReport`) やデバイス名設定 (`ProductNameSet`)、RTC 時刻設定 (`RTCTimeSet`) などに関連する型定義も含まれています。
- **Python スクリプトとの関連:**
  - `scripts/ecopacket_pb2.py` の元となるスキーマであり、Python 側でのメッセージエンコード・デコードの基礎となります。

### 1.2. `decodeMsg(hexString, msgtype, protoSource)`

- **概要:**
  - 指定された `protoSource` (文字列形式の Protobuf スキーマ) と `msgtype` (メッセージ型名) を用いて、16 進数文字列 (`hexString`) で表現されたバイナリデータをデコードし、JavaScript オブジェクトとして返します。
- **処理フロー:**
  1. `protobuf.parse(protoSource).root` でスキーマを解析。
  2. `root.lookupType(msgtype)` で指定されたメッセージ型を取得。
  3. `Buffer.from(hexString, 'hex')` で 16 進数文字列を Node.js の `Buffer` オブジェクトに変換。
  4. `PowerMessage.decode(Buffer)` でデコード。
  5. `PowerMessage.toObject(message, { defaults: false })` で JavaScript オブジェクトに変換。
- **Python スクリプトとの関連:**
  - Python 側では `ecopacket_pb2.YourMessageType().ParseFromString(bytes_data)` のような処理に相当します。

### 1.3. `convertData(stateDictObj, channel, state, value, stateObj)`

- **概要:**
  - デバイスから受信・デコードされた値 (`value`) を、ioBroker アダプター内部の状態定義 (`stateDictObj`, `stateObj`) に基づいて、適切な型や単位に変換するためのユーティリティ関数です。
- **処理内容例:**
  - 数値のスケーリング (乗算)。
  - `0`/`1` や文字列の `"0"`/`"1"` を `false`/`true` に変換。
  - 特定の診断コードを人間が読める文字列に変換。
- **Python スクリプトとの関連:**
  - 受信データを扱う際に、同様のデータ変換処理が必要になる場合に参考になりますが、`mqtt_capture_dp3_debug.py` の直接的なメッセージ送受信ロジックとは異なります。

### 1.4. `pstreamDecode(adapter, payload, usage, topic, msgtype, protoSourceDevice, protoMsg, log)`

- **概要:**
  - Protobuf でエンコードされたメッセージストリーム（通常は `HeaderMessage` にラップされた複数の `Header` メッセージ）をデコードするための主要な関数の一つ。
  - MQTT ブローカーから受信したメッセージのペイロードを処理する際に使用されます。
- **主要な処理ステップ:**
  1. Base64 エンコードされた `payload` をデコードし、`HeaderMessage` としてパース。
  2. `HeaderMessage` 内の各 `Header` オブジェクトを順番に処理。
  3. 各 `Header` から `cmdFunc` と `cmdId` を取得。
  4. `protoMsg` オブジェクト (デバイス定義ファイル `ef_xxx_data.js` から提供される、`cmdId` と `cmdFunc` の組み合わせに対応するペイロードの Protobuf メッセージ型名が格納されたオブジェクト) を参照し、`pdata` をデコードするための具体的なメッセージ型 (`prototyp`) を特定。
  5. `Header` の `encType` が `1` (かつ `src` が `32` でない場合など、特定の条件) の場合、`pdata` を `seq` (シーケンス番号) をキーとして XOR デコード。
     - XOR デコードロジック: `modarray.push(array[i] ^ seq);`
  6. 特定された `prototyp` と、必要に応じて XOR デコードされた `pdata` を用いて、`decodeMsg` 関数を呼び出し、実際のペイロード内容をデコード。
  7. デコードされたペイロードは、`prototyp` (メッセージ型名) をキーとして結果オブジェクト (`returnobj`) に格納される。
- **`getLastProtobufQuotas` との関連:**
  - `getLastProtobufQuotas` がデバイスにデータ要求を送信した後、デバイスから返信される応答メッセージ (例: `/thing/property/get_reply` トピックで受信するメッセージ) は、この `pstreamDecode` 関数によって処理される可能性が高いです。
  - Delta Pro 3 からの応答も、この関数を通じてデコードされ、内容が解釈されると推測されます。
- **Python スクリプトとの関連:**
  - Python スクリプトで MQTT メッセージを受信した際のデコード処理の参考になります。特に、`HeaderMessage` -> `Header` -> `pdata` (XOR デコード含む) -> 個別メッセージ型、という階層的なデコード処理や、`cmdId`/`cmdFunc` に基づくペイロード型の動的な特定ロジックは重要です。
  - Python スクリプトでは、ハートビートメッセージ (`/app/device/property/{DEVICE_SN}`) の XOR デコード処理を実装済みですが、他の応答メッセージも同様に `pstreamDecode` のロジックに倣って XOR デコードが必要になる可能性があります (ただし、`src !== 32` という条件がある点に注意)。

---

## 2. デバイス状態管理とストリームデータ処理 (535-1100 行目程度)

このセクションは、デバイスのオンライン/オフライン状態の管理と、MQTT で受信したストリームペイロードを解釈し、ioBroker のアダプタ状態を更新する中心的なロジックを含んでいます。

### 2.1. `setOnlineStatus(adapter, topic)` および `setOfflineStatus(adapter, topic)`

- **概要:**
  - 指定された `topic` (通常はデバイスのシリアルナンバーを含む) に関連付けられた ioBroker 内のデバイス状態オブジェクト (`.info.status`) を `online` または `offline` に更新します。
  - 現在の状態が更新対象の状態と異なる場合のみ、状態変更とログ出力を行います。
- **Python スクリプトとの関連:**
  - Python スクリプトでは、MQTT ブローカーへの接続状態 (`on_connect`, `on_disconnect`) や PING/PONG の状況、メッセージ受信の有無などから、デバイスのオンライン/オフライン状態を判断するロジックに相当します。ioBroker のような永続的な状態ストアは持ちませんが、同様の概念は重要です。

### 2.2. `storeStreamPayload(adapter, stateDictObj, stateObj, topic, payload, devtype, haenable, logged)`

- **概要:**
  - `pstreamDecode` 関数によってデコードされたペイロード (`payload`) を受け取り、その内容に基づいて ioBroker の状態オブジェクト (`stateObj`) を更新するための中心的な関数です。
  - `stateDictObj` は、デバイス種別ごとの状態定義 (各データポイントの名前、型、単位など) を保持するオブジェクトです。
  - `devtype` はデバイスの種類 (例: "deltaPro", "river2") を示し、`haenable` は Home Assistant 連携が有効かどうかを示します。
- **処理の主要ステップ:**
  1.  **ペイロードの存在確認:** `payload` が空でないことを確認します。
  2.  **チャネルごとの処理ループ:** `payload` オブジェクトの各キー (これを `channel` と呼びます。例えば `plug_heartbeat`, `inverter_heartbeat`, `BPInfoReport`, `JTS1_EMS_HEARTBEAT` など、Protobuf のメッセージ型名や、より具体的なデータカテゴリ名に相当) に対してループ処理を行います。
  3.  **オンライン状態設定:** 多くの `channel` の処理開始時に `setOnlineStatus(adapter, topic)` を呼び出し、デバイスがオンラインであることを記録します。
  4.  **状態ごとの処理ループ:** 各 `channel` 内部の各キー (これを `state` と呼びます。例えば `soc`, `remainTime`, `inputWatts` など、具体的なデータポイント名) に対してループ処理を行います。
  5.  **ネストされた構造の処理:**
      - `BPInfoReport` (バッテリーパック情報) や `JTS1_BP_STA_REPORT` (バッテリー状態レポート) のように、配列内に複数の情報セットが含まれる場合、配列をループして各要素を処理します。ioBroker 内の状態名も `BPInfo1`, `BPInfo2` のように連番で区別されます。
      - `JTS1_EMS_HEARTBEAT` のように、`pcsAPhase` や `meterHeartBeat` といったネストされたオブジェクトを持つ場合、再帰的に内部の値を処理し、ioBroker の状態名も `pcsAPhase_vol` のようにアンダースコアで連結されます。
  6.  **値の比較と更新:** `compareUpdate` 関数 (このコードブロックの範囲外) を呼び出し、受信した値 (`val`) と現在の ioBroker 内の状態値を比較し、変更があれば更新処理を行います。
  7.  **特殊なチャネル処理:**
      - `ProtoTime` / `ProtoTimeStat`: 時刻関連情報や統計情報を処理。ネスト構造が深く、特定のフィールド (`masterInfo`, `loadInfo`, `backupInfo`, `wattInfo`) を個別に扱います。
      - `ProtoPushAndSet`: デバイス設定に関連する情報を処理。`LoadStrategyCfg`, `backupIncreInfo`, `loadIncreInfo` など、こちらも複雑なネスト構造を持ちます。
      - `time_task_config_post`: スケジュールタスク設定の情報を処理。
      - `info`: デバイスがオフラインになった際に受信する可能性のある情報。`setOfflineStatus` を呼び出します。
      - `EnergyPack`: エネルギー統計情報 (Wh 単位) を処理。`sysEnergyStream` 配列内の各要素から `watthType` と `watth` を集計します。
  8.  **Home Assistant 更新:** `haenable` が true の場合、`compareUpdate` から返された更新情報を `haUpdate` 配列に集約し、関数の戻り値とします。
- **`getLastProtobufQuotas` との関連:**
  - `getLastProtobufQuotas` によって要求された全量データは、複数の `Header` メッセージとして `pstreamDecode` でデコードされ、その結果がこの `storeStreamPayload` 関数の `payload` として渡されると強く推測されます。
  - Delta Pro 3 からの応答に含まれるであろう様々なパラメータ (SoC, 入出力電力、バッテリー温度など) は、この関数内の各 `case` 文やネスト処理を通じて解釈され、対応する ioBroker の状態にマッピングされるはずです。
- **Python スクリプトとの関連:**
  - この関数は、Python スクリプトで MQTT メッセージを受信し、`pstreamDecode` に相当する処理でデコードした後の、**データ解釈と活用**の部分に大きく関連します。
  - Python スクリプトでは、`payload` 内のどの `channel` や `state` が Delta Pro 3 のどの情報に対応するのかを特定し、それらを適切にログ出力したり、将来的に Home Assistant エンティティにマッピングしたりする際の重要な参考情報となります。
  - 特に、`case` 文の分岐条件となっている `channel` 名 (例: `inverter_heartbeat`, `AppParaHeartbeatReport`) や、その内部で参照されている `state` 名は、Delta Pro 3 がどのようなデータを提供しうるかのヒントになります。
  - Delta Pro 3 の全量データを取得するためには、この関数が処理できるような構造のペイロードをデバイスから受信する必要があることを示唆しています。

---

## 3. "Station" ペイロード処理と状態比較・更新 (1100 行目程度 - ファイル終端)

このセクションには、主に "Station" タイプ (Delta Max や一部の River シリーズなど、パラメータ名がドット区切り形式で送信されてくるデバイス) のペイロードを処理する `storeStationPayload` 関数と、汎用的に状態を比較・更新する `compareUpdate` 関数が含まれています。

### 3.1. `storeStationPayload(adapter, stateDictObj, stateObj, topic, payload, haenable, logged)`

- **概要:**
  - `pstreamDecode` などでデコードされたペイロード (`payload`) のうち、特にドット区切り形式のパラメータ (`payload.params` または `payload.data.quotaMap`) を持つデバイス (ioBroker アダプタ内では "Station" と呼ばれることが多い) からのデータを処理し、ioBroker の状態を更新します。
  - `storeStreamPayload` と同様に、`stateDictObj` (状態定義) と `stateObj` (実際の状態値) を利用します。
- **処理の主要ステップ:**
  1.  **ペイロード形式の判別と抽出:**
      - `payload.params` が存在する場合: これを処理対象の `payloadobj` とします。特定のデバイス (Delta Max など) では、`ems.openBmsIdx` や `bmsMaster.bqSysStatReg` などの特定フィールドの値に基づいてデータの有効性をチェックします。
      - `payload.data.quotaMap` が存在する場合: これを `payloadobj` とします。こちらも同様に特定フィールドの値に基づいてデータの信頼性を評価します。
        - このパスは、`getLastProtobufQuotas` の応答 (`get_reply`) を処理する際に通る可能性が高いです。`adapter.quotas[topic] = payload` のように、受信した全量データをアダプタ内部に保存する処理もここに含まれます。
        - `timeTask` (スケジュールタスク設定) が含まれている場合、その内容を ioBroker の状態に反映します。
      - `payload.data.online === 0` の場合: デバイスがオフラインであることを示し、`setOfflineStatus` (実際には `setOfflineStatus` と同様のロジックを直接実行) を呼び出します。
  2.  **オンライン状態設定:** 有効なペイロードが確認できた場合、デバイスのオンライン状態を ioBroker に記録します。
  3.  **パラメータごとの処理ループ:** `payloadobj` (ドット区切りパラメータのマップ) の各キー (`comportion`) に対してループします。
      - キーをドット (`.`) で分割し、`channel` (例: `bmsMaster`) と `state` (例: `soc`) を取得します。
      - 特定のチャネル名 (`bms_bmsStatus` を `bmsMaster` に変更するなど) のマッピング処理を行います。
  4.  **状態定義の確認と値の変換:**
      - `stateDictObj[channel][state]` を参照し、対応する状態定義が存在することを確認します。
      - `convertData` 関数を呼び出し、受信値を ioBroker で扱う適切な形式に変換します。
  5.  **状態の比較と更新:**
      - 現在の ioBroker 内の状態値 (`old.val`) と変換後の値 (`value`) を比較します。
      - 値が異なる場合、または初回受信の場合は、`adapter.setStateAsync` で ioBroker の状態を更新します。
      - Home Assistant 連携 (`haenable`) が有効な場合、HA に送信するためのメッセージ (`haUpdate`) を準備します。
- **`getLastProtobufQuotas` との関連:**
  - この関数は、`getLastProtobufQuotas` の応答メッセージ (特に `payload.data.quotaMap` を持つ形式) を処理する上で中心的な役割を果たします。
  - Delta Pro 3 がもしドット区切り形式で全量データを返却する場合 (可能性は低いがゼロではない)、この関数がそのデータを解釈することになります。
  - `adapter.quotas[topic] = payload;` の部分は、取得した全量データを後から参照可能にするための重要な処理です。
- **Python スクリプトとの関連:**
  - Delta Pro 3 が `storeStreamPayload` で処理されるメッセージ形式 (ネストされた Protobuf オブジェクト) を主に使用すると考えられるため、この `storeStationPayload` 関数のロジックが直接的に Delta Pro 3 のデータ解釈に影響する可能性は低いかもしれません。
  - しかし、`getLastProtobufQuotas` の応答ペイロード全体を保存する `adapter.quotas[topic] = payload;` のようなアプローチは、Python スクリプトで受信した未解析の応答を一時的に保存・調査する際に参考になります。
  - また、`timeTask` のような特定の設定情報がどのように構造化されて送られてくるかの一例としても有用です。

### 3.2. `compareUpdate(adapter, stateDictObj, stateObj, haenable, topic, channel, state, val, origchannel, logged)`

- **概要:**
  - `storeStreamPayload` や `storeStationPayload` から呼び出される汎用的な関数で、受信した値 (`val`) と ioBroker 内の既存の状態値を比較し、必要であれば状態の更新と Home Assistant への通知を行います。
- **処理の主要ステップ:**
  1.  **状態定義の確認:** `stateDictObj[origchannel][state]` を参照し、状態定義が存在することを確認します。
  2.  **値の変換:** `convertData` 関数を呼び出し、受信値 `val` を適切な形式 `value` に変換します。
  3.  **既存状態の取得:** `adapter.getStateAsync` で現在の状態値 `old` を取得します。
  4.  **状態の比較と更新:**
      - 初回受信時 (`!old`) または値が変化した場合 (`old.val !== value`) に、`adapter.setStateAsync` で状態を更新します。
      - Home Assistant 連携が有効な場合、エンティティタイプ (`sensor`, `switch`, `select`, `text`) に応じて適切なペイロード形式で `haUpdate` オブジェクトを作成します。
      - スイッチなど一部のエンティティでは、値が同じでも HA 側での表示崩れを防ぐために強制的に更新情報を送信するロジックも含まれています。
- **Python スクリプトとの関連:**
  - Python スクリプトで受信データを扱う際に、以前の値と比較して変更があった場合のみ処理を行う、といった制御フローの参考になります。
  - Home Assistant エンティティへ値を送信する際の型変換 (例: boolean を "ON"/"OFF" 文字列に変換) のロジックも参考になります。

## 4. `prepareStreamCmd(adapter, topic, dp, val, productKey, deviceSn, protoSourceDevice, protoCommands)`

- **概要:**
  - デバイスに対してコマンド (設定変更など) を送信するための Protobuf メッセージを構築する関数です。
  - `dp` (データポイント名、例: `acUsageLimit`) と `val` (設定値) を受け取り、`protoCommands` (デバイスごとのコマンド定義) を参照して適切な `cmdFunc`, `cmdId`, ペイロード型 (`pbm`), ペイロード内容 (`pbs`) を決定し、`Header` メッセージを構築して返します。
- **処理の主要ステップ:**
  1. **コマンド定義の検索:** `protoCommands` オブジェクト内を検索し、指定された `dp` に対応するコマンド定義 (`command`) を見つけます。
  2. **ペイロードの構築:**
     - `command.pbs` (ペイロードのスキーマ文字列) と `command.pbm` (ペイロードのメッセージ型名) を使用し、`protobuf.parse()` と `root.lookupType()` で Protobuf の型を取得します。
     - 設定値 `val` をペイロードに設定します。この際、`command.valueConversion` が定義されていれば、それに基づいて値を変換します (例: 除算)。
     - 作成したペイロードオブジェクトをシリアライズ (`PowerMessage.encode(payload).finish()`) します。
  3. **ヘッダーの構築:**
     - `src`, `dest`, `cmdFunc`, `cmdId`, `seq`, `needAck`, `from`, `deviceSn`, `productId`, `version` などのヘッダーフィールドを設定します。
     - `cmdFunc` と `cmdId` は `command` 定義から取得します。
     - `pdata` にシリアライズしたペイロードを、`dataLen` にその長さを設定します。
  4. **Base64 エンコード:** 構築した `Header` メッセージ全体をシリアライズし、Base64 エンコードして返します。
- **`getLastProtobufQuotas` との関連性:**
  - この関数はコマンド送信に特化しており、`getLastProtobufQuotas` (データ取得要求) とは直接的な呼び出し関係はありません。
  - しかし、コマンド送信時の `Header` 構造 (特に `cmdFunc`, `cmdId` の使われ方や、`pdata` に実際の指示内容をエンコードする点) は、`getLastProtobufQuotas` のリクエストメッセージ構造を理解する上で間接的な参考になる可能性があります。
- **Python スクリプトとの関連:**
  - Python スクリプトで EcoFlow デバイスに何らかの設定変更コマンドを送信したい場合に、この関数のロジックが非常に重要になります。
  - 特に、コマンド名 (`dp`) から `cmdFunc`, `cmdId`、ペイロードの型と内容をどのように決定し、`Header` を構築してエンコードするか、という一連の流れは Python でのコマンド送信処理を実装する際の設計図となります。
  - Delta Pro 3 の特定機能を制御するためのコマンドを送信するには、まず `protoCommands` に相当する定義情報 (どのデータポイントがどの `cmdFunc`/`cmdId` に対応し、どのようなペイロードを取るか) を特定する必要があります。

## 5. `getLastProtobufQuotas(adapter, topic, productKey, deviceSn, userID, protoSourceDevice, log)`

- **概要:**
  - デバイスから「全量データ (latest quotas)」を取得するための要求メッセージを構築し、Base64 エンコードして返す関数です。これがまさに Delta Pro 3 からデータを受信するための最初のトリガーとなることが期待されるメッセージです。
- **処理の主要ステップ:**
  1. **ペイロードの準備:** 現状の実装では、`pdata` (ペイロード) は空の `setValue` メッセージ (`{ "value": 0, "value2": 0 }`) をシリアライズしたものですが、コメントアウトされている部分や他のデバイスの例を見ると、将来的には特定のパラメータを要求する内容が入る可能性も示唆されています (例: `"params": ["getAll"]` や `"moduleType": 0` など)。Delta Pro 3 の場合は、空のペイロードで全量データを要求できるのか、あるいは特定のパラメータ指定が必要なのかが重要な調査ポイントです。
  2. **ヘッダーの構築:**
     - `src`: 32 (ioBroker アダプタ側を示す)
     - `dest`: 32 (デバイス側を示す。ただし、他の箇所では `2` が使われている例もあり、デバイスやメッセージ種別によって異なる可能性あり)
     - `cmdFunc`: 2 (固定値。おそらく「読み取り」や「状態取得」のような意味合い)
     - `cmdId`: 255 (固定値。おそらく「全パラメータ」や「全クォータ」のような意味合い)
     - `seq`: 現在のミリ秒タイムスタンプ
     - `needAck`: 1 (ACK 応答を要求)
     - `from`: "ios" (固定。"Android" もあり得る)
     - `deviceSn`: デバイスのシリアルナンバー
     - `version`: "1.0.0" (固定)
     - `dataLen`: シリアライズされた `pdata` の長さ
  3. **メッセージの構築とエンコード:**
     - `setHeader` 型のオブジェクトを作成し、上記ヘッダーフィールドと `pdata` を設定します。
     - それを `setMessage` 型のオブジェクトでラップします。
     - `setMessage` オブジェクトをシリアライズし、Base64 エンコードして返します。
- **Python スクリプト (`mqtt_capture_dp3_debug.py`) との関連:**
  - **これが最重要関数です。** Python スクリプトの `on_connect` で送信しているデータ取得要求メッセージは、この `getLastProtobufQuotas` 関数のロジックを模倣して作成する必要があります。
  - 特に、`cmdFunc: 2`, `cmdId: 255`, `src: 32`, `dest: 32`, `from: "ios"` といったヘッダーフィールドの値は、Python スクリプトでも同様に設定すべきです。
  - ペイロード (`pdata`) の内容が鍵となります。ioBroker のこの関数では空に近いペイロード (実質的に `value:0, value2:0`) を使用していますが、Delta Pro 3 がこれに応答しない場合、`ef_deltapro3_data.js` や他のデバイスの `protoCommands` 定義、あるいは `main.js` での他のコマンド送信例を参考に、Delta Pro 3 用の正しい「全データ取得」ペイロードを見つけ出す必要があります。(例: `getAll` のようなキーワードを含む JSON 文字列を `pdata` に設定するなど)
  - シーケンス番号 (`seq`) はミリ秒タイムスタンプである点も重要です。
  - 送信先トピックは `/app/{USER_ID}/{DEVICE_SN}/thing/property/set` が使われているため、Python スクリプトもこれに合わせるべきです。(ioBroker の `main.js` の `sendQuotasTimer` からの呼び出しで確認済み)

---

## 6. 特定デバイスファミリー向けペイロード処理関数群

`ecoflow_utils.js` の終盤には、特定の EcoFlow デバイスファミリー（または互換デバイス）の MQTT ペイロードを処理するために特化した関数群が定義されています。これらは `storeStreamPayload` や `storeStationPayload` ほど汎用的ではなく、対象デバイスのデータ構造に強く依存しています。

### 6.1. `storeSHELLYpayload(adapter, stateDictObj, stateObj, topic, payload, haenable, logged)`

- **概要:**
  - Shelly デバイス（EcoFlow 製品群とは異なるが、連携のために ioBroker アダプタが対応している可能性のあるスマートホームデバイス）からの MQTT ペイロードを処理するための関数と推測されます。
  - ペイロードは `payload.data.quotaMap` または `payload.params` に格納されていることを期待し、その内部は JSON 形式のオブジェクトです。
- **処理内容:**
  - `cloud`, `mqtt`, `wifi_sta` といった通信状態に関する情報や、`total_power`, `emeters` (電流、電圧、電力、力率、積算電力量など) といった電力測定データを処理し、`compareUpdate` を介して ioBroker の状態を更新します。
- **Python スクリプトとの関連:**
  - EcoFlow Delta Pro 3 のデータ処理とは直接的な関連はありません。

### 6.2. `storeSHPpayload(adapter, stateDictObj, stateObj, topic, payload, haenable, logged)`

- **概要:**
  - EcoFlow Smart Home Panel (SHP) からの MQTT ペイロードを処理するための関数です。
  - こちらもペイロードは `payload.data.quotaMap` または `payload.params` に格納されている JSON オブジェクトを期待します。
- **処理内容:**
  - `cfgSta` (設定状態), `epsModeInfo` (EPS モード), `gridInfo` (系統情報), `emergencyStrategy` (緊急時戦略), `loadCmdChCtrlInfos` (負荷チャンネル制御情報), `splitPhaseInfo` (スプリットフェーズ情報), `mainsLoadWatt` (主電源負荷電力), `chUseInfo` (チャンネル使用情報), `loadChInfo` (負荷チャンネル名), `errorCodes` (エラーコード) など、SHP に特有の多岐にわたる情報を処理します。
  - `timeTask` (スケジュールタスク) の設定情報も詳細に解析し、ioBroker の状態に反映します。
- **Python スクリプトとの関連:**
  - Delta Pro 3 のデータとは異なるものの、EcoFlow デバイスが MQTT 経由でどのような詳細な設定情報や状態データを送信しうるかの一例として参考になります。
  - 特に、アレイやネストされたオブジェクトを含む複雑な JSON 構造のデータをどのようにパースし、個々の状態にマッピングしているかは、将来的に Delta Pro 3 の高度なデータを扱う際のヒントになる可能性があります。

### 6.3. `storePowerkitPayload(adapter, stateDictObj, stateObj, topic, payload, haenable, logged)`

- **概要:**
  - EcoFlow Power Kit システムからの MQTT ペイロードを処理するための関数です。
  - ペイロードは `payload.data.quotaMap` または `payload.params` に格納された JSON 文字列、あるいはネストされた JSON オブジェクトを期待し、必要に応じて `JSON.parse()` でパースします。
- **処理内容:**
  - Power Kit は複数のモジュール (例: バッテリーパック `bp2000`, `bp5000`、インバーターチャージャー `ichigh`) から構成されるため、ペイロードもモジュールごと、さらにモジュール内のシリアルナンバーごとにデータが階層化されている場合があります。
  - `bmsTotal` (全体の BMS 情報) や、各バッテリーパック (`bp` + `kitNum`) の詳細情報、オンラインモジュールのリスト (`onLineModuleSnList`) などを処理します。
- **Python スクリプトとの関連:**
  - Delta Pro 3 は単体のデバイスですが、Power Kit のように複数の内部コンポーネントや接続された拡張バッテリーがそれぞれ詳細な情報を持つ場合、このような階層的なデータ構造で MQTT メッセージが送られてくる可能性を考慮する上で参考になります。
  - JSON 文字列としてエンコードされたデータが MQTT ペイロードの一部として送信され、受信側でパースするというパターンも、EcoFlow デバイスの通信プロトコルの一つの特徴として認識できます。

---

## 7. ユーティリティ関数群 (ファイル末尾)

`ecoflow_utils.js` の末尾には、コマンドメッセージ構築のヘルパー関数、EcoFlow API から MQTT 接続情報を取得する関数、そしてこのモジュールが外部に提供する関数群のエクスポート定義が含まれています。

### 7.1. `getRandomInt(min, max)`

- **概要:** `min` (含む) と `max` (含まない) の間のランダムな整数を生成します。
- **利用箇所:** コマンド送信時のメッセージ ID (`id`) を生成するために `prepareStationCmd` などで使用されています。

### 7.2. `statesFromDict(allstates, dict)`

- **概要:** `allstates` (おそらく ioBroker の全状態オブジェクト) から、`dict` (特定のチャネルとキーの構造を持つオブジェクト) に基づいて、関連する状態のみを抽出して新しいオブジェクトとして返します。
- **利用箇所:** 具体的な呼び出し箇所はこのファイル内には見当たりませんが、アダプタの初期化時や特定デバイスの状態セットアップ時に利用される可能性があります。

### 7.3. `prepareStationCmd(adapter, serial, stationType, state, value, cmd, channel, logged)`

- **概要:** 「Station」タイプ (Delta Max, Delta Pro, Delta 2 など、JSON 形式のコマンドペイロードを受け付けるデバイス) 向けのコマンド送信メッセージ (JSON 形式) を構築します。
- **処理の主要ステップ:**
  1.  **コマンド定義の確認:** `cmd` オブジェクト (状態変更に対応するコマンド定義) が提供されていることを確認します。
  2.  **送信前チェック (SoC):** 特定のコマンド (AC 出力 ON など) の場合、現在の SoC が最小放電 SoC を下回っていればコマンド実行を中止します。
  3.  **デバイスタイプごとのメッセージ構築:** `stationType` に応じて、ベースとなるメッセージテンプレート (共通ヘッダーフィールドを含む JSON オブジェクト) を選択します。
  4.  **パラメータ設定:**
      - `state` (変更対象の状態名) と `value` (設定値) に基づいて、メッセージ内の `params` オブジェクトに適切なキーと値を設定します。
      - 値の変換 (例: `beepState` で `true` を `0` に、`false` を `1` に変換) や、特定の状態に応じた追加パラメータの取得・設定 (例: `delta2max` で `bpPowerSoc` を設定する際に `minDsgSoc` も考慮) が行われます。
      - `operateType` や `moduleType` もコマンド定義から設定します。
  5.  **メッセージ ID の付与:** `getRandomInt` で生成したランダムな ID をメッセージに付与します。
- **Python スクリプトとの関連:**
  - Delta Pro 3 が JSON 形式のコマンドも受け付ける場合 (主に設定変更系)、この関数のロジックがコマンドメッセージを構築する上で非常に参考になります。
  - 特に、`stationType` が `deltapro` の場合のメッセージ構造や、各 `state` (コマンド名) に対応する `params` のキー名と値のフォーマットは重要です。
  - **注意点:** Delta Pro 3 の全量データ取得は Protobuf 形式 (`getLastProtobufQuotas`) で行われる可能性が高いですが、個別の設定変更コマンドは、この `prepareStationCmd` が生成するような JSON 形式のメッセージで `/app/{USER_ID}/{DEVICE_SN}/thing/property/set` トピックに送信される可能性があります。(これは `main.js` の `cmdRequest` 関数の動作からの推測です)。

### 7.4. `prepareStreamCmd(adapter, serial, streamType, state, value, cmd, log)` (ファイル末尾の詳細版)

- **概要:** この関数は以前の分析 (セクション 4) で既に登場した `prepareStreamCmd` と同じものですが、ファイル末尾にその完全な実装があります。主に「ストリーム」タイプ (PowerStream, Smart Plug など、Protobuf の `Header` に直接コマンド情報を埋め込むデバイス) 向けのコマンド送信メッセージ (Protobuf 形式) を構築します。
- **追加の注目点 (Delta Pro Ultra 向け):**
  - `streamType === 'deltaproultra'` の場合のロジックがあり、これは Delta Pro 3 とは異なりますが、新しい世代の Delta シリーズがどのようなコマンド形式を取りうるかの一例となります。
  - `energyManageEnable` コマンドのように、複数の値 (`value` と `value2`) をペイロードに設定する例も見られます。
- **Python スクリプトとの関連:**
  - 先述の通り、Delta Pro 3 は `getLastProtobufQuotas` でデータ取得を行うため、コマンド送信も Protobuf の `Header` ベースである可能性は低いと考えられます。しかし、EcoFlow デバイスの Protobuf コマンドエンコーディングの多様性を示す例として認識しておくと良いでしょう。

### 7.5. `getEcoFlowMqttCredits(adapter, email, password)`

- **概要:** EcoFlow の公式 API にログインし、MQTT ブローカーへの接続に必要な認証情報 (ユーザー ID、ユーザー名、パスワード、URL、ポート、クライアント ID など) を取得します。
- **処理フロー:**
  1.  `https://api.ecoflow.com/auth/login` エンドポイントに POST リクエストを送信し、アクセストークンとユーザー ID を取得。
  2.  取得したトークンとユーザー ID を使用し、`https://api.ecoflow.com/iot-auth/app/certification` エンドポイントに GET リクエストを送信し、MQTT 接続情報を取得。
  3.  クライアント ID は `ANDROID_{UUID}_{USER_ID}` の形式で生成。
- **Python スクリプトとの関連:**
  - Python スクリプトで MQTT 接続情報を動的に取得したい場合に、この関数の API エンドポイント、リクエストヘッダー、リクエストボディ、レスポンス形式が非常に重要になります。
  - 現在は `config.json` に手動で設定していますが、このロジックを Python で再現することで、認証情報の自動取得が可能になります。

### 7.6. `exports.*`

- **概要:** この `ecoflow_utils.js` モジュールが外部 (主に `main.js`) に提供する関数を列挙しています。
- **エクスポートされている主要関数:**
  - `pstreamDecode`: Protobuf ストリームデコード
  - `storeStationPayload`, `storeStreamPayload`, etc.: 各デバイスタイプ向けペイロード処理
  - `createSubscribeTopics`: 購読トピック生成
  - `getEcoFlowMqttCredits`: MQTT 認証情報取得
  - `prepareStreamCmd`, `prepareStationCmd`: コマンドメッセージ構築
  - `getLastProtobufQuotas`, `getLastJSONQuotas` (ファイル末尾版): データ取得要求トリガー
  - その他ヘルパー関数
- **Python スクリプトとの関連:**
  - ioBroker アダプタのどの機能がこのユーティリティファイルに依存しているかを把握するのに役立ちます。

## Python スクリプトにおける `setMessage.header.pdata` の型とデコードに関する考察 (scripts/mqtt_capture_dp3_debug.py より移動)

`ioBroker.ecoflow-mqtt` の `pstreamDecode` 関数を参考に Python スクリプトで `setMessage` をデコードする際、`setMessage.header.pdata` (実質的には `setHeader.pdata`) の扱いで以下の課題と考察が生じた。

**課題:**

提供されている `scripts/ecopacket_pb2.py` (元は `scripts/ef_dp3_iobroker.proto` から生成されたと想定される) において、`setHeader` メッセージ内の `pdata` フィールドは `setValue` 型として定義されている。`setValue` 型は `optional int32 value = 1;` と `optional int32 value2 = 2;` というフィールドを持つ。これは単純なバイト列ではなく、整数値を保持するための型である。

一方で、`ioBroker.ecoflow-mqtt` の JavaScript コードでは、`setMessage` をデコードした後、その `header.pdata` をシーケンス番号 (`seq`) と共に XOR デコードの対象としている。これは、`header.pdata` が実際にはバイト列として扱われていることを強く示唆する。

Python の `protobuf` ライブラリはスキーマ定義に厳密に従うため、`pdata` が `setValue` 型として定義されていれば、そのフィールド (e.g., `pdata.value`, `pdata.value2`) にアクセスすることになる。これを直接バイト列として取得し XOR デコードすることはできない。

**考察と仮説:**

1.  **スキーマ定義の不一致/誤り:**

    - `ioBroker.ecoflow-mqtt` で実際に使用されている `.proto` ファイル、あるいは EcoFlow デバイスとの通信で暗黙的に期待されている `setHeader.pdata` の型は `bytes` である可能性が高い。
    - `scripts/ef_dp3_iobroker.proto` から `scripts/ecopacket_pb2.py` を生成する際に、何らかの理由で `pdata` が `setValue` 型として定義されてしまったか、あるいは EcoFlow 側が特殊なエンコード/デコード方法（例えば `setValue` のフィールドを特定の方法でバイト列に変換またはその逆）を行っている可能性がある。

2.  **Protobuf のフィールドエンコーディング:**

    - Protobuf では、フィールドがメッセージ型として定義されていても、エンコードされたバイト列上ではそのメッセージがシリアライズされたバイトデータとして格納される。`protobuf-decode` ツールなどでバイナリを解析した際に `pdata` が `message setValue {...}` のように表示されても、その `{...}` の部分が実際のバイト列を表していることもある。
    - 問題は、Python ライブラリで `ParseFromString` した際に、スキーマ定義に基づいてそのバイト列が `setValue` オブジェクトとして解釈されてしまう点にある。

3.  **ioBroker (JavaScript) の挙動:**
    - JavaScript の Protobuf ライブラリ (`protobufjs` など) は、型定義に対してより柔軟なアクセスを許容する場合がある。例えば、`bytes` 型として定義されていなくても、特定の条件下でバイトバッファとして直接アクセスできるような API が存在する可能性がある。

**Python スクリプトでの暫定対応と今後の方向性:**

- **暫定対応 (実施済み):** `scripts/mqtt_capture_dp3_debug.py` の `on_message` 関数内では、`header.pdata` が期待通り `bytes` 型でない場合 (現状のスキーマでは常に `setValue` 型となるため、この分岐は実質的に常に `setValue` 型として扱われる)、警告ログを出し、`pdata` オブジェクトの文字列表現を UTF-8 エンコードしたものをダミーのバイト列として XOR 処理の対象とする、というエラーハンドリングに近い形で実装した。これは、処理の続行と問題の可視化を目的としたもので、正しいデコード方法ではない。
- **根本解決のための確認事項:**
  1.  **`scripts/ef_dp3_iobroker.proto` の再確認:** `setHeader` 内の `pdata` フィールドの型定義を正確に確認する。もし `bytes` でない場合は、なぜ `setValue` なのか、EcoFlow の意図は何かを探る。
  2.  **`setValue` からバイト列への変換ロジック:** もし `pdata` が本当に `setValue` 型であり、かつその内容が XOR デコードされるべきバイト列を何らかの形で含んでいるのであれば、`setValue` オブジェクトからそのバイト列を抽出する具体的なロジック（例えば `value` フィールドと `value2` フィールドを特定の順序で結合するなど）を特定する必要がある。
  3.  **代替スキーマの検討:** `ioBroker.ecoflow-mqtt` のリポジトリや関連コミュニティで、より正確（あるいは `pdata` が `bytes` として定義されている） `.proto` ファイルが入手可能か調査する。
  4.  **受信バイナリの直接解析:** `setMessage` 全体のバイナリをダンプし、`protoc --decode=setMessage ...` やオンラインの Protobuf デコーダーを使い、`pdata` 部分が実際にどのようなバイト列としてエンコードされているかを手動で解析する。これにより、`setValue` 型のフィールドがどのように使われているか、あるいは本当に無視してバイト列として読むべきなのかの手がかりが得られる可能性がある。

---
