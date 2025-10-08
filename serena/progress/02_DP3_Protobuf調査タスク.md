# DP3 Protobuf関連 調査タスク

## 1. `proto/` ディレクトリ内の既存Protobuf定義ファイルの確認

*   **タスク:** `custom_components/ecoflow_cloud/devices/internal/proto/` ディレクトリ内に存在する `.proto` ファイルをリストアップし、それぞれのファイルがどのデバイスや機能に関連するものかを特定する。
    *   ファイル名から推測できる情報を記録する。
    *   ファイル内のメッセージ定義やサービス定義を簡単に確認し、用途を推測する。
*   **成果物:** `custom_components/ecoflow_cloud/devices/internal/proto/` ディレクトリ内に以下の `.proto` ファイルが確認された。
    *   **`powerstream.proto`:**
        *   **概要:** EcoFlow PowerStreamマイクロインバータの動作状態（ハートビート）、設定値、電力関連データなどを送受信するためのメッセージ型を定義。
        *   **主なメッセージ:** `InverterHeartbeat`, `PermanentWattsPack`, `SupplyPriorityPack`, `BatLowerPack`, `BatUpperPack`, `PowerItem`, `PowerPack`, `MeshChildNodeInfo` など。
        *   **用途推測:** PowerStreamマイクロインバータの監視・制御、電力データの時系列収集、メッシュネットワーク管理。
    *   **`platform.proto`:**
        *   **概要:** EcoFlowデバイスのプラットフォームレベルで共通的に利用される可能性のあるデータ構造やコマンドIDを定義。エネルギー関連統計、イベントログ、製品名設定、RTC設定など。
        *   **主なメッセージ・列挙型:** `EnergyItem`, `EnergyTotalReport`, `EventRecordItem`, `ProductNameSet`, `RTCTimeSet`, `PlCmdSets`, `PlCmdId` など。
        *   **用途推測:** デバイス共通の基本的な情報管理、統計データ送受信、時刻同期、コマンド種別定義。
    *   **`ecopacket.proto`:**
        *   **概要:** EcoFlowデバイス間の通信で使われるパケットのヘッダー構造を定義。送信元・宛先、コマンド種別、データ長、シーケンス番号、製品ID、バージョン情報などを含む。
        *   **主なメッセージ:** `Header`, `SendHeaderMsg`, `SendMsgHart`。
        *   **用途推測:** 異なる種類のデータ（例: PowerStreamのハートビート、Platformのエネルギーレポート）を統一的なパケット構造で送受信するための共通通信パケットフォーマット。`Header`が実際のデータ(`pdata`)をカプセル化する。

## 2. 既存コードでのProtobuf利用状況調査

*   **タスク:** プロジェクト全体（特に `custom_components/ecoflow_cloud/devices/internal/` ディレクトリ以下）で、上記で特定した `.proto` ファイルから生成されたPythonコード（通常 `_pb2.py` という接尾辞を持つ）がどのようにインポートされ、利用されているかを検索する。
    *   どのデバイスのデータ送受信処理で利用されているか。
    *   Protobufメッセージのエンコード・デコード処理が具体的にどのように実装されているか（例: `ParseFromString`, `SerializeToString` の使用箇所）。
    *   エラーハンドリングやバージョニング（もしあれば）の有無。
*   **成果物:** Protobuf生成コードの利用は、主に `custom_components/ecoflow_cloud/devices/internal/powerstream.py` ファイル内で確認された。`platform_pb2.py` の直接的な利用は限定的（自身の初期化コードのみ）。
    *   **利用デバイス:** EcoFlow PowerStream マイクロインバータ (`PowerStream` クラス)。
    *   **エンコード・デコード処理:**
        *   **デコード:** `powerstream.py` の `_prepare_data(self, raw_data)` メソッド内で実行される。
            1.  受信したバイト列 (`raw_data`) を `ecopacket_pb2.SendHeaderMsg().ParseFromString()` でパースし、共通ヘッダー情報を取得。
            2.  ヘッダー内の `cmd_id` が `1` (ハートビートと想定) の場合、ヘッダー内のペイロード (`packet.msg.pdata`) を `powerstream_pb2.InverterHeartbeat().ParseFromString()` でパースし、PowerStreamの状態情報を取得。
            3.  パースされた `InverterHeartbeat` オブジェクトの各フィールドの値が、Home Assistantエンティティで利用される内部データ構造（辞書形式の `raw["params"]`）に格納される。フィールドの存在確認には `HasField()` を使用。
        *   **エンコード:** `powerstream.py` 内には、現時点でProtobufメッセージを構築し `SerializeToString()` で送信データを作成するような明示的なエンコード処理は見当たらない。コマンド送信処理（`numbers`, `switches`, `selects` メソッド内の `lambda`）はコメントアウトされているか空であり、Protobufを利用したコマンド送信は未実装または別方式の可能性がある。
    *   **エラーハンドリングとバージョニング:**
        *   **エラーハンドリング:** `_prepare_data` メソッド全体が `try...except` で保護され、パースエラー発生時はログに記録される。また、未知の `cmd_id` を受信した場合もログ出力される。
        *   **バージョニング:** `ecopacket.Header` にバージョン関連フィールド (`version`, `payload_ver`) が存在するものの、`powerstream.py` 内でこれらのバージョン情報に基づいて処理を分岐するロジックは確認できなかった。

