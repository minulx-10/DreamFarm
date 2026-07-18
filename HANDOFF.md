# 몽중농원(DreamFarm) — 개발 인수인계 및 히스토리 가이드

이 문서는 삼광(三光) 개발 팀 내부의 협업 및 차기 프로젝트 인계를 위한 개발 가이드라인과 기술 스펙 설명서입니다. 
공동 작업 시 이 문서의 "개발 작업 로그"와 CHANGELOG.md를 함께 갱신해 주시기 바랍니다.

---

## 0. 프로젝트 개요
Pygame으로 제작한 감성 내러티브 농사 시뮬레이션 게임입니다. 식탁에서 반찬을 밀어낸 주인공 아이가 꿈속의 밭에서 여러 작물을 기르는 밭일을 겪으며, 흙 묻은 아버지의 노동과 다정한 사랑을 천천히 이해해 나가는 과정을 그립니다. 

- **가상 해상도**: 800×600 캔버스에 렌더링 후, 사용자 창/화면 크기에 맞춰 4:3 레터박스로 스케일링합니다(악몽 모드도 800×600 유지 — 픽셀 폰트 뭉개짐 방지). 1440p·4K처럼 2배 이상 들어가는 고해상도에서는 **정수 배율로 스냅**해 픽셀을 또렷하게 합니다(`game_main._apply_scaling`).
- **디자인 철학**: 픽셀아트 기반 그래픽과 절차적 신디사이저 효과음/배경음으로 구성됩니다. 소리는 개발/빌드 시점에 numpy로 합성하되(`tools/bake_audio.py`), 배포 산출물에는 `.ogg`로 미리 구워 실어 **런타임에는 numpy가 필요 없습니다**(안드로이드 빌드 안정화의 핵심).

---

## 1. 빌드, 실행 및 배포 규칙
- **개발 환경 실행**:
  ```bash
  pip install -r requirements.txt
  python main.py
  ```
  - 요구 환경: Python 3.10+ / pygame-ce (Pygame Community Edition) / numpy
- **패키징 및 배포 자동화**:
  - 원격 저장소에 `v*` 태그가 푸시되면 GitHub Actions 워크플로우(`.github/workflows/release.yml`)가 자동으로 기동되어 Windows용 EXE 단일 실행 파일을 PyInstaller로 빌드합니다.
  - **정식 릴리스**: `vX.Y.Z` 형태로 푸시하면 최신 안정화(Latest) 빌드로 등록됩니다.
  - **테스트/개발 프리릴리스**: `vX.Y.Z-dev.N` 형태로 푸시하면 테스터 배포용 프리릴리스로 등록됩니다.
- **브랜치 규칙**: 
  - `dev` 브랜치에서 기능 개선 및 테스트를 거친 후, `main` 브랜치로 병합(Merge)하여 정식 태그를 배포합니다.
  - 버전 넘버 정보는 `core/version.py` 에 기재된 `VERSION` 상수를 중앙 통제하여 갱신합니다.

---

## 2. 시스템 아키텍처 및 코드 구조

### 핵심 디렉토리 및 파일 스펙
```
main.py                엔트리 포인트(크래시 로그 폴백 포함). game_main.main()을 호출
game_main.py           실제 게임 루프 · 씬 전환 · 씬별 BGM · 오버레이/ESC · 창 좌표/정수배율 스케일링
core/
  game_state.py        게임 전역 상태 관리, 엔딩 판정 로직, 한글 조사 결합 헬퍼 및 내러티브 리디렉션 매핑
  narrative_data.py    게임 내 스토리 이벤트, 깨달음 및 대사 텍스트 테이블 격리 관리
  audio.py             오디오 API. 구운 core/sound/**.ogg 우선 로드, 없으면 numpy 지연합성 폴백
  platform.py          플랫폼 감지(IS_ANDROID) — p4a의 ANDROID_ARGUMENT 환경변수로 판별
  i18n.py              현지화 엔진 — t()/tf()/tnar(), 렌더 계층 자동 번역, locales JSON 로드
  i18n_data.py         한국어→영어 번역 카탈로그(베이스라인). locales/<lang>.json이 덮어씀
  locales/             언어별 번역 JSON (ko.json=소스 목록, en.json 등). GitHub PR로 기여
  palette.py           공용 색 팔레트(디자인 색 단일 소스) — assets가 re-export
  steam.py             스팀 도전과제 ctypes 스캐폴드(DLL/App ID 없으면 무해한 no-op)
tools/
  bake_audio.py        빌드 시 numpy로 소리를 core/sound/**.ogg 로 굽는 도구(런타임 numpy 제거용)
p4a-recipes/
  pygame-ce/           python-for-android용 pygame-ce 로컬 레시피(PR #2971, v2.4.0 고정)
  assets.py            픽셀아트 스프라이트 생성, 폰트 드로잉 및 계절별 렌더링 모듈
  save_system.py       게임 세이브 및 메타데이터(업적/엔딩 기록)의 메모리 캐시 및 원자적 쓰기(Atomic Write) 구현
  achievements.py      업적 조건 검사 및 업적 달성 토스트 알림 연출
  ui_utils.py          타이핑 효과(Typewriter) 및 반딧불이 물리 파티클(FireflyEmitter) 공통 연출 추출 모듈
  ui.py                공용 패널, 게이지 바, 버튼 등 공통 UI 프레임워크
  version.py           게임 버전 넘버링 중앙 통제 관리
scenes/
  title.py             메인 타이틀 화면 및 저작권(삼광) 푸터 렌더링
  farm.py              농장 메인 씬 (시뮬레이터와 렌더러를 조율하는 미디에이터 컨트롤러 구조)
  farm_simulator.py    농업 6대 스탯 변화, 날씨 영향 및 턴 경과 계산 물리 연산 모델
  farm_renderer.py     농장 지형, 벼/감자/사과나무 작물 드로잉 및 시간/계절별 화면 틴트 루프
  tending.py           MiniGameBase를 상속받는 밭일/날씨 미니게임 모음 (WaterPour, WeedPull, PestTap, SoilMound 등)
  gallery.py           추억 저장소 (엔딩 리플레이, 겪은 사건, 업적 리스트 및 설명 오버플로우 제어)
  *그 외 씬*            name_input, intro, crop_select, stage1~4, epiphany, star_connect, father_day, ending 등
```

