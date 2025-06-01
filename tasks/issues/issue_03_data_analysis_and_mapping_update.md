## ISSUE 03: デコード済みデータの意味解析とマッピング更新

### 概要

`captured_data.jsonl` に記録された EcoFlow Delta Pro 3 からのデコード済み MQTT メッセージについて、各フィールドの具体的な意味を特定し、それに基づいて Protobuf 定義ファイル (`.proto`) および `protobuf_mapping.py` を更新する。

### 背景

Issue 02「受信メッセージの解析・デコード」の完了により、MQTT メッセージのデコード処理が確立され、デバイスからのデータが `captured_data.jsonl` に JSON 形式で保存されるようになった。
しかし、一部のフィールド名が `unknownX` のように汎用的であったり、特定の `cmd_id` / `cmd_func` で受信されるメッセージ全体の意味がドキュメントだけでは不明確な場合がある。
これらのフィールドの正確な意味を特定し、Protobuf 定義やマッピング情報をより具体的で分かりやすいものにすることで、データの活用性を高め、Home Assistant 統合などの後続タスクを円滑に進めることを目指す。

### 主な参照情報

- `captured_data.jsonl`: 実際にデバイスから受信・デコードされたデータ。
- `ioBroker.ecoflow-mqtt/doc/devices/deltapro3.md`: EcoFlow Delta Pro 3 の MQTT パラメータ定義に関する詳細なドキュメント。
- `scripts/ecoflow_mqtt_parser/protobuf_mapping.py`: `cmd_id` / `cmd_func` と Protobuf メッセージ型のマッピング定義。
- `src/ef_dp3_iobroker_pb2.py` (および元の `.proto` ファイル): Protobuf メッセージ構造の定義。

### タスクリスト

1.  **デコード済みデータの意味解析:**
    1.  `captured_data.jsonl` に記録された各メッセージタイプ (特に `cmdFunc50_cmdId30_Report`, `cmdFunc32_cmdId2_Report` など) について、`ioBroker.ecoflow-mqtt/doc/devices/deltapro3.md` の対応するセクション (例: `RuntimePropertyUpload`, `DisplayPropertyUpload`) と照合する。
    2.  各フィールド、特に `unknownX` となっているフィールドについて、ドキュメント内の説明、単位、値の範囲などを参考に具体的な意味を特定する。
    3.  必要に応じて、実際のデバイスの動作や他の情報源 (コミュニティフォーラムなど) も参照し、意味の特定を試みる。
2.  **Protobuf 定義 (`.proto` ファイル) の更新:**
    1.  意味が特定できたフィールドについて、`src/ef_dp3_iobroker.proto` (仮のファイル名、実際の proto ファイル名に合わせる) 内の対応するメッセージ定義で、フィールド名を汎用的なもの (例: `unknown1`) から具体的な意味を表すもの (例: `battery_level_percent`) に変更する。
    2.  コメントを追記し、各フィールドの意味や単位などを明確にする。
    3.  `.proto` ファイル更新後、`protoc` コンパイラを実行して `src/ef_dp3_iobroker_pb2.py` を再生成する。
3.  **`protobuf_mapping.py` の更新:**
    1.  Protobuf メッセージ型名自体がより適切で分かりやすいものに変更できる場合は、`protobuf_mapping.py` のマッピングも更新する。
    2.  デコード処理側で、更新されたフィールド名や型名を正しく扱えるように必要に応じて修正する (主に `message_handler.py` のログ出力やデータ整形部分など、直接的なデコードロジック以外)。
4.  **ドキュメントの更新:**
    1.  特定できたフィールドの意味や、Protobuf 定義の変更点などを関連ドキュメント (例: `docs_4ai/technical.md` や、この Issue ファイル自体) に記録する。

### 期待される成果

- EcoFlow Delta Pro 3 から受信する MQTT データの各フィールドの意味が明確になる。
- Protobuf 定義ファイルおよび Python の生成コードが、より具体的で理解しやすいフィールド名を持つようになる。
- `protobuf_mapping.py` が最新の Protobuf 定義と整合性が取れた状態になる。
- 後続の Home Assistant Entity へのマッピング作業や、データ活用のための分析が容易になる。

### フィールド解析メモ (captured_data.jsonl と deltapro3.md の照合)

以下は、`captured_data.jsonl` に記録されたメッセージと `ioBroker.ecoflow-mqtt/doc/devices/deltapro3.md` のパラメータ定義を照合した結果のメモです。
特に `unknownX` となっているフィールドの意味の特定を試みています。

#### cmdFunc50_cmdId30_Report (RuntimePropertyUpload 相当と推測)

`src: 3` (BMS?) から `dest: 32` (App?) へ送信されるメッセージ。BMS 関連の詳細なランタイムデータが多い。

