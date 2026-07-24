# 몽중농원 텔레메트리 수신기

Cloudflare Worker + D1 (무료 티어). 수집만 한다 — 분석은 `tools/behavior_report.py`.

## 배포 (1회)

1. Cloudflare 계정 + `npm i -g wrangler` + `wrangler login`
2. `cd tools/telemetry-worker`
3. `wrangler d1 create dreamfarm-telemetry` → 출력된 `database_id`를 wrangler.toml의 REPLACE_ME에
4. `wrangler d1 execute dreamfarm-telemetry --remote --file=schema.sql`
5. `wrangler deploy` → 출력 URL(예: https://dreamfarm-telemetry.<계정>.workers.dev)
6. 게임 쪽 `core/telemetry.py`의 `URL`에 `<배포URL>/v1/events` 기입

## 데이터 확인

wrangler d1 execute dreamfarm-telemetry --remote --command "SELECT client_id, game_version, received_at, length(payload) FROM batches ORDER BY id DESC LIMIT 20"

## 계약

POST /v1/events — JSON(선택적 gzip, Content-Encoding: gzip):
{"client_id": "<uuid hex>", "game_version": "2.5.0", "events": [{...}, ...]}
이벤트 스키마는 specs/2026-07-24-behavior-data-design.md 참고. PII 없음(클라이언트가 보장).
