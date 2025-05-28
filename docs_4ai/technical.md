# 技術仕様書

## 1. 開発環境

## トラブルシューティング

### EcoFlow Delta Pro 3 MQTT スクリプト (`scripts/mqtt_capture_dp3_debug.py`) デバッグログ

#### 2025-05-27: MQTT メッセージ受信とデコードの問題

- **初期症状:** スクリプト実行後、MQTT ブローカーへの接続は成功するものの、期待されるデータメッセージが受信できない。PINGREQ/PINGRESP の交換は確認できる。
- **原因調査と対応:**
  1.  **`ecopacket_pb2.py` の欠落:** 当初、Protobuf 定義ファイル (`ecopacket_pb2.py`) が `scripts` ディレクトリに存在せず、ハートビートメッセージのデコード処理がスキップされていた。
      - **対応:** ユーザーが `ecopacket_pb2.py` を `scripts` ディレクトリに配置し、`protobuf` 依存関係を `requirements.txt` に追加。
  2.  **MQTT ブローカーからの即時切断 (RC: 128):** 以前のログでは、接続直後に `Unspecified error (RC: 128)` で切断される問題が発生していた。
      - **対応:** ユーザーが `uv run` でスクリプトを実行した環境ではこのエラーは発生せず、接続とトピック購読までは成功するようになった。
  3.  **データ取得要求の不足:** `ioBroker.ecoflow-mqtt` の動作を調査した結果、接続後に特定のデータ取得要求メッセージを送信する必要があることが判明。
      - **メッセージ仕様:** ioBroker は `/app/{userID}/{deviceID}/thing/property/get` トピックに対し、`Header` プロトコルバッファ (`src=32, dest=32, seq=timestamp, from='ios' or 'Android'`) を送信していた。
      - **対応:** `on_connect` 関数内で、トピック購読後に同様の `Header` メッセージを送信する処理を追加。
        - `seq` の `ValueError` 修正: `int(time.time() * 1000)` が `int32` の範囲を超えるため、`current_seq & 0xFFFFFFFF` で下位 32 ビットを使用するように修正。
        - `from` フィールドの `AttributeError` / `SyntaxError` 修正: Protobuf フィールド名が Python の予約語 `from` と衝突するため、`setattr(header_payload, "from", "Android")` で値を設定。
  4.  **購読トピックの不足とメッセージの暗号化:** ioBroker のログと比較し、購読すべきトピックが不足していること、および一部メッセージが暗号化 (`encType: 1`) されていることを特定。
      - **対応:**
        - `scripts/config.json` に ioBroker が購読しているトピックテンプレートを追加。
        - `on_message` 関数に、`encType == 1` の場合に AES-128-ECB でペイロードを復号する処理 (`decrypt_payload`) を追加。復号キーは MQTT パスワードの MD5 ハッシュ。
        - `on_message` 関数に、`cmdFunc` と `cmdId` に基づいてペイロードを動的にデコードするロジック (`PROTO_DECODERS` マッピング) を追加。
        - `requirements.txt` に `pycryptodome` を追加。
  5.  **依存関係 `pycrypto` と `pycryptodome` の競合:** `uv run` で実行すると `pycrypto` のビルドエラー (`longintrepr.h: No such file or directory`) が発生。`requirements.txt` には `pycryptodome` が指定されている。
      - **対応:** `pip uninstall pycrypto pycryptodome` で両方をアンインストール後、`pip install pycryptodome` で `pycryptodome` のみを再インストール。`python` コマンドで直接スクリプトを実行することで `Crypto` モジュールの `ModuleNotFoundError` は解消。`uv run` 時のエラーは `uv` の挙動の問題と切り分け。
  6.  **設定更新時の `KeyError`:** `update_config_with_dynamic_values` 関数でトピック文字列をフォーマットする際に `KeyError: 'USER_ID'` および `KeyError: 'DEVICE_SN'` が発生。
      - **原因:** `.format()` メソッドに渡す辞書のキー名と、テンプレート文字列内のプレースホルダー名（大文字・小文字）が不一致。
      - **対応:** `.format(USER_ID=..., DEVICE_SN=...)` のようにキー名をテンプレートに一致させた。
  7.  **`AttributeError: module 'ecopacket_pb2' has no attribute 'Header'` / `setHeader`:** `on_connect` 関数内でデータ取得要求メッセージを送信するために `ecopacket_pb2.Header()` や `ecopacket_pb2.setHeader()` (一時的な修正) を呼び出す箇所でエラー。
      - **原因特定と対応:** `ecopacket_pb2.py` を調査した結果、データ取得要求メッセージは `setMessage` 型でラップされ、その内部の `header` フィールドに `setHeader` 型のオブジェクトを格納する構造が正しいと判断。
        - スクリプト内の `on_connect` 関数および `status_monitor` スレッドで、この構造に従ってメッセージを構築・送信するように修正。
      - **現在の状況:** 上記修正後、ユーザーがスクリプトを実行したところ、ログの途中で処理が停止した。エラー詳細は未確認。

#### 2025-05-27 (以前のログ・サマリ)
