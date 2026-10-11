# 現在の状況

更新日: 2026-10-11

## 目的と決定事項

upstream追従の前に、過去の調査・判断・未確認事項を参照しやすくする。
資料整理に続き、ユーザー依頼で`dev`専用のコンテナ設定を最適化した。

- Private/App APIのみを使用。Public APIとDP3操作系の改修は保留。
- コンテキストは通常のMarkdownで管理し、Serena・Cursorは使わない。
- 開発HAは本番と同じHA Core **2026.10.0** を基準とし、自動起動する。
- 開発環境設定はupstreamを基準にする。独自のPython選定やAIツール導入を増やさない。
- 開発環境・調査資料・コンテキストは`dev`に置く。還元用`main`はupstreamとの差分を必要最小限に保つ。
  `dev`全体を`main`へ一括マージせず、本番運用・還元に必要な修正だけを個別に選別して移す。
- 本番HA・実DP3・その他機器へ接続しない。家庭向け設定を流用しない。

## リポジトリと保全対象

- 作業ブランチ: `dev`、tracking: `origin/dev`。監査時HEAD: `d1a5f7a`。
- `origin`: NEXTAltair/hassio-ecoflow-cloud、`upstream`: tolwi/hassio-ecoflow-cloud。
- ユーザーの既存差分: `.cursor/` の11ファイル削除と
  `custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto` のコメント変更。
  Cursorの削除はユーザーが意図した整理として確認済み。今回の資料整理に含める。
  protoのコメント変更は既存ユーザー変更としてそのまま保持する。
- 今回の資料整理・環境設定は、2026-10-11のユーザー依頼により`origin/dev`へ
  コミット・pushする。既存のprotoコメント変更は今回のコミットに含めない。
- `core/config/`、`scripts/config.json`、`test/test.env`、既存`.venv`は保護対象。
  `core/config/`には既存設定・DB・`secrets.yaml`があり、開発設定へ流用しない。
- 元の資料・変更前ファイル・既存差分のローカル退避先:
  `.git/codex-backups/context-20261011-151204/`。これはGit追跡・共有の対象外。

## 今回の確認結果

- 過去の49件のMarkdownを [履歴資料](../docs/research/archive/README.md) に集約。
  古い「現在の作業」「60%完了」などは履歴として保存し、現行計画から外した。
- BMS/cyclesの処理は現コードに存在する。energyのキー名には再確認事項がある。
  詳細は [調査索引](../docs/research/README.md) を参照。
- 実機接続・機能テスト・統合のコード変更・protobuf再生成は行っていない。
- Serenaの自動登録・停止処理とリポジトリ内の設定は削除した。
  既存コンテナ内やユーザー全体のMCP登録・インストールには手を加えていない。
- 削除済みCursorの11ファイルをGit履歴から読み取り確認した。
  大半はツール向け指示・汎用テンプレートで、2025-11-03のprotobuf重複シンボル対策だけを
  [調査索引](../docs/research/README.md)に短く残した。Cursor設定は復元しない。
- 旧ファイルはすべて移行済み。自動実行ポリシーによる削除拒否の後、ユーザーが
  `serena/`・`.serena/`・`docs_4ai/`を削除したことを確認した。
  `tasks/rfc/`は空のまま残っているが、移行漏れはない。

## 開発コンテナの現行構成

- [開発手順](../.devcontainer/README.md): 初回・再オープン、検証、HA起動停止、更新、rollback。
- HAは公式2026.10.0のdigest固定イメージ。編集・検証用はDebian Dev Container＋uv。
  Python 3.14.6は公式HAイメージ内の実測版、開発依存はhash付きlockで固定する。
  同リリースのソース指定は3.14.5なので、配布イメージの実体を優先した。
- HAを専用volume・最小設定・外向き通信のないネットワークで自動起動する。
  編集用コンテナにはGit・拡張・依存更新用の通常ネットワークも用意する。
- `test/test.env`・旧`core/config`・旧`.venv`を使わない。AIの導入は任意。
  起動時のnpm/apt install・MCP登録・広いエラー無視・二重workspace mountは廃止。
- WindowsのCompose BakeがDev Containersの一時Dockerfileを読む際に拒否されたため、
  `initializeCommand`で通常の`docker build`を行い、Composeには作成済みイメージを渡す。
  再オープン時はビルドキャッシュを使い、postCreateは版/smoke、postStartはHA準備待ちのみ。
- `make check`とVS Codeタスクは同じ入口。実機用の旧テストを自動実行しない。
- 変更前の16ファイル・保護対象95ファイルのhash・検証ログ:
  `.git/codex-backups/container-20261011-165104/`。統合コード・既存ユーザー差分は維持する。
- イメージビルド・新規作成・postCreate・postStart・HTTP応答・healthcheckが成功。
  両サービス停止後の通常CLI再オープンでも、同じコンテナIDで復帰し、依存再導入はなかった。
  標準の構成読み取りでも新しいPythonを参照する。旧コンテナは停止状態のまま保持した。
- オフラインsmokeはPython 72ファイルの構文と生成済みprotobuf 6ファイルのロードを確認。
  コンテナ内GitとLinux側ruff/mypyキャッシュも使用可能。
- `make check`はlint 1,855件（うち生成済みprotobuf 1,731件）、型検査4件を報告し失敗する。
  型検査はセンサーの継承と`IntegrationSensor`の引数に関する診断。
  統合コードと検査ルールは変えておらず、旧ツール版での比較は未実施。
  機能側の互換性課題として次段階へ残す。
