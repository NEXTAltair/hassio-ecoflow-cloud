# フォークの未解決Issueの確認

確認日: 2026-10-11。
対象: `NEXTAltair/hassio-ecoflow-cloud`の未解決Issue全2件。
基点: `main`の`1d7899e`と`dev`の`a8d9b9c`。統合コードの差はprotoコメント1行のみ。
判断: 2件とも未解決として残す。不要・対応済みと確定できるIssueはなく、閉じていない。

以下は先行取り込み前の調査記録。後続の明示依頼で#904/#921/#925の必要な修正を
main/devへ選別して取り込んだ。[取り込み記録](upstream_prs_20261011.md)を現在の状況として参照する。
未対応操作と実機での解決確認が残るため、Issue #1/#2は引き続き開いている。

## #1: タイマー設定消失

[Issue #1](https://github.com/NEXTAltair/hassio-ecoflow-cloud/issues/1)の本文は、
AC Standby TimeoutとAC Output Typeの`params.id`が153で重複することを原因としている。
現コードではそれぞれ10と59になっており、この重複は存在しない。
このIDの組合せはmainに含まれるupstream #595の実装でも確認できる。

一方、[報告者のコメント](https://github.com/NEXTAltair/hassio-ecoflow-cloud/issues/1#issuecomment-3021448324)は、
IDを変更した[b2d11d7](https://github.com/NEXTAltair/hassio-ecoflow-cloud/commit/b2d11d702e26c319f366bc83ac65bfa1eebfe449)
では解決せず、原因の再調査が必要と記している。
タイマー設定消失という症状の解消は確認できないため、対応済みとして閉じない。
元の原因説明と、未解決の症状を区別する。

- 現コード: [DP3のselect定義](../../custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py)。
- 残る確認: 現版での再発有無と、タイマー設定が変化する経路。実機には接続していない。
- #2の送信形式の問題との因果関係は未確認。重複Issueとも断定しない。

## #2: 操作エンティティの実装・安定化

[Issue #2](https://github.com/NEXTAltair/hassio-ecoflow-cloud/issues/2)は、
DP3の出力操作などをHA自動化で利用できる信頼性まで実装・検証する要求。
現在のPrivate/App API版にはnumber 3件、switch 8件、select 4件の操作定義がある。
すべてJSON/TCP形式の辞書を作り、[送信API](../../custom_components/ecoflow_cloud/api/__init__.py)
は辞書を[JSONMessage](../../custom_components/ecoflow_cloud/api/message.py)に変換して送信する。
DP3用Protobufコマンドの送信クラス・組み立て処理は現在のDP3実装にない。

送信APIはMQTT publishの前に目標値をローカル状態へ反映する。
そのため、HA上の値が一度変わることだけでは実機が設定を受け入れたと確認できない。
これはコード上の挙動であり、現ユーザー環境での再現は今回確認していない。

関連するupstream PRは確認時点で両方ともopen、未マージだった。

| PR | 対象 | 判断への意味 |
| --- | --- | --- |
| [#904](https://github.com/tolwi/hassio-ecoflow-cloud/pull/904) | Private DP3のAC充電電力をProtobuf送信へ変更 | 設定要求が無視されるという報告と修正案がある。現在のmainに修正はない。 |
| [#921](https://github.com/tolwi/hassio-ecoflow-cloud/pull/921) | #904を広げ、SOC・出力・タイマー等をProtobuf送信へ変更 | 操作系の未解決点に直接対応する。ただし、PR自身も未対応の設定が残ると述べている。 |

操作エンティティが存在することと、信頼できる操作が実装・検証されたことは区別する。
Public API側の追加機能だけでも、ユーザーが使うPrivate/App APIの要求を満たさない。
#2は継続が必要であり、閉じない。操作系の改修・PR取り込みは現方針どおり保留する。

## 確認方法と限界

- GitHubの未解決Issue一覧、各本文・全コメント、関連PRの現在の状態を取得した。
- 現DP3のコマンド定義をASTから取り出し、合成値で15件の辞書生成を確認した。
  ACタイマーと出力種別のIDが10/59で異なることを確認した。
- 現JSONMessageのシリアライザーを、連番生成のみスタブ化して単独実行した。
  15件すべてでJSON文字列ができ、設定パラメータが維持されることを確認した。
- 統合全体のimport、本番HA・実機・EcoFlowへの接続、MQTT publishは行っていない。
- Issue本文・タイトル・ラベル・状態は変更していない。

次の作業は[タスク計画](../../tasks/tasks_plan.md)で管理する。
