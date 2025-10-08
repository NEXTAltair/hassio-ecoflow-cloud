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

# Home Assistant起動
sudo -E container launch