| `captured_data.jsonl` のキー | サンプル値 (msg_seq: 4) | `deltapro3.md` / 開発者ドキュメントでの対応候補                                  | 型 (proto 推測) | 単位/値範囲/説明 (ドキュメントより)                                                                        | メモ・推測                                                                     |
| ---------------------------- | ----------------------- | -------------------------------------------------------------------------------- | --------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `unknown1`                   | 0                       | `bmsFltState`? (`diagnostic`)                                                    | sint32          | {0:OK?}                                                                                                    | BMS 故障状態 (0 なら OK)                                                       |
| `unknown2`                   | 1                       | `bmsProState`? (`diagnostic`)                                                    | sint32          | {0:OK?}                                                                                                    | BMS 保護状態 (0 なら OK)                                                       |
| `unknown3`                   | 2                       | `bmsAlmState`? (`diagnostic`)                                                    | sint32          | {0:OK?}                                                                                                    | BMS 警告状態 (0 なら OK)                                                       |
| `unknown4`                   | 0                       | `bmsBalState`? (`diagnostic`)                                                    | sint32          | {0:OK?}                                                                                                    | BMS バランス状態 (0 なら OK)                                                   |
| `unknown5`                   | 50332521                | -                                                                                | uint64?         | -                                                                                                          | BMS 関連の ID かカウンタ?                                                      |
| `unknown6`                   | 23                      | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown7`                   | 51510                   | `bmsBattVol` (mV) / `bmsMaxCellTemp`の下の`bmsBattSoc`                           | sint32          | `bmsBattVol`: -<br />`bmsBattSoc`: SOC of the main battery.                                                | `bmsBattVol` (51.510V) が有力。`bmsBattSoc`は float 型のはず。                 |
| `unknown8`                   | -8938                   | `bmsBattAmp` (mA 単位)                                                           | sint32          | -80-80A (開発者ドキュメントに直接記載なし、ioBroker 情報)                                                  | バッテリー電流 (-8.938A、放電)                                                 |
| `unknown9`                   | 30                      | `bmsMaxCellTemp` (°C)                                                            | sint32          | Temperature of the main battery (°C).                                                                      | 主バッテリー最高温度。`maxCellTemp18` と重複。                                 |
| `unknown10`                  | 1                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown11`                  | 80000                   | `bmsDesignCap` (mAh)                                                             | uint32          | Battery capacity (mAh).                                                                                    | バッテリー設計容量。`unknown24` と重複。                                       |
| `remainCap12`                | 18510                   | `bmsRemainCap` (mAh) (`ioBroker`のドキュメントより)                              | uint32          | - (開発者ドキュメントに直接の記載なし)                                                                     | バッテリー残容量。                                                             |
| `unknown13`                  | 80000                   | `bmsFullCap` (mAh) (`ioBroker`のドキュメントより)                                | uint32          | - (開発者ドキュメントに直接の記載なし)                                                                     | バッテリー満充電容量。                                                         |
| `unknown14`                  | 153                     | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown15`                  | 100                     | `bmsBattSoh` (%) (`ioBroker`のドキュメントより)                                  | uint32          | - (開発者ドキュメントに直接の記載なし)                                                                     | 主バッテリー SOH。 `soh54` (float) と比較要。                                  |
| `maxCellVol16`               | 3232                    | `bmsMaxCellVol` (mV, mult 0.001) (`ioBroker`より。開発者ドキュメントは V 単位か) | uint32          | 0-5V (x0.001) (`ioBroker`)                                                                                 | 最大セル電圧 (3.232V)                                                          |
| `minCellVol17`               | 3205                    | `bmsMinCellVol` (mV, mult 0.001) (`ioBroker`より。開発者ドキュメントは V 単位か) | uint32          | 0-5V (x0.001) (`ioBroker`)                                                                                 | 最小セル電圧 (3.205V)                                                          |
| `maxCellTemp18`              | 30                      | `bmsMaxCellTemp` (°C)                                                            | sint32          | Temperature of the main battery (°C).                                                                      | 主バッテリー最高温度 (`unknown9` と重複)                                       |
| `minCellTemp19`              | 28                      | `bmsMinCellTemp` (°C)                                                            | sint32          | Minimum temperature of the main battery (°C).                                                              | 主バッテリー最低温度。                                                         |
| `maxMosTemp20`               | 28                      | `bmsMaxMosTemp` (°C) (`ioBroker`より)                                            | sint32          | 0-100 °C (`ioBroker`) (開発者ドキュメントに直接の記載なし)                                                 | BMS MOS 最大温度                                                               |
| `minMosTemp21`               | 27                      | `bmsMinMosTemp` (°C) (`ioBroker`より)                                            | sint32          | 0-100 °C (`ioBroker`) (開発者ドキュメントに直接の記載なし)                                                 | BMS MOS 最小温度                                                               |
| `unknown22`                  | 0                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown23`                  | 3                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown24`                  | 80000                   | `bmsDesignCap` (mAh) (再掲)                                                      | uint32          | Battery capacity (mAh).                                                                                    | バッテリー設計容量 (`unknown11` と重複)                                        |
| `unknown25`                  | 23.137522               | `bmsBattSoc` (%)                                                                 | float           | SOC of the main battery.                                                                                   | 主バッテリー SOC。`unknown42`, `unknown44` と類似値。                          |
| `unknown26`                  | 0                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown27`                  | 460                     | `bmsChgRemTime` (min)                                                            | uint32          | Remaining charging time of the main battery (min).                                                         | 主バッテリー充電残時間。                                                       |
| `unknown28`                  | 619                     | `bmsDsgRemTime` (min)                                                            | uint32          | Remaining discharging time (min).                                                                          | 主バッテリー放電残時間。                                                       |
| `unknown29`                  | 3                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown30`                  | 0                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown31`                  | 27                      | `bmsMaxMosTemp` (°C) (`ioBroker`より) (再掲)                                     | sint32          | 0-100 °C (`ioBroker`) (開発者ドキュメントに直接の記載なし)                                                 | BMS MOS 最大温度 (`unknown20` と重複)                                          |
| `unknown32`                  | 16                      | -                                                                                | sint32          | -                                                                                                          | セル電圧配列の要素数か? (`cellVol33` は 16 要素)                               |
| `cellVol33`                  | `[3223, ...]`           | -                                                                                | repeated uint32 | mV?                                                                                                        | 各セル電圧 (16 セル分)                                                         |
| `unknown34`                  | 8                       | -                                                                                | sint32          | -                                                                                                          | セル温度配列の要素数か? (`cellTemp35` は 8 要素)                               |
| `cellTemp35`                 | `[28, ...]`             | -                                                                                | repeated sint32 | °C?                                                                                                        | 各セル温度 (8 個所分)                                                          |
| `version36`                  | "575d35"                | `bmsFirmVer` (string) (`ioBroker`より)                                           | string          | - (開発者ドキュメントに直接の記載なし)                                                                     | BMS ファームウェアバージョン                                                   |
| `bmsHeartVer37`              | 262                     | -                                                                                | uint32          | -                                                                                                          | BMS ハートビートバージョン?                                                    |
| `ecloudOcv38`                | 65535                   | -                                                                                | uint32          | -                                                                                                          | OCV (Open Circuit Voltage)関連? 65535 は無効値か                               |
| `deveiceSn39`                | "311e..."               | BMS Serial Number (仮称)                                                         | string          | -                                                                                                          | BMS のシリアル番号?                                                            |
| `unknown40`                  | 28                      | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown41`                  | 2                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown42`                  | 23.137857               | `bmsBattSoc` (%) (再掲)                                                          | float           | SOC of the main battery.                                                                                   | 主バッテリー SOC (`unknown25`, `unknown44` と類似)                             |
| `unknown43`                  | 0.9605322               | -                                                                                | float           | -                                                                                                          |                                                                                |
| `unknown44`                  | 23.137857               | `bmsBattSoc` (%) (再掲)                                                          | float           | SOC of the main battery.                                                                                   | 主バッテリー SOC (`unknown25`, `unknown42` と類似)                             |
| `unknown45`                  | -1                      | -                                                                                | sint32          | -1 は無効値や未設定を示すことが多い                                                                        |                                                                                |
| `unknown46`                  | 3                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown47`                  | 1                       | `bmsChgDsgState`                                                                 | sint32          | Charging/Discharging status of the main battery. 0: not charging/discharging, 1: discharging, 2: charging. | 充電/放電状態 (1 なら放電)。                                                   |
| `unknown48`                  | 0                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown49`                  | 0                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown50`                  | 12283595                | -                                                                                | uint64?         | -                                                                                                          |                                                                                |
| `unknown51`                  | 10159279                | -                                                                                | uint64?         | -                                                                                                          |                                                                                |
| `unknown52`                  | 99.95355                | -                                                                                | float           | -                                                                                                          | SOH 関連の値か？                                                               |
| `unknown53`                  | 0.0                     | -                                                                                | float           | -                                                                                                          |                                                                                |
| `soh54`                      | 99.9336                 | `bmsBattSoh` (%) (ioBroker 情報と型から推測)                                     | float           | - (開発者ドキュメントに直接の記載なし)                                                                     | バッテリー SOH。`unknown15` (uint32) と比較。こちらがより正確な SOH の可能性。 |
| `unknown55`                  | 3                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `mosTemp56`                  | `[27, ...]`             | -                                                                                | repeated sint32 | °C?                                                                                                        | MOS 温度 (3 個所分)                                                            |
| `unknown57`                  | 1                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown58`                  | `[25]`                  | -                                                                                | repeated sint32 | -                                                                                                          |                                                                                |
| `unknown61`                  | 1                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown62`                  | `[27]`                  | -                                                                                | repeated sint32 | -                                                                                                          |                                                                                |
| `unknown63`                  | 25                      | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown64`                  | 25                      | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown67`                  | 27                      | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown68`                  | 27                      | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown69`                  | 0                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `error70`                    | `[0, ...]`              | `bmsErrCode`? (ただし型違い) (`ioBroker`より)                                    | repeated uint32 | - (開発者ドキュメントに直接の記載なし)                                                                     | BMS エラーコード配列 (16 要素) 各要素がエラーフラグか。0 はエラーなし。        |
| `unknown71`                  | 3                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `batVolt72`                  | `[53687]`               | `bmsBattVol` (mV) (再掲)                                                         | repeated sint32 | - (開発者ドキュメントに直接の記載なし、ioBroker 情報)                                                      | バッテリー電圧 (配列だが通常 1 要素)                                           |
| `unknown73`                  | 91239                   | -                                                                                | uint32          | -                                                                                                          |                                                                                |
| `unknown74`                  | 0                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown75`                  | 0                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown76`                  | 0                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown77`                  | 0                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown78`                  | 0                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |
| `unknown79`                  | 667014                  | -                                                                                | uint64?         | -                                                                                                          |                                                                                |
| `unknown80`                  | 538378                  | -                                                                                | uint64?         | -                                                                                                          |                                                                                |
| `packSn81`                   | "d34d..."               | Battery Pack SN (仮称)                                                           | string          | -                                                                                                          | バッテリーパックのシリアル番号?                                                |
| `unknown82`                  | 0                       | -                                                                                | sint32          | -                                                                                                          |                                                                                |

#### cmdFunc32_cmdId2_Report (CMS/BMS のサマリー情報や充電制御関連情報と推測)

`src: 3` (BMS?) から `dest: 32` (App?) へ送信されるメッセージ。ネストした構造 (`msg32_2_1`, `msg32_2_2`) を持つ。

| `captured_data.jsonl` のキー | サンプル値 (msg_seq: 5) | `deltapro3.md` / 開発者ドキュメントでの対応候補                      | 型 (proto 推測) | 単位/値範囲/説明 (ドキュメントより)                                                                                                       | メモ・推測                                                                                                       |
| ---------------------------- | ----------------------- | -------------------------------------------------------------------- | --------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `msg32_2_1.unknown1`         | 1                       | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_1.unknown2`         | 1                       | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_1.unknown3`         | 1                       | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_1.volt4`            | 53350                   | `cmsBattVol` (mV) (`ioBroker`より。開発者ドキュメントに直接記載なし) | sint32          | Overall SOC の下に`cmsBattSoc`はあるが`cmsBattVol`はなし。                                                                                | CMS バッテリー電圧 (53.350V)                                                                                     |
| `msg32_2_1.unknown5`         | 130000                  | `cmsChgReqAmp`? (mA 単位?) (`ioBroker`より)                          | uint32          | 0-80A (開発者ドキュメントに直接記載なし、ioBroker 情報)                                                                                   | CMS 充電要求電流? (130A は大きすぎる。A 単位で 130.000A か、別のパラメータ)                                      |
| `msg32_2_1.unknown6`         | 0                       | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_1.maxChargeSoc7`    | 100                     | `cmsMaxChgSoc` (%)                                                   | uint32          | Charge limit.                                                                                                                             | 充電上限 SOC。                                                                                                   |
| `msg32_2_1.unknown8`         | 5                       | `cmsMinDsgSoc` (%)                                                   | uint32          | Discharge limit.                                                                                                                          | 放電下限 SOC。                                                                                                   |
| `msg32_2_1.unknown9`         | 61                      | `acOutFreq` (Hz)                                                     | uint32          | AC output frequency.                                                                                                                      | AC 出力周波数。DeltaPro3 ドキュメントの Set コマンド例では `cfgAcOutFreq`、Quota では`acOutFreq`。               |
| `msg32_2_1.unknown10`        | 0                       | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_1.unknown11`        | 0                       | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_1.unknown12`        | 400                     | `cmsChgRemTime` (min)                                                | uint32          | Remaining charging time (min).                                                                                                            | CMS 充電残時間。                                                                                                 |
| `msg32_2_1.unknown13`        | 619                     | `cmsDsgRemTime` (min)                                                | uint32          | Remaining discharging time (min).                                                                                                         | CMS 放電残時間。                                                                                                 |
| `msg32_2_1.unknown14`        | 1                       | `cmsChgDsgState`                                                     | sint32          | Charging/Discharging status. 0: not charging or discharging, 1: discharging, 2: charging.                                                 | CMS 充放電状態 (1 なら放電)。                                                                                    |
| `msg32_2_1.soc15`            | 61.260773               | `cmsBattSoc` (%)                                                     | float           | Overall SOC.                                                                                                                              | CMS バッテリー SOC。                                                                                             |
| `msg32_2_1.bmsIsConnt16`     | `[3,0,3]`               | -                                                                    | repeated sint32 | -                                                                                                                                         | BMS 接続状態 (複数パック対応? 各要素がパックの接続状態やタイプを示す可能性)                                      |
| `msg32_2_1.unknown17`        | 2                       | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_1.unknown18`        | 1                       | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_1.unknown19`        | 0                       | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_1.unknown20`        | 0                       | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_1.unknown21`        | 0                       | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_1.unknown22`        | 88                      | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_1.unknown23`        | 100                     | `cmsOilOffSoc` (%) / `cmsOilOnSoc` (%)                               | uint32          | `cmsOilOffSoc`: SOC for automatically stopping the Smart Generator.<br>`cmsOilOnSoc`: SOC for automatically stopping the Smart Generator. | スマートジェネレータ自動停止 SOC (`cmsOilOffSoc`) または開始 SOC (`cmsOilOnSoc`)。値から`cmsOilOffSoc`が妥当か。 |
| `msg32_2_2.unknown1`         | 0                       | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_2.unknown2`         | 0                       | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_2.unknown3`         | 0                       | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_2.unknown4`         | 1                       | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |
| `msg32_2_2.unknown5`         | 259                     | -                                                                    | sint32          | -                                                                                                                                         |                                                                                                                  |

