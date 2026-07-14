# 현지화(Localization) 가이드 — 한국어 ↔ 영어 (+ Crowdin)

스팀 글로벌 출시 대비, 게임을 한국어(기본)/영어(+향후 언어)로 전환할 수 있게 하는 시스템 설명서.

## 어떻게 동작하나

번역은 **원문(한국어) → 대상 언어 사전**이며, **렌더 계층에서 자동 적용**된다. 번역 소스는 두 겹:

1. **`core/i18n_data.py`의 `EN`** — 파이썬 베이스라인(항상 임포트 가능, 번들 실패 위험 없음).
2. **`core/locales/<lang>.json`** — **Crowdin에서 동기화하는 파일**. 있으면 베이스라인 위에 덮어써
   번역을 갱신·확장한다(en 외 언어는 이 JSON만으로 추가). → 실행 시 `1`을 base로, `2`를 override로 병합.

- **`core/i18n.py`** — 엔진.
  - `t(s)` : 문자열을 현재 언어로 번역(카탈로그에 있으면 대상 언어, 없으면 원문 폴백).
  - `tf(template, **kw)` : 동적 문자열용. 템플릿을 먼저 번역한 뒤 `{자리표시자}`를 채운다.
  - `tnar(ko_template, crop_key=…, **kw)` : 서사용(조사·작물 치환). 아래 참고.
  - `set_language('ko'|'en')`, `get_language()`, `toggle()`, `init(lang)`.
- **`core/assets.py`의 `_I18nFont`** — `get_font()`가 돌려주는 폰트 래퍼. `render()`/`size()` 시 문자열을
  `t()`로 번역한다. → **대부분의 라벨·짧은 문장은 호출부를 고치지 않아도 자동 번역**된다.
- **`core/ui.py`의 `wrap_text()`** — 줄바꿈 '전에' 원문을 통째로 `t()`로 번역한다.
- **언어 설정 저장** — 설정창(⚙)의 **언어 토글**이 `save_system`의 `"language"`에 저장하고, `game_main`이
  시작 시 불러와 `i18n.init()` 한다.

> **로직 안전**: 요일·작물·기억 제목 등 한국어 문자열은 **저장·비교엔 원문 그대로** 쓰이고 '표시'만
> 번역된다. 그래서 **세이브 호환성과 게임 로직에 영향이 없다.**

## Crowdin 워크플로 (번역 관리)

```bash
python tools/i18n_export.py         # core/i18n_data.py → core/locales/{ko,en}.json 생성/병합
crowdin upload sources              # ko.json(한국어 원문) 업로드  ← crowdin.yml 사용
crowdin upload translations -l en   # (선택) 기존 en.json 번역 선반영
crowdin download                    # 번역된 <lang>.json 내려받기 → 그대로 게임에 반영(코드 재생성 불필요)
```
- 자격 증명은 환경변수: `CROWDIN_PROJECT_ID`, `CROWDIN_PERSONAL_TOKEN`.
- `tools/i18n_export.py`는 **en.json을 덮어쓰지 않고 병합**한다(Crowdin 번역 보존 + 새 키만 베이스라인 추가).
- 빌드 번들: PyInstaller(`--add-data core/locales`)·buildozer(`include_exts=…,json`)로 EXE·APK에 포함됨.
- 새 언어 추가: Crowdin에서 번역 → `core/locales/ja.json` 등이 생기면 끝(`_LANGS`에 토글만 추가).

## 번역을 추가/수정하려면

- **기존 번역 수정**: **Crowdin에서** 고치거나 `core/locales/en.json`을 직접 편집(런타임에서 우선 적용).
- **새 원문(소스) 추가**: `core/i18n_data.py`의 `EN`에 `"한국어 원문": "English"`를 넣고
  `python tools/i18n_export.py` 실행(→ ko.json/en.json 갱신) → Crowdin 업로드.
