# 現在の状況

更新日: 2026-10-11

## 目的と方針

最新upstreamの統合コードを基準にし、開発専用の変更を少数のコミットで管理する。
旧`dev`は保存し、最新`main`から必要な設定・資料・protoコメントを移して`dev`を作り直した。

- Private/App APIのみを使用。Public APIの改修は保留。
  DP3操作系は2026-10-11の明示依頼で、未マージupstream PRを選別して先行取り込みした。
- 開発環境・調査資料・コンテキストは`dev`に置く。
  `main`へ戻す修正は個別に選別し、`dev`全体を一括マージしない。
- 本番HA・実機へ接続しない。開発HAは認証情報なしの最小設定と隔離ネットワークを使う。
- 開発HAの基準は本番と同じリリース版HA Core **2026.10.0**。
- コンテキストは通常のMarkdown。Serena・Cursorの導入やMCP登録は不要。
- push・公開はユーザーの明示的な依頼がある場合のみ行う。

## ブランチと移行内容

- 作業ブランチ: 作り直した`dev`。基点は`main`の`1d7899e`。
  `a8d9b9c`まで`origin/dev`へ公開し、trackingを設定した。
  先行修正`daa5e0b`と今回の文書更新はローカルのみ。
- `main`は`upstream/main`のv1.7.2（`de02d68`）を取り込み済み。
  基点の`1d7899e`はupstreamと同じツリー。現在は`f4cf2fd`で先行修正を個別に移植した。
  upstreamとの差はDP3ソースと回帰テストの2ファイルのみ。今回の更新は未push。
- 旧`dev`は`archive/dev-20261011`（`f786cad`）へ保存した。
  旧HEAD `ccdd092`に、未コミットだったmain追従の記録と今回の計画をコミットした状態。
  `origin/archive/dev-20261011`にも同じ旧履歴を公開して保存した。
- 2026-10-11の明示依頼で`main`と新しい`dev`を`origin`へpushした。
  旧履歴の保存と両枝の更新をatomicで反映し、`dev`だけに旧HEADを指定した
  `--force-with-lease`を使った。両枝と保存用ブランチのリモートHEADを確認済み。
  `main`は`origin/main`を、保存用ブランチは同名のリモート枝を追跡する。
- 旧`dev`と以前の`main`（`f1ca609`）の統合コード差分はprotoコメント1行だけだった。
  新しい`dev`の統合コードは最新`main`を使い、そのコメント変更（元コミット`ccdd092`）を移植した。
- 移行したのは隔離コンテナ・エディター設定・Markdown資料・protoコメント。
  旧実接続スクリプト・ローカルAI設定・旧merge属性は保存用ブランチに残した。
- 未コミット差分・移行元77ファイル・保護対象1,034ファイルのハッシュは
  `.git/codex-backups/dev-refresh-20261011-100952/`に退避した。Git追跡・共有の対象外。

## 開発環境

- [開発手順](../.devcontainer/README.md)を参照する。
- 公式HA 2026.10.0のdigest固定イメージ、専用volume、隔離ネットワークを維持した。
  編集・検証用は既存のDebian Dev Container＋uv、Python 3.14.6。
- コンテナの起動設定・固定済み依存・HA設定を引き継いだ。
  今回はコンテナの起動停止・再作成・依存導入を行っていない。
- `pyproject.toml`・`uv.lock`・CIは最新upstreamのまま。
  upstreamの開発依存はHA 2026.8.0で、隔離コンテナのHA 2026.10.0環境とは別。
  `mise.toml`はupstreamの構成を保ち、Pythonの版だけ配布イメージに合わせた。
- `make check`は既存のコンテナ内Pythonを使う。
  lintの保留ルールはupstreamの`mise.toml`から参照し、ローカル`.venv`を同期しない。
- manifestの版は1.7.2、protobufの範囲は`>=6.32.0,<8`。
  開発HA側の7.36.0との固定版衝突は、最新mainを基点にしたことで解消した。

## 今回の検証

- DP3の先行修正は11件の回帰テストで成功。13操作のProtobuf送信とJSON受信を合成値で確認した。
- smoke成功: Python 93ファイルの構文、生成済みprotobuf 12件の単独ロード、隔離設定と版。
  型検査はupstreamの除外設定で92ソースファイルを確認し成功した。
- 全体lintはGit記録どおりの権限で展開した分離worktreeで成功。
  `/workspace`では既存の空の`__init__.py` 2件の実行ビットによりEXE002が出る。
  Git記録は非実行だが、この環境ではchmodできなかった。詳細は[取り込み記録](../docs/research/upstream_prs_20261011.md)。
- 旧環境で報告したlint 1,855件・型検査4件は、この最新コード・設定では再現しなかった。
  機能コードや検査ルールへ独自の修正を加えて解消したものではない。
- 本番HA・実機・EcoFlowへの接続、HAへの統合セットアップ、VS CodeのReopen操作は今回未検証。
  テストでは統合モジュールのimportのみを行った。
  開発HAへの8123の接続は、コンテナ最適化時にユーザーが確認済み。

## フォークのIssue

- 2026-10-11の明示依頼で未解決Issue全2件を確認した。2件とも未解決として残し、閉じていない。
- #1は取り込み前からID重複がなくなっていたが、報告者はID変更後も未解決と記している。
- #2は13操作をProtobuf送信へ先行修正した。24V出力・AC出力種別の送信は無効で、実機動作は未確認。
  関連upstream #904/#921/#925は確認時点でopen・未マージ。
  根拠は[取り込み前の確認](../docs/research/fork_issues_20261011.md)と[取り込み記録](../docs/research/upstream_prs_20261011.md)。

## 保護対象と資料

- `core/config/`、`scripts/config.json`、`test/test.env`、既存`.venv`、ローカル`.env`を保護する。
  内容を開発設定へ流用せず、認証情報・実機識別子・受信ログの値を出力しない。
- 元の資料整理・環境変更の退避先は
  `.git/codex-backups/context-20261011-151204/`と
  `.git/codex-backups/container-20261011-165104/`。
- [調査索引](../docs/research/README.md)は今回のコードで確認した事実を記す。
  [履歴資料](../docs/research/archive/README.md)は当時の記録で、実行指示や現在の動作保証として使わない。
- 次の作業と移行の詳細は[タスク計画](tasks_plan.md)を参照する。
