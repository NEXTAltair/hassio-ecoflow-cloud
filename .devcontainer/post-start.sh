#!/bin/bash

# NVM初期化
source /usr/local/share/nvm/nvm.sh

# npmパッケージのインストール
npm install -g @anthropic-ai/claude-code
npm install -g @google/gemini-cli

# bashrcにNVM設定を追加（重複チェック付き）
if ! grep -q "source /usr/local/share/nvm/nvm.sh" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# NVM initialization added by devcontainer postStartCommand" >> ~/.bashrc
    echo 'export NVM_DIR="/usr/local/share/nvm"' >> ~/.bashrc
    echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm' >> ~/.bashrc
    echo '[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" # This loads nvm bash_completion' >> ~/.bashrc
fi

# システムパッケージの更新
sudo apt-get update
sudo apt-get install -y xdg-utils

# ワークスペースに移動してHome Assistant設定をセットアップ
cd /workspace
echo "Setting up Home Assistant development environment..."
make setup
echo "Home Assistant development environment setup complete!"
echo ""
echo "=========================================="
echo "🚀 Home Assistant is ready!"
echo "🌐 Access URL: http://localhost:8123"
echo "📁 Config directory: /workspace/core/config"
echo "🔧 Custom components: /workspace/custom_components"
echo "📝 Log file: /workspace/core/config/home-assistant.log"
echo "⚙️  Make commands: make setup, make docs, make dev"
echo "=========================================="
echo ""
echo "💡 Tip: Use 'make setup' to restore configuration after core updates"
echo "💡 Tip: Use 'make docs' to generate device documentation"

# Home Assistant起動
sudo -E container launch