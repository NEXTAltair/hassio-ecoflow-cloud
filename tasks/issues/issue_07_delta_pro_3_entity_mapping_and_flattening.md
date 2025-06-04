# Issue 07: DeltaPro3 entity mapping & flattening 問題まとめ

## 概要

DeltaPro3 の Home Assistant 統合において、一部エンティティ値が「不明」や「0V」等の異常値になる現象が継続している。本 issue では現象の詳細、原因仮説、今後の対応方針、調査・修正タスクを体系的にまとめる。

## 現象の詳細

- Home Assistant 上で DeltaPro3 の一部エンティティ値が「不明」や「0V」等の異常値になる。
- MQTT データ自体は受信・デコードできており、flat_dict にも値が入っている場合がある。
- しかし、UI 上で値が反映されない/ゼロになる項目が複数存在。

## 原因仮説・技術的背景

- flat 化後のフィールド名と、エンティティ定義側の参照名（sensors()等で指定）が一致していない。
- Protobuf→dict 変換時のフィールド名（proto 定義）が古い/ズレている/unknownXX のまま。
- flat 化ロジックでネストやリスト型の扱いに不備がある。
- エンティティ側で参照しているキー名が、flat_dict に存在しない。
- デバイス側が値を送っていない場合も一部含まれる。

## 調査・修正方針

- [DEBUG ログファイル](../../core/config/home-assistant.log)を活用し、どの時点で値が消失・変換ミスしているかを追跡
- [proto 定義](../../custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto)・エンティティ定義の突き合わせ表を作成し、ズレを修正
- flat_dict の内容と UI 表示値の差分を重点的に調査
- 進捗・調査結果は本 issue に随時追記

## 今後やるべきこと（TODO）

- [ ] 1. flat_dict の全内容を DEBUG ログで dump し、UI に出ない値が flat_dict に存在するか確認

  - **修正対象ファイルと理由:**
    - [`cdelta_pro_3.py`](../../custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py)
      → Home Assistant 側で DeltaPro3 のデータデコード・flat 化・エンティティ値反映のメイン処理。flat_dict 生成直後に全フィールド・値・型を詳細にログ出力することで、どこで値が消えるかを追跡できる。
  - **対応内容:**
    - `MessageToDict` 実行直後、または flat_dict 生成直後に
      - すべてのフィールド名・値・型を詳細に DEBUG ログ出力する処理を追加。
      - 例:
        ```python
        for k, v in flat_dict.items():
            _LOGGER.debug(f"flat_dict[{k!r}] = {v!r} (type: {type(v).__name__})")
        ```
    - これにより、どの段階で値が消失・変換されているかを追跡・特定できるようにする。
  - **期待される成果:**

    - flat_dict に値が存在するのに UI に出ない場合 → エンティティ定義やマッピングのズレ・型変換ミス等が疑われる
    - flat_dict にも値が存在しない場合 → デバイス未送信・デコード失敗・前処理ミス等が疑われる
    - どの時点で値が消失・変換ミスしているかを特定し、次の修正アクション（マッピング修正・flat 化ロジック修正等）に繋げる

  - **実行・分析結果(2025-06-03:17:51):**
    - flat_dict の DEBUG ログ出力を精査した結果、多くのフィールドが正しく展開・格納されていることが確認できた。
    - 例: bms_batt_soc, cms_batt_soc, pow_out_sum_w, ac_out_freq など、UI で「不明」や「0V」になると報告されていた値も flat_dict には存在し、値も正常。
    - 型も float, int, bool, str, list など適切に展開されている。
    - それにもかかわらず UI で値が出ない場合は、flat_dict のキー名とエンティティ定義側の参照名のズレ、または型変換・マッピングの問題が主な原因と考えられる。
    - flat_dict にも値が存在しない場合は、デバイス未送信・デコード失敗・前処理ミス等の可能性がある。
    - 今後は flat_dict のキー名とエンティティ定義の参照名の完全な突き合わせ、型変換・バリデーションの見直し、UI 側の判定ロジック調査などを重点的に進める必要がある。

