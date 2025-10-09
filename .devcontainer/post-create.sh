#!/bin/bash

# コンテナビルド時のみ実行されるスクリプト

# NVM初期化
source /usr/local/share/nvm/nvm.sh

# npmパッケージのインストール
npm install -g @anthropic-ai/claude-code
npm install -g @google/gemini-cli

# bashrcにNVM設定を追加（重複チェック付き）
if ! grep -q "source /usr/local/share/nvm/nvm.sh" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# NVM initialization added by devcontainer postCreateCommand" >> ~/.bashrc
    echo 'export NVM_DIR="/usr/local/share/nvm"' >> ~/.bashrc
    echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm' >> ~/.bashrc
    echo '[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" # This loads nvm bash_completion' >> ~/.bashrc
fi

# システムパッケージの更新
sudo apt-get update
sudo apt-get install -y xdg-utils

# Serena専用キャッシュディレクトリの作成と権限設定
mkdir -p /home/vscode/.cache/uv-serena
sudo chown -R vscode:vscode /home/vscode/.cache/uv-serena

# Serena MCP設定（コンテナビルド時のみ）
if command -v claude &> /dev/null; then
    echo "Configuring Serena MCP for Claude Code..."
    # 既存のSerena設定を削除
    claude mcp remove serena 2>/dev/null || true
    # 新規設定を追加（UV_CACHE_DIR環境変数付き）
    bash -lc "claude mcp add --transport stdio serena --env UV_CACHE_DIR=/home/vscode/.cache/uv-serena -- uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant --project /workspaces/hassio-ecoflow-cloud"
    echo "Serena MCP configured successfully"
    echo "Note: Restart Claude Code for changes to take effect"
fi

echo "post-create.sh completed"
