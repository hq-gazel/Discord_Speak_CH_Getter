"""OBS 埋め込みスクリプト: 現在の Discord VC を StreamKit URL に変換し指定ブラウザソースへ自動反映。

OBS の [ツール > スクリプト] に登録して使用する。
pypresence は OBS が指す Python に導入済みであること (README 参照)。

スレッド設計:
    - Discord IPC / asyncio は背景スレッド (lib.discord_rpc.VoiceWatcher) に隔離
    - OBS API 呼び出しは obs.timer のコールバック (メインスレッド) でのみ実施
"""

import os
import sys

# このファイルと同階層を import パスに追加 (lib パッケージを解決するため)
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import obspython as obs  # noqa: E402

from lib.config import ConfigError, build_app_config, load_config_file  # noqa: E402
from lib.discord_rpc import VoiceWatcher  # noqa: E402
from lib.obs_source import list_browser_sources, set_browser_url  # noqa: E402
from lib.url_builder import build_streamkit_url  # noqa: E402

CONFIG_PATH = os.path.join(_HERE, "cfg", "config.json")
TOKEN_PATH = os.path.join(_HERE, "cfg", "token.json")

TICK_MS = 1000

_state = {
    "cfg": None,
    "watcher": None,
    "source_name": "話者",
    "client_id": "",
    "client_secret": "",
    "last_applied": None,  # 直近で反映した (guild_id, channel_id)
    "running_timer": False,
}


def _log(msg):
    print(msg, flush=True)


def _apply(guild_id, channel_id):
    cfg = _state["cfg"]
    url = build_streamkit_url(guild_id, channel_id, **cfg.streamkit)
    if url is None:
        if cfg.on_leave == "blank":
            set_browser_url(_state["source_name"], "about:blank", log=_log)
        else:
            _log("[INFO] VC 未参加 → URL は据え置き (on_leave=keep)")
        return
    set_browser_url(_state["source_name"], url, log=_log)


def _tick():
    watcher = _state["watcher"]
    if watcher is None:
        return
    current = watcher.get_current()
    if current != _state["last_applied"]:
        _state["last_applied"] = current
        _apply(*current)


def _start_auto():
    cfg = _state["cfg"]
    watcher = VoiceWatcher(cfg, TOKEN_PATH, log=_log)
    _state["watcher"] = watcher
    watcher.start()
    obs.timer_add(_tick, TICK_MS)
    _state["running_timer"] = True
    _log("[INFO] auto モード開始: Discord RPC 接続中...")


def _start_manual():
    cfg = _state["cfg"]
    _log(f"[INFO] manual モード: guild={cfg.manual_guild_id} channel={cfg.manual_channel_id}")
    _apply(cfg.manual_guild_id, cfg.manual_channel_id)


def _load_and_run():
    try:
        raw_cfg = load_config_file(CONFIG_PATH)
        cfg = build_app_config(raw_cfg, _state["client_id"], _state["client_secret"])
    except ConfigError as exc:
        _log(f"[ERROR] 設定不備: {exc}")
        return
    _state["cfg"] = cfg
    if not _state["source_name"]:
        _state["source_name"] = cfg.source_name
    _log(f"[INFO] mode={cfg.mode} source='{_state['source_name']}'")
    if cfg.mode == "manual":
        _start_manual()
    else:
        _start_auto()


def _teardown():
    if _state["running_timer"]:
        obs.timer_remove(_tick)
        _state["running_timer"] = False
    watcher = _state["watcher"]
    if watcher is not None:
        watcher.stop()
        _state["watcher"] = None
    _state["last_applied"] = None


# --- OBS script hooks ---
def script_description():
    return (
        "現在の Discord VC を StreamKit Voice Widget URL に変換し、指定ブラウザソースへ自動反映します。\n"
        "下の欄に Discord アプリの Client ID / Client Secret を入力してください"
        " (mode=auto の場合のみ必須)。詳細は README を参照。"
    )


def script_properties():
    props = obs.obs_properties_create()
    source_list = obs.obs_properties_add_list(
        props,
        "source_name",
        "話者ソース",
        obs.OBS_COMBO_TYPE_EDITABLE,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    for name in list_browser_sources():
        obs.obs_property_list_add_string(source_list, name, name)
    obs.obs_properties_add_text(
        props, "discord_client_id", "Discord Client ID", obs.OBS_TEXT_PASSWORD
    )
    obs.obs_properties_add_text(
        props, "discord_client_secret", "Discord Client Secret", obs.OBS_TEXT_PASSWORD
    )
    obs.obs_properties_add_button(props, "reload", "設定リロード", _on_reload)
    obs.obs_properties_add_text(
        props,
        "status_info",
        "状態は OBS の [スクリプトログ] を参照してください",
        obs.OBS_TEXT_INFO,
    )
    return props


def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "source_name", "話者")
    obs.obs_data_set_default_string(settings, "discord_client_id", "")
    obs.obs_data_set_default_string(settings, "discord_client_secret", "")


def _sync_state_from_settings(settings):
    name = obs.obs_data_get_string(settings, "source_name")
    if name and name != _state["source_name"]:
        _state["source_name"] = name
        _state["last_applied"] = None  # 新しいソースへ次の tick で再反映させる
    _state["client_id"] = obs.obs_data_get_string(settings, "discord_client_id")
    _state["client_secret"] = obs.obs_data_get_string(settings, "discord_client_secret")


def script_update(settings):
    _sync_state_from_settings(settings)


def _on_reload(props, prop):
    _log("[INFO] 設定リロード")
    _teardown()
    _load_and_run()
    return True


def script_load(settings):
    _sync_state_from_settings(settings)
    _load_and_run()


def script_unload():
    _teardown()
