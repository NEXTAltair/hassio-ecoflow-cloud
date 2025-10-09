#!/bin/bash

# コンテナ起動時に毎回実行されるスクリプト

# 古いSerenaプロセスをクリーンアップ
echo "Cleaning up old Serena processes..."
pkill -f "serena start-mcp-server" 2>/dev/null || true

# Home Assistant起動
sudo -E container launch