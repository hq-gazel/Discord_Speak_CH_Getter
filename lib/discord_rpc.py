"""pypresence を背景スレッドで動かし、現在の VC (guild_id, channel_id) を追従取得する。

OBS API には触れない。結果は Lock 付きの共有状態に格納し、呼び出し側が get_current()/status()
でポーリングする (OBS 側はメインスレッドの timer から参照する)。
"""

from __future__ import annotations

import asyncio
import threading
import time

from . import token_store


def parse_voice_payload(payload):
    """RPC 応答 / イベントから (guild_id, channel_id) を抽出する。

    - GET_SELECTED_VOICE_CHANNEL: data はチャンネルオブジェクト (id / guild_id を持つ)
    - VOICE_CHANNEL_SELECT イベント: data は {channel_id, guild_id}
    - VC 外 / DM 通話 / 退出時はいずれかが None
    pypresence のハンドラがフル payload・内側 data のどちらを渡しても扱えるようにする。
    """
    if not isinstance(payload, dict):
        return (None, None)
    data = payload
    if "data" in payload:
        inner = payload.get("data")
        if isinstance(inner, dict):
            data = inner
        else:  # data が None など (退出)
            return (None, None)
    channel_id = data.get("channel_id") or data.get("id")
    guild_id = data.get("guild_id")
    return (guild_id, channel_id)


def extract_auth_code(resp):
    """AUTHORIZE 応答から OAuth code を取り出す。"""
    if isinstance(resp, dict):
        inner = resp.get("data")
        if isinstance(inner, dict) and inner.get("code"):
            return inner["code"]
        if resp.get("code"):
            return resp["code"]
    return getattr(resp, "code", None)


def _default_log(msg):
    print(msg, flush=True)


HANDSHAKE_TIMEOUT = 15  # 秒: Discord IPC 接続確立 (READY 受信) の上限
AUTHORIZE_RESPONSE_TIMEOUT = 90  # 秒: ユーザーが認可ダイアログを操作するまでの猶予


def _start_with_timeout(client, *, timeout=HANDSHAKE_TIMEOUT):
    """pypresence の Client.start() は READY 応答待ちにタイムアウトが無く、
    Discord 側が応答しない場合に無期限でブロックするため、自前でタイムアウトを掛ける。"""
    client.loop.run_until_complete(asyncio.wait_for(client.handshake(), timeout))


def _authorize(client, client_id, scopes=("rpc",)):
    """RPC OAuth2 の AUTHORIZE コマンドは redirect_uri を受け付けない
    (Error 5000: Redirect URI cannot be used in the RPC OAuth2 Authorization flow)。
    redirect_uri はトークン交換 (token_store.exchange_code) の方でのみ使う。"""
    from pypresence.payloads import Payload

    payload = {
        "cmd": "AUTHORIZE",
        "args": {
            "client_id": str(client_id),
            "scopes": list(scopes),
        },
        "nonce": f"{Payload.time():.20f}",
    }
    client.send_data(1, payload)
    return client.loop.run_until_complete(client.read_output())


def _authorize_via_client(client, app_config, token_path, log):
    """接続済みの client を使って AUTHORIZE → code 交換 → トークン保存までを行う。"""
    log("[INFO] AUTHORIZE要求を送信します")
    resp = _authorize(client, app_config.client_id)
    log(f"[INFO] AUTHORIZE応答を受信しました: {resp!r}")
    code = extract_auth_code(resp)
    if not code:
        raise RuntimeError(f"AUTHORIZE 応答に code がありません: {resp!r}")
    log("[INFO] 認可コードを取得、アクセストークンに交換します")
    exchanged = token_store.exchange_code(
        app_config.client_id, app_config.client_secret, code, app_config.redirect_uri
    )
    saved = token_store.save_token(token_path, exchanged)
    log("[OK] 認可完了、トークンを保存しました")
    return saved


def authorize_now(app_config, token_path, *, log=_default_log):
    """フル認可フロー (AUTHORIZE → code 交換 → トークン保存) を単独で実行する。

    VoiceWatcher の背景接続とは別に一時的な Discord IPC 接続を張って完結するので、
    既存の watcher スレッドとは独立に (OBS のボタン等から) いつでも呼び出せる。
    """
    from pypresence import Client

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = Client(app_config.client_id, loop=loop, response_timeout=AUTHORIZE_RESPONSE_TIMEOUT)
    try:
        log("[INFO] Discord IPC へ接続中...")
        try:
            _start_with_timeout(client)
        except TimeoutError as exc:
            raise RuntimeError(
                "Discord IPC 接続がタイムアウトしました。"
                "Discordアプリが起動・ログイン済みか確認してください。"
            ) from exc
        log("[OK] IPC接続完了")
        saved = _authorize_via_client(client, app_config, token_path, log)
        client.authenticate(saved["access_token"])
        return saved
    finally:
        try:
            client.close()
        except Exception:
            pass


