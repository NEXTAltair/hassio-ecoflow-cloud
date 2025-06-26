# EcoFlow Delta Pro3対応タスク分解

## 1. 仕様・現状調査
- [ ] Delta Pro3のMQTT/Protobuf仕様調査
    - 参考: ioBroker.ecoflow-mqtt, GitHub issue #270 など
- [ ] 既存Delta Pro/Delta 2 Maxの定義・構造調査
- [ ] Protobufデコードの既存実装有無調査（proto/ディレクトリ確認）

## 2. 設計
- [ ] Delta Pro3用デバイス定義設計（センサー/スイッチ/スライダー/セレクト項目の洗い出し）
- [ ] Protobufデコード処理設計（.protoファイル作成 or 既存流用）
- [ ] デバイス判定・分岐ロジック設計

## 3. 実装
- [ ] delta_pro3.py新規作成（delta_pro.pyをベースに）
- [ ] Protobufデコード処理の実装
- [ ] Delta Pro3用エンティティ定義の実装
- [ ] デバイス管理ロジックへの登録

## 4. テスト
- [ ] サンプルデータ/実機でのデコードテスト
- [ ] Home Assistant上でのエンティティ表示・操作テスト
- [ ] エラー/例外時の挙動確認

## 5. ドキュメント
- [ ] READMEへのDelta Pro3対応追記
- [ ] 使い方・注意点の記載

---

### 備考
- タスクは進捗に応じて細分化・追加してください。
- Protobuf仕様が不明な場合は、まずサンプルデータ収集・解析から着手。