- [ ] 2. proto 定義のフィールド名・コメントを再度見直し、エンティティ側と突き合わせて修正

  - **修正対象ファイルと理由:**
    - [`custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto`](../../custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto)（proto 定義の見直し・コメント修正）
    - [`custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py`](../../custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py)（エンティティ側の参照名・型修正）
    - 必要に応じて [`docs_4ai/`](../../docs_4ai/) ､ [`tasks`](../../tasks/) 配下の設計ドキュメント
  - **対応内容:**
    - [issue_03_data_analysis_and_mapping_update.md の「フィールド一覧・マッピング表」参照](issue_03_data_analysis_and_mapping_update.md)
    - フィールド名やコメントが古い/ズレている場合、正しい意味・単位・型に修正し、エンティティ定義と整合させる
    - proto ファイルの各フィールドに単位・意味・型を明記し、曖昧・未記載・誤りがあれば修正案を作成する
      - 【具体的な対応例】
        - `bms_batt_vol`, `bms_batt_amp` などは proto 側で mV/mA 単位だが、エンティティ側では V/A として扱うため「1000 で割る」などの変換ルール・注記を明記する。
        - `bms_full_cap_mah`, `bms_remain_cap_mah` などは message によってフィールド名が異なるため、flat_dict のキー名をどちらに合わせるか統一方針を明記する。
        - コメントが `//bool` など曖昧なものや、意味が推測コメント (`// BMS related ID or counter?`) になっているものは、実データや設計ドキュメントを参照して正確な意味・単位・型を補足する。
        - コメント・const 名・エンティティ名で単位や意味が明確でないものは、proto 側・エンティティ側ともに補足・修正する。
        - flat_dict 生成時のキー名は、複数 message で同じ意味のフィールド名が異なる場合どちらに合わせるか明確化し、今後の保守性向上を図る。
    - エンティティ側の参照名・型アノテーションも proto 側に合わせて修正する
    - どうしても揃わない場合は、flat_dict からエンティティ名への alias/mapping 辞書を実装し、保守性を高める
    - 上記の突き合わせ表・修正方針・命名規則・コメント例を docs_4ai/ 配下や本 issue に記録し、今後の保守・拡張時の指針とする
    - 具体的な作業手順例や成果物イメージも issue 内に明記し、現状調査 → 突き合わせ → 修正 → 記録の流れを明確にする
  - **期待される成果:**
    - proto/エンティティ間のフィールド名・型・意味・単位のズレが解消され、Home Assistant で正しく値が反映される
    - コメント・命名規則・設計方針が明文化され、今後の保守・拡張が容易になる
  - **実行・分析結果(YYYY-MM-DD:hh:mm):**
    - （作業・検証の進捗や結果をここに随時追記）

- [ ] 3. flat_dict のキー名とエンティティ定義のキー名が一致しているか確認・必要ならマッピング追加
  - UI で値が出ない場合、flat_dict のキーとエンティティ参照名のズレがないかを確認し、必要に応じて alias/mapping を追加する。
- [ ] 4. repeated/ネスト型フィールドの flat 化が正しく行われているか確認
  - ネストや repeated フィールドが正しく flat 化されているか、取りこぼしや重複がないかを検証する。
- [ ] 5. デバイスから値が本当に送られているか（flat_dict 自体に値がない場合）も確認
  - デバイス側の未送信や通信不良で値が入っていない場合もあるため、raw データや payload の内容も確認する。
- [ ] 6. XOR/Base64/メッセージ種別判定など、前処理の条件分岐が正しいか再確認
  - XOR デコードや Base64 判定、cmdFunc/cmdId などの分岐条件が正しいかを再度見直す。
- [ ] 7. 他デバイス（PowerStream 等）とのフィールド名対応表を作成し、ズレの吸収・共通化を進める
  - 他デバイスとの比較で命名・flat 化ルールの共通化・吸収を進める。
- [ ] 8. 必要に応じて flat_dict→ エンティティ名への alias/mapping 辞書を実装
  - 参照名のズレが多い場合は、flat_dict からエンティティ名への変換辞書を実装し、保守性を高める。

## 進捗・調査ログ

- 本 issue に調査結果・修正内容・進捗を随時追記する。

## 関連ファイル・参考リンク

- [`custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py`](../../custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py)
- [`custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker_pb2.py`](../../custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker_pb2.py)
- [`custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto`](../../custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto)
- [`tasks/issues/issue_05_delta_pro_3_prepare_data_implementation.md`](issue_05_delta_pro_3_prepare_data_implementation.md)
- [`tasks/issues/ISSUE_06_delta_pro3_prepare_data_decode_failure.md`](ISSUE_06_delta_pro3_prepare_data_decode_failure.md)
- [`tasks/issues/issue_04_delta_pro_3_entity_data_mapping.md`](issue_04_delta_pro_3_entity_data_mapping.md)
  - DeltaPro3 のデータとエンティティの正規対応表・命名規則・マッピング方針について記載。JS 実装（ef_deltapro3_data.js）との対応も明記。

## 成果/期待される成果

- DeltaPro3 のエンティティ値が正しく Home Assistant に反映される
- フィールド名・マッピングのズレが解消され、保守性・拡張性が向上する
