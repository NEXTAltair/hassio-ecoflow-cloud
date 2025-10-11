# Serena MCP接続タイムアウト問題 - トラブルシューティング記録

## 問題概要

Claude CodeでSerena MCPサーバーへの接続が30秒でタイムアウトし、`Failed to connect`エラーが発生する問題。

**発生日時**: 2025-10-10
**環境**: VS Code Dev Container (Debian/Ubuntu), WSL2

## 症状

```
> /mcp
serena: ✗ Failed to connect
Connection to MCP server "serena" timed out after 30000ms
```

## 根本原因の特定

### タイムライン分析

**成功したケース**:
```
15:36:12.445 - Claude Code接続開始
15:36:13.605 - Serenaプロセス起動 (1.16秒後)
15:36:37.799 - MCP準備完了 (約25秒後)
結果: 接続成功 ✅
```

**失敗したケース**:
```
04:13:57.979 - Claude Code接続開始
04:14:27.985 - タイムアウト発生 (30秒経過)
04:14:33.438 - Serenaプロセス起動 (35.46秒後) ❌
結果: タイムアウトにより接続失敗
```

### 原因

1. **uvxの起動遅延が不安定**
   - 成功時: 1.16秒
   - 失敗時: 35秒以上
   - `uvx --from git+https://github.com/oraios/serena`の起動時間が変動

2. **Claude CodeのMCPタイムアウトが固定**
   - ハードコードされた30秒タイムアウト
   - Serenaプロセス起動前にタイムアウト

3. **Serena自体の初期化は高速**
   - Gitignore処理: 0.33秒
   - Language Server初期化: 0.58秒
   - 合計: 約0.9秒

## パフォーマンス改善の履歴

### 第1回最適化 (コミット 33aa594)

**変更内容**:
- `.gitignore`に`core/`追加（1.8GB、15,000+ファイル除外）
- `pyrightconfig.json`作成（Pyrightスキャン対象を最小化）
- `.serena/project.yml`の`ignored_paths`修正

**結果**:
- Gitignore処理: 32.3秒 → 0.33秒 (98%削減)
- Pyrightスキャン: 15,210ファイル → 75ファイル (99.5%削減)
- Serena初期化: 38秒+ → 0.9秒 (97%削減)

**しかし**: uvxの起動遅延問題は未解決

### 第2回最適化 (2025-10-10)

