# セットアップ詳細

`auto` モード (RPC 自動検出) を使う場合の手順。`manual` モードのみで使う場合は
手順 1・4 を飛ばし、`cfg/config.json` の `mode` を `manual` にして
`manual.guild_id` / `manual.channel_id` を記入するだけでよい。

---

## 1. Discord アプリの作成

1. [Discord Developer Portal](https://discord.com/developers/applications) を開く。
2. **New Application** でアプリを作成する。
   - > [!IMPORTANT]
   - > **必ず「個人所有」にすること。** チーム (Team) に紐づくアプリは RPC の制限により
   - > OAuth2 の scope エラーになり使用できない。
3. 左メニュー **OAuth2** を開く。
   - **Redirects** に Redirect URI を追加する（例: `http://localhost:3000/callback`）。
     ここで登録した値と `cfg/config.json` の `redirect_uri` を**完全一致**させる。
   - **Client ID** と **Client Secret** を控える（Secret は Reset Secret で再表示できる）。
     手順 5 で OBS スクリプトの GUI に入力する。
4. **rpc スコープの allowlist (テスター) 登録**
   - `rpc` スコープは未承認アプリでは利用が制限されており、アプリの **テスター (allowlist)**
     に登録されたユーザーのみが使える（最大 50 名）。
   - OAuth2 設定内のテスター/メンバー欄に、**自分の Discord ユーザー ID** を追加する。
   - 自分のユーザー ID は、Discord クライアントで [設定 > 詳細設定 > 開発者モード] を ON にした上で、
     自分のアイコンを右クリック → 「ユーザー ID をコピー」で取得できる。

## 2. OBS の Python を設定

1. OBS を起動し、[ツール > スクリプト] を開く。
2. **[Python設定]** タブで、**Python 3.12** のインストールフォルダ
   （`python312.dll` がある場所）を指定する。
   - 例: `C:\Users\<you>\AppData\Local\Programs\Python\Python312`
   - OBS が対応する Python のマイナーバージョン (3.6–3.12) に合わせる。

## 3. 依存ライブラリの導入

OBS が手順 2 で指した Python に対して `pypresence` を入れる（venv は使わない）。

```pwsh
uv pip install --python "C:\Users\<you>\AppData\Local\Programs\Python\Python312\python.exe" -r requirements.txt
```

> OBS が import するのはこの Python なので、必ず**同じ Python** に入れること。

## 4. 動作確認 (OBS 無し・任意)

スクリプト登録の前に、Discord 検出が通るか単体で確認できる
（手順 1 で控えた Client ID / Client Secret を引数で渡す）。

```pwsh
& "C:\Users\<you>\AppData\Local\Programs\Python\Python312\python.exe" -m lib.cli `
    --client-id "手順1のClient ID" --client-secret "手順1のClient Secret"
```

- 初回は Discord クライアント上に**認可ポップアップ**が出るので許可する。
- 現在の VC の `guild` / `channel` と StreamKit URL が表示されれば成功。
- 成功すると `cfg/token.json` にトークンがキャッシュされ、以後は自動認証になる。

## 5. OBS スクリプトの登録

1. OBS の [ツール > スクリプト] → **[スクリプト]** タブ → `+` で `obs_discord_vc.py` を追加。
2. プロパティの **「話者ソース」** で、URL を反映したいブラウザソースを選択
   （ドロップダウンには既存の browser_source が並ぶ。任意入力も可）。
3. **Discord Client ID** / **Discord Client Secret** の欄に手順 1 の値を入力する
   （パスワード欄としてマスク表示される。OBS のシーンコレクション設定に保存される）。
   - **「OBS起動時に自動接続」** チェックボックスは既定 **OFF**。OFF のままだと
     従来通りスクリプト読込時には接続せず、**[Discord接続を開始]** ボタンを押すまで
     Discord IPC に接続しない。ON にすると、OBS起動時/スクリプト読込時に
     ボタン操作なしで自動的に接続を開始する。
4. VC に参加すると、選択したブラウザソースの URL が StreamKit URL に自動更新される。
5. 設定 (`cfg/config.json` や Client ID/Secret) を変更したら、プロパティの **[設定リロード]** を押す。

## トラブルシュート

| 症状 | 対処 |
| --- | --- |
| スクリプトログに import エラー (pypresence) | 手順 3 を OBS が指す Python に対して実行したか確認 |
| `scope` / `4006` エラー | アプリが個人所有か、テスター (allowlist) に自分を登録したか確認 |
| 認可後に token が保存されない | `redirect_uri` がアプリ登録値と一致しているか確認 |
| ソース未検出の警告 | OBS プロパティで正しいブラウザソース名を選択しているか確認 |
| URL が更新されない | [スクリプトログ] を開き `[OK]/[WARN]/[ERROR]` を確認 |
| Client ID/Secret を入力しても反映されない | 入力後にプロパティの **[設定リロード]** を押したか確認 |
| 自動接続をONにしたのに接続しない | OBS再起動、またはスクリプトの再読込 (一度削除して再追加) が必要 |

ログは OBS の [ツール > スクリプト] 画面下部の **[スクリプトログ]** に出力される。
