# DP3 実機テスト計画タスク

## 1. 概要

Delta Pro 3実機を使用した包括的なテスト計画を実行し、Home Assistant統合の実用性・安定性・パフォーマンスを検証する。
実際の使用環境での動作確認により、リリース前の最終品質保証を行う。

## 2. 前提条件

### **必要機材・環境**
- [ ] **EcoFlow Delta Pro 3実機**: 動作確認済み
- [ ] **Home Assistant環境**: 最新安定版
- [ ] **ネットワーク環境**: 安定したWiFi接続
- [ ] **テスト用負荷**: AC/DC負荷機器
- [ ] **測定機器**: 電力計、マルチメーター等

### **ソフトウェア要件**
- [ ] **DP3統合実装**: 全機能実装完了
- [ ] **テストツール**: pytest、Home Assistant Test環境
- [ ] **監視ツール**: ログ収集・分析ツール

## 3. Phase 1: 基本機能検証テスト

### **3.1 デバイス認識・接続テスト**

#### **初期接続テスト**
```yaml
test_case: "DP3_001_初期接続"
objective: "DP3デバイスの認識・接続確認"
steps:
  1. Home Assistant統合設定
     - EcoFlowアカウント情報入力
     - デバイス自動発見確認
     - DP3デバイス選択・追加

  2. デバイス認識確認
     - デバイス情報表示確認
     - シリアル番号・モデル名確認
     - ファームウェアバージョン確認

  3. MQTT接続確認
     - MQTTブローカー接続状態
     - ハートビートメッセージ受信
     - データ更新頻度確認

expected_results:
  - デバイスが正常に認識される
  - 全エンティティが生成される
  - データが定期的に更新される

pass_criteria:
  - 接続成功率: 100%
  - エンティティ生成: 全て成功
  - データ更新間隔: 5秒以内
```

#### **再接続・復旧テスト**
```yaml
test_case: "DP3_002_再接続復旧"
objective: "ネットワーク断線からの自動復旧確認"
steps:
  1. 正常接続状態確認
  2. WiFi接続を意図的に切断
  3. 5分間待機
  4. WiFi接続復旧
  5. 自動再接続確認

expected_results:
  - 自動的に再接続される
  - データ受信が再開される
  - エンティティ状態が正常に更新される

pass_criteria:
  - 再接続時間: 2分以内
  - データ復旧: 完全
  - エラー発生: なし
```

### **3.2 データ受信・表示テスト**

#### **センサーデータ精度テスト**
```yaml
test_case: "DP3_003_センサー精度"
objective: "センサーデータの精度・一貫性確認"
test_scenarios:
  - バッテリー残量表示
  - 電力値表示
  - 電圧・電流値表示
  - 温度値表示

verification_method:
  1. DP3液晶画面の値を記録
  2. Home Assistantエンティティ値を記録
  3. 誤差を計算・評価

pass_criteria:
  - SOC誤差: ±2%以内
  - 電力誤差: ±5%以内
  - 電圧誤差: ±1%以内
  - 温度誤差: ±2℃以内
```

#### **リアルタイム更新テスト**
```yaml
test_case: "DP3_004_リアルタイム更新"
objective: "データ更新の即応性確認"
steps:
  1. AC負荷接続（例: 1000W）
  2. Home Assistant画面でAC出力電力確認
  3. 負荷切断
  4. 電力値変化の応答時間測定

expected_results:
  - 負荷変化が即座に反映される
  - 更新遅延が最小限

pass_criteria:
  - 更新遅延: 10秒以内
  - データ一貫性: 100%
```

## 4. Phase 2: 制御機能検証テスト

### **4.1 出力制御テスト**

