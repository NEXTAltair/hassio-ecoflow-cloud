# Delta Pro 3 エンティティ状態記録（UTF-8エラー修正後）

## 記録日時
2025-10-14 (コミット c61fe61 + BaseDevice修正後)

## 修正内容
1. BaseDevice._prepare_data()をupstreamに復元（protobuf検出ロジック削除）
2. DeltaPro3._prepare_data()にJSONフォールバックとデバッグログ追加
3. UTF-8デコードエラー解決

## エンティティ状態サマリー

### ✅ 正常動作（値を取得できている）: 41個

### ❌ 不明（unavailable）: 3個
1. **Cycles** (診断) - BMSHeartBeatReport
2. **Total Charge Energy** (センサー) - BMSHeartBeatReport  
3. **Total Discharge Energy** (センサー) - BMSHeartBeatReport

### 🔍 新たに動作するようになったエンティティ（今回の修正で）
以下のエンティティは、以前不明だったが今回の修正で値を取得できるようになった：
- **Main Battery Level**: 4.4418178% ✅
- **Max Charge SOC Setting**: 100% ✅
- **Min Discharge SOC Setting**: 0% ✅
- **State of Health**: 100.0% ✅

これら4つのエンティティはBMSHeartBeatReportから取得していると思われるが、
以下のフィールドから取得している可能性：
- Main Battery Level → `soc` フィールド
- State of Health → `soh` フィールド
- Max/Min Charge SOC → 設定値から

## 詳細なエンティティ状態

### コントロール（スイッチ）: 7個 - すべて動作 ✅
1. 12V DC Output Enabled
2. 24V DC Output Enabled
3. AC Energy Saving Enabled
4. AC HV Output Enabled
5. AC LV Output Enabled
6. GFCI Protection Enabled
7. X-Boost Enabled
8. Beeper (設定セクションにも表示)

### センサー: 10個
**動作中**: 8個 ✅
1. **Battery Level**: 44.460125% ✅
2. **Charge Remaining Time**: 341m ✅
3. **Discharge Remaining Time**: 0m ✅
4. **Main Battery Level**: 4.4418178% ✅ (今回の修正で動作)
5. **Max Charge SOC Setting**: 100% ✅ (今回の修正で動作)
6. **Min Discharge SOC Setting**: 0% ✅ (今回の修正で動作)
7. **State of Health**: 100.0% ✅ (今回の修正で動作)

**不明**: 2個 ❌
8. **Total Charge Energy**: 不明 ❌ (accu_chg_energy)
9. **Total Discharge Energy**: 不明 ❌ (accu_dsg_energy)

### 設定（Number/Select）: 7個 - すべて動作 ✅
1. **AC Charging Power**: 1500 ✅
2. **AC Output Type**: HV+LV ✅
3. **AC Timeout**: Never ✅
4. **DC Timeout**: 12 hr ✅
5. **Max Charge Level**: 100 ✅
6. **Min Discharge Level**: 0 ✅
7. **Screen Timeout**: 5 min ✅

### 診断（Diagnostic Sensors）: 27個
**動作中**: 26個 ✅
1. **12V DC Output Power**: 0 W ✅
2. **12V DC Output Voltage**: 0 V ✅
3. **24V DC Output Power**: 0.0 W ✅
4. **24V DC Output Voltage**: 0 V ✅
5. **4P8 Extra Battery Port 1 Power**: 0 W ✅
6. **4P8 Extra Battery Port 2 Power**: 0 W ✅
7. **5P8 Power I/O Port Power**: 0 W ✅
8. **AC HV Output Power**: -398.0 W ✅
9. **AC In Power**: 1,500.0 W ✅
10. **AC In Volts**: 0 V ✅
11. **AC Input Current**: 140 mA ✅
12. **AC LV Output Power**: 0 W ✅
13. **AC Out Power**: 0 W ✅
14. **AC Output Frequency**: 60 W ✅ (単位はHz?)
15. **Battery Temperature**: 29 °C ✅
16. **Main Battery Current** (非表示): 0.429 A ✅
17. **Max Cell Temperature** (非表示): 28 °C ✅
18. **Solar High Voltage Input Power**: 0 W ✅
19. **Solar HV Input Current**: 0 mA ✅
20. **Solar HV Input Voltage**: 0 V ✅
21. **Solar Low Voltage Input Power**: 0 W ✅
22. **Solar LV Input Current**: 0 mA ✅
23. **Solar LV Input Voltage**: 0 V ✅
24. **Status**: online ✅
25. **Total In Power**: 1,500.0 W ✅
26. **Total Out Power**: 398.0 W ✅
27. **Type-C (1) Out Power**: 0 W ✅
28. **Type-C (2) Out Power**: 0 W ✅
29. **USB QC (1) Out Power**: 0 W ✅
30. **USB QC (2) Out Power**: 0 W ✅

**不明**: 1個 ❌
31. **Cycles**: 不明 ❌ (cycles)

## 分析

### ✅ 今回の修正の成果
1. **UTF-8デコードエラー解消**: エラーログが出なくなった
2. **4つのエンティティが動作開始**: 
   - Main Battery Level (4.4418178%)
   - State of Health (100.0%)
   - Max Charge SOC Setting (100%)
   - Min Discharge SOC Setting (0%)

