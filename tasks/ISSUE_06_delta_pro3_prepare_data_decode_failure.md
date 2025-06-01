# ISSUE_06: Delta Pro 3 \_prepare_data メッセージ複合失敗の原因分析・解決

## 概要

- 実データテストで、特定のメッセージ（例: cmdFunc=32, cmdId=2 や cmdFunc=254, cmdId=21 など）で MessageToDict でフィールドは得られているのに、最終出力が 0 件またはごく一部しか抽出されない現象が継続。
- 主要なバッテリー情報や電力情報が安定して抽出できない場合が多い。
- 詳細な原因分析・解決を本 ISSUE で行う。
- [ISSUE_05_delta_pro_3_prepare_data_implementation.md](ISSUE_05_delta_pro_3_prepare_data_implementation.md) の 7.3 から分離。

## 参考ログ

- [実データテストログ (real_data_test.log)](../scripts/delta_pro3_real_data_test/test_results/real_data_test.log)
- [生メッセージ (raw_messages.jsonl)](../scripts/delta_pro3_real_data_test/test_results/raw_messages.jsonl)
- [処理済みデータ (processed_data.jsonl)](../scripts/delta_pro3_real_data_test/test_results/processed_data.jsonl)

## サブタスク 1 の修正案（なぜ修正が必要かも明記）

- [x] 1. MessageToDict 直後の全フィールド・値・型を詳細ログ出力するよう修正し、どこで値が消えるか特定

  - 2025-06-01 15:03
  - **修正対象ファイルと理由:**
    - [`scripts/delta_pro3_real_data_test/prepare_data_processor.py`](../scripts/delta_pro3_real_data_test/prepare_data_processor.py)
      → 実データテストのデコード・フィールド抽出のメイン処理。MessageToDict 直後の全フィールド・値・型を詳細にログ出力することで、どこで値が消えるかを追跡できる。
  - **対応内容:**
    - 各ファイルで `MessageToDict` 実行直後に、
      - すべてのフィールド名・値・型を詳細にログ出力する処理を追加する。
      - 例: `for k, v in result.items(): logger.debug(f"{k}: {v} ({type(v)})")`
    - これにより、どの段階で値が消失・変換されているかを追跡・特定できるようにする。
  - **追加分析**: 生メッセージ・処理済みデータファイル
    - raw_messages.jsonl では、cmdFunc=32, cmdId=50/2 のメッセージが交互に記録されている。
    - processed_data.jsonl では、cmdFunc=32, cmdId=50 のみ 3 フィールド（ac_phase_type, pcs_work_mode, plug_in_info_pv_l_vol）が出力され、cmdFunc=32, cmdId=2 のデータは常に空（field_count=0）。
    - これはログ分析と一致し、「デコード自体は成功しているが、変換関数のフィールド名不一致で値が消えている」ことを裏付けている。
    - 生メッセージのバイナリ長・内容も安定しており、データ破損やデコード失敗は発生していない。
    - 他の型（DisplayPropertyUpload 等）では複数フィールドが正しく出力されているため、変換ロジックの修正で解決可能と考えられる。