**注意点:**

- 上記の対応付けはあくまで現時点での推測であり、実際の Protobuf 定義 (`.proto`ファイル) や追加のドキュメント、デバイスの挙動と照らし合わせて検証が必要です。
- `unknownX` フィールドの中には、予約領域や内部的なフラグなど、直接ユーザーが意識する必要のない情報も含まれている可能性があります。
- 同じパラメータが複数のメッセージタイプやフィールドで報告されることもあります (例: SOC, 電圧など)。
- `DisplayPropertyUpload` に記載のあるパラメータでも、`cmdFunc50_cmdId30_Report` (Runtime 相当) に含まれてくることがあります。デバイスからのデータ送信の効率化や実装の都合によるものと考えられます。
- 数値の単位 (例: mV vs V, mA vs A) やスケールファクター (mult) に注意が必要です。

### 2025-05-29 11:18 実行ログ解析

- **送信リクエスト:** `cmdId:1, cmdFunc:20` (src:1, dest:32)
- **受信メッセージ (`/app/device/property/{SN}`):**
  - `HeaderMessage` -> `Header` -> `pdata` のデコード成功。
  - 確認された `pdata` の `cmdId`/`cmdFunc` とデコード結果:
    - `cmdId:21, cmdFunc:254` -> `DisplayPropertyUpload` (複数回)
    - `cmdId:50, cmdFunc:32` (encType:0, src:3) -> `cmdFunc50_cmdId30_Report` (複数回)
    - `cmdId:2, cmdFunc:32` -> `cmdFunc32_cmdId2_Report` (複数回)
    - **`cmdId:22, cmdFunc:254` -> `RuntimePropertyUpload` (新規確認、複数回)**