#### **AC出力制御テスト**
```yaml
test_case: "DP3_005_AC出力制御"
objective: "AC出力ON/OFF制御の動作確認"
test_procedure:
  1. 初期状態確認
     - AC出力状態確認
     - 接続負荷確認

  2. AC出力ON操作
     - Home AssistantスイッチでON
     - DP3実機でAC出力確認
     - 負荷への電力供給確認

  3. AC出力OFF操作
     - Home AssistantスイッチでOFF
     - DP3実機でAC出力停止確認
     - 負荷への電力供給停止確認

measurement_points:
  - コマンド送信時刻
  - DP3応答時刻
  - 実際の出力変化時刻

pass_criteria:
  - コマンド成功率: 100%
  - 応答時間: 3秒以内
  - 状態同期: 完全
```

#### **X-Boost機能テスト**
```yaml
test_case: "DP3_006_X-Boost制御"
objective: "X-Boost機能の動作確認"
test_setup:
  - 高負荷機器準備（2000W以上）
  - AC出力ON状態

test_procedure:
  1. X-Boost OFF状態で高負荷接続
     - 過負荷保護動作確認

  2. X-Boost ON操作
     - Home AssistantスイッチでON
     - DP3でX-Boost有効確認

  3. 高負荷動作確認
     - 2000W以上の負荷動作
     - 出力電力・電圧測定

pass_criteria:
  - X-Boost有効化: 成功
  - 高負荷動作: 安定
  - 過負荷保護: 適切
```

#### **DC出力制御テスト**
```yaml
test_case: "DP3_007_DC出力制御"
objective: "DC出力制御の動作確認"
test_items:
  - シガーソケット出力制御
  - USB出力動作確認
  - Type-C出力動作確認

verification:
  - 各出力ポートの電圧測定
  - 負荷接続時の電力測定
  - 制御応答時間測定

pass_criteria:
  - 全出力ポート: 正常動作
  - 制御応答: 3秒以内
  - 電圧精度: ±5%以内
```

### **4.2 充電制御テスト**

#### **充電上限設定テスト**
```yaml
test_case: "DP3_008_充電上限制御"
objective: "充電上限設定の動作確認"
test_procedure:
  1. 現在SOC確認（例: 60%）
  2. 充電上限を70%に設定
  3. AC充電開始
  4. 70%到達時の動作確認
  5. 充電停止確認

monitoring_points:
  - SOC変化
  - 充電電力変化
  - 充電停止タイミング

pass_criteria:
  - 設定値での充電停止: 確認
  - 設定精度: ±1%以内
  - 制御応答: 即座
```

#### **AC充電電力設定テスト**
```yaml
test_case: "DP3_009_AC充電電力制御"
objective: "AC充電電力設定の動作確認"
test_scenarios:
  - 400W設定テスト
  - 1200W設定テスト
  - 2900W設定テスト

verification_method:
  1. Home Assistantで電力値設定
  2. AC充電開始
  3. 実際の充電電力測定
  4. 設定値との比較

pass_criteria:
  - 設定精度: ±50W以内
  - 制御応答: 10秒以内
  - 安定性: 継続動作
```

## 5. Phase 3: 負荷・ストレステスト

### **5.1 長時間動作テスト**

#### **24時間連続動作テスト**
```yaml
test_case: "DP3_010_24時間連続動作"
objective: "長時間動作での安定性確認"
test_duration: 24時間
monitoring_interval: 5分

test_conditions:
  - 軽負荷接続（200W程度）
  - 定期的なコマンド送信
  - データ受信継続

monitoring_items:
  - データ受信率
  - コマンド成功率
  - メモリ使用量
  - エラー発生頻度

pass_criteria:
  - データ受信率: 99%以上
  - コマンド成功率: 98%以上
  - メモリリーク: なし
  - 重大エラー: なし
```

#### **高頻度操作テスト**
```yaml
test_case: "DP3_011_高頻度操作"
objective: "高頻度操作での安定性確認"
test_duration: 2時間
operation_interval: 30秒

test_operations:
  - AC出力ON/OFF切り替え
  - 充電上限値変更
  - X-Boost ON/OFF切り替え

monitoring:
  - コマンド応答時間
  - エラー発生率
  - デバイス応答性

pass_criteria:
  - 全操作成功率: 95%以上
  - 平均応答時間: 5秒以内
  - デバイス異常: なし
```

