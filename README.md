# discord_ch_to_obs

今いる **Discord のボイスチャンネル (VC)** を自動検出して、[StreamKit Voice Widget](https://streamkit.discord.com/overlay) の URL を **OBS のブラウザソースへ自動反映**する OBS 埋め込みスクリプト。

VC を移動・入退室するたびに URL が自動で書き換わるので、配信中に手作業で貼り替える必要がない。

## 必要なもの

- OBS Studio
- Python 3.12 (OBS の [ツール > スクリプト > Python設定] で指定するもの)
- Discord アプリ (デスクトップ版、起動・ログイン済み)

## クイックセットアップ

詳しい手順・トラブルシュートは **[docs/setup.md](docs/setup.md)** を参照。ここでは流れだけ:

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリを**個人所有**で作成
   - OAuth2 の **Redirects** に `http://localhost:3000/callback` を登録
   - OAuth2 の **テスター欄** に自分の Discord ユーザー ID を登録 (rpc スコープ利用に必須)
   - Client ID / Client Secret を控える
2. OBS の [Python設定] で Python 3.12 のフォルダを指定
3. その Python に依存を導入 (venv は使わない)
   ```pwsh
   uv pip install --python "<OBSが指すPython>\python.exe" -r requirements.txt
   ```
4. OBS の [スクリプト] タブで `obs_discord_vc.py` を追加し、プロパティで
   **話者ソース** を選択、**Client ID / Client Secret** を入力
   - 「**OBS起動時に自動接続**」チェックボックス (既定OFF) をONにすると、
     ボタン操作なしで OBS起動時/スクリプト読込時に自動で Discord IPC 接続を開始する

初回のみ Discord 上に認可ポップアップが出るので許可する (以後は `cfg/token.json` で自動認証)。

## 動作モード (`cfg/config.json` の `mode`)

| mode | 説明 |
| --- | --- |
| `auto` | RPC で現在 VC を自動検出・追従 (既定)。Client ID/Secret が必要 |
| `manual` | `manual.guild_id` / `manual.channel_id` から固定 URL を生成 (RPC 不使用) |

## 設定ファイル (`cfg/config.json`)

| キー | 既定 | 説明 |
| --- | --- | --- |
| `mode` | `"auto"` | `"auto"` / `"manual"` |
| `source_name` | `"話者"` | 反映先ブラウザソース名 (OBS プロパティの選択が優先) |
| `redirect_uri` | `"http://localhost:3000/callback"` | Developer Portal の Redirect と完全一致させる |
| `manual.guild_id` / `manual.channel_id` | `""` | manual モード用の ID |
| `streamkit.*` | 省略時は既定 | StreamKit overlay の表示オプション (`icon`/`online`/`logo`/`small`) |
| `on_leave` | `"keep"` | VC 退出時の挙動。`"keep"`=据え置き / `"blank"`=about:blank |

秘匿情報 (`client_id` / `client_secret`) は `config.json` には書かず、**OBS スクリプトのプロパティ画面**に入力する。

## 困ったら

まず OBS の [スクリプトログ] を確認。よくあるエラーと対処は **[docs/setup.md のトラブルシュート](docs/setup.md#トラブルシュート)** にまとめてある。

## 既知の制約

- **rpc スコープ**: 未承認アプリはテスター (allowlist) 登録ユーザーのみ利用可
- **チーム所有アプリ不可**: RPC 制限で scope エラーになるため必ず個人所有アプリにする
- **DM / グループ通話**: `guild_id` が無く StreamKit URL を生成できない (更新スキップ)
- **秘匿情報の保存先**: Client ID/Secret は OBS のシーンコレクション設定に**平文で保存**される

## 開発

```pwsh
uv run --no-project --with pytest pytest -q   # テスト
ruff check --fix .                             # Lint (format は使わない)
```