- **`get_reply`:** 今回の実行ログでは、`cmdId:1, cmdFunc:20` に対する `get_reply` は受信されなかった。これは `cmdId:255, cmdFunc:2` で応答があった以前のログと整合する。
- **Base64 デコード:** `/app/device/property/{SN}` からのメッセージペイロードに対する Base64 デコードは期待通り失敗し、生のバイナリデータが後続の Protobuf デコードに使用されている。

**考察:**

- `RuntimePropertyUpload` (`cmdId:22, cmdFunc:254`) が新たに確認された。このメッセージの内容と `DisplayPropertyUpload` との差分や、ioBroker のドキュメントとの関連性を調査する必要がある。
- 引き続き `get_reply` の安定的な受信と、その内容 (特にフォーマットバイト `0x3c` の意味) の解明が重要。

- [ ] `RuntimePropertyUpload` (`cmdId:22, cmdFunc:254`) のフィールド詳細解析と `.proto` ファイルへの反映。

### cmdId/cmdFunc → 型名（Protobuf/論理名）完全対応表（2024-06-01 時点, 全情報源突合）

| cmdId | cmdFunc | 型名（Protobuf/論理名）            | 用途・備考                              |
| ----- | ------- | ---------------------------------- | --------------------------------------- |
| 21    | 254     | DisplayPropertyUpload              | 定期アップロード（UI 表示用プロパティ） |
| 22    | 254     | RuntimePropertyUpload              | 詳細ランタイムアップロード              |
| 50    | 32      | cmdFunc50_cmdId30_Report           | BMS 詳細ランタイム                      |
| 2     | 32      | cmdFunc32_cmdId2_Report            | CMS/BMS サマリー                        |
| 23    | 254     | cmdFunc254_cmdId23_Report          | タイムスタンプ付きレポート              |
| 17    | 254     | setDp3                             | 設定コマンド                            |
| 18    | 254     | setReplyDp3                        | 設定コマンド応答                        |
| 255   | 2       | setReply_dp3                       | SET コマンドに対する応答（汎用）        |
| 1     | 20      | （標準 MQTT, Get ALL Quotas）      | 全プロパティ取得要求（応答は複数型）    |
| -     | -       | RTCTimeSet                         | RTC 時刻設定                            |
| -     | -       | RTCTimeSetAck                      | RTC 時刻設定応答                        |
| -     | -       | ProductNameSet                     | 製品名設定                              |
| -     | -       | ProductNameSetAck                  | 製品名設定応答                          |
| -     | -       | ProductNameGet                     | 製品名取得要求                          |
| -     | -       | ProductNameGetAck                  | 製品名取得応答                          |
| -     | -       | RTCTimeGet                         | RTC 時刻取得要求                        |
| -     | -       | RTCTimeGetAck                      | RTC 時刻取得応答                        |
| -     | -       | EventRecordReport                  | イベント・エラーログ通知                |
| -     | -       | EventInfoReportAck                 | イベント応答                            |
| -     | -       | SendMsgHart                        | ハートビート                            |
| -     | -       | Header/Send_Header_Msg             | 共通ヘッダー構造                        |
| -     | -       | TimeTaskItemV2/TimeTaskParamDetail | タイマー予約関連                        |

- cmdId/cmdFunc の組み合わせが明確なものは全て網羅。
- 未分類・調査中の型も、.proto 定義・js 実装・ドキュメントから抽出し記載。
- js 実装や実データで観測された新規型・未解明型も随時追加。
- DisplayPropertyUpload/RuntimePropertyUpload/cmdFunc50_cmdId30_Report/cmdFunc32_cmdId2_Report/setDp3/setReplyDp3 等、全ての主要型を含む。
- Get ALL Quotas 等の特殊コマンドも記載（応答は複数型）。

#### DisplayPropertyUpload（全フィールド網羅, ioBroker 実装/deltapro3.md 反映）

