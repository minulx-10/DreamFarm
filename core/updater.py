# -*- coding: utf-8 -*-
"""가벼운 업데이트 '알림' — GitHub 최신 릴리스와 현재 버전을 비교해 새 버전이 있으면 알린다.

자기 자신을 교체하지 않는다(안전): 알림 + 다운로드 페이지 링크만 제공한다. 백그라운드·논블로킹으로
한 번만 확인하고, 오프라인/오류/차단 시 조용히 무시한다. 설정 `update_check`(기본 켜짐)로 끌 수 있다.
전송하는 것은 공개 릴리스 API에 대한 단순 GET뿐이며 사용자 데이터는 보내지 않는다.
(스팀 출시 후에는 스팀이 자동 업데이트를 담당하므로 이 알림은 꺼두거나 스팀 빌드에서 빼면 된다.)
"""
import threading
import json
import re
from urllib.request import urlopen, Request

REPO = "minulx-10/DreamFarm"
RELEASES_PAGE = "https://github.com/%s/releases/latest" % REPO
_API = "https://api.github.com/repos/%s/releases/latest" % REPO

available = None    # 새 버전이 있으면 태그 문자열(예: "v2.3.0"), 없으면 None
_checked = False


def _nums(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "")[:3]) or (0,)


def _worker():
    global available
    try:
        from core.version import VERSION
        req = Request(_API, headers={"User-Agent": "DreamFarm-Updater",
                                     "Accept": "application/vnd.github+json"})
        with urlopen(req, timeout=6) as r:
            tag = json.load(r).get("tag_name", "")
        if tag and _nums(tag) > _nums(VERSION):   # /releases/latest 는 프리릴리스를 제외한 최신 안정판
            available = tag
    except Exception:
        pass   # 오프라인·차단·파싱 오류 → 조용히 무시


def check_async():
    """설정이 켜져 있으면 백그라운드로 한 번 확인한다(시작을 막지 않음)."""
    global _checked
    if _checked:
        return
    _checked = True
    try:
        from core import save_system
        if not save_system.get_setting("update_check"):
            return
    except Exception:
        pass
    threading.Thread(target=_worker, daemon=True).start()


def open_download_page():
    import webbrowser
    try:
        webbrowser.open(RELEASES_PAGE)
    except Exception:
        pass