### 아키텍처 연동 설계
- **농장 제어 분할**: 메인 농장 화면은 객체지향 설계(OOP)에 맞춰 스탯 연산부(`FarmSimulator`), 그리기 연산부(`FarmRenderer`)로 철저히 삼분할되어 `FarmScene` 이 컨트롤러 겸 미디에이터로 이들을 통제합니다.
- **미니게임 상속 체계**: 모든 미니게임은 `MiniGameBase` 부모 클래스를 상속받아 셋업, 입력 수신, 결과 판정(Settle) 등 공통의 수명주기를 일관성 있게 공유합니다.
- **수확 조작의 특성화**: 당근(드래그 뽑기), 사과(가지 당기기), 감자(흔들어 캐기), 벼(탈곡 및 도정 미니게임) 등 작물의 성격에 따른 상이한 플레이 매커니즘을 가집니다.

---

## 3. 기술 설계 노하우 및 팁
1. **임시 테스트 및 렌더링 검증**:
   - 오디오나 비디오 장치가 갖춰지지 않은 환경에서 렌더링 테스트를 수행할 경우, SDL dummy 환경 변수를 임시로 지정해 실행합니다:
     ```python
     import os
     os.environ["SDL_VIDEODRIVER"] = "dummy"
     os.environ["SDL_AUDIODRIVER"] = "dummy"
     ```
2. **알파 블렌딩 투명도 처리**:
   - Pygame의 `pygame.draw` 함수들은 기본적으로 투명도(Alpha)를 덮어쓰므로 반투명 겹침을 표현할 때는 반드시 `pygame.SRCALPHA` 속성을 가진 독립 서피스를 생성하여 그 위에 드로잉한 후 메인 캔버스에 `blit` 해야 합니다.
3. **절차적 오디오 연산 (구워서 배포)**:
   - 효과음과 배경음은 numpy 배열 연산으로 ADSR 엔벨로프·톤을 합성하고 `_to_sound`로 int16 스테레오로 변환합니다.
   - **런타임에는 numpy를 쓰지 않습니다.** 빌드 시 `python tools/bake_audio.py`가 이 합성 결과를 `core/sound/{sfx,bgm}/*.ogg`로 굽고(길이가 긴 BGM은 libsndfile 크래시 회피를 위해 블록 단위로 인코딩), `core/audio.py`는 그 파일을 우선 로드합니다. `.ogg`가 없을 때만 numpy를 지연 로드해 즉석 합성합니다.
   - **안드로이드**: `SDL_ANDROID_TRAP_BACK_BUTTON`으로 뒤로가기(K_AC_BACK→ESC)를 가로채고, `APP_WILLENTERBACKGROUND/DIDENTERFOREGROUND`로 백그라운드 시 오디오·렌더를 멈춥니다. p4a에 pygame-ce 레시피가 없어 `p4a-recipes/`의 로컬 레시피로 빌드합니다. `requirements`에서 numpy를 뺀 것이 빌드 속도·안정성의 핵심입니다.
4. **글자 래핑 및 넘침 방지**:
   - 해상도나 레이아웃 영역에 따라 글씨가 잘리는 현상을 막기 위해, 카드나 컨테이너의 내부 너비보다 충분히 좁은 가로 폭 제약(`col_w - 74` 등)을 주어 `wrap_text`가 개행을 수행하게 유도합니다.
5. **현지화(한/영) — 문구를 어떻게 번역되게 하나** (`core/i18n.py`, 자세히는 `LOCALIZATION.md`):
   - **정적 문자열**은 원문을 그대로 두면 렌더 계층(`get_font` 래퍼·`wrap_text`)이 자동 번역합니다. `core/i18n_data.py`(또는 커뮤니티 번역 `core/locales/en.json`)에 `"원문": "English"`만 넣으면 됩니다.
   - **변수와 합쳐지는 동적 문구**는 f-string 대신 `i18n.tf("… {n} …", n=…)`로 감싸고 템플릿(자리표시자 포함)을 카탈로그에 등록합니다.
   - **이름 조사·작물 치환이 얽힌 서사**는 `i18n.tnar(ko_template, crop_key=game_state.crop, name=…, name_eun=…)`. KO 템플릿엔 `{name_eun}`+`당근` 리터럴, EN 템플릿엔 `{name}`·`{crop}` 자리표시자(작물 영어단어는 `_EN_CROP`에서 자동 주입)를 씁니다. `.format`이 남는 인자를 무시하므로 두 언어 템플릿의 자리표시자가 달라도 안전합니다.
   - **주의**: 씬이 자체 줄바꿈을 쓰면 조각 단위로 렌더돼 카탈로그와 안 맞습니다 → 통째로 `i18n.t()` 한 뒤 `wrap_text`로 개행하세요(`transition.py` 참고).