| フィールド名                | 型     | 単位/範囲   | enum/状態値・選択肢 | 説明                                          | 備考       |
| --------------------------- | ------ | ----------- | ------------------- | --------------------------------------------- | ---------- |
| plugInInfo_4p8_1Resv        | array  |             |                     | plug in info_4p8_1 resv                       | diagnostic |
| plugInInfo_4p8_2Resv        | array  |             |                     | plug in info_4p8_2 resv                       | diagnostic |
| plugInInfo_5p8Resv          | array  |             |                     | plug in info_5p8 resv                         | diagnostic |
| errcode                     | string |             |                     | errcode                                       |            |
| utcTimezoneId               | string |             |                     | utc timezone id                               |            |
| pcsFanLevel                 | string |             |                     | pcs fan level                                 |            |
| plugInInfo_5p8Detail        | string |             |                     | plug in info_5p8 detail                       |            |
| bmsErrCode                  | string |             |                     | bms err code                                  |            |
| plugInInfo_4p8_1Detail      | string |             |                     | plug in info_4p8_1 detail                     |            |
| plugInInfo_4p8_2Detail      | string |             |                     | plug in info_4p8_2 detail                     |            |
| plugInInfo_4p8_1Sn          | string |             |                     | SN of the device connected to Extra Battery 1 |            |
| plugInInfo_4p8_1FirmVer     | string |             |                     | plug in info_4p8_1 firm ver                   |            |
| plugInInfo_4p8_2Sn          | string |             |                     | SN of the device connected to Extra Battery 2 |            |
| plugInInfo_4p8_2FirmVer     | string |             |                     | plug in info_4p8_2 firm ver                   |            |
| plugInInfo_5p8DsgChg        | string |             |                     | Charging/Discharging type of Power In/Out     |            |
| plugInInfo_5p8Sn            | string |             |                     | SN of the device connected to Power In/Out    |            |
| plugInInfo_5p8FirmVer       | string |             |                     | plug in info_5p8 firm ver                     |            |
| pdErrCode                   | string |             |                     | pd err code                                   |            |
| llcErrCode                  | string |             |                     | llc err code                                  |            |
| mpptErrCode                 | string |             |                     | mppt err code                                 |            |
| plugInInfo_5p8ErrCode       | string |             |                     | plug in info_5p8 err code                     |            |
| plugInInfo_4p8_1ErrCode     | string |             |                     | plug in info_4p8_1 err code                   |            |
| plugInInfo_4p8_2ErrCode     | string |             |                     | plug in info_4p8_2 err code                   |            |
| llcInvErrCode               | string |             |                     | llc inv err code                              |            |
| powInSumW                   | number | 0-8000 W    |                     | Total input power                             |            |
| powOutSumW                  | number | 0-8000 W    |                     | Total output power                            |            |
| energyBackupStartSoc        | number | 0-100 %     |                     | Backup reserve level                          |            |
| powGetQcusb1                | number | 0-120 W     |                     | Real-time power of the USB 1 port             |            |
| powGetQcusb2                | number | 0-120 W     |                     | Real-time power of the USB 2 port             |            |
| powGetTypec1                | number | 0-4000 W    |                     | Real-time power of Type-C port 1              |            |
| powGetTypec2                | number | 0-4000 W    |                     | Real-time power of Type-C port 2              |            |
| acAlwaysOnMiniSoc           | number | 0-100 %     |                     | Sets the minimum SOC to enable AC Always-on   |            |
| powGetPvH                   | number | 0-1600 W    |                     | Real-time high-voltage PV power               |            |
| powGetPvL                   | number | 0-1000 W    |                     | Real-time low-voltage PV power                |            |
| powGet_12v                  | number | 0-60 W      |                     | Real-time 12V power                           |            |
| powGet_24v                  | number | 0-400 W     |                     | Real-time 24V power                           |            |
| powGetLlc                   | number | 0-8000 W    |                     | pow get llc                                   |            |
| powGetAc                    | number | 0-8000 W    |                     | Real-time AC power                            |            |
| powGetAcIn                  | number | 0-8000 W    |                     | Real-time AC input power                      |            |
| powGetAcHvOut               | number | 0-8000 W    |                     | Real-time grid power                          |            |
| powGetAcLvOut               | number | 0-4000 W    |                     | Real-time low-voltage AC output power         |            |
| powGetAcLvTt30Out           | number | 0-8000 W    |                     | Real-time power of the low-voltage AC output  |            |
| powGet_5p8                  | number | 0-4000 W    |                     | Real-time power of the Power In/Out port      |            |
| utcTimezone                 | number | -1200-1200  |                     | utc timezone                                  |            |
| powGetBms                   | number | 0-8000 W    |                     | pow get bms                                   |            |
| powGet_4p8_1                | number | 0-4000 W    |                     | Real-time power of Extra Battery Port 1       |            |
| powGet_4p8_2                | number | 0-4000 W    |                     | Real-time power of Extra Battery Port 2       |            |
| acOutFreq                   | number | 49-61 Hz    |                     | AC output frequency                           |            |
| plugInInfoPvHChgVolMax      | number | 0-150 V     |                     | Maximum charging voltage of HV PV port        |            |
| plugInInfoPvHChgAmpMax      | number | 0-15 A      |                     | Maximum charging current of HV PV port        |            |
| bmsBattSoc                  | number | 0-100 %     |                     | SOC of the main battery                       |            |
| bmsBattSoh                  | number | 0-100 %     |                     | SOH of the main battery                       |            |
| bmsDesignCap                | number | 0-80000 mAh |                     | Battery capacity                              |            |
| bmsDsgRemTime               | number | 0-15999 min |                     | Remaining discharging time                    |            |
| bmsChgRemTime               | number | 0-15999 min |                     | Remaining charging time of the main battery   |            |
| bmsMinCellTemp              | number | 0-80 °C     |                     | Minimum temperature of the main battery       |            |
| bmsMaxCellTemp              | number | 0-80 °C     |                     | Temperature of the main battery               |            |
| bmsMinMosTemp               | number | 0-100 °C    |                     | bms min mos temp                              |            |
| bmsMaxMosTemp               | number | 0-100 °C    |                     | bms max mos temp                              |            |
| cmsBattSoc                  | number | 0-100 %     |                     | Overall SOC                                   |            |
| cmsBattSoh                  | number | 0-100 %     |                     | Overall SOH                                   |            |
| cmsDsgRemTime               | number | 0-15999 min |                     | Remaining discharging time                    |            |
| cmsChgRemTime               | number | 0-15999 min |                     | Remaining charging time                       |            |
| timeTaskChangeCnt           | number | 0-60        |                     | time task change cnt                          |            |
| generatorPvHybridModeSocMax | number | 0-100 %     |                     | generator pv hybrid mode soc max              |            |
| generatorCareModeStartTime  | number | 0-2000 h    |                     | generator care mode start time                |            |
| plugInInfoAcInFeq           | number | 50-60 Hz    |                     | AC input frequency                            |            |
| plugInInfoPvLChgVolMax      | number | 0-60 V      |                     | Maximum charging voltage of LV PV port        |            |
| plugInInfoPvLChgAmpMax      | number | 0-20 A      |                     | Maximum charging current of LV PV port        |            |
| plugInInfo_5p8DsgPowMax     | number | 0-4000 W    |                     | Maximum discharging power of Power In/Out     |            |
| plugInInfoAcOutDsgPowMax    | number | 0-4000 W    |                     | Maximum AC discharging power                  |            |
| plugInInfo_5p8ChgHalPowMax  | number | 0-4000 W    |                     | Maximum AC charging power In/Out port         |            |
| plugInInfoAcInChgHalPowMax  | number | 0-2000 W    |                     | Maximum AC charging power                     |            |

#### RuntimePropertyUpload（全フィールド網羅, ioBroker 実装/deltapro3.md 反映）

