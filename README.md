# discord_ch_to_obs

現在自分が入っている **Discord のボイスチャンネル (VC)** を自動検出し、対応する
[StreamKit Voice Widget](https://streamkit.discord.com/overlay) の overlay URL を
**OBS のブラウザソース「話者」に自動で反映**する OBS 埋め込み Python スクリプト。

VC を移動・入退室するたびに URL が自動で書き換わるので、配信中に手作業で貼り替える必要がない。

## 仕組み

- **Discord 検出**: Discord IPC (RPC) に `pypresence` で接続し、`GET_SELECTED_VOICE_CHANNEL` で
  現在の VC を取得 → `VOICE_CHANNEL_SELECT` イベントを購読して以後の変化に追従。
- **OBS 反映**: OBS プロセス内から `obspython` API で対象ブラウザソースの `url` を直接更新
  （obs-websocket は不要）。
- **スレッド分離**: Discord IPC / asyncio は背景スレッドに隔離し、OBS API 呼び出しは
  OBS メインスレッドの timer コールバックでのみ実行する。

```
OBS [ツール>スクリプト] → obs_discord_vc.py
   ├─[背景スレッド] lib/discord_rpc.py  … pypresence で現在VC取得・追従
   └─[OBSメインスレッド] timer → lib/url_builder.py → lib/obs_source.py で「話者」更新
```

## 動作モード

`cfg/config.json` の `mode` で切替:

| mode | 説明 |
| --- | --- |
| `auto` | RPC で現在 VC を自動検出・追従 (既定)。OBS スクリプトのプロパティで client_id/secret が必要 |
| `manual` | `cfg/config.json` の `manual.guild_id` / `manual.channel_id` から URL を生成 (RPC 不使用) |

## セットアップ

詳細は [docs/setup.md](docs/setup.md) を参照。要点のみ:

1. **Discord アプリ作成** (個人所有。チーム所有は RPC 制限で不可)
   - [Developer Portal](https://discord.com/developers/applications) で New Application
   - OAuth2 に Redirect を登録 (既定 `http://localhost:3000/callback`)
   - OAuth2 のテスター欄に **自分の Discord ユーザー ID** を登録 (rpc スコープ利用に必須)
   - Client ID / Client Secret を控えておく (手順 4 で OBS の GUI に入力する)
2. **OBS の Python を設定**: OBS の [ツール > スクリプト > Python設定] で Python 3.12 の
   インストールフォルダを指定
3. **依存を OBS の Python へ導入** (venv は使わない):
   ```pwsh
   uv pip install --python "<上で指定したPython>\python.exe" -r requirements.txt
   ```
4. **スクリプト登録**: [スクリプト] タブで `obs_discord_vc.py` を追加 → プロパティで
   **「話者ソース」を選択**し、**Discord Client ID / Client Secret を入力**する
   (パスワード欄としてマスク表示される)

初回起動時、Discord クライアント上に認可ポップアップが出るので許可する
（以後は `cfg/token.json` のキャッシュで自動認証）。

## 設定ファイル (`cfg/config.json`)

| キー | 既定 | 説明 |
| --- | --- | --- |
| `mode` | `"auto"` | `"auto"` / `"manual"` |
| `source_name` | `"話者"` | 反映先 OBS ブラウザソース名 (OBS プロパティの選択が優先) |
| `redirect_uri` | `"http://localhost:3000/callback"` | Discord アプリに登録した Redirect と一致させる |
| `manual.guild_id` | `""` | manual モードのサーバー ID |
| `manual.channel_id` | `""` | manual モードの VC チャンネル ID |
| `streamkit.icon` | `true` | StreamKit overlay の表示オプション |
| `streamkit.online` | `true` | 同上 |
| `streamkit.logo` | `"white"` | 同上 |
| `on_leave` | `"keep"` | VC 退出時の挙動。`"keep"`=据え置き / `"blank"`=about:blank |

秘匿情報 (`client_id` / `client_secret`) は `config.json` には書かない。
**OBS スクリプトのプロパティ画面 (パスワード欄)** に入力し、OBS のシーンコレクション設定に保存される。

## 動作確認 (OBS 無し)

Discord 検出部分だけを切り分けて確認できる (mode=auto の場合は引数で client_id/secret を渡す):

```pwsh
& "<OBSのPython>\python.exe" -m lib.cli --client-id XXXX --client-secret YYYY
```

現在の VC の guild/channel と生成された StreamKit URL が表示される。

## 開発

```pwsh
# テスト (lib 純関数は pypresence 非依存なのでどの Python でも可)
uv run --no-project --with pytest pytest -q

# Lint (format は使わない)
ruff check --fix .
```

## 既知の制約

- **rpc スコープ**: 未承認アプリは OAuth2 のテスター (allowlist) 登録ユーザーのみ利用可。自分を登録すれば個人利用は可能。
- **チーム所有アプリ不可**: RPC 制限により scope エラーになる。必ず個人所有アプリにする。
- **DM / グループ通話**: `guild_id` が無いため StreamKit Voice Widget URL を生成不可（更新スキップ）。
- **OBS 組込 Python**: `pypresence` は OBS が指すインタプリタ自体に導入する（venv 不使用、Python 3.12 推奨）。
- **秘匿情報の保存先**: Client ID/Secret は OBS のスクリプトプロパティに入力すると、
  OBS のシーンコレクション設定ファイルに**平文で保存**される。他人と共有する場合は注意。

## 参考

- 先行 C# 実装: <https://github.com/dichternebel/voice-channel-grabber>
- StreamKit Overlay: <https://streamkit.discord.com/overlay>
- pypresence: <https://qwertyquerty.github.io/pypresence/>
# Discord_Speak_CH_Getter
