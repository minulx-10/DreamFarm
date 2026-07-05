# 몽중농원(DreamFarm) — 작업 인수인계 문서

> 이 문서는 **다음 세션의 나(콜드 스타트) 자신**을 위한 것이다. 새 대화는 이 레포의 이력을 모른 채
> 시작한다. 작업 전 이 문서와 `agent_rules.md`, 그리고 자동 로드되는 개인 메모리(MEMORY.md)를 먼저 읽어라.
> **작업할 때마다 이 문서의 "작업 로그"와 CHANGELOG.md를 갱신하라. (사용자 상시 지시)**

---

## 0. 이 게임이 무엇인가
Pygame으로 만든 감성 내러티브 농장 게임. 식탁에서 반찬을 밀어낸 아이가 꿈속 밭에서 작물을
직접 길러 아버지의 노동·사랑을 이해해 가는 이야기. 가상 해상도 800×600(악몽 모드 960×720)에서
렌더링 후 실제 창 크기로 스케일링(레터박스). 팀(반 친구들) 대상 배포 중이며 테스터 피드백을
빠르게 반영하는 사이클로 개발한다.

## 1. 빌드·실행·배포 (가장 중요)
- 실행: `pip install -r requirements.txt` 후 `python main.py` (Python 3.10+, pygame-ce, numpy).
- **배포는 git 태그로 트리거된다.** `.github/workflows/release.yml`이 `v*` 태그 push 시
  PyInstaller로 `DreamFarm.exe`(onefile, ~29MB)를 빌드해 GitHub Release에 올린다.
  - **안정 태그**(`v1.0.7`) → 정식 릴리스, Latest 표시(반 친구들용).
  - **개발 태그**(`-dev`/`-beta`/`-rc` 포함, 예 `v1.0.6-dev.4`) → **프리릴리스**(테스터용, Latest 아님).
- **브랜치**: `main`=안정, `dev`=개발. 현재 작업은 `dev`에서 진행하고 `dev`에 태그를 달아 프리릴리스한다.
  정식 배포는 `dev`→`main` 병합 후 `main`에서 안정 태그.
- 버전 표기: `core/version.py`의 `VERSION`(현재 "1.0.6"). 화면 좌상단에 `vX.Y.Z`로 뜬다.
  기존 태그는 절대 덮어쓰지 말고 항상 새 태그 생성.
- 릴리스 후 `gh run watch <id> --exit-status`로 빌드 완료 확인, `gh release view <tag>`로 프리릴리스 여부·자산 확인.
- `gh release edit <tag> --notes "..."`로 릴리스 본문(변경 내역) 작성.

## 2. 코드 구조 (핵심 파일)
```
main.py                게임 루프·씬 전환·씬별 BGM 매핑(BGM_BY_SCENE)·오버레이 처리·좌표 스케일링
                       · FRESH_ON_ENTER: 진입 때 새로 생성되는 씬 집합(text-input 등은 여기 있어야 함)
core/
  game_state.py        전역 상태, 엔딩 판정, STORY_EVENTS(선택형 이벤트+QTE), 텍스트 데이터
  audio.py             numpy 절차적 오디오 엔진 (효과음/배경음 전부 런타임 합성, 외부 음원 0개)
  assets.py            create_sprite_from_string 픽셀 스프라이트, 폰트, draw_crop_food/seed, 배경 렌더
  save_system.py       세이브/메타(엔딩·클리어 횟수·업적) JSON 저장
  achievements.py      업적 시스템(정의·해제·토스트). main 루프가 update/draw 호출
  settings_overlay.py  설정/저장 오버레이(톱니). ESC로 열림(main.py에서 라우팅)
  ui.py                패널·버튼·미터·draw_understanding_badge·draw_story_backdrop(night/warm/nightmare)
  version.py           VERSION 한 곳 관리
scenes/                title·name_input·intro·crop_select·farm·stage1~4·tending·story_choice·
                       memory·epiphany·star_connect·father_day·gallery·ending·transition
```
- **작물별 분기**는 `game_state.crop`("carrot"/"apple"/"potato"/"rice")로 어디서나 갈린다.
  crops.py의 CROPS에 growth_goal·family·라벨·no_weeds 등. apple=나무류(is_tree), rice=무논.
