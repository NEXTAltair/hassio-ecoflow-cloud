## 問題の概要

EcoFlow Delta Pro 3 からの MQTT メッセージは `scripts/mqtt_capture_dp3_debug.py` スクリプト (現在は `scripts/ecoflow_mqtt_parser/` 配下のモジュール群) で受信できているものの、そのペイロードを正しくデコードし、Protobuf メッセージとして解釈することが課題であった。
具体的には、`/app/device/property/{DEVICE_SN}` トピックなどでメッセージを受信するが、Base64 デコードの扱いや、デコード後の Protobuf デシリアライズ処理が適切でなく、有効なデータとして利用できていなかった。

## 現在の状況と解決策 (Issue 完了時点)

- **MQTT 接続と基本処理の確立:**
  - `scripts/ecoflow_mqtt_parser/` 配下のモジュール (`mqtt_client_setup.py`, `message_handler.py`, `main_parser.py` 等) に処理を分割。
  - MQTT ブローカーへの接続、トピック購読、メッセージ受信、データ取得要求メッセージ (`cmdId:1, cmdFunc:20`) の送信に成功。
    - 当初、`mqtt_client_setup.py` の `publish_get_all_data_request` 内で `Header` メッセージの `from` フィールド (Python では `from_`) を設定しようとして `TypeError` が発生したが、Protobuf 定義に当該フィールドが存在しない可能性が高いため一時的にコメントアウトし、データ取得自体は成功。
- **`/app/device/property/{DEVICE_SN}` トピックメッセージの解析成功:**
  - **エンコード形式:** このトピックのペイロードは Base64 エンコードされていないことが多く、その場合は元のバイナリデータのまま処理。
  - **デコードフロー:**
    1. 受信ペイロードを `pm.HeaderMessage` (実際には `ef_dp3_iobroker_pb2.HeaderMessage`) としてデコード。
    2. `HeaderMessage` 内部の各 `pm.Header` (実際には `ef_dp3_iobroker_pb2.Header`) を取り出す。
    3. 各 `Header` の `pdata` フィールドに対し、`enc_type` と `src` の値に基づいて `common.xor_decode_pdata` による XOR デコードを実行 (またはスキップ)。
    4. XOR デコード後の `pdata` を、`Header` の `cmd_id` と `cmd_func` の値に基づき、`protobuf_mapping.py` で定義された特定の Protobuf メッセージ型 (例: `DisplayPropertyUpload`, `cmdFunc50_cmdId30_Report`, `cmdFunc32_cmdId2_Report`) にデコード。
  - **結果出力:** デコードされた内容は `captured_data.jsonl` に JSON 形式で正しく記録されるようになった。
    - `message_handler.py` の `_protobuf_to_dict_with_hex` メソッド内の `json_format.MessageToDict` の引数 `including_default_value_fields` が原因で発生していたエラーは、引数を `always_print_fields_with_no_presence=True` と `use_integers_for_enums=True` に修正することで解決。
- **ioBroker ドキュメントの活用:**
  - `ioBroker.ecoflow-mqtt/doc/devices/deltapro3.md` が、デコードされた Protobuf メッセージの各フィールドの意味を理解する上で非常に重要な参照情報であることが確認された。

## 主な課題 (解決済み)

1.  **`/app/device/property/{DEVICE_SN}` トピックメッセージのエンコード形式特定:** 解決済み。Base64 エンコードされていないケースを正しく処理。
2.  **Protobuf メッセージ型の特定とデコード処理の実装:** 解決済み。`HeaderMessage` -> `Header` -> `pdata` (XOR デコード含む) -> 具体的な型へのデコードフローを確立。
3.  **動的な Protobuf 型特定とデコードロジックの欠如:** 解決済み。`protobuf_mapping.py` により `cmd_id` / `cmd_func` に基づく動的デコードを実現。

## 残存課題・次のステップ