## 3. DP3におけるProtobuf利用の可能性検討

*   **タスク:**
    *   既存のProtobuf定義がDP3に流用可能か、あるいはDP3用に新たなProtobuf定義が必要になるかを検討する。
    *   もしDP3がProtobuf通信を行う場合、どのような情報（バッテリー状態、電力情報、制御コマンドなど）がProtobufメッセージとして交換される可能性があるかを推測する。
    *   （もし入手可能であれば）DP3の通信仕様に関する情報（ドキュメント、API仕様、キャプチャデータなど）と照らし合わせる。
*   **成果物:** DP3におけるProtobuf利用に関する考察、および交換される可能性のある情報（メッセージ候補）は以下の通り。
    *   **既存Protobuf定義のDP3への流用可能性:**
        *   **`ecopacket.proto` (共通通信ヘッダー): 流用可能性 高。** 製品IDやバージョンフィールドでDP3を識別することで対応可能と推測。
        *   **`platform.proto` (共通プラットフォーム機能): 流用可能性 中～高。** エネルギー統計、イベントログ、時刻同期等の基本構造は流用できる可能性があるが、DP3特有の項目追加やコマンドIDの新規割り当てが必要と推測。
        *   **`powerstream.proto` (PowerStream特化機能): 流用可能性 低～中。** PowerStreamとは製品カテゴリが異なるため全体的な流用は困難。ただし、バッテリーパラメータやエラーコードの扱いなど、部分的な概念は参考になる可能性あり。

    *   **DP3がProtobuf通信を行う場合に交換される可能性のある情報（メッセージ候補の推測）:**
        *   **基本状態・ハートビート情報 (DP3専用メッセージ):**
            *   バッテリー関連: SOC (メイン/拡張)、電圧 (全体/セル)、電流、温度 (全体/セル)、SOH、サイクル数、充放電残時間、容量情報、BMSエラー/警告コード。
            *   インバータ/出力関連: AC出力電力・電圧・周波数 (総計/ポート毎)、DC出力電力 (各ポート)、X-Boost状態、インバータ温度、インバータエラー/警告コード。
            *   入力関連: AC入力電力・電圧、ソーラー入力電力・電圧・電流 (MPPT毎)、カーチャージ入力電力。
            *   デバイス全体: 総入出力電力、動作モード、EPSモード状態、ファン状態、LED輝度、デバイス温度、FWバージョン、SN、ネットワーク状態。
        *   **設定コマンド・応答 (DP3専用メッセージ / `platform.proto`拡張):**
            *   充電上限/下限SOC、AC充電電流/電力、AC/DC出力ポートON/OFF、X-Boost ON/OFF、ユニット/スクリーンタイムアウト、ビープ音ON/OFF、LED輝度、AC常時出力、EPSモード設定、ソーラー充電モード設定、FWアップデート関連。
        *   **統計情報 (`platform.proto` `EnergyItem`拡張 / DP3専用メッセージ):**
            *   日次/月次/総計の各種エネルギー量 (ソーラー発電、AC充放電、DC放電など)。
        *   **イベントログ (`platform.proto` `EventRecordItem`拡張 / DP3専用メッセージ):**
            *   各種保護機能作動ログ、過負荷ログ、FWアップデート/設定変更履歴。

    *   **DP3通信仕様に関する情報との照らし合わせ:**
        *   現時点ではDP3の具体的な通信仕様は不明なため、上記は既存情報からの類推。
        *   今後、DP3のMQTTトピック構造やJSONデータ、あるいはキャプチャデータ等が入手できれば、Protobufで通信されるフィールドの特定やメッセージ構造の精度向上が期待できる。

