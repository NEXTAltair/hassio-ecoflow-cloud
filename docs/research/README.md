# 調査索引

更新日: 2026-10-11。調査再開時は [現在の状況](../../tasks/active_context.md) を先に読む。

この索引は、過去の記録と現コードの読み取り結果をつなぐ。
現コードはupstream v1.7.2を取り込んだ`1d7899e`に、選別した未マージ修正を加えた
`main`の`f4cf2fd`。旧`dev`は`archive/dev-20261011`に保存した。
先行修正をmain/devへpushし、合成入力の回帰テストは実施済み。
実機での機能テストは行っていない。「現コードにある」と「実機で動作する」を区別する。
次の作業は [タスク計画](../../tasks/tasks_plan.md) に記録する。

## 現在の残課題

[残課題と優先順位](current_problems_20261011.md)に、push後の確認結果をまとめた。
操作の成功確認・タイマー症状をP1、未対応2操作・センサー経路・検査入口・
workspace権限・ログ出力をP2として、確認済みの不足と検証待ちを分けている。

## 現コードとの照合

| テーマ | 2026-10-11に確認できたこと | 根拠と未確認事項 |
| --- | --- | --- |
| BMS heartbeat | `BMS_HEARTBEAT_COMMANDS`に`(32, 50)`があり、`DP3BMSHeartBeatReport`のデコード処理もある。 | [現コード](../../custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py)。広い候補集合にある他の組合せや、実機の送信状況は今回未検証。 |
| cycles | protoのfield 14と、`cycles`を参照するセンサー定義がある。 | [proto](../../custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto)。古い「BMS未実装」は現在の説明として使わない。 |
| energy | センサーとprotoのfield 79/80は`accu_chg_energy`/`accu_dsg_energy`で一致し、変換は`preserving_proto_field_name=True`。 | #742を含む最新mainで名称の一致を確認した。受信からセンサーまでの適合と単位は未検証。2025年の「camelCaseで修正済み」を現在の動作保証にしない。 |
| SOH | `StateOfHealthSensorEntity`が`bms_batt_soh`を参照する。BMS heartbeatには`soh`/`real_soh`等もあり、別メッセージには`bms_batt_soh`がある。 | #799は最新mainに含まれる。どの受信メッセージから値を取るかと実機動作は未検証。 |
| デコード・flat化・ログ | DP3独自のデコード、辞書変換、flat化処理があり、#850に加え、#925のJSON判別修正を先行取り込みした。 | JSON誤ログは変更前に再現し、取り込み後の回帰テストで解消した。実値のdumpを旧手順からそのまま実行しない。 |
| Private DP3操作 | #921のProtobuf送信と#904のAC充電範囲を選別して先行取り込みした。13操作に対応し、24V出力とAC出力種別の送信は無効にした。 | [取り込み記録](upstream_prs_20261011.md)。送信テストはモックMQTTで成功。実機での受理・動作は未検証。 |

## テーマ別に読む資料

| 調べたいこと | 過去の記録 | 読むときの注意 |
| --- | --- | --- |
| BMSのcmdFunc/cmdId | [解決策発見](archive/memories/delta_pro_3_bms_heartbeat_solution_found.md) → [再起動時の引き継ぎ](archive/memories/container_rebuild_context_2025_10_15.md) | [古い完全対応表](archive/memories/delta_pro_3_complete_message_mapping.md)の「未確定」と区別する。 |
| cycles/energyの調査経緯 | [調査結果](archive/memories/delta_pro_3_cycles_investigation_results.md) → [BMS実装](archive/memories/delta_pro_3_bms_heartbeat_implementation.md) → [camelCase修正記録](archive/memories/delta_pro_3_energy_sensors_fixed_camelcase.md) | 古い不明状態や当時の動作結果は、現在の実機状態を示さない。 |
| SOH・不明エンティティ | [不明エンティティ](archive/memories/delta_pro_3_unavailable_entities_investigation.md)、[UTF-8修正後の状態](archive/memories/delta_pro_3_entity_status_after_utf8_fix.md) | 当時の観測と現コードのフィールド参照を別々に確認する。 |
| MQTT・XOR・Protobuf | [調査記録](archive/investigations/)、[進行記録](archive/progress/)、[コマンド対応表](archive/memories/delta_pro_3_command_id_mapping.md) | 通信・捕捉の手順は履歴。今回は実接続を行わない。 |
| MessageToDictとflat化 | [複合失敗の分析](archive/investigations/ISSUE_06_delta_pro3_prepare_data_decode_failure.md)、[マッピングとflat化](archive/investigations/issue_07_delta_pro_3_entity_mapping_and_flattening.md) | 旧参照の欠落と、現コードとの変更点に注意する。 |
| UTF-8デコード問題 | [修正レポート](archive/investigations/utf8_decode_error_analysis.md) | 報告時点の修正。今回の動作確認結果ではない。 |
| 旧設計・実装案 | [仕様資料](archive/specifications/)、[旧タスク案](archive/plans/) | 実装済み仕様と提案コードが混在。操作系の案は現在保留。 |
| 旧AIツール運用 | [ツール運用の履歴](archive/tooling/) | 現在の導入手順ではない。Serenaは不要。 |

## Cursor撤去時に残した過去メモ

2025-11-03の記録では、`ef_dp3_iobroker_pb2`と旧`dev_apl_comm`の同時読み込みで
`TIME_TASK_MODE`がdescriptor poolへ重複登録され、エラーになった。
当時はDP3の事前読み込み・トップレベルimportを揃え、`dev_apl_comm`を事前読み込みから外した。
根拠は削除前の`.cursor/rules/error-documentation.mdc`とコミット
`fc3b73d8458b51c4b956873f6573aff5f367e6d2`。

2026-10-11の現コードではDP3の事前読み込み・トップレベルimportは残るが、
`dev_apl_comm`は存在しない。当時の遅延import案や復旧報告は履歴として扱う。
今回、統合全体のロードや実機動作は再検証していない。

## フォークの未解決Issue

[取り込み前の確認記録](fork_issues_20261011.md)で、#1のタイマー設定消失と
#2の操作機能を現コード・upstream PRへ照合した。その後、明示依頼で
[#904/#921/#925を選別して先行取り込み](upstream_prs_20261011.md)した。
症状の解消・実機動作は未確認で、未対応操作も残るため、Issue #1/#2は開いたまま。

## 資料の扱い

- 現在の方針・制約は [AGENTS.md](../../AGENTS.md) と現在の状況へ集約する。
- 新しい調査では、日付・対象コミット・確認方法・結論・未確認事項・根拠を短く記録する。
- 実装やメッセージの正しさは、原資料の宣言だけで確定せず、現コードと検証結果を確認する。
- 過去の本文は [履歴資料](archive/README.md) に保存。資料全体を毎回読み込む必要はない。
- 認証情報・実機識別子・受信データの値を、新しい要約へ転記しない。
