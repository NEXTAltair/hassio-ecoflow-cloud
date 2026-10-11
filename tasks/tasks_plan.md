# 次の作業

更新日: 2026-10-11

[現在の状況](active_context.md) と [調査索引](../docs/research/README.md) を前提にする。
旧DP3実装計画の進捗率・期限は [履歴](../docs/research/archive/context/tasks_plan.md) に保存した。

## 今回の資料整理

- [x] 元資料49件を退避して履歴資料へ集約する。
- [x] 現在の方針・調査索引・次の作業を通常のMarkdownへ整理する。
- [x] 過去のBMS/cycles/energy/SOH記録を現コードと突き合わせる。
- [x] Serenaの自動登録・プロセス停止処理を開発スクリプトから外す。
- [x] 移行内容・リンク・既存差分の保全を確認し、旧Serenaのファイルを削除する。
- [x] ユーザーによる`serena/`・`.serena/`・`docs_4ai/`の削除を確認する。
  `tasks/rfc/`は空のまま残っている。資料の移行漏れはなく、今回のSerena撤去は完了。
- [x] ユーザーが削除したCursorの11ファイルを確認する。
  汎用指示・旧ツール設定は移植せず、protobuf重複シンボル対策の履歴だけを調査索引へ残す。

## 今回: dev専用コンテナの最適化

- [x] upstreamのdevcontainer・VS Code・依存定義を基準に、フォーク独自設定を見直す。
  新たなAIツール導入や独自のPython管理を追加しない。
- [x] 配布コンテナとHA Core 2026.10.0の不一致を解決する。
  現在の配布latestはPython 3.13.5／HA 2025.12.4、upstream依存定義はHA 2026.8.0。
  devではHA公式2026.10.0を使い、検証用Pythonを配布イメージの実測版3.14.6へ合わせる。
- [x] 認証情報なしの隔離設定と専用volumeを用意する。
  env-file・EcoFlow自動設定を使わず、HAだけを外向き通信のないネットワークへ置く。
- [x] コンテナ作成、postCreate、postStart、HA準備完了、停止後の再オープンをCLIで個別に確認する。
  両サービスのID・volumeを再利用し、依存再導入なし。
- [x] lint・型検査・接続不要の検証を、採用環境の同じPythonで実行する。
  現在の入口は `ruff check custom_components` と `mypy custom_components`。
  `make check`とVS Codeタスクに統一。smoke成功、lint 1,855件・型検査4件を課題として記録。
  機能コードは変更せず、既存ユーザー差分・保護対象95ファイルの内容を維持する。
  テスト全体の一括実行は、実接続スクリプトを含めない範囲を確認してから行う。
- [x] コンテナを起動し、8123の開発HAへ接続できることを確認する。
  2026-10-11にユーザーが確認済み。
- [ ] 必要時にVS Code拡張の導入・動作を確認する。
  コンテナ内で進める。Windowsネイティブ側の環境確認は完了。
  拡張とVS Code側のReopen操作は個別には未確認。HA接続の確認結果は上記に記録済み。
- [ ] 次段階で型検査4件のHA互換性を確認する。lintは生成物の扱いとルール範囲をupstreamと照合する。

今回の資料整理・環境設定は、2026-10-11のユーザー依頼により`origin/dev`へ
コミット・pushする。既存のprotoコメント変更は今回のコミットに含めない。

## 次段階: upstream追従

開発環境・調査資料・コンテキストの変更は`dev`に残す。
還元用`main`はupstreamに近い状態を保ち、必要な修正だけを個別に選別して移す。
`dev`全体を`main`へ一括マージしない。

以下はユーザーから引き継いだ候補。現在のコード・変更内容・適用要否は次段階で再確認する。
この資料整理ではmerge/rebase/cherry-pickを行っていない。

- [ ] protobuf固定とHA 2026.10.0の衝突を解消する（upstream v1.7.2の範囲指定が候補）。
- [ ] [#742](https://github.com/tolwi/hassio-ecoflow-cloud/pull/742): PV/energyキー。
- [ ] [#799](https://github.com/tolwi/hassio-ecoflow-cloud/pull/799): SOH。
- [ ] [#850](https://github.com/tolwi/hassio-ecoflow-cloud/pull/850)・
  [#925](https://github.com/tolwi/hassio-ecoflow-cloud/pull/925): ログ。

## 保留

- DP3操作系の新規実装・改修、制御関連#904/#921。
- Public APIの対応・遅延対策。
- protobuf再生成、本番HA・実機への接続。

欠落している `mock_protobuf_data` を参照する旧テストや、保存データを出力する研究スクリプトは
そのまま検証入口に採用しない。必要性と匿名化した入力を確認してから扱う。
