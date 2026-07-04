"""OAuth トークンのキャッシュ (cfg/token.json) と Discord トークンエンドポイント呼び出し。

トークン交換/更新は追加依存を避けるため stdlib の urllib で行う。
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN_URL = "https://discord.com/api/oauth2/token"


def load_token(path):
    """token.json を読み込む。無い/壊れている場合は None。"""
    p = Path(path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def save_token(path, token_response: dict, *, now=None) -> dict:
    """トークンエンドポイント応答を正規化して token.json に保存し、保存内容を返す。"""
    now = time.time() if now is None else now
    data = {
        "access_token": token_response.get("access_token", ""),
        "refresh_token": token_response.get("refresh_token", ""),
        "scope": token_response.get("scope", ""),
        "token_type": token_response.get("token_type", "Bearer"),
        "expires_at": now + float(token_response.get("expires_in", 0) or 0),
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def is_valid(token, *, leeway=60, now=None) -> bool:
    """access_token があり、leeway 秒の余裕を見て未失効なら True。"""
    if not token or not token.get("access_token"):
        return False
    now = time.time() if now is None else now
    return float(token.get("expires_at", 0)) - leeway > now


def _post_token(payload: dict, *, timeout=15) -> dict:
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def exchange_code(client_id, client_secret, code, redirect_uri) -> dict:
    """AUTHORIZE で得た code を access_token に交換する。"""
    return _post_token(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
    )


def refresh_access_token(client_id, client_secret, refresh_token) -> dict:
    """refresh_token を使って access_token を更新する。"""
    return _post_token(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    )
