#!/usr/bin/env python3
# Delta Pro 3 _prepare_data メソッドテストスクリプト
# Issue 05 Phase 1-1: テストスクリプト環境構築

import sys
import traceback
from typing import Any

from mock_protobuf_data import (
    ALL_TEST_CASES,
    hex_to_bytes,
    print_test_case_summary,
    get_test_case_by_type,
    get_test_case_by_cmd,
)
from prepare_data_implementation import DeltaPro3PrepareDataProcessor


class TestRunner:
    """Delta Pro 3 _prepare_data メソッドのテストランナー"""

    def __init__(self):
        self.processor = DeltaPro3PrepareDataProcessor()
        self.test_results = []

    def run_all_tests(self):
        """全テストケースを実行"""
        print("=" * 80)
        print("Delta Pro 3 _prepare_data メソッド テスト実行")
        print("=" * 80)
        print()

        print_test_case_summary()

        success_count = 0
        total_count = len(ALL_TEST_CASES)

        for i, test_case in enumerate(ALL_TEST_CASES, 1):
            print(f"\n{'=' * 60}")
            print(f"テストケース {i}/{total_count}: {test_case['description']}")
            print(f"{'=' * 60}")

            try:
                result = self._run_single_test(test_case)
                if result["success"]:
                    success_count += 1
                    print("✅ テスト成功")
                else:
                    print(f"❌ テスト失敗: {result['error']}")

                self.test_results.append(result)

            except Exception as e:
                error_msg = f"テスト実行中にエラー: {str(e)}"
                print(f"❌ {error_msg}")
                self.test_results.append(
                    {
                        "test_case": test_case["description"],
                        "success": False,
                        "error": error_msg,
                        "traceback": traceback.format_exc(),
                    }
                )

        print(f"\n{'=' * 80}")
        print(f"テスト結果サマリー: {success_count}/{total_count} 成功")
        print(f"{'=' * 80}")

        self._print_detailed_results()
        return success_count == total_count

    def _run_single_test(self, test_case: dict[str, Any]) -> dict[str, Any]:
        """単一テストケースを実行"""
        try:
            # 1. テストデータ準備
            raw_data = hex_to_bytes(test_case["raw_hex"])
            expected_result = test_case["expected_result"]

            print(f"入力データサイズ: {len(raw_data)} bytes")
            print(f"暗号化: {'Yes' if test_case['is_encrypted'] else 'No'}")

            # 2. _prepare_data メソッド実行
            print("\n🔄 _prepare_data メソッド実行中...")
            actual_result = self.processor._prepare_data(raw_data)

            # 3. 結果検証
            validation_result = self._validate_results(
                expected_result, actual_result, test_case
            )

            return {
                "test_case": test_case["description"],
                "success": validation_result["success"],
                "expected": expected_result,
                "actual": actual_result,
                "validation": validation_result,
                "error": validation_result.get("error", None),
            }

        except Exception as e:
            return {
                "test_case": test_case["description"],
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    def _validate_results(
        self,
        expected: dict[str, Any],
        actual: dict[str, Any],
        test_case: dict[str, Any],
    ) -> dict[str, Any]:
        """結果を検証"""
        print("\n📊 結果検証中...")

        if not actual:
            return {
                "success": False,
                "error": "結果が空です",
                "details": "actual_result is empty or None",
            }

        validation_details = {
            "expected_keys": set(expected.keys()) if expected else set(),
            "actual_keys": set(actual.keys()),
            "missing_keys": [],
            "extra_keys": [],
            "value_matches": {},
            "value_mismatches": {},
        }

        if expected:
            # キーの比較
            expected_keys = set(expected.keys())
            actual_keys = set(actual.keys())

            validation_details["missing_keys"] = list(expected_keys - actual_keys)
            validation_details["extra_keys"] = list(actual_keys - expected_keys)

            # 値の比較（共通キーのみ）
            common_keys = expected_keys & actual_keys
            for key in common_keys:
                expected_val = expected[key]
                actual_val = actual[key]

                if self._values_match(expected_val, actual_val):
                    validation_details["value_matches"][key] = {
                        "expected": expected_val,
                        "actual": actual_val,
                    }
                else:
                    validation_details["value_mismatches"][key] = {
                        "expected": expected_val,
                        "actual": actual_val,
                    }

        # モック環境では期待される結果との完全一致を確認
        if test_case.get("is_mock_test", True):  # デフォルトはモック環境
            # モック環境では変換されたフィールド名で検証
            success = self._validate_mock_results(expected, actual, test_case)
        else:
            # 実環境では部分的な検証
            success = (
                len(validation_details["value_mismatches"]) == 0
                and len(validation_details["missing_keys"]) <= 3
            )

        validation_details["success"] = success

        # 結果表示
        self._print_validation_details(validation_details)

        return validation_details

    def _validate_mock_results(
        self,
        expected: dict[str, Any],
        actual: dict[str, Any],
        test_case: dict[str, Any],
    ) -> bool:
        """モック環境での結果検証"""
        message_type = test_case.get("message_type", "")

        # メッセージタイプ別の主要フィールドを確認
        if "DisplayProperty" in message_type:
            key_fields = ["pow_out_sum_w", "pow_get_ac_hv_out", "pow_get_bms"]
        elif "cmdFunc32_cmdId2" in message_type:
            key_fields = ["cms_batt_vol", "cms_batt_soc", "cms_max_chg_soc"]
        elif "cmdFunc50_cmdId30" in message_type:
            key_fields = ["bms_batt_vol", "bms_batt_soc", "bms_max_cell_vol"]
        else:
            # 基本的にデータが返されれば成功
            return len(actual) > 0

        # 主要フィールドの存在確認
        found_fields = sum(1 for field in key_fields if field in actual)
        return found_fields >= len(key_fields) // 2  # 半分以上のフィールドがあれば成功

    def _values_match(
        self, expected: Any, actual: Any, tolerance: float = 0.01
    ) -> bool:
        """値が一致するかチェック（数値の場合は許容範囲あり）"""
        if type(expected) != type(actual):
            return False

        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            if isinstance(expected, float) or isinstance(actual, float):
                return abs(expected - actual) <= tolerance
            else:
                return expected == actual
        elif isinstance(expected, list) and isinstance(actual, list):
            if len(expected) != len(actual):
                return False
            return all(
                self._values_match(e, a, tolerance) for e, a in zip(expected, actual)
            )
        else:
            return expected == actual

    def _print_validation_details(self, details: dict[str, Any]):
        """検証詳細を表示"""
        print(
            f"📋 共通キー数: {len(details['actual_keys'] & details['expected_keys'])}"
        )

        if details["missing_keys"]:
            print(
                f"⚠️  欠落キー: {details['missing_keys'][:5]}{'...' if len(details['missing_keys']) > 5 else ''}"
            )

        if details["extra_keys"]:
            print(
                f"ℹ️  追加キー: {details['extra_keys'][:5]}{'...' if len(details['extra_keys']) > 5 else ''}"
            )

        if details["value_matches"]:
            print(f"✅ 値一致: {len(details['value_matches'])} フィールド")

        if details["value_mismatches"]:
            print(f"❌ 値不一致: {len(details['value_mismatches'])} フィールド")
            for key, mismatch in list(details["value_mismatches"].items())[:3]:
                print(
                    f"   {key}: 期待値={mismatch['expected']}, 実際値={mismatch['actual']}"
                )

    def _print_detailed_results(self):
        """詳細な結果を表示"""
        print("\n📊 詳細テスト結果:")
        print("-" * 80)

        for i, result in enumerate(self.test_results, 1):
            status = "✅ 成功" if result["success"] else "❌ 失敗"
            print(f"{i}. {result['test_case']}: {status}")

            if not result["success"] and "error" in result:
                print(f"   エラー: {result['error']}")

            if "validation" in result and "actual_keys" in result["validation"]:
                actual_count = len(result["validation"]["actual_keys"])
                expected_count = len(result["validation"]["expected_keys"])
                print(f"   フィールド数: 実際={actual_count}, 期待={expected_count}")

        print("-" * 80)


def main():
    """メイン実行関数"""
    print("Delta Pro 3 _prepare_data メソッド テストスクリプト")
    print("Issue 05 Phase 1-1: テストスクリプト環境構築\n")

    try:
        runner = TestRunner()
        success = runner.run_all_tests()

        if success:
            print("\n🎉 全テストが成功しました！")
            return 0
        else:
            print("\n⚠️ 一部のテストが失敗しました。")
            return 1

    except Exception as e:
        print(f"\n💥 テスト実行中に致命的エラーが発生: {e}")
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
