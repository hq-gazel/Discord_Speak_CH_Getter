from lib.discord_rpc import extract_auth_code, parse_voice_payload


def test_parse_get_selected_voice_channel():
    # GET_SELECTED_VOICE_CHANNEL: data はチャンネルオブジェクト (id / guild_id)
    resp = {
        "cmd": "GET_SELECTED_VOICE_CHANNEL",
        "data": {"id": "222", "guild_id": "111", "name": "general"},
        "evt": None,
    }
    assert parse_voice_payload(resp) == ("111", "222")


def test_parse_voice_channel_select_event():
    # VOICE_CHANNEL_SELECT イベント: data は {channel_id, guild_id}
    event = {"channel_id": "222", "guild_id": "111"}
    assert parse_voice_payload(event) == ("111", "222")


def test_parse_nested_event_payload():
    event = {"evt": "VOICE_CHANNEL_SELECT", "data": {"channel_id": "222", "guild_id": "111"}}
    assert parse_voice_payload(event) == ("111", "222")


def test_parse_left_channel():
    assert parse_voice_payload({"data": None}) == (None, None)
    assert parse_voice_payload({"channel_id": None, "guild_id": None}) == (None, None)
    assert parse_voice_payload(None) == (None, None)


def test_parse_dm_no_guild():
    # DM 通話: channel_id はあるが guild_id が無い
    assert parse_voice_payload({"channel_id": "999"}) == (None, "999")


def test_extract_auth_code():
    assert extract_auth_code({"data": {"code": "abc"}}) == "abc"
    assert extract_auth_code({"code": "xyz"}) == "xyz"
    assert extract_auth_code({}) is None
    assert extract_auth_code(None) is None