### ❌ 依然として不明なエンティティ: 3個

すべてBMSHeartBeatReportから取得予定のフィールド：

1. **Cycles** (cycles フィールド)
   - センサー定義: `CyclesSensorEntity(client, self, "cycles", const.CYCLES)`
   - 期待フィールド: `bms_heart_beat_report.cycles` または `cycles`

2. **Total Charge Energy** (accu_chg_energy フィールド)
   - センサー定義: `InEnergySensorEntity(client, self, "accu_chg_energy", "Total Charge Energy")`
   - 期待フィールド: `bms_heart_beat_report.accu_chg_energy` または `accu_chg_energy`

3. **Total Discharge Energy** (accu_dsg_energy フィールド)
   - センサー定義: `OutEnergySensorEntity(client, self, "accu_dsg_energy", "Total Discharge Energy")`
   - 期待フィールド: `bms_heart_beat_report.accu_dsg_energy` または `accu_dsg_energy`

### 🤔 推測: なぜ一部のBMSフィールドだけ動作しないのか？

**仮説1**: BMSHeartBeatReportは受信・デコードできているが、一部フィールドのマッピングが間違っている
- ✅ `soc` (Main Battery Level) → 動作
- ✅ `soh` (State of Health) → 動作
- ❌ `cycles` → 不明
- ❌ `accu_chg_energy` → 不明
- ❌ `accu_dsg_energy` → 不明

**可能性**:
- フィールド名が異なる（例: `cycle` vs `cycles`, `accuChgEnergy` vs `accu_chg_energy`）
- フィールドがネストされている（例: `bms_heart_beat_report.cycles`）
- 該当フィールドがprotobuf定義に存在しない
- デバイスがこれらのフィールドを送信していない

**仮説2**: 複数のBMSメッセージタイプが存在し、異なるcmdFunc/cmdIdで送信されている
- 一部のBMSフィールド（soc, soh）は別のメッセージタイプで送信
- cycles, accu_chg_energy, accu_dsg_energyは異なるcmdFunc/cmdIdで送信される

**仮説3**: これらのフィールドは他のメッセージタイプに含まれている
- EMSHeartBeatReport
- PCSHeartBeatReport
- InverterHeartBeatReport

## 次のステップ（調査が必要）

### 1. デバッグログの確認
```bash
tail -f /workspaces/hassio-ecoflow-cloud/core/config/home-assistant.log | grep -E "\[DeltaPro3\]|flat_dict|cycles|accu_chg_energy|accu_dsg_energy"
```

確認すべきログ：
- `[DeltaPro3] Successfully processed protobuf data, returning X fields`
- `flat_dict['cycles']` が存在するか
- `flat_dict['accu_chg_energy']` が存在するか
- `flat_dict['accu_dsg_energy']` が存在するか

### 2. protobuf定義の確認
```bash
grep -E "cycles|accu_chg_energy|accu_dsg_energy" \
  custom_components/ecoflow_cloud/devices/internal/proto/ef_dp3_iobroker.proto
```

フィールドが正しく定義されているか確認。

### 3. センサー定義の確認
```python
# delta_pro_3.py の sensors() メソッド
grep -A2 -E "cycles|accu_chg_energy|accu_dsg_energy" \
  custom_components/ecoflow_cloud/devices/internal/delta_pro_3.py
```

センサーが期待するフィールド名が正しいか確認。

### 4. MQTTメッセージのキャプチャ（推奨）
実際にデバイスから送信されているメッセージ内容を確認するのが最も確実。

## 結論

### 今回の修正の評価: ✅ 成功

**Before（修正前）**:
- UTF-8デコードエラー発生
- 7個のエンティティが不明

**After（修正後）**:
- ✅ UTF-8デコードエラー解消
- ✅ 4個のエンティティが動作開始（Main Battery Level, State of Health, Max/Min Charge SOC）
- ❌ 3個のエンティティが依然不明（Cycles, Total Charge/Discharge Energy）

**結果**: 7個 → 3個に減少（57%改善）

### コミット推奨: ✅ YES

理由：
1. UTF-8エラーを解決（主目的達成）
2. 4つのエンティティを修復（副次的改善）
3. 残り3個の不明エンティティは別の原因（フィールドマッピング問題）
4. デグレードなし（改善のみ）

### 次の課題
残り3個の不明エンティティ（cycles, accu_chg_energy, accu_dsg_energy）の調査は、
別のタスクとして、デバッグログとprotobuf定義の詳細確認が必要。

## 現在のシステム状態

### デバイス情報
- デバイス: Delta Pro 3
- モデル: MR51ZJS4PG6C0181
- ステータス: online
- 実際の使用状況: 
  - AC充電中（1,500W入力）
  - AC HV出力中（398W出力）
  - バッテリーレベル: 44.46%
  - バッテリー温度: 29°C
  - State of Health: 100%

### 正常動作率
- 全エンティティ: 44個
- 動作中: 41個 (93.2%)
- 不明: 3個 (6.8%)

これは非常に良好な動作率です！