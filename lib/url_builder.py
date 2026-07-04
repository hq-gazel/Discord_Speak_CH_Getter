"""StreamKit Voice Widget の overlay URL を生成する純関数。"""

from __future__ import annotations

from urllib.parse import urlencode

STREAMKIT_VOICE_BASE = "https://streamkit.discord.com/overlay/voice"


def build_streamkit_url(guild_id, channel_id, *, icon=True, online=True, logo="white"):
    """guild_id / channel_id から StreamKit Voice Widget の URL を生成する。

    どちらかが欠ける (VC 外 / DM 通話など) 場合は None を返す。
    """
    if not guild_id or not channel_id:
        return None
    query = urlencode(
        {
            "icon": "true" if icon else "false",
            "online": "true" if online else "false",
            "logo": logo,
        }
    )
    return f"{STREAMKIT_VOICE_BASE}/{guild_id}/{channel_id}?{query}"