| フィールド名                | 型         | 単位/範囲   | enum/状態値・選択肢 | 説明                                          | 備考 |
| --------------------------- | ---------- | ----------- | ------------------- | --------------------------------------------- | ---- |
| acPhaseType                 | diagnostic |             | 0:OK?               | ac phase type                                 |      |
| pcsWorkMode                 | diagnostic |             | 0:OK?               | pcs work mode                                 |      |
| plugInInfoAcOutType         | diagnostic |             | 0:OK?               | plug in info ac out type                      |      |
| mpptMonitorFlag             | diagnostic |             | 0:OK?               | mppt monitor flag                             |      |
| bmsBalState                 | diagnostic |             | 0:OK?               | bms bal state                                 |      |
| bmsAlmState                 | diagnostic |             | 0:OK?               | bms alm state                                 |      |
| bmsProState                 | diagnostic |             | 0:OK?               | bms pro state                                 |      |
| bmsFltState                 | diagnostic |             | 0:OK?               | bms flt state                                 |      |
| bmsAlmState_2               | diagnostic |             | 0:OK?               | bms alm state_2                               |      |
| bmsProState_2               | diagnostic |             | 0:OK?               | bms pro state_2                               |      |
| ...                         | ...        | ...         | ...                 | ...                                           | ...  |
| errcode                     | string     |             |                     | errcode                                       |      |
| utcTimezoneId               | string     |             |                     | utc timezone id                               |      |
| pcsFanLevel                 | string     |             |                     | pcs fan level                                 |      |
| plugInInfo_5p8Detail        | string     |             |                     | plug in info_5p8 detail                       |      |
| bmsErrCode                  | string     |             |                     | bms err code                                  |      |
| plugInInfo_4p8_1Detail      | string     |             |                     | plug in info_4p8_1 detail                     |      |
| plugInInfo_4p8_2Detail      | string     |             |                     | plug in info_4p8_2 detail                     |      |
| plugInInfo_4p8_1Sn          | string     |             |                     | SN of the device connected to Extra Battery 1 |      |
| plugInInfo_4p8_1FirmVer     | string     |             |                     | plug in info_4p8_1 firm ver                   |      |
| plugInInfo_4p8_2Sn          | string     |             |                     | SN of the device connected to Extra Battery 2 |      |
| plugInInfo_4p8_2FirmVer     | string     |             |                     | plug in info_4p8_2 firm ver                   |      |
| plugInInfo_5p8DsgChg        | string     |             |                     | Charging/Discharging type of Power In/Out     |      |
| plugInInfo_5p8Sn            | string     |             |                     | SN of the device connected to Power In/Out    |      |
| plugInInfo_5p8FirmVer       | string     |             |                     | plug in info_5p8 firm ver                     |      |
| pdErrCode                   | string     |             |                     | pd err code                                   |      |
| llcErrCode                  | string     |             |                     | llc err code                                  |      |
| mpptErrCode                 | string     |             |                     | mppt err code                                 |      |
| plugInInfo_5p8ErrCode       | string     |             |                     | plug in info_5p8 err code                     |      |
| plugInInfo_4p8_1ErrCode     | string     |             |                     | plug in info_4p8_1 err code                   |      |
| plugInInfo_4p8_2ErrCode     | string     |             |                     | plug in info_4p8_2 err code                   |      |
| llcInvErrCode               | string     |             |                     | llc inv err code                              |      |
| powInSumW                   | number     | 0-8000 W    |                     | Total input power                             |      |
| powOutSumW                  | number     | 0-8000 W    |                     | Total output power                            |      |
| energyBackupStartSoc        | number     | 0-100 %     |                     | Backup reserve level                          |      |
| powGetQcusb1                | number     | 0-120 W     |                     | Real-time power of the USB 1 port             |      |
| powGetQcusb2                | number     | 0-120 W     |                     | Real-time power of the USB 2 port             |      |
| powGetTypec1                | number     | 0-4000 W    |                     | Real-time power of Type-C port 1              |      |
| powGetTypec2                | number     | 0-4000 W    |                     | Real-time power of Type-C port 2              |      |
| acAlwaysOnMiniSoc           | number     | 0-100 %     |                     | Sets the minimum SOC to enable AC Always-on   |      |
| powGetPvH                   | number     | 0-1600 W    |                     | Real-time high-voltage PV power               |      |
| powGetPvL                   | number     | 0-1000 W    |                     | Real-time low-voltage PV power                |      |
| powGet_12v                  | number     | 0-60 W      |                     | Real-time 12V power                           |      |
| powGet_24v                  | number     | 0-400 W     |                     | Real-time 24V power                           |      |
| powGetLlc                   | number     | 0-8000 W    |                     | pow get llc                                   |      |
| powGetAc                    | number     | 0-8000 W    |                     | Real-time AC power                            |      |
| powGetAcIn                  | number     | 0-8000 W    |                     | Real-time AC input power                      |      |
| powGetAcHvOut               | number     | 0-8000 W    |                     | Real-time grid power                          |      |
| powGetAcLvOut               | number     | 0-4000 W    |                     | Real-time low-voltage AC output power         |      |
| powGetAcLvTt30Out           | number     | 0-8000 W    |                     | Real-time power of the low-voltage AC output  |      |
| powGet_5p8                  | number     | 0-4000 W    |                     | Real-time power of the Power In/Out port      |      |
| utcTimezone                 | number     | -1200-1200  |                     | utc timezone                                  |      |
| powGetBms                   | number     | 0-8000 W    |                     | pow get bms                                   |      |
| powGet_4p8_1                | number     | 0-4000 W    |                     | Real-time power of Extra Battery Port 1       |      |
| powGet_4p8_2                | number     | 0-4000 W    |                     | Real-time power of Extra Battery Port 2       |      |
| acOutFreq                   | number     | 49-61 Hz    |                     | AC output frequency                           |      |
| plugInInfoPvHChgVolMax      | number     | 0-150 V     |                     | Maximum charging voltage of HV PV port        |      |
| plugInInfoPvHChgAmpMax      | number     | 0-15 A      |                     | Maximum charging current of HV PV port        |      |
| bmsBattSoc                  | number     | 0-100 %     |                     | SOC of the main battery                       |      |
| bmsBattSoh                  | number     | 0-100 %     |                     | SOH of the main battery                       |      |
| bmsDesignCap                | number     | 0-80000 mAh |                     | Battery capacity                              |      |
| bmsDsgRemTime               | number     | 0-15999 min |                     | Remaining discharging time                    |      |
| bmsChgRemTime               | number     | 0-15999 min |                     | Remaining charging time                       |      |
| bmsMinCellTemp              | number     | 0-80 °C     |                     | Minimum temperature of the main battery       |      |
| bmsMaxCellTemp              | number     | 0-80 °C     |                     | Temperature of the main battery               |      |
| bmsMinMosTemp               | number     | 0-100 °C    |                     | bms min mos temp                              |      |
| bmsMaxMosTemp               | number     | 0-100 °C    |                     | bms max mos temp                              |      |
| cmsBattSoc                  | number     | 0-100 %     |                     | Overall SOC                                   |      |
| cmsBattSoh                  | number     | 0-100 %     |                     | Overall SOH                                   |      |
| cmsDsgRemTime               | number     | 0-15999 min |                     | Remaining discharging time                    |      |
| cmsChgRemTime               | number     | 0-15999 min |                     | Remaining charging time                       |      |
| timeTaskChangeCnt           | number     | 0-60        |                     | time task change cnt                          |      |
| generatorPvHybridModeSocMax | number     | 0-100 %     |                     | generator pv hybrid mode soc max              |      |
| generatorCareModeStartTime  | number     | 0-2000 h    |                     | generator care mode start time                |      |
| plugInInfoAcInFeq           | number     | 50-60 Hz    |                     | AC input frequency                            |      |
| plugInInfoPvLChgVolMax      | number     | 0-60 V      |                     | Maximum charging voltage of LV PV port        |      |
| plugInInfoPvLChgAmpMax      | number     | 0-20 A      |                     | Maximum charging current of LV PV port        |      |
| plugInInfo_5p8DsgPowMax     | number     | 0-4000 W    |                     | Maximum discharging power of Power In/Out     |      |
| plugInInfoAcOutDsgPowMax    | number     | 0-4000 W    |                     | Maximum AC discharging power                  |      |
| plugInInfo_5p8ChgHalPowMax  | number     | 0-4000 W    |                     | Maximum AC charging power In/Out port         |      |
| plugInInfoAcInChgHalPowMax  | number     | 0-2000 W    |                     | Maximum AC charging power                     |      |

#### setReplyDp3（設定コマンド応答, 全フィールド網羅, ioBroker/Python/proto 定義反映）