6. **UI/디자인 통일 규칙** (`DESIGN_AUDIT.md`):
   - **색**은 `core/palette.py`(assets가 re-export)의 이름을 우선 씁니다. 새 아이콘/작물 색도 팔레트 톤에 맞춥니다.
   - **패널·버튼·그림자**는 `core/ui.py`의 `draw_panel`/`draw_button`/`draw_soft_shadow`를 쓰면 상단 **디자인 토큰**(`RADIUS`, `SHADOW_OFFSET` 등)으로 자동 통일됩니다. 개별 화면에서 모서리·그림자를 직접 그리지 마세요.
   - **작물·아이콘**은 픽셀 스프라이트로 통일돼 있습니다(`create_sprite_from_string`, `draw_crop_food`, `icon_*`). 새 것도 같은 방식+정수 배율로.
   - **배경 그라데이션**은 계단식 밴딩(`_quantize`/`_bg_quant`)으로 도트 톤을 유지합니다.
   - **래스터(사진/일러스트) 에셋**이 새로 들어오면 `assets._pixelize()`(numpy 없음)로 도트 톤에 맞출 수 있습니다.

---

## 4. 개발 작업 로그 (최근 업데이트가 위)

- **2026-07-18 저녁** (화면비 적응 마무리 · BGM 다양화 · 미출시):
  - **전 화면 꽉 참(레터박스 0) + 레이아웃 v2.2 방식 확정**: `layout.MAX_W/H = 2600/1500` —
    상한은 '비정상 길쭉 창 안전판'일 뿐, 실기기(폴더블 양방향·32:9·4K)는 전부 상한 안이라
    정수 배율 오버스캔(`ceil(창/배율)`)이 창을 정확히 채운다. **상한이 오버스캔보다 작으면
    그만큼 검은 띠가 생긴다** — 상한을 줄일 땐 반드시 창 레벨 픽셀 검사로 확인할 것
    (`scratch/qa/full_*.png` 생성 스크립트 참고). 안전영역은 항상 가운데, 세로 확장 화면은
    배경 연장 + 중앙 게임 블록 + 바 폭 확장 + '밭 수첩' 토글, 가로 확장은 사이드 패널(ox≥122).
    ⚠ '아래 밴드 대시보드 카드'는 여러 안(상하 분산→위 밴드→아래 밴드→양끝→중앙 페어)을
    거쳐 **최종 폐기**(팀 결정) — 다시 제안하지 말 것.
  - **작물별 배경 변주**: `assets.draw_tiled_background` — 들녘 스캐터(사과 낙엽·덤불 /
    벼 갈대·물빛 / 감자 돌무더기·짚단), 지평선 실루엣(과수원 나무 열·다랑이 물빛 계단·
    이랑 언덕), 위 여백 별 채우기. 전부 결정적 패턴(해시) — 새 작물을 추가하면 여기와
    nm(악몽) 색 분기에 한 갈래씩 추가할 것.
  - **과수원·논 비주얼**: `_draw_plain_soil`(사과) — 풀포기·계절 낙하물·다져진 밑동·뿌리·
    사다리(성장 82%↑)·떨어진 사과(수확기). 디테일은 SRCALPHA 레이어에 그려
    `pixelate(3, smooth=False)`(큰 픽셀 유지), 흩뿌림은 고정 시드 RNG. `_draw_paddy_field`(벼) —
    논둑 그리드(가로 1+세로 2, 풀 포함)·물꼬·부평초·우렁이. 새 디테일 추가 시 nm(악몽) 색
    분기 잊지 말 것.
  - **전면 베일 규칙(신규)**: 화면 전체를 덮는 딤/틴트/페이드는 `core/ui.draw_full_veil(screen,
    color)`를 쓴다 — (800,600) 서피스 fill은 넓은/세로 화면에서 여백만 밝게 남는다.
    (일시정지·설정·종료·dev·튜토리얼·일지·돌발·미니게임 딤·갤러리 모달·엔딩 틴트·회상/
    아버지의 날 페이드·수확 섬광·도정 오버레이·에필로그 틴트 전부 전환 완료. 새 전면 효과도
    이 헬퍼로.)
  - **BGM 9곡 체제**: gallery(오르골)/epilogue(여명)/stage(경쾌한 일손) 추가 —
    `_BGM_BUILDERS` 등록 + `BGM_BY_SCENE` 매핑(stage1~4→stage). ogg는 신규 3곡만 선별
    베이크(`core/sound/bgm/`) — 전체 재베이크는 기존 ogg 바이너리 diff를 오염시키니 금지.
  - 설정에 '업데이트 확인' 토글(닫기와 한 줄), 일지 힌트에 방향키 안내.
  - ⚠ 이날 디스크가 가득 차 `locales/en.json` 생성이 한 번 실패했었다 — i18n export 후
    `--check` 통과를 반드시 확인할 것.