**GitHub Issuesで発見した情報**:
- [Issue #617](https://github.com/oraios/serena/issues/617): Codexでのタイムアウト報告
- [Issue #494](https://github.com/oraios/serena/issues/494): Claude Codeでの接続失敗
- 公式ドキュメント: 大規模プロジェクトは**プロジェクトインデックス**推奨

**実施した対策**:

1. **プロジェクトインデックスの作成**
   ```bash
   uvx --from git+https://github.com/oraios/serena serena project index
   ```
   - 93ファイルをインデックス化（33秒）
   - シンボルキャッシュ作成: `.serena/cache/python/document_symbols_cache_v23-06-25.pkl`
   - 初回ツール適用の遅延を防止

2. **ログレベルの最適化**
   ```json
   {
     "env": {
       "SERENA_LOG_LEVEL": "INFO"  // DEBUG → INFO
     }
   }
   ```
   - 不要な詳細ログを削減
   - stderr出力量の減少

**結果**:
- `/mcp`コマンドで接続成功 ✅
- **Claude Code再起動後も正常動作確認済み** ✅
  - 初期化時間: 約2秒（Gitignore 0.334秒 + Language Server 0.681秒）
  - MCPツール動作確認: `list_dir`が0.004秒で実行成功
  - Pyrightスキャン: 75ファイル（最適化済み）

## 設定ファイル

### `.claude/settings.local.json`
現在の設定（変更なし）:
```json
{
  "permissions": {
    "allow": [
      "mcp__serena__*",
      ...
    ]
  }
}
```

### `~/.claude.json` (MCP設定)
```json
{
  "projects": {
    "/workspaces/hassio-ecoflow-cloud": {
      "mcpServers": {
        "serena": {
          "type": "stdio",
          "command": "uvx",
          "args": [
            "--from",
            "git+https://github.com/oraios/serena",
            "serena",
            "start-mcp-server",
            "--context",
            "ide-assistant",
            "--project",
            "/workspaces/hassio-ecoflow-cloud"
          ],
          "env": {
            "UV_CACHE_DIR": "/home/vscode/.cache/uv-serena",
            "SERENA_LOG_LEVEL": "INFO"
          }
        }
      }
    }
  }
}
```

### `.serena/project.yml`
```yaml
language: python
ignore_all_files_in_gitignore: true
ignored_paths: ["core"]
read_only: false
excluded_tools: []
initial_prompt: ""
project_name: "hassio-ecoflow-cloud"
log_level: DEBUG
```

### `pyrightconfig.json`
```json
{
  "include": ["custom_components/ecoflow_cloud"],
  "exclude": ["core", "**/node_modules", "**/__pycache__", ".git", ".venv", "venv"],
  "pythonVersion": "3.13",
  "typeCheckingMode": "basic"
}
```

### `.gitignore`
```
# Exclude Home Assistant core repository
core/
```

## 推奨事項

### 今後の運用

1. **定期的なインデックス再作成**
   ```bash
   uvx --from git+https://github.com/oraios/serena serena project index
   ```
   - コードベース大幅変更後
   - 新規ファイル追加後

2. **ログレベルの使い分け**
   - 通常運用: `INFO`
   - デバッグ時: `DEBUG`

3. **キャッシュクリア（必要時）**
   ```bash
   rm -rf ~/.cache/uv-serena/git-v0/locks/*
   ```

### トラブルシューティング手順

1. **接続失敗時**
   ```bash
   # プロセス確認
   ps aux | grep serena

   # ログ確認
   tail -100 ~/.serena/logs/$(date +%Y-%m-%d)/mcp_*.txt

   # Claude CLIログ
   ls -lt ~/.cache/claude-cli-nodejs/-workspaces-*/mcp-logs-serena/
   ```

2. **プロセス再起動**
   ```bash
   pkill -9 -f "serena start-mcp-server"
   /mcp
   ```

3. **キャッシュ確認**
   ```bash
   du -sh ~/.cache/uv-serena/
   ls -la /workspaces/hassio-ecoflow-cloud/.serena/cache/
   ```

## 参考リンク

- [Serena GitHub Repository](https://github.com/oraios/serena)
- [Issue #617: MCP timeout in Codex](https://github.com/oraios/serena/issues/617)
- [Issue #494: Failed to connect in Claude Code](https://github.com/oraios/serena/issues/494)
- [Issue #470: Gitignore parsing hang](https://github.com/oraios/serena/issues/470)

## 学んだ教訓

1. **Serena自体は高速** - 問題はuvx起動時間
2. **プロジェクトインデックスは必須** - 公式推奨を最初から従うべき
3. **ログはSerenaのstderr** - Claude Codeが"error"として記録するが正常
4. **タイムアウトはClaude Code側** - Serena側で調整不可

## ステータス

- [x] 根本原因特定
- [x] Pyrightスキャン最適化
- [x] Gitignore処理最適化
- [x] プロジェクトインデックス作成
- [x] ログレベル最適化
- [x] `/mcp`コマンドで接続確認
- [x] Claude Code再起動後の動作確認
- [ ] Dev Container再ビルド後の動作確認（次のステップ）

## Dev Container再ビルド時の注意事項

### 必要な手順

コンテナ再ビルド後は以下のセットアップが必要：

1. **Serena MCP設定の確認**
   ```bash
   cat ~/.claude.json | jq '.projects["/workspaces/hassio-ecoflow-cloud"].mcpServers.serena'
   ```
   - 設定が保持されているか確認
   - `SERENA_LOG_LEVEL: INFO`になっているか確認

2. **プロジェクトインデックスの再作成**
   ```bash
   uvx --from git+https://github.com/oraios/serena serena project index
   ```
   - キャッシュ（`.serena/cache/`）がコミットされている場合は不要
   - 念のため実行推奨

3. **接続確認**
   ```bash
   /mcp
   ```

### 期待される動作

- Serena初期化: 2秒以内
- MCPツール利用可能
- タイムアウトなし

---
作成日: 2025-10-10
最終更新: 2025-10-11
