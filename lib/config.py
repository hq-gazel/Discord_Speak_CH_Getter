"""設定の読込・検証。

- 秘匿情報 (client_id / client_secret) は呼び出し側から渡す
  (OBS 本体: スクリプトのプロパティ画面 / lib.cli: コマンドライン引数)
- 非秘匿設定 (mode / source_name / manual / streamkit / on_leave / redirect_uri) は
  ``cfg/config.json`` から読む
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG = {
    "mode": "auto",
    "source_name": "話者",
    "redirect_uri": "http://localhost:3000/callback",
    "manual": {"guild_id": "", "channel_id": ""},
    "streamkit": {"icon": True, "online": True, "logo": "white"},
    "on_leave": "keep",
}

VALID_MODES = ("auto", "manual")
VALID_ON_LEAVE = ("keep", "blank")


class ConfigError(Exception):
    """設定不備を表す例外。"""


@dataclass
class AppConfig:
    mode: str
    source_name: str
    redirect_uri: str
    manual_guild_id: str
    manual_channel_id: str
    streamkit: dict
    on_leave: str
    client_id: str
    client_secret: str


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config_file(path) -> dict:
    """config.json を読み、欠落キーは DEFAULT_CONFIG で補完して返す。"""
    p = Path(path)
    if not p.exists():
        return dict(DEFAULT_CONFIG)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"config.json の JSON が不正です: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("config.json はオブジェクト (辞書) である必要があります")
    return _deep_merge(DEFAULT_CONFIG, raw)


def build_app_config(cfg: dict, client_id: str = "", client_secret: str = "") -> AppConfig:
    """設定辞書と client_id/client_secret を検証し AppConfig を構築する。"""
    mode = str(cfg.get("mode", "auto")).strip().lower()
    if mode not in VALID_MODES:
        raise ConfigError(f"mode は {VALID_MODES} のいずれか。実際={mode!r}")

    on_leave = str(cfg.get("on_leave", "keep")).strip().lower()
    if on_leave not in VALID_ON_LEAVE:
        raise ConfigError(f"on_leave は {VALID_ON_LEAVE} のいずれか。実際={on_leave!r}")

    source_name = str(cfg.get("source_name", "話者")).strip()
    if not source_name:
        raise ConfigError("source_name が空です")

    manual = cfg.get("manual") or {}
    manual_guild_id = str(manual.get("guild_id", "")).strip()
    manual_channel_id = str(manual.get("channel_id", "")).strip()

    streamkit = cfg.get("streamkit") or {}

    client_id = str(client_id or "").strip()
    client_secret = str(client_secret or "").strip()

    if mode == "auto" and (not client_id or not client_secret):
        raise ConfigError(
            "mode=auto には Discord Client ID / Client Secret が必要です"
            " (OBS のスクリプトプロパティ、または lib.cli の --client-id/--client-secret で指定)"
        )
    if mode == "manual" and (not manual_guild_id or not manual_channel_id):
        raise ConfigError(
            "mode=manual には config.json の manual.guild_id と manual.channel_id が必要です"
        )

    return AppConfig(
        mode=mode,
        source_name=source_name,
        redirect_uri=str(cfg.get("redirect_uri", "")).strip(),
        manual_guild_id=manual_guild_id,
        manual_channel_id=manual_channel_id,
        streamkit={
            "icon": bool(streamkit.get("icon", True)),
            "online": bool(streamkit.get("online", True)),
            "logo": str(streamkit.get("logo", "white")),
        },
        on_leave=on_leave,
        client_id=client_id,
        client_secret=client_secret,
    )