| フィールド名            | 型     | 単位/範囲                               | enum/状態値・選択肢 | 説明                                               | 備考          |
| ----------------------- | ------ | --------------------------------------- | ------------------- | -------------------------------------------------- | ------------- |
| actionId                | int    |                                         |                     | コマンド実行 ID（リクエストと対応）                |               |
| configOk                | bool   |                                         | true/false          | 設定反映成功フラグ                                 |               |
| cfgPowerOff             | switch |                                         | 0:off, 1:on         | Shut down the entire device                        |               |
| enBeep                  | switch |                                         | 0:off, 1:on         | Beeper on/off                                      |               |
| acStandbyTime           | level  | 0-1440 min                              | see states          | AC timeout (min)                                   | select 有     |
| dcStandbyTime           | level  | 0-1440 min                              | see states          | DC timeout (min)                                   | select 有     |
| screenOffTime           | level  | 0-1800 s                                | see states          | Screen timeout (s)                                 | select 有     |
| devStandbyTime          | level  | 0-1440 min                              | see states          | Device timeout (min)                               | select 有     |
| lcdLight                | level  | 0-100 %                                 |                     | Screen brightness                                  | mult:0.390625 |
| cfgHvAcOutOpen          | switch |                                         | 0:off, 1:on         | high-voltage AC output switch                      |               |
| cfgLvAcOutOpen          | switch |                                         | 0:off, 1:on         | low-voltage AC output switch                       |               |
| cfgDc12vOutOpen         | switch |                                         | 0:off, 1:on         | 12V output switch                                  |               |
| xboostEn                | switch |                                         | 0:off, 1:on         | X-Boost switch                                     |               |
| cmsMaxChgSoc            | level  | 50-100 %                                |                     | Charge limit                                       |               |
| cmsMinDsgSoc            | level  | 0-30 %                                  |                     | Discharge limit                                    |               |
| plugInInfoPvLDcAmpMax   | number | 0-15 A                                  |                     | Maximum input current of the low-voltage PV port   |               |
| plugInInfoPvHDcAmpMax   | number | 0-10 A                                  |                     | Maximum input current of the high-voltage PV port  |               |
| plugInInfoAcInChgPowMax | number | 100-1500 W                              |                     | Maximum AC input power for charging                |               |
| plugInInfo_5p8ChgPowMax | number | 500-4000 W                              |                     | Maximum charging power of the Power In/Out port    |               |
| cmsOilSelfStart         | switch |                                         | 0:off, 1:on         | Smart Generator auto start/stop switch             |               |
| cmsOilOnSoc             | level  | 10-30 %                                 |                     | SOC for automatically starting the Smart Generator |               |
| cmsOilOffSoc            | level  | 50-100 %                                |                     | SOC for automatically stopping the Smart Generator |               |
| llc_GFCIFlag            | switch |                                         | 0:off, 1:on         | GFCI switch                                        |               |
| acEnergySavingOpen      | switch |                                         | 0:off, 1:on         | AC energy-saving mode switch                       |               |
| multiBpChgDsgMode       | select | 0:default, 1:automatic, 2:main bat prio | see states          | Battery charging/discharging order                 |               |
| lowDischargeLimitCmd    | int    |                                         |                     | 低放電制限コマンド（詳細不明, not EF-API）         |               |
| unknown167              | int    |                                         |                     | 未解明フィールド                                   |               |

#### cmdFunc50_cmdId30_Report（BMS 詳細ランタイム, 全フィールド網羅, .proto 定義・実データ反映）

| フィールド名                | 型              | 単位/範囲 | enum/状態値・選択肢  | 説明                                         | 備考       |
| --------------------------- | --------------- | --------- | -------------------- | -------------------------------------------- | ---------- |
| bms_flt_state               | sint32          |           | 0:OK                 | BMS fault state                              |            |
| bms_pro_state               | sint32          |           | 0:OK                 | BMS protection state                         |            |
| bms_alm_state               | sint32          |           | 0:OK                 | BMS alarm state                              |            |
| bms_bal_state               | sint32          |           | 0:OK                 | BMS balance state                            |            |
| unknown5                    | uint64          |           |                      | BMS 関連 ID/カウンタ?                        |            |
| unknown6                    | sint32          |           |                      |                                              |            |
| bms_batt_vol                | sint32          | mV        |                      | メインバッテリー電圧（例: 51510=51.510V）    |            |
| bms_batt_amp                | sint32          | mA        |                      | メインバッテリー電流（例: -8938=-8.938A）    | 放電時負値 |
| bms_max_cell_temp_dup       | sint32          | °C        |                      | 最高セル温度（maxCellTemp18 と重複）         |            |
| unknown10                   | sint32          |           |                      |                                              |            |
| bms_design_cap_mah_dup      | uint32          | mAh       |                      | バッテリー設計容量（unknown24 と重複）       |            |
| bms_remain_cap_mah          | uint32          | mAh       |                      | バッテリー残容量                             |            |
| bms_full_cap_mah            | uint32          | mAh       |                      | バッテリー満充電容量                         |            |
| unknown14                   | sint32          |           |                      |                                              |            |
| bms_batt_soh_percent_int    | uint32          | %         |                      | バッテリー SOH（整数, soh54 と比較）         |            |
| max_cell_vol_mv             | uint32          | mV        |                      | 最大セル電圧                                 |            |
| min_cell_vol_mv             | uint32          | mV        |                      | 最小セル電圧                                 |            |
| max_cell_temp_c             | sint32          | °C        |                      | 最高セル温度                                 |            |
| min_cell_temp_c             | sint32          | °C        |                      | 最低セル温度                                 |            |
| max_mos_temp_c              | sint32          | °C        |                      | BMS MOS 最高温度                             |            |
| min_mos_temp_c              | sint32          | °C        |                      | BMS MOS 最低温度                             |            |
| unknown22                   | sint32          |           |                      |                                              |            |
| unknown23                   | sint32          |           |                      |                                              |            |
| bms_design_cap_mah          | uint32          | mAh       |                      | バッテリー設計容量                           |            |
| bms_batt_soc_percent_float1 | float           | %         |                      | バッテリー SOC（float, unknown42/44 と類似） |            |
| unknown26                   | sint32          |           |                      |                                              |            |
| bms_chg_rem_time_min        | uint32          | min       |                      | 充電残時間                                   |            |
| bms_dsg_rem_time_min        | uint32          | min       |                      | 放電残時間                                   |            |
| unknown29                   | sint32          |           |                      |                                              |            |
| unknown30                   | sint32          |           |                      |                                              |            |
| max_mos_temp_c_dup          | sint32          | °C        |                      | BMS MOS 最高温度（maxMosTemp20 と重複）      |            |
| cell_vol_array_size         | sint32          |           |                      | cellVol33 配列の要素数（通常 16）            |            |
| cell_vol_mv                 | repeated uint32 | mV        |                      | 各セル電圧配列（16 セル）                    |            |
| cell_temp_array_size        | sint32          |           |                      | cellTemp35 配列の要素数（通常 8）            |            |
| cell_temp_c                 | repeated sint32 | °C        |                      | 各セル温度配列（8 個所）                     |            |
| bms_firm_ver                | string          |           |                      | BMS ファームウェアバージョン                 |            |
| bms_heart_ver               | uint32          |           |                      | BMS ハートビートバージョン?                  |            |
| ecloud_ocv                  | uint32          |           |                      | OCV 関連? 65535 は無効値か                   |            |
| bms_sn                      | string          |           |                      | BMS シリアル番号?                            |            |
| unknown40                   | sint32          |           |                      |                                              |            |
| unknown41                   | sint32          |           |                      |                                              |            |
| bms_batt_soc_percent_float2 | float           | %         |                      | バッテリー SOC（float, unknown25/44 と類似） |            |
| unknown43                   | float           |           |                      |                                              |            |
| bms_batt_soc_percent_float3 | float           | %         |                      | バッテリー SOC（float, unknown25/42 と類似） |            |
| unknown45                   | sint32          |           | -1:無効値/未設定?    |                                              |            |
| unknown46                   | sint32          |           |                      |                                              |            |
| bms_chg_dsg_state           | sint32          |           | 0:idle,1:放電,2:充電 | 充電/放電状態                                |            |
| unknown48                   | sint32          |           |                      |                                              |            |
| unknown49                   | sint32          |           |                      |                                              |            |
| unknown50                   | uint64          |           |                      |                                              |            |
| unknown51                   | uint64          |           |                      |                                              |            |
| unknown52                   | float           |           |                      | SOH 関連値?                                  |            |
| unknown53                   | float           |           |                      |                                              |            |
| bms_batt_soh_percent_float  | float           | %         |                      | バッテリー SOH（float, soh54,最も正確?）     |            |
| unknown55                   | sint32          |           |                      |                                              |            |
| mos_temp_c                  | repeated sint32 | °C        |                      | MOS 温度（3 個所）                           |            |
| unknown57                   | sint32          |           |                      |                                              |            |
| unknown58                   | repeated sint32 |           |                      |                                              |            |
| unknown61                   | sint32          |           |                      |                                              |            |
| unknown62                   | repeated sint32 |           |                      |                                              |            |
| unknown63                   | sint32          |           |                      |                                              |            |
| unknown64                   | sint32          |           |                      |                                              |            |
| unknown67                   | sint32          |           |                      |                                              |            |
| unknown68                   | sint32          |           |                      |                                              |            |
| unknown69                   | sint32          |           |                      |                                              |            |
| bms_err_code_flags          | repeated uint32 |           |                      | BMS エラーコード配列（16 要素,0:エラーなし） |            |
| unknown71                   | sint32          |           |                      |                                              |            |
| bat_volt_mv_array           | repeated sint32 | mV        |                      | バッテリー電圧（配列,通常 1 要素）           |            |
| unknown73                   | uint32          |           |                      |                                              |            |
| unknown74                   | sint32          |           |                      |                                              |            |
| unknown75                   | sint32          |           |                      |                                              |            |
| unknown76                   | sint32          |           |                      |                                              |            |
| unknown77                   | sint32          |           |                      |                                              |            |
| unknown78                   | sint32          |           |                      |                                              |            |
| unknown79                   | uint64          |           |                      |                                              |            |
| unknown80                   | uint64          |           |                      |                                              |            |
| pack_sn                     | string          |           |                      | バッテリーパックシリアル番号?                |            |
| unknown82                   | sint32          |           |                      |                                              |            |