- **2026-07-18 오후** (전면 QA 3차 — 실플레이·시각·코드 감사 통합 · 미출시):
  - **QA 방법**: `qa_sweep.py` 166장 시각 검수 + 씬/시스템별 코드 감사 + 헤드리스 실플레이를
    병행해 300+건을 수집·검증, 확정 건을 일괄 수정. 상세 목록은 CHANGELOG 미출시 섹션.
  - **치명 3건**: ① 세이브가 밭 수치를 FarmScene(빈 껍데기)에서 읽어 전부 null 저장 —
    '이어하기'가 1일차 밭으로 열리던 회귀(삼분할 때부터). `snapshot/restore`가 `farm.sim`을
    쓰도록 수정 + 로드 시 `restore_state`(작물·악몽·도전 먼저)→씬 생성→restore 순서로.
    ② 엔딩 1/2/3 재감상이 `get_ending`을 재호출해 회차 기록·업적·엔딩 해금을 위조 —
    `replay=True` 경로 신설(부작용 없음, 획득한 엔딩만). ③ 갤러리 이야기·기억 목록 클릭 불능
    (`_update_tab_rects`가 handle_events 초입마다 클릭 판정 리스트를 비움).
  - **구조 변경(회귀 주의)**: 일지가 이제 **정본(당근·밭)으로 저장**된다 — 표시 시점에
    `_localize_journal_line`이 언어별 치환·번역(EN은 carrot→작물 영단어 치환까지).
    `story_choice`도 저장은 정본, 표시는 `i18n.tnar`. 구세이브(치환 저장)는 호환 유지.
    회상 매칭은 정본·치환 이중 대조.
  - **오디오 축 정리**: BGM 볼륨은 '채널' 한 축만 쓴다(Sound.set_volume 금지 — 곱해져 제곱
    감쇠). 채널 0은 `set_reserved(1)`로 보호. 음량·음소거는 user_settings에 저장/복원.
  - **레이아웃**: `layout.MAX_W/H = 1760/1440` — 21:9(3440×1440 2배 스냅)·세로 9:16까지
    캔버스가 꽉 찬다. 스케일 target은 `round()`(내림이면 1px 헤어라인).
  - **오버레이 시간 정지**: 설정/종료/개발자 창이 열리면 PAUSE_SCENES(+epilogue)의
    scene.update를 건너뛴다 — 새 시간 압박 씬을 만들면 PAUSE_SCENES에 꼭 추가.
  - **작은 크기 픽셀 UI 노하우**: ① 28px급 버튼의 1px 테두리는 `pixel_rect(width=1)` 링이
    아니라 '금색 채움 위에 배경 채움(inflate(-2,-2))'으로 — 링은 좌우변이 끊겨 보인다.
    ② 높이 26px급 알약엔 CHAMFER_SM — CHAMFER(6)는 테두리가 '[ ]'처럼 분리돼 보인다.
    ③ 함수 안에서 `from core.pixelfx import pixelate` 지역 임포트 금지 — 같은 함수 앞쪽의
    모듈 전역 사용까지 UnboundLocalError로 죽는다(assets에서 실제로 터졌음).
  - **알려진 한계(다음 작업 후보)**: 회상 조각·기억 갤러리는 획득 시점 언어로 저장(이름 조사
    주입 구조), IME 후보창 위치 미보정(`set_text_input_rect`에 가상 좌표), 농장 씬의 석양
    해가 HUD 뒤에 슬쩍 걸침(검토 후 보류 — 재배치는 전 씬 배경 공유라 영향 큼), 배경
    별/스프라이트 일부의 소형 draw.circle은 유지(1~2px는 도트와 동일).

- **2026-07-18** (v2.5.0-dev.1 태그 배포 + 레포 전반 정리):
  - **배포**: 커밋 a95a94b → 태그 `v2.5.0-dev.1` 푸시 → CI 성공(EXE·APK·AAB 프리릴리스 등록).
    `buildozer.spec` version이 2.2.2로 낡아 APK 파일명이 어긋나던 것 → 2.5.0으로 동기화
    (**다음 태그부터** 파일명 반영. 앞으로 버전 올릴 때 `core/version.py`와 함께 갱신할 것).
  - **레포 정리**: README(특징·조작법·구조·문서 표를 v2.5 기준으로), 소개 사이트 `docs/`
    (특징 카드 3장 추가 + **스크린샷 15장 현행 빌드로 전면 교체** — main 병합 시 Pages 반영),
    GitHub 이슈 #2~#7 진행 코멘트/제목 갱신(＃6은 v2.5 안정판 기준으로 개명), 레포
    description·토픽 정리. 스크린샷 원본은 `scratch/qa/sweep/`(qa_sweep.py 재생성 가능).

- **2026-07-18 새벽** (v2.5 — IDEAS_STEAM 로드맵 완주 · 미출시):
  - **에필로그**: `scenes/epilogue.py` — BEATS 스크립트(라벨·본문·인터랙션·틴트). 내부에
    실제 FarmScene을 배경 호스트로 만들어 `draw_tiled_background`+`draw_farm_plot`만 빌려
    그리고(HUD 없음), 손맛 인터랙션(WaterPour·WeedPull·SoilMound)을 그대로 꽂는다.
    끝나면 `update_meta(epilogue_seen=True)`+업적. game_main 등록: SCENE_FACTORIES/
    FRESH_ON_ENTER/BGM("night")/FF_SCENES. 해금은 `save_system.epilogue_unlocked()`.
  - **도전 규칙**: `game_state.challenge`(None|no_journal|drought|seven_days, 세이브 포함,
    reset 시 보존 — 작물과 동일 취급). 적용 지점: FarmSimulator.__init__(시드·목표·안내),
    `advance_weather`(한발 고정), `apply_field_pressure`(이레 8일 초과 강제 종료),
    `inspect_message`+`draw_compact_meter`/건강 요약(무일지 가림). 해금
    `challenge_unlocked()`(기본 엔딩 3종). UI는 crop_select 좌하단 순환 버튼.
  - **연출**: 계절 배너(sim.last_season 비교→season_banner_timer, 세이브에 last_season 포함),
    수확 플래시(stage4 `_harvest_burst` — 성공 3경로에서 호출), 첫 회상 보장(try_trigger_memory
    `first_due`), 미니게임 변형(WaterPour 후반 밴드 축소·PestTap windy).
  - **데모**: `version.DEMO` — title 4곳 게이트(새 게임 2경로·달 이스터에그·에필로그)+안내 문구.
  - **주의**: 새 씬을 만들면 game_main의 4개 테이블(팩토리/FRESH/BGM/FF·PAUSE 해당 시)을
    모두 확인할 것. 도전 규칙을 늘리면 crop_select.CHALLENGES와 achievements 훅도 함께.

