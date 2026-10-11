# 現在の残課題と優先順位

確認日: 2026-10-11。先行修正のpush後に、Private/App APIの現コード、
フォークの未解決Issue、関連upstream PR、検証入口を確認した。
以下の「確認済み」はコード・環境で確認できた事項。「検証待ち」は不具合の発生を断定しない。
P1は操作の信頼性と既報症状、P2は未対応機能・検証・開発環境を優先して扱う。

## 公開と検証の状態

- `origin/main`: `f4cf2fd88dc5784378bee3ab362c29d289384f2e`。
  upstream v1.7.2との差はDP3ソースと回帰テストの2ファイルのみ。
- `origin/dev`: 先行修正と取り込み記録を含む`d56c231`までmainとatomicで通常pushした。
  ローカルとの一致を確認した。この整理記録はdevの追加文書コミットとして公開する。
- 旧devの`origin/archive/dev-20261011`は保存済み。今回のpushで履歴の書き換えは行っていない。
- mainの[Lint workflow](https://github.com/NEXTAltair/hassio-ecoflow-cloud/actions/runs/38137670597)は成功。
  devの`d56c231`に対応するActions実行は確認時点で0件。
  hassfest/HACS validationの成功を今回の確認結果に含めない。
- 取り込み時のオフライン回帰テスト11件、smoke、92ファイルの型検査は成功した。
  全体lintは分離worktreeで成功したが、現在のworkspaceには下表の権限問題が残る。
  詳細は[取り込み記録](upstream_prs_20261011.md)を参照する。
- GitHub上のIssueは#1/#2の2件ともopen。関連upstream #904/#921/#925もopen・未マージのまま。
  本番への適用・実機動作は未確認で、今回接続や操作は行っていない。

## 残課題

| 優先度 | 課題 | 現在の判断と根拠 | 次に確認すること |
| --- | --- | --- | --- |
| P1 | 操作の成功確認・失敗時の扱い（#2） | **処理の不足を確認、実機動作は検証待ち。** 13操作はProtobuf化済みだが、APIはpublish前に目標状態を更新する。MQTT送信層は結果を呼び出し元へ返さず、DP3SetReplyの成功フラグを操作結果として扱う専用処理もない。画面の変化だけでは受理を確認できない。 | 合成した成功・拒否・無応答・送信失敗で、ACKと後続テレメトリーから状態がどう更新されるかを整理する。利用環境での受理・動作は別途の検証対象。 |
| P1 | タイマー設定消失（#1） | **過去の報告、現版での再発は未確認。** 旧ID重複は取り込み前から存在せず、報告者はID変更でも未解決と記している。今回のProtobuf化で症状が解消した根拠はない。 | タイマーの送信フィールドと受信側の状態更新を合成入力で追う。実機での再発確認が得られるまで解決扱いにしない。 |
| P2 | 24V DC出力・AC出力種別 | **未対応を確認。** 既知のDP3SetCommand schemaに対応フィールドがなく、送信コールバックは無効。既存エンティティを有効にしても操作は送信されない。AC HV/LVの個別ON/OFFと12V出力は対応済み。 | 必要な操作かを切り分け、送信形式の信頼できる根拠が得られるまで保留。推測したフィールド番号で実装しない。 |
| P2 | energy・SOH・cyclesの受信から表示まで | **対応コードあり、経路と単位の検証待ち。** センサー定義とprotoはあるが、BMS候補の広い集合・未知通知のfallback・SOHの別メッセージ参照が残る。現在の11テストは各センサーへの値の到達や単位を網羅しない。 | 合成Protobufからデコード、flat化、data holder、センサー値・単位までを検証する。実機の値が現在欠落しているとは断定しない。 |
| P2 | 回帰テストの自動実行 | **検査入口の不足を確認。** 11テストは手動実行のみ。`make check`はsmoke・lint・型検査、upstreamのLint CIはcustom_componentsのlint・型検査で、今回追加したtestsを実行しない。 | 既存の検証入口とCIにオフライン回帰テストを組み込む方法を整理する。独自のツールチェーンや依存を増やさない。 |
| P2 | workspaceのlint失敗 | **環境の問題を確認。** 空の`__init__.py` 2件が実権限777/root所有、Git記録は100644。EXE002が出てworkspaceの`make check`は成功しない。この環境でchmodは許可されなかった。 | 所有権・実行ビットを適切に直せる環境で修正する。機能コードやlint除外で隠さない。分離worktreeでのlint成功と区別する。 |
| P2 | ログに識別情報・データが含まれる | **出力箇所をコードで確認。** MQTT接続と認証処理にはアカウント名・client IDのINFOログ、DP3には受信値や一部raw bytesのDEBUGログ、送信例外にはtopic・payloadのログがある。実際の漏えいや現ログの内容は調査していない。 | 値を含めずに診断できるログへ整理し、共有するログ・診断データの匿名化範囲を確認する。実ログの取得・転載は行わない。 |

## 根拠

- 操作と状態: [API送信処理](../../custom_components/ecoflow_cloud/api/__init__.py)、
  [MQTT publish](../../custom_components/ecoflow_cloud/api/ecoflow_mqtt.py)、
  [data holder](../../custom_components/ecoflow_cloud/devices/data_holder.py)、
  [DP3デコード・set_reply](../../custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py)、
  [DP3SetCommand/DP3SetReply schema](../../custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto)。
- Issue: [#1](https://github.com/NEXTAltair/hassio-ecoflow-cloud/issues/1)、
  [ID変更後も未解決とするコメント](https://github.com/NEXTAltair/hassio-ecoflow-cloud/issues/1#issuecomment-3021448324)、
  [#2](https://github.com/NEXTAltair/hassio-ecoflow-cloud/issues/2)。
  [取り込み前の調査](fork_issues_20261011.md)は当時のコードの記録として扱う。
- センサー: [DP3の定義](../../custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py)、
  [センサー実装](../../custom_components/ecoflow_cloud/sensor.py)。
- 検証入口: [回帰テスト](../../tests/test_delta_pro_3.py)、
  [dev検証スクリプト](../../.devcontainer/dev.sh)、[Makefile](../../Makefile)、
  [upstream基準のmise](../../mise.toml)、[Lint CI](../../.github/workflows/lint.yaml)。
- workspaceの権限: `custom_components/__init__.py`と
  `custom_components/ecoflow_cloud/devices/public/__init__.py`をstatとGit indexで照合した。
- ログ: [認証処理](../../custom_components/ecoflow_cloud/api/__init__.py)、
  [MQTT送信層](../../custom_components/ecoflow_cloud/api/ecoflow_mqtt.py)、
  [DP3受信処理](../../custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py)。
  実際の認証情報・実機識別子・受信値はこの記録に含めない。

## 今回修正済みとして区別する事項

- 13操作のJSON送信はProtobufへ変更し、AC充電範囲は400–2900 Wにした。
- 未対応操作の`None`送信による例外・誤った目標状態更新を避けた。
- JSON受信でProtobufの誤エラーが出る問題は変更前に再現し、修正後の回帰テストで解消した。
- energyのfield名とSOHのセンサー追加は最新upstreamに含まれる。
  BMS heartbeatのデコードも存在し、過去資料の「未実装」を現状として扱わない。
- 旧環境のlint 1,855件・型検査4件は今回のコードと設定では再現しなかった。
  workspaceのEXE002 2件とは別の記録。

上記はコード・オフライン検証の結果であり、利用環境での動作保証やIssueの解決確認ではない。
Issue #1/#2は両方残す。本文・タイトル・ラベル・コメントは変更していない。

## 次の作業の順序

1. workspaceのファイル権限を直せる条件を確認し、回帰テストを通常の検証へ組み込む。
2. 合成データでACK・送信失敗・後続テレメトリーを追い、#1/#2の状態更新経路を検証する。
3. energy・SOH・cyclesのセンサーまでの経路を検証し、ログの匿名化が必要な箇所を整理する。
4. 未対応2操作と実機での受理・タイマー再発の確認は、必要性と別途の実機操作許可がある場合に扱う。

Public APIの独自改修、protobuf再生成、本番HA・実機への接続は保留。
upstreamの開発依存HA 2026.8.0と隔離HA 2026.10.0の違い、VS Code Reopen、
HAへの統合セットアップは未検証事項として残し、現在の不具合とは断定しない。
作業のチェックリストは[タスク計画](../../tasks/tasks_plan.md)で管理する。