- **정적 문자열**: 원문을 키로 넣기만 하면 렌더 계층이 자동 번역.
- **동적 문자열**(변수 포함): 호출부를 `i18n.tf("… {n} …", n=…)`로 바꾸고 템플릿(자리표시자 포함)을 등록.
  고정 열거형(ON/OFF 등)은 각 변형을 그대로 키로 넣어도 된다("전체화면: ON" → …).
- 규칙: `{자리표시자}`·`\n`·기호(`·` `—` `%` 등)는 그대로 보존.

## 현재 커버리지 (dev.7 기준, 약 970개 번역)

✅ 타이틀·설정·크레딧·갤러리(추억 저장소)·작물 선택·이름 입력·업적(제목/설명)·종료 확인 ·
   밭 HUD(요일/날씨/건강/예보/미터/할 일)·밭일 일지 본문·미니게임 카운터(잡초/햇살/빗물/별 잇기 등)·
   이해도 단계명·전환(결과) 화면.
✅ **서사(내러티브) 완료 — `i18n.tnar` 기반**:
   - **인트로**(일반 + 악몽 도입부 — 이름·작물·조사 반영)
   - **엔딩 5종**(진/노멀/배드/시듦/악몽 — 제목·본문)
   - **회상(기억) 9종**(이름 조사·작물·수저(젓가락↔포크↔숟갈) 반영)
   - **수확 안내/프롬프트** 및 **미니게임 결과**(밭 정리/물 주기/해충/수확)
   - carrot·rice·apple·potato 각 작물의 문맥 치환(밭↔논↔과수원)까지 반영·검증 완료.

✅ **특수 이벤트·개발용까지 완료**:
   - 돌발 상황(강제 대기)·밭 자세히 보기(경고+날씨 팁)·아버지의 날 프롬프트·별 잇기 안내·개발자
     이스터에그 토스트·개발자 모드(F9) 메시지까지 번역. → **사실상 전 화면이 영어로 표시된다.**

## 남은 것

- **UI 통일(픽셀 일관성)** — 현지화와 별개의 시각 디자인 과제. `DESIGN_AUDIT.md` 참고.
- **문구 다듬기** — 영어 폭에 따른 미세 레이아웃/표현 조정은 실제 플레이하며 계속 보완.

### 조사/작물 치환 처리 패턴 — `i18n.tnar`

서사 문자열은 **`i18n.tnar(ko_template, crop_key=game_state.crop, name=…, name_eun=…, …)`** 로 감싼다.
- **KO**: 템플릿을 `format`(조사 채움)한 뒤 `swap_crop_word`로 '당근'→현재 작물 치환.
- **EN**: 카탈로그의 영어 템플릿을 가져와 `{name}`/`{crop}`/`{food}`/`{field}`/`{utensil}`를 채운다
  (작물 영어 단어는 `crop_key`로 자동 주입 — `core/i18n.py`의 `_EN_CROP`).

```python
# KO 키: "{name_eun} 식탁 위 당근 반찬을 슬쩍 밀어냈다."
# EN 값: "{name} quietly pushed the {food} aside on the table."
i18n.tnar("{name_eun} 식탁 위 당근 반찬을 슬쩍 밀어냈다.",
          crop_key=game_state.crop, name=name, name_eun=name_eun)
```

`.format()`은 남는 인자를 무시하므로 KO 템플릿엔 `{name_eun}`, EN 템플릿엔 `{name}`을 써도 안전하다.
새 작물 문맥 단어가 필요하면 `_EN_CROP`에 추가한다.

> 씬이 자체 줄바꿈을 쓰면(예: `transition.py`) 조각 단위로 렌더돼 카탈로그 키와 안 맞는다. 그런 곳은
> **먼저 통째로 `i18n.t()` 한 뒤** `core.ui.wrap_text`로 줄바꿈해야 매칭·정확한 영어 줄바꿈이 된다.

## 참고

- 부트스트랩 번역은 파일별로 분할해 병렬 생성 후 병합했다(일회성). 이후 유지보수는 위처럼
  `core/i18n_data.py`를 직접 편집한다.
- 폰트 Galmuri11은 라틴 문자·한자(三光)를 모두 렌더한다(확인 완료).