- **2026-07-17 심야** (v2.4 콘텐츠 확장 — IDEAS_STEAM 로드맵 1차 · 미출시):
  - **구조 요점**: '해의 성격'은 `narrative_data.YEAR_SEEDS`+`roll_year_seed()`(FarmSimulator.__init__에서
    추첨, `game_state.year_seed`, 세이브 포함) → `advance_weather`가 가중 추첨. 회상은
    `farm_simulator.MEMORY_POOLS`/`CROP_MEMORY_POOLS`(모듈 데이터)로 이사 — 갤러리 목록은
    `all_memory_titles()`로 자동 동기화. 이벤트는 `STORY_EVENTS`에 `"crop"`/`"not_crop"` 키,
    비반복은 메타 `stories_seen`(이제 **정본 제목**으로 기록 — `story_choice.canon_title`) 대조.
    엔딩 작물 문단은 `EndingScene.CROP_ENDING_LINES`(기존 본문 카탈로그 키를 건드리지 않도록
    번역 후 별도 문장을 이어 붙임).
  - **창고**: `core/storehouse.py`(ITEMS+unlocked_ids — 메타 파생 상태, 별도 저장 없음),
    아이콘은 assets `item_*` 9종. 회차 아카이브·누적 통계는 `save_system.record_run`
    (엔딩 실플레이 경로에서 호출, `game_state.final_day`/`run_stats` 사용) → 업적 재평가는
    `achievements.on_run_recorded`. 갤러리 탭은 4~5개 동적(`tab_rects`), 목록들은 휠 스크롤.
  - **밸런스 확인**: playtest 곡선 유지(잘함/보통→true, 못함→wither/normal) — 시드가 승패를
    뒤집지 않음. 통합 테스트 `scratch/qa_v24.py`(시드 편향·필터·비반복·기록·해금·렌더 8종).
  - **주의**: 새 이벤트/회상/창고 텍스트를 추가하면 반드시 i18n_data에 EN을 함께 넣고
    `tools/i18n_export.py` 재생성. 범용 이벤트 본문에는 '밭/당근' 단어를 피할 것(벼 치환 이슈).

- **2026-07-17 밤** (일시정지 완화 · 스팀 아이디어 문서 · 미출시):
  - **자동 일시정지**: `game_main.PAUSE_SCENES`(farm·stage1~4·star_connect·story_choice)에서만,
    `WINDOWFOCUSLOST`(키보드 포커스 상실)일 때만 발동. 마우스 이탈로는 더 이상 멈추지 않는다.
    새 씬에 시간 압박을 넣으면 PAUSE_SCENES에 추가할 것.
  - **`IDEAS_STEAM.md` 신설**: 플레이타임·흥미 확장 아이디어와 우선순위 로드맵(팀 논의용).
    콘텐츠 실측 수치(이벤트 6·회상 14·업적 16·완주 3~5h)가 담겨 있으니 콘텐츠 추가 시 갱신.

- **2026-07-17 저녁** (모자이크 근절 · 앰비언트 · 신기능 3종 · 미출시):
  - **글로우 렌더 규칙 변경(중요)**: 소프트 글로우는 이제 `pixelfx.glow_sprite(radius, color, px, steps,
    core)` + `blit_glow`(캐시·계단 알파 링)로 그린다. 균일 알파 선화·오브젝트는 `pixelate(surf, block,
    smooth=False)`(최근접 서브샘플). **평균 축소 pixelate를 소프트 원에 쓰면 '모자이크 검열'처럼 보인다** —
    새 글로우는 반드시 glow_sprite로. 맥동 글로우는 반경을 몇 px 단위로 양자화해 캐시 폭주 방지.
  - **날씨 앰비언트**: `farm_renderer._ambient_init/update_ambient/_draw_ambient` — FarmScene.update가
    매 프레임 굴린다. 날씨 문자열이 바뀌면 자동 재초기화.
  - **신기능**: 텍스트 속도 설정(`text_speed`: slow/normal/fast — `ui_utils.text_speed_factor()`가
    Typewriter에 곱함), 밭 일지 열람(J / `farm_renderer.JOURNAL_BTN` — ESC 처리를 위해 game_main의
    ESC 분기에 farm_journal 예외 있음), F12 스크린샷(game_main 루프, 세이브 폴더/screenshots).
  - **QA 도구**: `scratch/qa_ratios.py`(종횡비 매트릭스), `scratch/loop_test.py`를 game_main 기준으로
    복구(+F12·J·ESC 경로 포함 실루프 54프레임 검증). 스윕은 156장.

