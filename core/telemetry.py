"""옵트인 텔레메트리 — 런 종료 시 행동 로그를 배치 업로드한다.

stdlib urllib만 쓴다 (Android 빌드에 requests 없음 — buildozer.spec 참고).
URL이 비어 있거나 설정(telemetry)이 꺼져 있으면 전부 no-op.
실패는 조용히 큐에 남겨 다음 세션 시작 때 재시도한다. 게임을 막는 일은 없다.
전송 내용 = 로컬 JSONL 그대로 (PII 없음 — behavior.py가 보장).
"""
import gzip
import json
import os
import threading
import urllib.request

from core import behavior, save_system
from core.version import VERSION

# 배포한 Worker 주소 (tools/telemetry-worker/README.md 절차 후 기입).
# 예: "https://dreamfarm-telemetry.<계정>.workers.dev/v1/events"
URL = ""
TIMEOUT = 3.0


def enabled():
    return bool(URL) and bool(save_system.get_setting("telemetry"))


def _pending_path():
    return os.path.join(behavior._dir(), "pending_upload.json")


def _load_pending():
    try:
        with open(_pending_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _queue(name):
    """실패한 런 파일명을 재시도 큐에 남긴다 (중복 없이)."""
    try:
        pending = _load_pending()
        if name not in pending:
            pending.append(name)
        with open(_pending_path(), "w", encoding="utf-8") as f:
            json.dump(pending[-30:], f)   # 오래된 것부터 버린다
    except Exception:
        pass


def _unqueue(name):
    try:
        pending = [p for p in _load_pending() if p != name]
        with open(_pending_path(), "w", encoding="utf-8") as f:
            json.dump(pending, f)
    except Exception:
        pass


def _post(events, cid):
    payload = json.dumps({"client_id": cid,
                          "game_version": VERSION,
                          "events": events}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        URL, data=gzip.compress(payload), method="POST",
        headers={"Content-Type": "application/json", "Content-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.status == 200


def _upload_file(name, cid):
    try:
        path = os.path.join(behavior._dir(), os.path.basename(name))
        events = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    events.append(json.loads(line))
                except Exception:
                    continue
        if events and _post(events, cid):
            _unqueue(name)
        else:
            _queue(name)
    except Exception:
        _queue(name)


def upload_run(name):
    """런 종료 시 호출 — 백그라운드 스레드로 업로드. 비활성이면 no-op."""
    if not name or not enabled():
        return
    # client_id는 최초 생성 시 meta 파일 쓰기가 일어난다 — 업로드 스레드가 아니라
    # 여기(메인 스레드)에서 미리 해석해 넘겨야 자동저장 등 다른 메타 쓰기와 경합하지 않는다.
    cid = behavior.client_id()
    threading.Thread(target=_upload_file, args=(name, cid), daemon=True).start()


def retry_pending():
    """세션 시작 시 호출 — 밀린 업로드 재시도."""
    if not enabled():
        return
    cid = behavior.client_id()
    def _run():
        for name in list(_load_pending()):
            _upload_file(name, cid)
    threading.Thread(target=_run, daemon=True).start()