- **밭 렌더**: farm.py `draw_farm_plot` → is_tree면 `_draw_plain_soil`+`_draw_tree`(픽셀나무),
  rice면 `_draw_paddy_field`(무논)+rice 전용 `draw_crop` 분기, 그 외 field_bed.jpg 6구덩이.
- **손맛 미니게임**: tending.py(WaterPour·WeedPull·PestTap·SoilMound + 날씨 5종). farm 위 오버레이.
- **선택형 이벤트 QTE**: story_choice.py, task kind = tap/trail/hold/rub, theme(fence/water/soil).
- **수확**: stage4_harvest.py — 작물별 조작(당근=연타, 사과=아래로당김, 감자=좌우흔들, 벼=탈곡→도정).

## 3. 지금까지 한 일 (최근 세션들, v1.0.6 전후)
- 작업표시줄 아이콘(AppUserModelID + logo.png 투명여백 크롭), 앱 아이콘 크기 보정
- 작물 플레이타임 차등: 사과 growth_goal 34, 벼 26 (오래 걸리는 작물일수록 길게)
- **픽셀 나무 리워크**: 가지 먼저→잎 나중(현실 성장), 끝눈으로 '죽순 단계' 방지, 악몽 검붉은 잎, 열매
- **나무 가지치기 QTE**: 가지가 실제 나무 밑동(anchor)에서 뻗어 나오게
- **새벽의 고라니 QTE**: 진짜 울타리+부러진 틈+고라니 / 길 잃은 벌: 목적지 꽃 모양
- **감자 수확**: 좌우 번갈아 흔들기(풀림 게이지) / 감자 포기=둥근 잎 덤불+감자꽃 / 아이콘 감자화
- **업적 시스템** 신설: core/achievements.py + 갤러리 "업적" 탭 + 마크풍 토스트(9종)
- **벼(무논)**: 밭 전체가 물에 잠기게, 수분 실시간 반영, 물 깊이감·물결·반짝임, 모내기(처음부터 모),
  잎사귀·고개숙인 이삭, 밥공기(찻잔 탈피), mini_rice 초록 벼로, 물 위 갈색 흙패치 제거
- **벼 수확 데드락 버그 수정**: 탈곡 중 손 떼면 다시 못 잡던 것(준비상태 복귀 누락) → 한 줄 추가
- **악)몽중농원**: 논·나무밭·별잇기 배경까지 검붉게, 이름창 빨간 배경
- **ESC로 설정 열기**(메뉴 뒤로가기·확인창 ESC는 보존)
- **물주기/물대기**: 입구(스파웃)가 아래로 기울며 붓기, 논 물꼬 개방 연출
- **돌발상황 BGM** 신규 numpy 합성 → 밭정리·선택형 이벤트에 적용
- 겹침/여백 수정: 악몽 인트로 페이지 분할, 엔딩 크레딧 안내(우하단), 설정 확인창 여백,
  갤러리 엔딩카드 텍스트/버튼, 이름 입력 2회차 버그(FRESH_ON_ENTER에 name_input 추가)
- 엔딩 크레딧: 화면전환 없이 이어서 + 스페이스바 홀드 게이지(실수 다시하기 방지)
- 텍스트: 사과 '반찬'→'한 조각', 젓가락→포크, 이해도 라벨 "마음"→"이해도"
- 작물 선택창에 작물별 클리어 횟수 배지, 저장/불러오기 확인 절차, 갤러리→게임 진입 버그 수정

## 4. 앞으로 할 일 / 남은 후보

### 박서현/s0t.x1y 피드백 배치 (2026-07-06 접수) — 우선 처리
- [x] **A. 업적 카드 텍스트 오버플로우** — 완료(cell_h 58, 텍스트 안쪽 정렬).
- [x] **B. 악몽 잡초 빨갛게** — 완료(`weed_nm` 스프라이트 + farm/tending nightmare 교체).
- [x] **I. 감자 수확 밑에서 천천히 올라오게** — 완료(potato_loosen만큼 수직 상승).
- [x] **업적 브실골 등급 구분 + 1개 추가** — 완료(bronze/silver/gold/platinum 라벨·메달색,
  '열 번의 결실'(gold) 추가 = 총 10종. clears 합 10 이상 시 해제).
