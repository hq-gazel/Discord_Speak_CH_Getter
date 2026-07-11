import json

import pytest

from lib.config import (
    ConfigError,
    build_app_config,
    load_config_file,
)


def test_load_config_file_defaults(tmp_path):
    cfg = load_config_file(tmp_path / "nope.json")
    assert cfg["mode"] == "auto"
    assert cfg["streamkit"]["logo"] == "white"
    assert cfg["streamkit"]["small"] is False


def test_load_config_file_merge(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"mode": "manual", "streamkit": {"logo": "black"}}), encoding="utf-8")
    cfg = load_config_file(p)
    assert cfg["mode"] == "manual"
    assert cfg["streamkit"]["logo"] == "black"
    assert cfg["streamkit"]["icon"] is True  # 既定が保持される


def test_load_config_file_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config_file(p)


def test_auto_requires_secrets():
    with pytest.raises(ConfigError):
        build_app_config({"mode": "auto"})


def test_auto_ok():
    ac = build_app_config({"mode": "auto"}, client_id="i", client_secret="s")
    assert ac.mode == "auto"
    assert ac.client_id == "i"
    assert ac.client_secret == "s"


def test_manual_requires_ids():
    with pytest.raises(ConfigError):
        build_app_config({"mode": "manual"})


def test_manual_ok():
    ac = build_app_config({"mode": "manual", "manual": {"guild_id": "g", "channel_id": "c"}})
    assert ac.manual_guild_id == "g"
    assert ac.manual_channel_id == "c"


def test_manual_ignores_missing_secrets():
    # manual モードでは client_id/secret が空でもエラーにならない
    ac = build_app_config({"mode": "manual", "manual": {"guild_id": "g", "channel_id": "c"}})
    assert ac.client_id == ""
    assert ac.client_secret == ""


def test_invalid_mode():
    with pytest.raises(ConfigError):
        build_app_config({"mode": "weird"})


def test_invalid_on_leave():
    with pytest.raises(ConfigError):
        build_app_config(
            {"mode": "manual", "manual": {"guild_id": "g", "channel_id": "c"}, "on_leave": "x"}
        )


def test_streamkit_coercion():
    ac = build_app_config(
        {"mode": "manual", "manual": {"guild_id": "g", "channel_id": "c"}, "streamkit": {}}
    )
    assert ac.streamkit == {"icon": True, "online": True, "logo": "white", "small": False}


def test_streamkit_small_true():
    ac = build_app_config(
        {
            "mode": "manual",
            "manual": {"guild_id": "g", "channel_id": "c"},
            "streamkit": {"small": True},
        }
    )
    assert ac.streamkit["small"] is True