- **2026-07-17** (전 씬 정밀 QA 2차 · 미출시):
  - **QA 방법**: `scratch/qa_sweep.py`(신설)로 전 씬/상태 154장(KO/EN·악몽·창 비율별 캔버스 포함)을 실제 게임
    그리기 순서(캔버스→안전영역→씬→크롬)로 캡처해 시각 검수 + 코드 리뷰 + 헤드리스 클릭/로직 플레이 병행.
    `smoke_test.py`·`playtest.py`는 farm 삼분할 이후 API(`farm.sim.do_action(action, farm)`)로 복구해 통과.
  - **주요 수정**(상세는 CHANGELOG 미출시 섹션): 날씨 미니게임 5종·QTE 일러스트 도트화(+ RGBA 알파 무시 버그
    3곳 — `pygame.draw`를 screen에 직접 쓰면 알파가 무시되는 함정, HANDOFF 팁#2 재확인), '밭 수첩' 토글 위치
    이동(패널 겹침), 배속 버튼을 타자기 씬 6곳으로 한정(`game_main.FF_SCENES`), 튜토리얼 중 크롬 숨김+차단,
    존재하지 않는 엔딩 4종(happy/growth/skill/rush) 죽은 분기 제거, i18n 카탈로그 중복 키 14건·유령 키 정리,
    갤러리 업적 카드 EN 겹침 수정, `draw_button` 넘침 시 폰트 자동 축소(전역), 타이틀 Enter 진행 보호.
  - **주의(회귀 방지)**: ① 라벨을 문자열 연결로 조립하면("✕ "+라벨) EN 카탈로그 매칭이 깨진다 — 조각을 먼저
    `i18n.t()` 하고 붙일 것. ② `i18n_data.py`에 같은 KO 키를 다시 넣으면 앞 항목이 조용히 무시된다 —
    `scratch/dedupe_i18n.py` 참고. ③ 엔딩 타입은 nightmare/true/normal/bad/wither 5종뿐. ④ 스크린샷 스윕은
    `python scratch/qa_sweep.py` (출력: `scratch/qa/sweep/`).

- **2026-07-14** (v2.2.0 정식 배포 이후 · 미출시):
  - **화면 비율 적응형 UI**: 고정 800×600(4:3) 레터박스 → **적응형 캔버스**. `core/layout.py`가 창 비율에 맞춰
    캔버스 크기(안전영역 800×600 + 여백)를 정하고, `game_main`이 캔버스 버퍼 + 안전영역 서브서피스(`safe_sub`)를
    만들어 **씬/오버레이는 safe_sub(800×600)에 그대로 그린다**(씬 코드 무수정). 여백은 `layout.bleed_edges`가
    채우되 단순 스트레치가 아니라 **소프트 블러 + 밝기 자동 감지**로 처리한다: 밤 씬은 꿈-어둠 페이드 + 떠다니는
    빛 입자(`set_time`으로 애니메이션), 밝은 밭 씬은 부드러운 자연 연장만(`draw_story_backdrop`·`draw_tiled_background`
    끝에서 호출). 상/하 HUD 바는
    부모(캔버스) 폭으로 확장(`draw_top_bar`·`draw_bottom_bar`가 `screen.get_parent()` 감지). 입력은 `to_virtual_pos`가
    실좌표→캔버스→안전영역 로컬로 역보정(드래그 rel도 캔버스 배율). 창 모드 RESIZABLE + `recompute_layout`이
    리사이즈 시 재계산(안드로이드는 set_mode 재호출 안 함). **4:3은 완전 동일**. 개별 씬 크롬의 추가 앵커는 점진 확장.
  - **v2.2.0 정식 배포**: `v2.1.1`→`v2.2.0`(깔끔한 마이너 업). dev 라인은 `2.2.2-dev`였으나 안정 버전은
    `2.2.0`으로. GitHub Pages 소개 사이트 공개(`docs/`, main /docs) + 트레일러 GIF·스크린샷.
  - **선택 이벤트·밭 튜토리얼 영어 수정**: 선택 이벤트는 본문을 줄 단위로, 튜토리얼은 제목을 고정폰트로
    렌더해 영어에서 미번역/넘침. 둘 다 통짜 번역·폭에 맞춘 폰트 자동 축소로 수정(`story_choice`,
    `farm_renderer.draw_tutorial`). *v2.2.0 배포본엔 미포함 — 다음 릴리스 반영.*
  - **Crowdin 제거 → GitHub PR 번역 워크플로**: Crowdin 무료 오픈소스 라이선스는 '상업 제품 없음'을
    요구해(스팀 유료 판매와 상충) 채택 불가로 판단. `crowdin.yml` 삭제, `tools/i18n_export.py`를
    동기화·`--add <lang>`·`--check`(CI) 도구로 개편, `.github/workflows/i18n-check.yml`(JSON·유령키 검사)
    추가, `LOCALIZATION.md`·`CONTRIBUTING.md`를 PR 워크플로로 재작성. 정본은 여전히 `core/i18n_data.py`,
    번역은 `core/locales/*.json`(부분 번역 시 영어로 폴백).
  - **라이선스 정리**: 게임은 독점(All Rights Reserved) 유지하되, `LICENSE`에 **기여 라이선스 조항**
    추가(번역 PR을 상업 배포 포함 사용 가능) → 공개+상업 판매와 커뮤니티 번역을 양립. 폰트/라이브러리
    제3자 고지는 `THIRD-PARTY-NOTICES.md`로 분리(Galmuri11 OFL·pygame-ce LGPL 등).
- **2026-07-14** (v2.2.2-dev.12 프리릴리스 — 영어 현지화 QA: 긴 문장 넘침·미번역):
  - **밭일 일지 = 한국어 원문 저장 + 표시 시점 번역**: `farm_simulator._write_journal`는 일지를 KO 원문으로
    저장하고, 엔딩의 `_localize_journal_line`이 표시할 때 번역합니다. `[N일째·계절·날씨]`·`성장 N%`는 정규식으로
    인식해 `tf`로 재조립, `", "`로 합쳐진 '조합' 줄(잡초·벌레·배수)은 **마침표를 떼고 조각별 `i18n.t` 후 재조립**,
    나머지 정적 줄은 `i18n.t`. 긴 영어 줄은 `wrap_text(…, 560)`으로 개행 → 언어 전환 즉시 반영 + 창 넘침 해결.
  - **엔딩 태도 요약 영어화**: `_draw_result`가 `i18n.t("당신의 태도: ") + 항목별 i18n.t` 로 조립.
  - **인트로 세로 넘침 자동 폰트 맞춤**: `intro.prepare_page`가 페이지마다 패널(높이 272)에 들어오는 가장 큰
    폰트(22→16)를 골라 `self.page_font`로 그립니다. 악)몽중농원(악몽) 도입부의 영어 오버플로 해결.
  - **자동 축소 폰트 유틸**: 이름 입력 안내(`name_input._fit_font`)·개발자 모드 버튼(`dev_overlay`)이 폭에 맞춰
    폰트를 줄입니다. 가장 긴 dev 라벨은 짧은 표현으로(`악몽 토글`→`Nightmare`, `이해도 +N`→`Insight +N`).
  - **카탈로그 보강/단축**: 설정 `ON/OFF` 라벨 추가, 종료 확인 `Quit the game?`·이름 안내 `Your name in the
    dream field?`로 단축. `tools/i18n_export.py`는 en.json을 **병합**하므로, **바뀐** 키를 반영하려면 en.json을
    지우고 재생성해야 합니다(현재 사람 번역 없음 → 안전). ko/en.json 재생성 완료.
  - **알려진 한계(향후 작업)**: 일지·서사의 작물 명사가 **당근이 아닌 작물(감자·사과·벼)에서 영어로는 아직
    'carrot'/원문**으로 나올 수 있음. 이유: 일지 본문 EN 카탈로그가 `{crop}` 자리표시자 대신 리터럴 'carrot'을
    씀 + 일지 저장이 크로피파이(당근 치환)돼 비-당근 키가 카탈로그와 불일치. 근본 해결책은 일지를 **정규(당근)로
    저장**하도록 바꾸고(현재 크로피파이 저장 + retro 매칭이 이에 의존하니 `ending._draw_journal`의 retro 매칭도
    `k == line.strip()`로 함께 수정) 본문 EN 카탈로그를 `{crop}`화하는 것. 기본 작물이 당근이라 실사용 영향은 작음.
