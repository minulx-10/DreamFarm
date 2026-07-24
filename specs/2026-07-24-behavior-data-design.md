# 행동 데이터 시스템 설계 (2026-07-24)

## 목적

플레이어 행동을 구조화된 이벤트로 기록하고, 그 위에 네 가지 기능을 얹는다.

1. 게임 내 상세 행동 기록 뷰
2. 행동 기반 반응형 게임플레이 (서사·이벤트 풀·난이도)
3. 개발자용 로컬 분석 대시보드
4. 옵트인 텔레메트리 (직접 운영하는 엔드포인트로 업로드)

## 아키텍처: 단일 이벤트 로그 파이프라인

모든 행동은 한 곳(`core/behavior.py`)을 거쳐 기록되고, 네 소비자는 전부 이
로그에서 파생한다. 쓰기 경로 1개, 스키마 1개.

```
플레이어 행동
    │
    ▼
core/behavior.py ── log(event, **fields)
    │                       │
    ├─ JSONL append (런당 1파일, <저장폴더>/behavior/)
    └─ 인메모리 집계 갱신
                            │
    ┌───────────┬───────────┼───────────────┐
    ▼           ▼           ▼               ▼
게임 내 뷰   profile()   tools/         텔레메트리
(갤러리)    반응형 성향  behavior_report  업로더(옵트인)
```

## 이벤트 스키마

JSONL 한 줄 = 이벤트 하나.

```json
{"v": 1, "t": 1784000000.0, "day": 12, "phase": "morning",
 "e": "water", "x": 3, "y": 1}
```

- `v`: 스키마 버전 (정수, 시작 1)
- `t`: epoch 초 (float)
- `day` / `phase`: 게임 내 시점
- `e`: 이벤트 이름 (아래 목록)
- 나머지: 이벤트별 부가 필드

### 이벤트 목록 (v1)

| 이벤트 | 발생 지점 | 부가 필드 |
|---|---|---|
| `run_start` | 런 시작 | crop, seed, challenge |
| `action` | farm_simulator 행동 관문 (scenes/farm_simulator.py:362) | kind(water/weed/pest/...), 대상 좌표 |
| `minigame` | stage1~4 종료 | stage, score, max, duration |
| `choice` | story_choice 선택 | choice_id, picked |
| `day_end` | 일 전환 | day, actions_today |
| `event_seen` | 농장 이벤트 발생 | event_id |
| `ending` | 엔딩 도달 | ending_type, days |
| `session` | 앱 시작/종료 | state(start/stop) |

플레이어가 입력한 자유 텍스트(이름 등)는 **절대 기록하지 않는다** (PII 차단).

### 파일 레이아웃

- `<저장폴더>/behavior/run_<seed>_<시작epoch>.jsonl` — 런당 1파일
- 세이브 스냅샷에 현재 run 파일명 포함 → 로드 시 같은 파일에 이어씀
- append + flush. 기록 실패는 try/except로 삼키고 1회만 경고 로그 —
  **행동 기록이 게임플레이를 깨는 일은 없어야 한다**
- 익명 `client_id`(UUID4)를 meta에 1회 생성·보관

## 소비자 1: 게임 내 행동 기록 뷰

- 기존 갤러리 통계 페이지 확장 (IDEAS_STEAM 2-3에서 만든 곳)
- 런별: 일별 행동 타임라인 요약
- 평생: 패턴 문구 — "가장 자주 물 준 시간대", "최장 연속 접속", "방치 최다 일수" 등
- 문구는 기존 i18n 경로(core/i18n, i18n_data) 사용

## 소비자 2: 반응형 게임플레이

`behavior.profile()`이 현재 런 + 평생 로그에서 성향을 파생한다.
성향은 **저장하지 않는다** — 로그에서 항상 재계산 (세이브 호환성 무풍).

파생 성향(0.0~1.0 연속값):

- `diligence` — 물주기 규칙성·일일 행동 밀도
- `neglect` — 무행동 일수 비율
- `skill` — 미니게임 성적 이동평균
- `reaction` — 잡초·벌레 발생 후 제거까지 걸린 일수

반영 3종:

1. **서사 반응** — 아버지 대사·일지·이벤트 문구 풀에 성향 조건부 항목 추가
   (narrative_data 확장, 기존 year_seed 성격 시드와 결합).
   예: 성실형에게 "너 새벽마다 물을 주더라".
2. **이벤트 풀 가중치** — 이벤트 추첨 시 성향별 가중치 곱.
   예: neglect 높음 → 가뭄·잡초 이벤트 가중 ↑. 완만하게(가중치 0.5~2.0 클램프).
3. **난이도 조정** — skill에 따라 미니게임 파라미터 ±10% 이내 보정, 클램프.
   **도전 규칙(무일지·한발·이레) 모드에서는 비활성** — 공정성 유지.

## 소비자 3: 개발자 대시보드

- `tools/behavior_report.py` — 저장폴더의 JSONL 전부 스캔, 단일 HTML 리포트 생성
  (일별 행동 히트맵, 미니게임 성적 추이, 이벤트 발생 분포, 성향 변화)
- 의존성: stdlib만. 차트는 inline SVG 생성
- `core/dev_overlay.py`에 현재 런 성향 4종 실시간 표시 추가 (개발 모드 한정)

## 소비자 4: 텔레메트리

### 서버 (직접 운영)

- Cloudflare Worker + D1 (무료 티어; KV는 쓰기 1k/일 제한이라 D1 채택)
- `POST /v1/events` — gzip JSON 배치 `{client_id, game_version, events:[...]}`
- D1 테이블 `batches(client_id, game_version, received_at, payload)`
- 코드 위치 `tools/telemetry-worker/` (wrangler 프로젝트).
  배포·계정 연결은 사용자가 수행 — README에 절차 문서화

### 클라이언트

- **옵트인, 기본 꺼짐.** 설정 오버레이에 토글 + 수집 항목 안내 문구
- 켜져 있으면 엔딩 시(이탈 업로드는 미구현 — run_id 중복제거 도입 후 고려) 해당 런 JSONL 배치 업로드
- 실패 시 로컬 큐 유지, 다음 기회에 재시도. 타임아웃 3초, 업로드는 스레드로
  — 메인 루프 블로킹 금지
- 전송 내용 = 로컬 로그와 동일(스키마 v 포함), PII 없음

## 오류 처리 원칙

- behavior 기록·업로드 실패는 어떤 경우에도 게임 진행을 막지 않는다
- 스키마를 모르는 이벤트를 만나면 소비자(뷰·리포트)는 건너뛴다 (전방 호환)

## 테스트

- `core/behavior.py` 단위 테스트: 기록→집계→profile 파생 왕복
- `tools/behavior_report.py` 스모크: 샘플 JSONL → HTML 생성 확인
- 반응형: 성향 극단값에서 가중치·난이도 클램프 검증
- 게임 내 뷰: 기존 헤드리스 렌더 검증 방식 재사용

## 구현 단계

1. 토대 — core/behavior.py + 훅 + 집계
2. 게임 내 기록 뷰 (갤러리 확장)
3. 반응형 — 서사 → 이벤트 가중치 → 난이도 순
4. 대시보드 — tools/behavior_report.py + dev_overlay
5. 텔레메트리 — Worker + 클라 옵트인 업로더

## 비범위 (이번에 안 함)

- 실시간 스트리밍 업로드 (런 종료 배치만)
- 서버 측 분석 UI (수집만; 분석은 로컬 리포트로)
- Steam 스탯 API 연동 (기존 IDEAS_STEAM 2-3 별도 트랙)