class VoiceWatcher:
    """Discord RPC に接続し、選択中の VC を追従するワーカー。"""

    def __init__(self, app_config, token_path, *, log=_default_log):
        self.cfg = app_config
        self.token_path = token_path
        self.log = log
        self._lock = threading.Lock()
        self._current = (None, None)
        self._connected = False
        self._error = None
        self._stop = threading.Event()
        self._thread = None
        self._loop = None

    # --- thread-safe state ---
    def get_current(self):
        with self._lock:
            return self._current

    def status(self):
        with self._lock:
            return {
                "connected": self._connected,
                "current": self._current,
                "error": self._error,
            }

    def _set_current(self, guild_id, channel_id):
        with self._lock:
            self._current = (guild_id, channel_id)

    def _set_connected(self, value, error=None):
        with self._lock:
            self._connected = value
            self._error = error

    # --- lifecycle ---
    def start(self):
        self._thread = threading.Thread(target=self._run, name="VoiceWatcher", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        loop = self._loop
        if loop is not None:
            try:
                loop.call_soon_threadsafe(loop.stop)
            except RuntimeError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=5)

    # --- worker ---
    def _new_loop(self):
        factory = getattr(asyncio, "ProactorEventLoop", None)  # Windows 名前付きパイプ対応
        return factory() if factory is not None else asyncio.new_event_loop()

    def _on_voice_select(self, data):
        guild_id, channel_id = parse_voice_payload(data)
        self._set_current(guild_id, channel_id)
        self.log(f"[INFO] VOICE_CHANNEL_SELECT guild={guild_id} channel={channel_id}")

    def _run(self):
        backoff = 2
        while not self._stop.is_set():
            try:
                self._connect_and_watch()
                backoff = 2
            except Exception as exc:
                self._set_connected(False, str(exc))
                if self._stop.is_set():
                    # stop() による意図的な切断 (loop.stop()) はエラーではないので静かに終える
                    self.log("[INFO] watcher: 停止要求により接続を中断しました")
                else:
                    self.log(f"[ERROR] watcher: {exc}")
            if self._stop.is_set():
                break
            time.sleep(min(backoff, 30))
            backoff = min(backoff * 2, 30)

    def _connect_and_watch(self):
        from pypresence import Client  # OBS の Python に導入済み前提 (遅延 import)

        loop = self._new_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        client = Client(self.cfg.client_id, loop=loop)
        try:
            try:
                _start_with_timeout(client)
            except TimeoutError as exc:
                raise RuntimeError(
                    "Discord IPC 接続がタイムアウトしました。"
                    "Discordアプリが起動・ログイン済みか確認してください。"
                ) from exc
            self._authenticate(client)
            self._set_connected(True)
            self.log("[OK] Discord RPC 認証成功")

            initial = client.get_selected_voice_channel()
            guild_id, channel_id = parse_voice_payload(initial)
            self._set_current(guild_id, channel_id)
            self.log(f"[INFO] 初期VC guild={guild_id} channel={channel_id}")

            client.register_event("VOICE_CHANNEL_SELECT", self._on_voice_select)
            client.subscribe("VOICE_CHANNEL_SELECT")

            loop.run_forever()  # イベント配信を継続 (stop() で停止)
        finally:
            self._set_connected(False)
            try:
                client.close()
            except Exception:
                pass

    def _authenticate(self, client):
        token = token_store.load_token(self.token_path)

        if token_store.is_valid(token):
            try:
                client.authenticate(token["access_token"])
                return
            except Exception as exc:
                self.log(f"[WARN] 既存トークンで認証失敗、更新/再認可します: {exc}")

        if token and token.get("refresh_token"):
            try:
                refreshed = token_store.refresh_access_token(
                    self.cfg.client_id, self.cfg.client_secret, token["refresh_token"]
                )
                saved = token_store.save_token(self.token_path, refreshed)
                client.authenticate(saved["access_token"])
                self.log("[OK] トークンをリフレッシュしました")
                return
            except Exception as exc:
                self.log(f"[WARN] リフレッシュ失敗、再認可します: {exc}")

        # フル認可フロー (初回は Discord クライアント上で認可ポップアップが出る)。
        # 既に接続済みの client をそのまま使う (新規に別接続を張ると二重接続になりタイムアウトするため)。
        saved = _authorize_via_client(client, self.cfg, self.token_path, self.log)
        client.authenticate(saved["access_token"])
