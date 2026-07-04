from lib.token_store import is_valid, load_token, save_token


def test_save_and_load(tmp_path):
    path = tmp_path / "token.json"
    saved = save_token(
        path,
        {"access_token": "a", "refresh_token": "r", "expires_in": 3600},
        now=1000.0,
    )
    assert saved["expires_at"] == 1000.0 + 3600
    loaded = load_token(path)
    assert loaded["access_token"] == "a"
    assert loaded["refresh_token"] == "r"


def test_load_missing(tmp_path):
    assert load_token(tmp_path / "nope.json") is None


def test_load_corrupt(tmp_path):
    p = tmp_path / "token.json"
    p.write_text("{broken", encoding="utf-8")
    assert load_token(p) is None


def test_is_valid():
    assert is_valid({"access_token": "a", "expires_at": 10000}, now=100) is True
    assert is_valid({"access_token": "a", "expires_at": 100}, now=10000) is False
    assert is_valid({"access_token": "", "expires_at": 10000}, now=100) is False
    assert is_valid(None) is False


def test_is_valid_leeway():
    # 余裕 (leeway) を考慮して失効直前は無効扱い
    assert is_valid({"access_token": "a", "expires_at": 130}, now=100, leeway=60) is False
    assert is_valid({"access_token": "a", "expires_at": 200}, now=100, leeway=60) is True