### **5.2 異常系テスト**

#### **過負荷保護テスト**
```yaml
test_case: "DP3_012_過負荷保護"
objective: "過負荷時の保護機能確認"
test_scenarios:
  - AC出力過負荷（4000W以上）
  - DC出力過負荷
  - 短絡保護

verification:
  - 保護機能動作確認
  - Home Assistantでの状態表示
  - 自動復旧機能確認

pass_criteria:
  - 保護機能: 正常動作
  - 状態表示: 正確
  - 自動復旧: 成功
```

#### **通信エラー回復テスト**
```yaml
test_case: "DP3_013_通信エラー回復"
objective: "通信エラーからの回復確認"
error_scenarios:
  - MQTT接続断
  - 不正コマンド送信
  - タイムアウト発生

recovery_verification:
  - 自動再接続
  - エラー状態表示
  - 正常状態復旧

pass_criteria:
  - 自動回復: 成功
  - 回復時間: 5分以内
  - データ整合性: 維持
```

## 6. Phase 4: パフォーマンステスト

### **6.1 応答性能テスト**

#### **コマンド応答時間測定**
```python
# tests/performance/test_dp3_response_time.py

import asyncio
import time
from statistics import mean, stdev

class DP3PerformanceTest:
    """DP3パフォーマンステストクラス"""

    async def test_command_response_time(self, device, iterations=100):
        """コマンド応答時間測定"""
        response_times = []

        for i in range(iterations):
            start_time = time.time()

            # AC出力切り替えコマンド
            current_state = device.data.params.get("invCfgAcEnabled", False)
            new_state = not current_state

            await device.send_ac_output_command(new_state)

            # 状態変化待機
            while True:
                await asyncio.sleep(0.1)
                if device.data.params.get("invCfgAcEnabled") == new_state:
                    break
                if time.time() - start_time > 10:  # タイムアウト
                    break

            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)

            # 元の状態に戻す
            await device.send_ac_output_command(current_state)
            await asyncio.sleep(1)

        # 統計計算
        avg_time = mean(response_times)
        std_time = stdev(response_times)
        max_time = max(response_times)
        min_time = min(response_times)

        return {
            "average": avg_time,
            "std_dev": std_time,
            "max": max_time,
            "min": min_time,
            "samples": len(response_times)
        }
```

#### **データ処理性能測定**
```python
    async def test_data_processing_performance(self, device, duration_minutes=10):
        """データ処理性能測定"""
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        message_count = 0
        processing_times = []

        while time.time() < end_time:
            # メッセージ受信待機
            initial_count = device.data.message_count

            while device.data.message_count == initial_count:
                await asyncio.sleep(0.1)
                if time.time() > end_time:
                    break

            # 処理時間測定
            process_start = time.time()
            # データ処理完了待機
            await asyncio.sleep(0.1)
            process_end = time.time()

            processing_times.append(process_end - process_start)
            message_count += 1

        return {
            "total_messages": message_count,
            "messages_per_minute": message_count / duration_minutes,
            "avg_processing_time": mean(processing_times),
            "max_processing_time": max(processing_times)
        }
```

### **6.2 リソース使用量測定**

