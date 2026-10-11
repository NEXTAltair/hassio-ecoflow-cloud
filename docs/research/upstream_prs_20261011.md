# DP3の未マージupstream PRの先行取り込み

実施日: 2026-10-11。Issue調査後の「未マージの変更を先に取り込む」という明示依頼による。
対象はPrivate/App APIのDP3修正。機能コードと回帰テストを個別コミットとしてmainへ移し、
開発設定・調査資料・コンテキストはdevに置く。

## 取り込み元

確認時点で3件ともopen・未マージ。取得したHEADとAPIの報告するHEADの一致を確認した。

| PR | 確認したHEAD | 採用した内容 |
| --- | --- | --- |
| [#904](https://github.com/tolwi/hassio-ecoflow-cloud/pull/904) | `2d89e06bee16869a1982349f51c9f2d11b0a04ea` | AC充電電力の範囲を400–2900 Wにする。送信は#921の共通実装へまとめる。 |
| [#921](https://github.com/tolwi/hassio-ecoflow-cloud/pull/921) | `70b49a1a30fd7d56ab4385e56f130401b088e587` | 既知の操作をDP3SetCommand＋DP3SendHeaderMsgへ変更する。未対応2操作の送信を止める。 |
| [#925](https://github.com/tolwi/hassio-ecoflow-cloud/pull/925) | `47550409c065444eab4760d6616dc26ecff7742d` | JSONオブジェクトを先に判別して既存JSONパーサーへ渡す。5件の回帰テストを取り込む。 |

## 実装と補正

- number 3件、switch 7件、select 3件の計13操作をProtobuf送信にした。
  共通ヘッダーは`cmd_func=254`/`cmd_id=17`、`src=32`/`dest=2`。
  既存generated schemaを使い、再生成や依存追加は行っていない。
- AC充電電力は#904の範囲修正を採用した。利用環境での範囲・実動作は今回未検証。
- #921の未対応操作はコールバックから`None`を返していた。
  現送信APIはその後に`to_mqtt_payload()`を呼ぶため、そのままでは失敗する。
  コマンド自体を`None`にして、操作してもpublishや目標状態の更新が起きない形へ補正した。
- 24V DC出力とAC出力種別は送信フィールドがschemaにない。
  エンティティ定義は残し、初期状態では無効・非表示にした。既存登録が有効のままでも送信しない。
  12V DC出力、AC HV/LV出力の個別ON/OFFは13操作に含まれる。
- 未知の送信フィールドは`ValueError`を送出し、`None`を送信経路へ渡さない。
- JSON判別は#925のオブジェクト用ガードを採用した。
  前後の空白、オンライン状態、command/replyを保持し、binary/Base64のProtobuf受信も維持した。
- #921の別フォーク向けREADME、HACS表示名、独自manifest版の変更は採用していない。
  mainの差分はDP3ソースと回帰テストの2ファイルだけ。

## コミットと公開状態

- devの機能コミット: `daa5e0bbaa3284c90bb3761a72ba7ca154a4bbb8`。
- mainの個別移植コミット: `f4cf2fd88dc5784378bee3ab362c29d289384f2e`。
  dev全体のmergeは行っていない。取り込み元と著者はコミット本文に記録した。
- 取り込み時点の公開基点はmain `1d7899e`、dev `a8d9b9c`だった。
  続く2026-10-11の明示依頼で、main `f4cf2fd`とdev `d56c231`をatomicで通常pushした。
  両枝のリモートHEADとローカルの一致を確認済み。整理資料はdevの追加文書コミットで公開する。
- 取り込み前の未コミットIssue調査・文書5件・patch・main/dev参照は
  `.git/codex-backups/upstream-prs-20261011-111924/`に保存した。

## 検証

- #925のテストを変更前コードで実行すると、JSONの誤ログに関する8サブケースが失敗した。
  取り込み後は元の5テストがすべて成功した。
- 6テストを追加し、計11テストが成功した。合成値とモックMQTTのみを使った。
  13操作の対象フィールド・ヘッダー・payload長、実送信APIまでのbinary化、
  出力ON/OFFのゼロ値の保持、未対応操作の無送信、AC充電範囲、診断表示、未知フィールドを確認した。
- 既存smokeは成功。Python構文93ファイル、generated protobuf 12件、隔離設定と版を確認した。
- 型検査は92ソースファイルで成功。回帰テストのlintも成功した。
- push後のmainの[Lint workflow](https://github.com/NEXTAltair/hassio-ecoflow-cloud/actions/runs/38137670597)も成功した。
  回帰テスト11件は手動実行で、現在の`make check`とCIには未組み込み。
- mainの分離worktreeで、upstreamの保留ルールを使った全体lintが成功した。
  mainの2ファイルが検証済みdevとbyte単位で一致し、mainの差分に開発資料がないことを確認した。
- `/workspace`では既存の空の`custom_components/__init__.py`と
  `custom_components/ecoflow_cloud/devices/public/__init__.py`に実行ビットがあり、EXE002が出る。
  Git記録は100644だが、この環境ではchmodが許可されなかった。
  分離worktreeでは記録どおりの権限で検査できた。元ファイルの内容・権限は変更していない。

本番HA・実機・EcoFlowへの接続、実MQTT publish、HA再起動、依存導入は行っていない。
テストでは統合モジュールをimportしたが、HAへの統合セットアップは実行していない。

## Issueの扱い

[フォークのIssue確認](fork_issues_20261011.md)は取り込み前の状態を記録する。
#1のタイマー消失は原因・解消とも実機では未確認。
#2は送信経路を修正したが、未対応2操作と実機検証が残るため完了とは判定しない。
Issue #1/#2は開いたままとし、実機検証は別の明示依頼まで行わない。

残る不足・環境問題・検証待ちは[現在の残課題](current_problems_20261011.md)へ整理した。
次の作業は[タスク計画](../../tasks/tasks_plan.md)で管理する。