- [ ] **C. 굼벵이/해충 더 '해충스럽게'**: 현재 애벌레 디자인이 밋밋('개구림'). 더 벌레답게 리디자인
  (`sprites['bug']` in assets.py). 다리·더듬이·질감 등.
- [ ] **D. 쌀밥 접시 제거**: 엔딩 '쌀밥을 클릭' 테이블 씬에서 밥공기 아래 접시가 중복/어색.
  ending.py 테이블/음식 렌더에서 rice일 때 접시 빼거나 밥공기만.
- [ ] **E. 물뿌리개 물이 정확히 입구(스파웃)에서 나가게**: 현재 stream 시작점이 근사치라 캔 몸통
  중앙에서 나가는 것처럼 보임. tending.py WaterPour draw의 spout 좌표를 스프라이트 회전에
  맞춰 정확히 계산(렌더로 튜닝). 회전 캔의 실제 입구 픽셀에 stream 시작점 정렬.
- [ ] **F. 사과나무 어린 단계 UI 개선**: '죽순' 고치며 넣은 끝눈이 마인크래프트 블록처럼 밋밋함.
  farm.py `_draw_tree` 어린 단계(g<0.34 apex) 잎을 더 자연스러운 새싹/떡잎으로.
- [ ] **G. 거름/흙 북돋기 텍스트 일관성**: 사과나무는 버튼이 '거름 주기'인데 일지/안내는 '흙 북돋아'.
  나무일 때 안내 문구도 '거름'으로. (farm.py apply_action 결과문/notice)
- [ ] **H. 완전 초기화(태초부터) 옵션**: 현재 새 게임도 메타(클리어 횟수·업적·엔딩 해금) 유지.
  '전체 초기화'로 메타까지 지우는 옵션 추가(설정 오버레이? save_system에 wipe_meta).
- [ ] **I. 감자 수확 시 밑에서 천천히 올라오게**: 지금은 이미 뽑힌 상태로 보임. 흔들수록(potato_loosen)
  감자가 흙 밑에서 서서히 솟아오르게 stage4_harvest.py 감자 draw에 수직 오프셋 추가.


- 수확 씬(벼 탈곡·도정) 시각 폴리시: 아직 gold-tint sprout4 + 선/원. 밭 벼처럼 잎사귀·이삭·낟알로.
- 벼 모내기 '직접 심기' 인터랙션(현재는 연출만).
- 나무 거름 주기 QTE가 6구덩이용 SoilMound라 나무엔 약간 안 맞음 → 나무 전용 연출.
- 정식 릴리스(main 병합 + 안정 태그 vX)는 테스터 OK 후.

## 5. 안 되는 것 / 주의
- **순수 100% 파이썬 프로젝트다.** GitHub 언어 통계에 **Python 100%**로 떠야 한다(사용자 요구).
  → 다른 프로그래밍 언어 소스(JS/HTML/CSS/C/Cython/셰이더 등)나 컴파일 확장을 넣지 말고 모든 로직을
  파이썬으로 구현한다. 그래서 소리도 음원 파일 대신 numpy 합성, 그래픽도 코드로 그린다.
  (참고: `.md` 문서·`.yml` 워크플로는 linguist에서 prose/data로 분류돼 언어 통계 바에서 제외되므로 무방.)
- **오디오 파일은 못/안 만든다** → 필요한 소리는 audio.py에서 numpy로 합성한다(위 100% 파이썬 원칙과 일치).
- **사용자가 PowerPoint로 편집한 발표자료(.pptx)는 재빌드로 덮어쓰지 말 것**(개인 메모리 참조).
- 헤드리스 환경엔 오디오/디스플레이 장치 없음 → SDL dummy 드라이버로 렌더 검증(아래 노하우).
- git 커밋 시 CRLF 경고는 Windows 줄바꿈 자동변환이라 무시해도 됨.
- 커밋/푸시/릴리스는 outward-facing이므로 사용자 요청("올려"/"마음대로 해") 있을 때 진행.