#### cmdFunc32_cmdId2_Report（CMS/BMS サマリー, 全フィールド網羅, .proto 定義・実データ反映）

| フィールド名             | 型     | 単位/範囲 | enum/状態値・選択肢 | 説明                                        | 備考 |
| ------------------------ | ------ | --------- | ------------------- | ------------------------------------------- | ---- |
| cms_flt_state            | sint32 |           | 0:OK                | CMS fault state                             |      |
| cms_pro_state            | sint32 |           | 0:OK                | CMS protection state                        |      |
| cms_alm_state            | sint32 |           | 0:OK                | CMS alarm state                             |      |
| cms_ntc_state            | sint32 |           | 0:OK                | CMS NTC state                               |      |
| cms_ntc_num              | sint32 |           |                     | CMS NTC number                              |      |
| cms_ntc_temp             | sint32 | °C        |                     | CMS NTC temperature                         |      |
| bms_flt_state            | sint32 |           | 0:OK                | BMS fault state                             |      |
| bms_pro_state            | sint32 |           | 0:OK                | BMS protection state                        |      |
| bms_alm_state            | sint32 |           | 0:OK                | BMS alarm state                             |      |
| bms_ntc_state            | sint32 |           | 0:OK                | BMS NTC state                               |      |
| bms_ntc_num              | sint32 |           |                     | BMS NTC number                              |      |
| bms_ntc_temp             | sint32 | °C        |                     | BMS NTC temperature                         |      |
| bms_cell_volt_max        | sint32 | mV        |                     | BMS cell voltage max                        |      |
| bms_cell_volt_min        | sint32 | mV        |                     | BMS cell voltage min                        |      |
| bms_cell_volt_diff       | sint32 | mV        |                     | BMS cell voltage diff                       |      |
| bms_cell_volt_avg        | sint32 | mV        |                     | BMS cell voltage avg                        |      |
| bms_temp_max             | sint32 | °C        |                     | BMS temperature max                         |      |
| bms_temp_min             | sint32 | °C        |                     | BMS temperature min                         |      |
| bms_temp_avg             | sint32 | °C        |                     | BMS temperature avg                         |      |
| bms_soc                  | sint32 | %         | 0-100               | BMS state of charge                         |      |
| bms_soh                  | sint32 | %         | 0-100               | BMS state of health                         |      |
| bms_cycle                | sint32 |           |                     | BMS cycle count                             |      |
| bms_cap                  | sint32 | mAh       |                     | BMS capacity                                |      |
| bms_current              | sint32 | mA        |                     | BMS current                                 |      |
| bms_volt                 | sint32 | mV        |                     | BMS voltage                                 |      |
| bms_power                | sint32 | mW        |                     | BMS power                                   |      |
| bms_res                  | sint32 | mΩ        |                     | BMS resistance                              |      |
| bms_fet_state            | sint32 |           |                     | BMS FET state                               |      |
| bms_fet_temp             | sint32 | °C        |                     | BMS FET temperature                         |      |
| bms_fet_curr             | sint32 | mA        |                     | BMS FET current                             |      |
| bms_fet_volt             | sint32 | mV        |                     | BMS FET voltage                             |      |
| bms_fet_power            | sint32 | mW        |                     | BMS FET power                               |      |
| bms_fet_res              | sint32 | mΩ        |                     | BMS FET resistance                          |      |
| bms_fet_num              | sint32 |           |                     | BMS FET number                              |      |
| bms_fet_type             | sint32 |           |                     | BMS FET type                                |      |
| bms_fet_ver              | sint32 |           |                     | BMS FET version                             |      |
| bms_fet_sn               | sint32 |           |                     | BMS FET serial number                       |      |
| bms_fet_sw_ver           | sint32 |           |                     | BMS FET software version                    |      |
| bms_fet_hw_ver           | sint32 |           |                     | BMS FET hardware version                    |      |
| bms_fet_manu_date        | sint32 |           |                     | BMS FET manufacture date                    |      |
| bms_fet_manu_name        | string |           |                     | BMS FET manufacturer name                   |      |
| bms_fet_manu_sn          | string |           |                     | BMS FET manufacturer serial number          |      |
| bms_fet_manu_sw_ver      | string |           |                     | BMS FET manufacturer software version       |      |
| bms_fet_manu_hw_ver      | string |           |                     | BMS FET manufacturer hardware version       |      |
| bms_fet_manu_date_str    | string |           |                     | BMS FET manufacturer date (string)          |      |
| bms_fet_manu_name_str    | string |           |                     | BMS FET manufacturer name (string)          |      |
| bms_fet_manu_sn_str      | string |           |                     | BMS FET manufacturer serial number (string) |      |
| bms_fet_manu_sw_ver_str  | string |           |                     | BMS FET manufacturer software ver (string)  |      |
| bms_fet_manu_hw_ver_str  | string |           |                     | BMS FET manufacturer hardware ver (string)  |      |
| bms_fet_manu_date_str2   | string |           |                     | BMS FET manufacturer date (string2)         |      |
| bms_fet_manu_name_str2   | string |           |                     | BMS FET manufacturer name (string2)         |      |
| bms_fet_manu_sn_str2     | string |           |                     | BMS FET manufacturer serial number (str2)   |      |
| bms_fet_manu_sw_ver_str2 | string |           |                     | BMS FET manufacturer software ver (str2)    |      |
| bms_fet_manu_hw_ver_str2 | string |           |                     | BMS FET manufacturer hardware ver (str2)    |      |