1.  **`get_reply` トピックのメッセージフォーマット検証:**
    - データ取得要求に対する応答が期待される `/app/{USER_ID}/{DEVICE_SN}/thing/property/get_reply` トピックでメッセージを受信した場合の処理について、現状は `_process_get_reply_message` で Base64 デコードと `HeaderMessage` としてのパースを試みている。
    - ioBroker の実装では、このトピックのメッセージペイロード先頭バイトが `0x01` や `0x02` の場合に `setMessage` や `setReply` といった特殊な型でデコードしている部分がある。`0x0a` (Length-delimited field) のケースと合わせ、これらの特殊ケースの検証と対応が必要な場合がある。 (現状のログではこのトピックのメッセージは確認できていないため優先度は低い)
2.  **デコード済みデータの意味解析:**
    - `captured_data.jsonl` に記録された `cmdFunc50_cmdId30_Report` や `cmdFunc32_cmdId2_Report` などのメッセージ内容について、`ioBroker.ecoflow-mqtt/doc/devices/deltapro3.md` と照合し、`unknownX` となっているフィールドの具体的な意味を特定する。
3.  **Protobuf 定義とマッピングの更新:**
    - 上記の解析で意味が特定できたフィールドについて、`ef_dp3_iobroker_pb2.py` (または元の `.proto` ファイル) のフィールド名をより分かりやすいものに修正し、`protobuf_mapping.py` のデコーダーも合わせて更新する。
4.  **Home Assistant Entity へのマッピング検討:**
    - 解析されたデータを Home Assistant のセンサーやスイッチ等にどのように対応付けるかを検討開始する。

## 調査方針・解決策 (実施済み)

1.  **`/app/device/property/{DEVICE_SN}` トピックのメッセージ解析強化:**
    - **Base64 デコード処理の見直し:** 常に試行し、失敗時はフォールバックする形で対応。
    - **Protobuf デコード試行:** `HeaderMessage` -> `Header` の順でデコード試行し、成功。
    - **ioBroker のロジック移植:** `HeaderMessage` -> `Header` -> `pdata` (XOR デコード) -> 各種ステータス用 Protobuf 型へのデコードフローを `message_handler.py` の `_process_header_pdata` 等で再現。`cmdId` と `cmdFunc` に基づく型マッピングは `protobuf_mapping.py` で実現。
2.  **`get_reply` トピックのメッセージ解析:** (一部対応)
    - `message_handler.py` の `_process_get_reply_message` で Base64 デコードと`HeaderMessage`としてのパースを実装。特殊ケースの検証は今後の課題。
3.  **XOR デコード処理の実装と適用:**
    - `message_handler.py` の `_process_header_pdata` 内で、ioBroker の条件 (`enc_type == 1 && src != 32`) に基づき `common.xor_decode_pdata` を適用。
4.  **エラーハンドリングとロギングの全体的強化:**
    - デコード処理の各ステップで詳細なログ出力を行うように改善。
    - `json_format.MessageToDict` の引数問題を修正し、Protobuf デコード結果が正しく JSON に変換されるようになった。
5.  **`ecopacket_pb2.py` (現 `ef_dp3_iobroker_pb2.py`) の再検証:**
    - ioBroker で使われている Protobuf 定義をベースに利用することで、多くのデバイス固有メッセージ型に対応。

## 期待される成果 (達成済み)

- `/app/device/property/{DEVICE_SN}` トピックから受信するメッセージを、高い成功率で正しい Protobuf 型にデコードし、その内容 (デバイスのステータス情報など) を JSON 形式で `captured_data.jsonl` に保存できるようになった。
- これにより、EcoFlow デバイスからの MQTT メッセージを解析し、Home Assistant 連携などの次のステップに進むための基盤が整った。

## 具体的なタスクリスト (更新)

0.  [x] **既存実装の調査:** (完了)
1.  [x] **`/app/device/property/{DEVICE_SN}` トピックメッセージ解析の実装:** (完了)
2.  [ ] **`get_reply` トピックメッセージ解析の実装:** (一部完了、特殊ケース未対応)
    1.  [ ] ioBroker での `get_reply` 処理方法の再調査（特に先頭バイト `0x01`, `0x02`, `0x0a` のケース）。
    2.  [ ] 必要であれば、上記特殊ケースに対応するデコード処理を Python スクリプトに実装。
3.  [x] **XOR デコード処理の適用:** (完了)
4.  [x] **エラーハンドリングとロギングの全体的強化:** (完了)
5.  [x] **Protobuf 定義の検証:** (完了、ioBroker ベースのものを採用)
