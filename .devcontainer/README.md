# 開発コンテナ（dev専用）

この設定・調査資料は`dev`に残し、還元用`main`へ一括マージしない。
HAは公式**2026.10.0**イメージ、編集・検証はDebian Dev Container＋uvを使う。
Python **3.14.6**は公式HAイメージ内の実測値に合わせた。
リリースソースの`.python-version`は3.14.5だが、配布イメージの実体とは異なる。
イメージdigestと開発依存のhash付きlockを固定し、再オープン時のインストールを省いた。
起動前の`initializeCommand`がDockerfileをビルドし、変更がなければキャッシュを使う。
Composeは作成済みのイメージを使う。WindowsでCompose BakeがDev Containersの
一時Dockerfileの読み取りを拒否したため、ビルドを通常の`docker build`に分けた。

## 初回・再オープン

1. Windows Docker Desktopを起動し、`desktop-linux` contextを使う。
2. VS Codeでこのリポジトリを開き、**Dev Containers: Rebuild and Reopen in Container**。
3. 初回のイメージ取得・ビルド後、postCreateが版とオフラインsmokeを確認する。
4. Composeが開発HAを起動し、postStartがHTTP準備完了を待つ。
5. Portsにある`homeassistant:8123`をブラウザーで開く。初回は開発用ユーザーを作る。

以後は**Reopen in Container**。HAのプロセスはComposeが管理し、postStartで重複起動しない。
VS Codeを閉じる際はこのComposeのサービスを停止する設定。専用volumeは残る。
8123が他の用途で使われていれば、VS Codeが提示する別のローカルポートを使う。

`test/test.env`や`.devcontainer/.env`は不要で、コンテナのenv-fileとして渡さない。
EcoFlow認証情報の自動注入は行わない。
既存の`core/config`・旧コンテナ・既存`.venv`は流用しない。
AI CLI・Serena・AI拡張は必須設定から外した。必要なものは利用者が任意で追加する。

## 検証

コンテナ内で`make check`（smoke・lint・型検査）。個別には:

```bash
make versions
make smoke
make lint
make typecheck
make status
make logs
```

VS Codeの`EcoFlow:`タスクも同じ入口を使う。
ruff/mypyのキャッシュはコンテナ内の`/home/vscode/.cache`へ置く。
Windowsのbind mountへの大量書き込みを避け、再オープン時には再利用する。
Gitの所有者チェックは編集コンテナ内で`/workspace`だけを許可する。
ホスト側のglobal Git設定は変更しない。
`smoke`は版、隔離設定、protobufの辞書変換、Python構文、生成済みprotobufの単独ロードを確認する。
統合の実接続・ロード成功を保証するものではない。旧テスト全体は自動実行しない。
`make docs`は生成物を書き換えるので、必要時だけ実行して差分を確認する。

現在の統合manifestは`protobuf==6.32.0`のままで、HA 2026.10.0の制約7.36.0と競合する。
この機能側の修正は次段階のupstream追従で扱う。開発HAにEcoFlowを設定しない。

### 2026-10-11の検証結果

| 確認 | 結果 |
| --- | --- |
| イメージビルド・新規作成 | 成功 |
| postCreate・オフラインsmoke | 成功。Python 72ファイルの構文、生成済みprotobuf 6ファイルのロード |
| postStart・HA準備完了 | 成功。HA 2026.10.0 / Python 3.14.6 / protobuf 7.36.0、HTTP応答とhealthcheck |
| 両サービス停止後の通常再オープン | 成功。同じコンテナID・volumeを再利用し、postCreate・依存インストールを再実行せず |
| コンテナ内Git・Linux側検査キャッシュ | 使用可能 |
| lint / 型検査 | 1,855件 / 4件の診断。`make check`は終了コード2で失敗を報告 |
| コンテナ起動後の8123へのHA接続 | ユーザーが確認済み |
| VS Code拡張の導入・動作、VS Code側のReopen操作 | 個別には未確認。必要時に確認する |

lintの1,731件は生成済みprotobufの`.py`/`.pyi`に出る。ツールはruff 0.17.0 / mypy 2.4.0。
統合コード・検査ルールは変更しておらず、この環境で検出した課題として記録した。
旧ツール版での比較は行っていない。型検査の4件はセンサーの継承と
`IntegrationSensor`の引数に関する診断で、機能側の互換性調査として次段階へ残す。
実機・EcoFlow接続と統合全体のロードは未検証。HA側にEcoFlow/MQTT設定は存在しない。

## 開発HAの停止・再起動とログ

ホストのPowerShellで、リポジトリ直下から:

```powershell
docker compose -f .devcontainer/compose.yaml ps
docker compose -f .devcontainer/compose.yaml logs --tail 100 homeassistant
docker compose -f .devcontainer/compose.yaml restart homeassistant
docker compose -f .devcontainer/compose.yaml stop homeassistant
docker compose -f .devcontainer/compose.yaml up -d homeassistant
```

コード変更はread-only bindで即座にHA側から見えるが、読み直しにはHAの再起動が必要。
HAのファイルログは専用volumeの`/config/home-assistant.log`。
開発側からは`/ha-state/home-assistant.log`を`make logs`で読む。
VS Code起動のログは**Dev Containers: Show Container Log**。

開発HAは最小設定と`internal`ネットワークで起動し、外向き通信を遮断する。
編集用コンテナだけは別の通常ネットワークにも接続し、Git・拡張・依存更新を利用できる。
家庭向け設定・実機認証情報を持ち込まず、機器探索・MQTT・EcoFlow接続を設定しない。
Docker socket・ホストネットワーク・デバイスのmountも使わない。

## 依存更新

HA版を変えるときは`compose.yaml`のタグ/digestと`requirements.in`のHA版を揃える。
公式イメージ内のPython版・同リリースの`homeassistant/package_constraints.txt`のprotobuf制約も確認する。
Pythonを変更する場合は`Dockerfile`のARG・ルート`.python-version`・`mise.toml`、
`dev.sh`の版検査も揃える。後者のHA/protobuf版検査も対象リリースに合わせる。
開発依存はWindowsに既存のuvがある場合、PowerShellで更新できる:

```powershell
uv pip compile --no-config --python-version 3.14.6 --python-platform x86_64-unknown-linux-gnu --generate-hashes .devcontainer/requirements.in -o .devcontainer/requirements.lock
```

lock差分を確認し、**Rebuild Container**して`make check`を実行する。
lock生成・イメージビルドには通信が必要。HAの隔離ネットワークは維持する。

## 保全・rollback

変更前の16ファイルと保護対象のhashは
`.git/codex-backups/container-20261011-165104/`へ退避した。
rollbackはこの退避と差分を比較し、今回変更したファイルだけを戻す。
ユーザーの`.cursor`削除・protoコメント変更、先行した資料整理をまとめて戻さない。
新しいHA状態volumeや旧コンテナを削除する必要はない。
今回追加したファイルは`Dockerfile`・`.dockerignore`・`compose.yaml`・`dev.sh`・
`requirements.in`・`requirements.lock`・`ha-config/configuration.yaml`・この手順書。
不要になったものだけを個別に扱い、`.devcontainer`全体や既存設定を一括削除しない。