- [ ] 2. 変換・フィルタロジックを現状の MessageToDict 出力フィールド名に合わせて修正し、必要な値が正しく抽出・出力されることを確認する

  - 例: cms_batt_vol_mv, cms_batt_soc_percent など、現状の出力名で抽出
  - まずは全フィールドを一時的にそのまま出力し、必要なものをピックアップ・リネームしていく
  - 2025-06-01 15:28
  - **修正対象ファイルと理由:**
    - [`scripts/delta_pro3_real_data_test/prepare_data_processor.py`](../scripts/delta_pro3_real_data_test/prepare_data_processor.py)
      → 変換関数（\_transform_cms_bms_summary など）で、MessageToDict の出力フィールド名（cms_batt_vol_mv, cms_batt_soc_percent など）に合わせて抽出・リネーム処理を修正する。
      → 一時的にフィルタを外し、全フィールドをそのまま出力することで、必要な値をピックアップしやすくする。
  - **対応内容:**
    - 変換関数で抽出するフィールド名を、MessageToDict の出力に合わせて修正する。
    - 一時的にフィルタを外し、全フィールドをそのまま出力して確認する。
    - 必要なフィールドをピックアップし、意味付け・リネームを進める。
    - これにより、cmdFunc=32, cmdId=2 などでも必要な値が正しく抽出・出力されることを確認する。
  - **実行・分析結果（2025-06-01）:**
    - 変換関数修正後、cmdFunc=32, cmdId=2 のメッセージで `msg32_2_1`, `msg32_2_2` 配下の全フィールドが `msg32_2_1.フィールド名` / `msg32_2_2.フィールド名` 形式で flat に抽出・出力されることを確認。
    - 例: `cms_batt_vol_mv`, `cms_batt_soc_percent`, `cms_max_chg_soc_percent`, `cms_min_dsg_soc_percent`, `ac_out_freq_hz_config`, `cms_chg_rem_time_min`, `cms_dsg_rem_time_min`, `cms_chg_dsg_state`, `bms_is_conn_state`, `cms_oil_off_soc_percent` など、MessageToDict の出力フィールドがすべて出力されている。
    - unknown 系フィールドも含め、28 フィールド前後が安定して抽出されている。
    - cmdFunc=32, cmdId=50 など他の型も従来通り正しく抽出されている。
    - flat 化・prefix 付与により、フィールドの重複やネストによる取りこぼしがなくなり、今後の意味付け・リネーム作業が容易になった。
    - **今後のアクション:**
      - 必要なフィールドをピックアップし、意味付け・リネームを進める。
      - unknown 系フィールドの実値・変動を観察し、ioBroker JS 実装や実データと照合しながらマッピング精度を高める。
      - 変換ロジックの最適化・不要な冗長出力の整理を進める。

- [ ] 3. unknown 系フィールドや新規フィールドの実値サンプル・変動パターンを記録し、意味付け・マッピング精度向上のためのサンプル収集を行う

  - 2025-06-01 15:39
  - 例: msg32_2_1.unknownXX_s1 などの値を時系列でサンプル保存し、既知フィールドとの相関や変動パターンを観察
  - ioBroker JS 実装のマッピングや実データと比較し、意味付け候補を列挙・検証する
  - 必要に応じて、`unknown_fields_samples.jsonl` 内容もサンプルとして保存し、フィールドの安定性・変動性を記録
  - これにより、unknown 系フィールドの意味付け・マッピング精度向上を目指す
    - **サンプル保存のための修正対象ファイルと理由:**
    - [`scripts/delta_pro3_real_data_test/prepare_data_processor.py`](../scripts/delta_pro3_real_data_test/prepare_data_processor.py)
      → unknown 系・新規フィールドの値を flat に抽出・出力するロジックの実装箇所。サンプル保存用に、全フィールドの値や unknown 系のみの値を時系列で記録できるよう、出力形式や保存処理の追加・修正が必要。
    - [`scripts/delta_pro3_real_data_test/main.py`](../scripts/delta_pro3_real_data_test/main.py)
      → 実データテストのメインスクリプト。サンプル保存用に、抽出した全フィールド値や unknown 系のみの値を jsonl 等で保存する処理や、保存先ファイル名・出力タイミングの制御が必要。
    - [`scripts/delta_pro3_real_data_test/test_results/`](../scripts/delta_pro3_real_data_test/test_results/)
      → サンプル保存先ディレクトリ。**用途ごとにファイル名で区別して保存する運用とする。**
      - 例 1: `message_to_dict_samples.jsonl` … MessageToDict で得られる全フィールドのサンプルを時系列で保存（全体像・変換過程の追跡・検証用）
      - 例 2: `unknown_fields_samples.jsonl` … unknown 系・未定義フィールドのみを抽出して時系列で保存（意味付け・マッピング精度向上用）
      - 例 3: `raw_payload_samples.jsonl` … raw データや payload バイト列のサンプルを保存（必要に応じて）
    - **理由:**
    - unknown 系・新規フィールドの実値サンプルを時系列で保存・観察することで、意味付け・マッピング精度向上に役立てるため。
    - flat 出力・詳細ログだけでなく、サンプルを継続的に蓄積・比較できる仕組みが必要なため。
    - ファイル名で用途を明確に区別することで、管理・参照・自動処理が容易になるため。

- [ ] 4. cmdFunc/cmdId ごとのフィールドマッピング・変換ルールを再整理
- [ ] 5. 必要に応じて ioBroker JS 実装の該当箇所を再調査 6
- [ ] 6. 原因特定後、\_prepare_data ロジックを修正し再テスト
- [ ] 7. 成功率・抽出フィールド数の改善を確認
- [ ] 8. ISSUE_05 に解決内容を記録・リンク