## 6. 습득한 노하우 (헤매지 말 것)
1. **변경은 반드시 헤드리스 렌더로 눈으로 검증**한다. 스크래치 스크립트 패턴:
   ```python
   import os; os.environ["SDL_VIDEODRIVER"]="dummy"; os.environ["SDL_AUDIODRIVER"]="dummy"
   import sys; sys.path.insert(0, os.path.abspath("."))
   import pygame; pygame.init(); screen=pygame.display.set_mode((800,600))
   from core.assets import init_sprites; init_sprites()
   from core import audio; audio.init()
   from core.game_state import game_state
   game_state.crop="rice"; game_state.nightmare=False
   from scenes.farm import FarmScene
   f=FarmScene(); f.growth=12; f.moisture=82; f.tutorial_active=False; f.crop_offsets=[0]*6
   f.draw(screen)
   pygame.image.save(screen.subsurface(pygame.Rect(44,140,362,318)).copy(), "scratch/out.png")
   ```
   그 PNG를 Read 툴로 열어 확인. 스크래치는 `scratch/`(gitignore됨)에 두고 끝나면 삭제.
   - 튜토리얼 오버레이가 가리면 `f.tutorial_active=False`.
   - 밭 플롯만 크롭: `pygame.Rect(44,140,362,318)`.
   - 로직 버그는 pygame.event.Event로 입력을 시뮬레이션해 상태 전이를 assert(예: 수확 데드락 검증).
2. **pygame.draw는 알파 블렌딩을 하지 않고 픽셀을 덮어쓴다.** SRCALPHA 서피스에 낮은 알파로
   draw하면 아래를 지워버린다(벼 논 물이 갈색으로 뚫렸던 버그의 원인). 반투명 겹침은 별도
   서피스에 그려서 blit하거나, 화면에 직접 불투명 선으로 그린다.
3. **오디오**는 전부 numpy 합성: `_tone/_adsr/_noise/_pad_progression/_melody` + `_to_sound`.
   새 BGM = 빌더 함수 + `_BGM_BUILDERS`에 등록 + main.py `BGM_BY_SCENE`에서 씬에 매핑.
   `pygame.sndarray.make_sound`에 넘기기 전 반드시 `_to_sound`로 int16 스테레오 변환.
4. **픽셀 폰트(Galmuri11)는 이모지·일부 기호(✓ 등)를 지원 안 함** → 두부(□)로 뜬다. 텍스트로
   대체하거나 도형을 직접 그린다.
5. **씬 인스턴스는 시작 시 1회 생성 후 재사용**. 진입마다 재초기화가 필요하면(텍스트 입력의
   `start_text_input` 등) main.py `FRESH_ON_ENTER`에 넣어야 한다.
6. **밭/스탯 좌표**: 밭 플롯 오프셋 (44,140), crop_positions()는 그 안 6구덩이. 무논 inner rect는
   좌표계가 다르니 정렬 주의.
7. **엄청난 양의 병렬 시각 요청**이 올 때: Ultracode/워크플로우로 이슈별 read-only 조사 병렬화 →
   결과 받아 본인이 인라인 구현 + 렌더 검증(파일 충돌 방지). 실제로 유효했음.
8. **작업표시줄 아이콘**: Windows는 pygame 창을 python.exe로 묶는다.
   `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(...)`를 창 생성 전에 호출하면
   set_icon 아이콘이 작업표시줄에 뜬다. 아이콘 원본의 투명여백은 `get_bounding_rect`로 크롭해 꽉 채운다.

## 7. 작업 로그 (append-only; 최신이 위)
- **2026-07-06** (피드백 배치 일부): 업적 카드 오버플로우 수정, 악몽 잡초 빨갛게, 감자 수확 상승,
  업적 브실골 등급화+'열 번의 결실' 추가(10종). §4의 C/D/E/F/G/H는 다음 세션 몫.
- **2026-07-06** (v1.0.6-dev.3): 벼 수확 데드락 수정, ESC→설정, 물주기 입구 애니메이션, 벼 UI 리워크.
  커밋 735343b, 프리릴리스 v1.0.6-dev.3.
- **2026-07-03** (v1.0.6-dev.2): 돌발상황 BGM·무논/작물 그래픽·엔딩 크레딧. 커밋 1168eb9.
- **2026-07-03** (v1.0.6-dev.1): 업적 시스템·픽셀나무 리워크·QTE 테마·감자수확. 커밋 297a4aa.
> 새 작업 시 여기에 날짜·요약·커밋/태그를 추가할 것.
