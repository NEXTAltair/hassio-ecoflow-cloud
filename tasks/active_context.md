# アクティブコンテキスト

## 現在の作業状況

### 作業フェーズ
**Delta Pro 3 対応実装 - エンティティ定義フェーズ**

### 現在のフォーカス
- Delta Pro 3 デバイスの Home Assistant エンティティ定義実装
- Protocol Buffers メッセージとエンティティのマッピング
- センサー、スイッチ、ナンバー、セレクトの各エンティティタイプの実装

### 最近の変更
1. **ドキュメント構造整理** (2025-10-08)
   - serena/ ディレクトリを新規作成し、調査記録と進行記録を分離
   - tasks/issues/ → serena/investigations/ へ移動
   - 完了済み調査タスクを serena/progress/ へアーカイブ

2. **ブランチ戦略の確立** (前回セッション)
   - main: upstream 同期 + 最小限の DeltaPro3 対応のみ
   - dev: 開発作業、AI アシスタント設定、開発ツール全般

### 次のステップ
1. Delta Pro 3 エンティティ定義の完成 (tasks/rfc/09_DP3_エンティティ定義実装タスク.md)
2. コマンド送信機能の実装 (tasks/rfc/10_DP3_コマンド送信実装タスク.md)
3. Home Assistant 統合テスト (tasks/rfc/12_DP3_Home Assistant統合テストタスク.md)

### 技術的な決定事項
- **MQTT プロトコル**: EcoFlow 独自の XOR エンコーディング + Protocol Buffers
- **エンティティマッピング**: Protobuf メッセージフィールドを Home Assistant エンティティに直接マッピング
- **データフラット化**: ネストされた Protobuf 構造を単一階層のエンティティに展開

### 既知の課題
- MQTT 認証フローの詳細が一部不明 (tasks/rfc/11_MQTT_Authentication_Flow.md 参照)
- 一部のエンティティで単位変換が必要 (mV → V, mA → A など)

### ブロッカー
現在なし

### 参照ドキュメント
- [製品要求仕様書](../docs_4ai/product_requirement_docs.md)
- [技術仕様書](../docs_4ai/technical.md)
- [アーキテクチャ設計](../docs_4ai/architecture.md)
- [エンティティ仕様](../docs_4ai/dp3_entity_specification.md)
- [cmdId/cmdFunc マッピング](../docs_4ai/cmd_id_func_mapping.md)