## 4. Protobuf関連ライブラリ・ツールの確認

*   **タスク:**
    *   プロジェクトが依存しているProtobuf関連のPythonライブラリ（例: `protobuf`）のバージョンを確認する。
    *   `.proto` ファイルからPythonコードを生成するためのプロトコルコンパイラ (`protoc`) のバージョンや利用方法（もしプロジェクト内に手順があれば）を確認する。
*   **成果物:**
    *   **Protobuf Pythonライブラリ:**
        *   `requirements.txt` に `protobuf==5.27.0` の記述があり、このバージョンが利用されている。
    *   **プロトコルコンパイラ (`protoc`) およびコード生成手順:**
        *   `README.md`, `docs/Contribution.md`, `devcontainer.json`, `core/Dockerfile.dev` を確認したが、`protoc` の具体的なバージョン、インストール手順、または `.proto` ファイルからPythonコード (`_pb2.py`) を生成するためのコマンド例やスクリプトに関する明確な情報は記載されていなかった。
        *   Dev Container環境が利用されているが、`protoc` のセットアップがそのプロセスに自動的に組み込まれているかは不明。
        *   `custom_components/ecoflow_cloud/devices/internal/proto/` ディレクトリ内に `_pb2.py` ファイルがリポジトリにコミットされている。これは、開発者がローカルで `protoc` を実行して生成したファイルをコミットしているか、CI等で自動生成されている可能性を示唆するが、具体的な手順は現時点では不明。

## 5. まとめと次のステップ

*   **タスク:** 上記調査結果を総括し、DP3のProtobuf対応を進める上での課題、不明点、推奨されるアプローチをまとめる。
*   **成果物:**
    *   **調査サマリー:**
        *   **Protobuf定義ファイル:** `custom_components/ecoflow_cloud/devices/internal/proto/` に `powerstream.proto`, `platform.proto`, `ecopacket.proto` が存在。それぞれPowerStream特化、プラットフォーム共通、共通通信ヘッダーを定義していると推測される。
        *   **既存利用状況:** 主にPowerStreamデバイスの受信データデコード処理 (`powerstream.py` の `_prepare_data` メソッド) に限定。`ecopacket` でカプセル化された `powerstream.InverterHeartbeat` をデコード。エンコード処理やコマンド送信での利用は現状なし。
        *   **DP3への流用可能性:** `ecopacket.proto` は流用性が高い。`platform.proto` はDP3向け拡張が必要。`powerstream.proto` の直接流用は困難だが設計思想は参考になる可能性あり。
        *   **DP3での想定情報:** バッテリー状態、入出力情報、設定コマンドなどがProtobufで交換される可能性を推測。
        *   **ライブラリ・ツール:** Python `protobuf==5.27.0` を利用。`protoc` のバージョンやコード生成手順はプロジェクト内に明確な情報なし。

    *   **DP3 Protobuf対応の具体的な次のアクションアイテム:**
        1.  **DP3通信仕様の入手・解析 (最優先):**
            *   DP3がProtobuf通信を行うか、その場合のメッセージ定義 (`.proto`) を特定する。
            *   メーカー資料の入手、または実機からの通信キャプチャ・解析 (MQTTデータ内のBase64エンコードされたProtobufメッセージ等に注意) を行う。
        2.  **`protoc` 利用方法の確立:**
            *   DP3対応で `.proto` ファイルの新規作成・編集が必要な場合、`protoc` でPythonコードを生成する手順を明確化する。
            *   推奨バージョン特定、開発環境への導入、コード生成コマンドの標準化とドキュメント化を行う。
        3.  **DP3用Protobufメッセージ定義の作成/拡張:**
            *   DP3通信仕様に基づき、新規 `.proto` 作成または既存定義 (`platform.proto` 等) を拡張する。
        4.  **DP3デバイスクラスへのProtobuf処理実装:**
            *   受信データデコード処理 (`_prepare_data` メソッド) を実装。
            *   コマンド送信時のエンコード処理を実装。
            *   エラーハンドリング、バージョニング対応を検討・実装。
        5.  **テスト実施:**
            *   Protobufエンコード/デコードの単体テスト。
            *   実機またはシミュレータを用いた結合テスト。

---

### 備考
- 各タスクは進捗や新たな発見に応じてさらに細分化・追記してください。
- 実装・設計・ドキュメント化の各フェーズで本タスクを参照・更新すること。