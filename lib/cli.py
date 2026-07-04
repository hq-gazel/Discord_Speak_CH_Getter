"""OBS 無しで Discord 検出 + URL 生成を確認する単体実行ツール。

使い方 (OBS が指す Python で実行。mode=auto の場合は --client-id/--client-secret が必要):
    & "<OBSのPython>\\python.exe" -m lib.cli --client-id XXXX --client-secret YYYY
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .config import ConfigError, build_app_config, load_config_file
from .discord_rpc import VoiceWatcher
from .url_builder import build_streamkit_url

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "cfg" / "config.json"
TOKEN_PATH = ROOT / "cfg" / "token.json"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-id", default="", help="Discord アプリの Client ID (mode=auto)")
    parser.add_argument(
        "--client-secret", default="", help="Discord アプリの Client Secret (mode=auto)"
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        raw_cfg = load_config_file(CONFIG_PATH)
        cfg = build_app_config(raw_cfg, args.client_id, args.client_secret)
    except ConfigError as exc:
        print(f"[ERROR] 設定不備: {exc}")
        return 1

    if cfg.mode == "manual":
        url = build_streamkit_url(cfg.manual_guild_id, cfg.manual_channel_id, **cfg.streamkit)
        print(f"[OK] manual モード guild={cfg.manual_guild_id} channel={cfg.manual_channel_id}")
        print(f"[OK] URL: {url}")
        return 0

    print("[INFO] Discord RPC に接続します (初回は Discord で認可ポップアップが出ます)。Ctrl+C で終了。")
    watcher = VoiceWatcher(cfg, TOKEN_PATH)
    watcher.start()
    last = object()
    try:
        deadline = time.time() + 120
        while time.time() < deadline:
            st = watcher.status()
            current = st["current"]
            if current != last:
                last = current
                guild_id, channel_id = current
                url = build_streamkit_url(guild_id, channel_id, **cfg.streamkit)
                if url:
                    print(f"[OK] 現在VC guild={guild_id} channel={channel_id}")
                    print(f"[OK] URL: {url}")
                else:
                    print(f"[INFO] VC 未参加 / DM (guild={guild_id} channel={channel_id})")
            if st["error"]:
                print(f"[ERROR] {st['error']}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] 終了します")
    finally:
        watcher.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
