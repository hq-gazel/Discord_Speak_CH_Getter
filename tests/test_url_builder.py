from lib.url_builder import build_streamkit_url


def test_basic_url():
    url = build_streamkit_url("111", "222")
    assert (
        url
        == "https://streamkit.discord.com/overlay/voice/111/222?icon=true&online=true&logo=white"
    )


def test_options():
    url = build_streamkit_url("1", "2", icon=False, online=False, logo="black")
    assert "icon=false" in url
    assert "online=false" in url
    assert "logo=black" in url


def test_missing_returns_none():
    assert build_streamkit_url(None, "2") is None
    assert build_streamkit_url("1", None) is None
    assert build_streamkit_url("", "") is None