#### **メモリ使用量監視**
```python
import psutil
import gc

class ResourceMonitor:
    """リソース使用量監視クラス"""

    def __init__(self):
        self.initial_memory = psutil.Process().memory_info().rss
        self.peak_memory = self.initial_memory
        self.measurements = []

    def measure(self):
        """現在のリソース使用量測定"""
        process = psutil.Process()
        memory_usage = process.memory_info().rss
        cpu_percent = process.cpu_percent()

        self.peak_memory = max(self.peak_memory, memory_usage)

        measurement = {
            "timestamp": time.time(),
            "memory_rss": memory_usage,
            "memory_vms": process.memory_info().vms,
            "cpu_percent": cpu_percent,
            "thread_count": process.num_threads()
        }

        self.measurements.append(measurement)
        return measurement

    def get_summary(self):
        """リソース使用量サマリー"""
        if not self.measurements:
            return None

        memory_values = [m["memory_rss"] for m in self.measurements]
        cpu_values = [m["cpu_percent"] for m in self.measurements]

        return {
            "initial_memory_mb": self.initial_memory / 1024 / 1024,
            "peak_memory_mb": self.peak_memory / 1024 / 1024,
            "avg_memory_mb": mean(memory_values) / 1024 / 1024,
            "avg_cpu_percent": mean(cpu_values),
            "max_cpu_percent": max(cpu_values),
            "measurement_count": len(self.measurements)
        }
```

## 7. Phase 5: 実用性テスト

### **7.1 実使用シナリオテスト**

#### **停電時バックアップテスト**
```yaml
test_case: "DP3_014_停電バックアップ"
objective: "停電時のバックアップ動作確認"
test_scenario:
  1. 通常時の動作確認
  2. 模擬停電（AC入力遮断）
  3. バックアップ動作確認
  4. Home Assistantでの状態監視
  5. AC入力復旧
  6. 通常動作復帰確認

monitoring_items:
  - 切り替え時間
  - 負荷継続供給
  - バッテリー消費
  - 状態表示精度

pass_criteria:
  - 切り替え時間: 20ms以内
  - 負荷供給継続: 100%
  - 状態表示: 正確
```

#### **ソーラー充電テスト**
```yaml
test_case: "DP3_015_ソーラー充電"
objective: "ソーラー充電時の動作確認"
test_conditions:
  - ソーラーパネル接続
  - 晴天時テスト
  - 曇天時テスト

monitoring:
  - ソーラー入力電力
  - 充電効率
  - MPPT動作
  - Home Assistantでの表示

verification:
  - 最大電力点追従
  - 効率的な充電
  - 正確なデータ表示
```

### **7.2 ユーザビリティテスト**

#### **操作性評価**
```yaml
test_case: "DP3_016_操作性評価"
objective: "Home Assistantでの操作性確認"
evaluation_items:
  - エンティティ配置
  - 操作の直感性
  - 応答性
  - エラー表示

user_scenarios:
  - 初回設定
  - 日常的な操作
  - 設定変更
  - トラブル対応

evaluation_criteria:
  - 操作の分かりやすさ
  - 応答の速さ
  - エラー情報の有用性
```

## 8. 成果物・次ステップ

### **8.1 期待される成果物**
- [ ] **実機テスト結果レポート**: 全テストケースの結果
- [ ] **パフォーマンス測定データ**: 応答時間・リソース使用量
- [ ] **問題・改善点リスト**: 発見された課題と対策
- [ ] **実用性評価**: 実際の使用での評価結果
- [ ] **推奨設定・使用方法**: ベストプラクティス

### **8.2 品質基準**
- [ ] **基本機能テスト**: 100%成功
- [ ] **制御機能テスト**: 95%以上成功
- [ ] **負荷テスト**: 安定動作確認
- [ ] **パフォーマンス**: 要求仕様満足

### **8.3 次ステップへの引き継ぎ**
- [ ] **問題修正**: 発見された課題の対応
- [ ] **ドキュメント更新**: テスト結果反映
- [ ] **リリース準備**: 最終品質確認

---

## 備考

- **安全第一**: 実機テスト時の安全確保
- **詳細記録**: 全テスト結果の詳細記録
- **継続改善**: テスト結果を基にした継続的改善
- **実用性重視**: 実際の使用環境での検証

このタスクの完了により、DP3統合の実用性・安定性が確認され、安心してリリースできる品質が保証されます。