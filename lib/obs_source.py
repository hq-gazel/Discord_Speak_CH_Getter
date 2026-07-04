"""obspython 経由でブラウザソースの url を書き換える (OBS メインスレッド専用)。

obspython は OBS 実行時のみ提供される。OBS 外 (CLI/テスト) では obs=None となり no-op。
"""

from __future__ import annotations

try:
    import obspython as obs
except ImportError:  # OBS 外
    obs = None


def _default_log(msg):
    print(msg, flush=True)


def set_browser_url(source_name, url, *, log=_default_log) -> bool:
    """指定ブラウザソースの url を差し替える。成功で True。"""
    if obs is None:
        log("[WARN] obspython が無い環境です (OBS 外のため更新スキップ)")
        return False
    src = obs.obs_get_source_by_name(source_name)
    if src is None:
        log(f"[WARN] ソース未検出: {source_name!r}")
        return False
    try:
        settings = obs.obs_source_get_settings(src)  # 既存設定を保持
        obs.obs_data_set_string(settings, "url", url)
        obs.obs_source_update(src, settings)
        obs.obs_data_release(settings)
        log(f"[OK] '{source_name}' の url を更新: {url}")
        return True
    finally:
        obs.obs_source_release(src)


def list_browser_sources():
    """browser_source 種別のソース名一覧 (OBS プロパティのドロップダウン用)。"""
    if obs is None:
        return []
    names = []
    sources = obs.obs_enum_sources()
    if sources is not None:
        for src in sources:
            if obs.obs_source_get_id(src) == "browser_source":
                names.append(obs.obs_source_get_name(src))
        obs.source_list_release(sources)
    return names