- 2026-10-11にユーザーがコンテナを起動し、8123の開発HAへの接続を確認した。
  Windowsネイティブ側の環境確認は完了。拡張・開発時の検証はコンテナ内で進める。
  VS Code拡張の導入・動作とVS Code側のReopen操作は個別には未確認。
  統合全体のロード・実接続は未確認。

## 変更前の環境監査と残る機能側の課題

2026-10-11の読み取り監査で確認した内容:

- Windows `docker.exe` の `desktop-linux` contextでDocker Desktopへ接続できた。
- `test/test.env`はコメントのみでGit除外済み。Dev Containers全体の起動完了とは別。
- 資料整理時の監査では既存対象コンテナと`hass`プロセスが稼働していた。
  今回の環境変更前には既存コンテナは停止済み。こちらから起動・停止・再作成は行っていない。
- upstreamのdevcontainerも `dcbr/hass-custom-devcontainer` を指定している。
  配布`latest`のdigestは監査したローカルイメージと一致し、Python 3.13.5／HA 2025.12.4。
  [HA 2026.10.0](https://github.com/home-assistant/core/blob/2026.10.0/pyproject.toml) は
  Python >=3.14.2を要求するため、そのままでは本番同等版にならない。
- upstreamはイメージの版を指定せず、暗黙の`latest`を参照している。
  配布元の[requirements](https://github.com/dcbr/hass-custom-devcontainer/blob/master/requirements.txt)は
  HA 2025.12.4固定、[Dockerfile](https://github.com/dcbr/hass-custom-devcontainer/blob/master/Dockerfile)は
  Python 3.13ベース。[公開ワークフロー](https://github.com/dcbr/hass-custom-devcontainer/blob/master/.github/workflows/build-and-push-image.yml)は手動実行のみ。
  旧版維持を必須とする互換性上の理由は、確認した更新履歴・upstreamのPR #633/#708には記載がない。
  配布更新が追いついていないという見方は推測。専用イメージのsetup/launchが担っていた
  HA環境の作成・最小設定・起動は、新構成のイメージビルドとComposeへ分けた。
- 配布元には2026-04-06作成の[HA 2026.4.1への更新PR #41](https://github.com/dcbr/hass-custom-devcontainer/pull/41)が未マージで残る。
  Dependabotによる提案で、更新保留の理由を説明するコメント・レビューは確認できない。
  upstreamのIssue/PR本文・コメントを`devcontainer`、`dev container`、`dcbr`、Python版等で検索した範囲では、
  古いイメージを継続指定する理由を問う議論は見つからなかった。公開議論がないことの断定ではない。
- [upstreamの依存定義](https://github.com/tolwi/hassio-ecoflow-cloud/blob/de02d680cdfe1adcec60c43047ff3ed3da15e0ee/pyproject.toml)
  はHA 2026.8.0固定。upstream基準への復帰と本番同等版への一致を別々に確認する必要がある。
- upstreamの[mise.toml](https://github.com/tolwi/hassio-ecoflow-cloud/blob/de02d680cdfe1adcec60c43047ff3ed3da15e0ee/mise.toml)は
  Python 3.14・uv・`.venv`を使い、CIも`mise run lint`を実行する。イメージ内のHA用venvとは別の検証導線。
  [開発手順](https://github.com/tolwi/hassio-ecoflow-cloud/blob/de02d680cdfe1adcec60c43047ff3ed3da15e0ee/docs/Contribution.md)にある
  `Reset homeassistant`タスクや`Home Assistant`デバッグ設定は、現upstreamのVS Code設定には存在しない。
- 公開された検証例は[PR #812](https://github.com/tolwi/hassio-ecoflow-cloud/pull/812)のDev Container（版・イメージ不明）と、
  [PR #879](https://github.com/tolwi/hassio-ecoflow-cloud/pull/879)のHA 2026.8.1／HAOS 18.2。
  後者は手元で`uv sync`が`Python.h`不足により失敗し、型検査を限定して実行したと明記する。
  これらは個別の利用者報告であり、開発者全体の運用やイメージ差し替えの有無は確定できない。
- 既存`.venv`はLinux用Python 3.13.3／protobuf 6.31.1で、コンテナ内のHA用環境とは別。
  変更前のVS Codeには`.venv`と`/workspace/venv`の参照が混在していた。
  現在のコンテナ用参照は`/home/vscode/.local/ha-venv`に統一した。旧`.venv`は保持する。
- 現manifest/requirementsの`protobuf==6.32.0`固定とHA 2026.10.0の衝突は、次段階のupstream追従で扱う。
  upstreamでは[#928](https://github.com/tolwi/hassio-ecoflow-cloud/issues/928)でHA側の`protobuf==7.36.0`との競合が報告され、
  [v1.7.2](https://github.com/tolwi/hassio-ecoflow-cloud/releases/tag/v1.7.2)で`>=6.32.0,<8`へ修正された。
  #928のコメントにはHA Core 2026.10.0での復旧報告もある。これは利用者報告で、当フォークの動作確認ではない。

## 次に読む資料

1. [調査索引](../docs/research/README.md): 現コードで確認した内容、過去の根拠、未確認事項。
2. [タスク計画](tasks_plan.md): 環境のupstream標準化と受信側の追従候補。
3. [履歴資料](../docs/research/archive/README.md): 必要なテーマだけを参照する。