- **2026-07-13** (v2.2.2-dev.6 ~ dev.10 프리릴리스 — 대형 배치):
  - **제작진 화면 · 팀 표기 (dev.6)**: 제작진(크레딧) 화면과 엔딩 롤에 팀원·역할 추가, 제작사 표기를
    `삼광 (Samgwang)` → **`삼광 (三光)`** 으로 통일(픽셀 폰트가 한자 렌더 가능 확인). 메인 화면의 6버튼을
    '플레이 3버튼 + 보조 1줄'로 정리, 설정창에 **전체화면 토글** 추가(`game_state.request_fullscreen_toggle`).
  - **영어 현지화 (dev.7)** — `core/i18n.py`: **렌더 계층 자동 번역**. `get_font()`가 돌려주는 폰트 래퍼가
    `render()/size()` 시, `wrap_text()`가 줄바꿈 전에 원문을 번역. **로직 키는 한국어 원문 유지, 표시만 번역**
    → 세이브·비교 로직 무영향. 동적 문구는 `i18n.tf("…{n}…", n=…)`, **서사(조사·작물 치환)는 `i18n.tnar()`**
    (KO는 `swap_crop_word`+조사, EN은 카탈로그 템플릿 + `_EN_CROP` 자리표시자). 약 970개 번역(인트로·엔딩5·
    회상9·수확·미니게임·이벤트, 4작물 검증). `wrap_text`의 영어 공백-삼킴 버그도 수정. 상세 `LOCALIZATION.md`.
  - **Crowdin 연동 (dev.7)**: 런타임이 `core/locales/<lang>.json`(Crowdin 동기화)을 `i18n_data.py` 베이스라인
    위에 **병합** 로드 → 번역 수정이 코드 재생성 없이 반영. `crowdin.yml`, `tools/i18n_export.py`(en.json 비파괴
    병합), EXE(`--add-data core/locales`)·APK(`include_exts +json`) 번들.
  - **스팀 대비 (dev.7)**: `core/steam.py` — **순수 ctypes**로 공식 `steam_api64.dll` 직접 호출(“100% 파이썬”
    유지 위해 C 래퍼 미사용). DLL/App ID 없으면 완전 no-op. `achievements.unlock()`에 연결. 상세 `STEAM.md`.
  - **UI 통일 P1~P4 (dev.7~dev.10)** — `DESIGN_AUDIT.md`:
    - **P1**: 작물 사과·감자·쌀밥을 벡터 → **픽셀 스프라이트**로 통일(`draw_crop_food`은 정수 배율만).
      화면 스케일링은 1440p·4K처럼 2배↑ 들어갈 때 **정수 배율로 스냅**(`_apply_scaling`, 1080p/720p 무변).
    - **P2**: 날씨 5종·톱니·메달 아이콘 **픽셀화**(`icon_*`, `draw_weather_icon`, `_draw_gear_icon`,
      `_draw_medal`은 절반해상도→2배). 공용 색 팔레트 **`core/palette.py`** 신설(assets가 re-export).
    - **P3**: dad.png/field_bed.jpg는 이미 픽셀아트여서 field는 그대로, dad만 2px 블록 가볍게.
      `_pixelize()`(numpy 없음) 도구 남김.
    - **P4**: UI 크롬 **디자인 토큰**(`core/ui.py` `RADIUS`/`SHADOW_*` 등, draw_panel/button/shadow 기본값)
      + 배경 **밴딩**(하늘·잔디 계단식 + 색 계단화, `_quantize`/`_bg_quant`).
  - **배포**: dev.7·dev.10 태그로 프리릴리스 CI 성공(Windows EXE + Android APK/AAB). 로드맵 이슈 [#7].

- **2026-07-09** (v2.1.1 정식 배포):
  - **세이브 파일 경로 이전**: 스팀 배포 환경 및 윈도우 보안 정책에 따른 쓰기 제한 문제를 방지하기 위해 세이브 데이터 저장 경로를 실행 파일(EXE)이 위치한 폴더에서 사용자 AppData(`AppData\Roaming\MongjungNongwon`)로 이전. (기존 세이브 데이터 이전을 원하는 경우 수동으로 파일들을 이 경로에 옮겨야 복구됨을 안내 기재)
  - **QTE 완료 조건 해결**: 선택형 이벤트의 돌 줍기 등 QTE 미니게임의 완료 확인 조건식이 `hold` 유형 분기문에만 갇혀 있어 tap/trail/rub 유형 완료 시 멈춰있던 버그 수정.
  - **개발자 모드 크래시 해결**: F9 오버레이 창에서 성장 및 수확가능 클릭 시 `FarmScene`에 직접 필드가 없어 발생하던 `AttributeError` 크래시를 `farm.sim`을 참조하도록 수정.
  - **로딩 및 코드 최적화**: 모든 씬 기동 시 일괄 인스턴스화 대신 지연 초기화(Lazy Loading) 적용으로 기동 속도 최적화. `main.py` 내 좌표 계산 보정 헬퍼 `to_virtual_pos` 통합 및 윈도우 창 아이콘 크롭 로직 함수화.
  - **진엔딩 판정 조건 완화 및 오타 수정**: 이해도 최대치와 작물 체력이 가득 찬 상태에서도 진엔딩에 도달하기 어렵게 설계되어 있던 인내 및 공감, 실수 횟수 조건 판정 밸런스를 개선(완화)하고, 이해도 최고 단계의 명칭인 `"한 조각 of 시간"` -> `"한 조각의 시간"` 오타 수정.
  - **클리어 후 이어하기 세이브 즉시 삭제**: 플레이어가 엔딩에 도달하여 수확을 마친 즉시 `save_slot.json` 파일을 자동 소멸시켜 세이브 보존 다중 엔딩 획득 버그 차단.
  - **안내 및 라이선스**: `README.md` 해상도 오인 문구 수정, 폰트 SIL OFL 1.1 라이선스 준수를 위해 루트 `LICENSE` 파일 생성 및 `ending.py` 크레딧에 라이선스 공지 표기.
  - **텍스트 동적 치환 및 단축키 복원**: 일지나 밭 상황 알림 내 하드코딩된 "당근" 텍스트를 기르는 작물에 맞게 치환하고, 엔딩 화면에서의 엔딩 재감상 단축키(1~3) 복원.
  - **버전 갱신**: 프로젝트 버전을 `v2.1.1`로 격상.

- **2026-07-08** (v2.1.0 정식 배포):
  - **버그 수정**: 밭일 미니게임(`tending.py`) 로드 시 수치 리디렉션 꼬임으로 인한 `AttributeError` 해결.
  - **UI/UX 갱신**: 별 잇기 미니게임 게이지를 시간제한에서 별 연결 진행률로 직관화 개편. 히든 업적 오버플로우 여백 추가.
  - **저작권 오너십 적용**: 메인 타이틀, 갤러리 씬, 리드미 푸터에 삼광 팀 저작권(`© 삼광. All Rights Reserved.`) 탑재.
  - **버전 갱신**: 프로젝트 버전을 `v2.1.0` 으로 격상 및 배포 릴리스 정리 완료.

- **2026-07-07** (v2.0.0 정식 배포 및 구조 개선):
  - **코어 최적화**: 세이브 캐싱 및 원자적 쓰기(Atomic Write) 도입. Numpy 지수 감쇠 커널 합성곱 기반의 오디오 로우패스 100배 최적화 완료.
  - **중복 코드 통합**: 타이핑 및 파티클 연출을 `core/ui_utils.py` 로 모듈화. 조사 결합 헬퍼 통합.
  - **God Object 분해**: `farm.py` 의 시뮬레이터(`FarmSimulator`), 렌더러(`FarmRenderer`) 삼분할 모듈 캡슐화.
  - **미니게임 상속**: `MiniGameBase` 선언 및 9개 미니게임 상속 마이그레이션. 벌레 속도 델타 타임(dt) 기반 프레임 독립화.

- **2026-07-07** (피드백 배치 10 반영):
  - 호미 전통식 디자인 개편, QTE 닦기 표적 위치 재정렬, 기밀 히든 업적 2줄 개행 처리.

- **2026-07-07** (피드백 배치 9 반영):
  - 히든 업적 3종(백전노장, 붉은 새벽을 걷다, 창조주의 악수) 추가, 갤러리 히든 업적 탭 동적 활성화, 설정 M키 음소거 연동.

- **2026-07-07** (피드백 배치 8 반영):
  - 이벤트 씬 악몽 연동, 엔딩 시 악몽 BGM 대체, 사과 가지치기 붉은빛 리워크, 악몽 전용 엔딩 연출 신설, 버전 표시 스위치 추가.
