# 현지화(Localization) 가이드 — 한국어 ↔ 영어 (+ 향후 언어)

게임을 한국어(기본)/영어(+향후 언어)로 전환하는 시스템과 **GitHub PR 기반 번역 기여** 방법 설명서.

## 어떻게 동작하나

번역은 **원문(한국어) → 대상 언어 사전**이며, **렌더 계층에서 자동 적용**된다. 번역 소스는 두 겹:

1. **`core/i18n_data.py`의 `EN`** — 파이썬 베이스라인(정본, 항상 임포트 가능·번들 실패 위험 없음).
2. **`core/locales/<lang>.json`** — 커뮤니티 번역 파일. 있으면 베이스라인 위에 덮어써 번역을 갱신·확장한다
   (en 외 언어는 이 JSON만으로 추가). → 실행 시 `1`을 base로, `2`를 override로 병합한다.

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
> 번역된다. 그래서 **세이브 호환성과 게임 로직에 영향이 없다.** 미번역 키는 폴백:
> en은 한국어 원문, 기타 언어는 영어 베이스라인으로 표시된다(빈 값은 로더가 건너뜀).

## 번역 기여 워크플로 (GitHub PR)

별도 서비스 없이 **저장소에서 직접** 번역한다. 정본은 `core/i18n_data.py`, 번역은 `core/locales/*.json`.

| 파일 | 내용 |
|------|------|
| `core/locales/ko.json` | 소스 문자열 목록 `{한국어원문: 한국어원문}` — 번역할 문자열의 정본 목록(자동 생성) |
| `core/locales/en.json` | 영어 번역 `{한국어원문: English}` — 베이스라인 |
| `core/locales/<lang>.json` | 기타 언어(ja/zh …). 값만 해당 언어로 바꾸면 됨 |

**기존 번역을 고치려면** — `core/locales/<lang>.json`에서 값을 수정하고 PR을 올린다(런타임에서 우선 적용).

**새 언어를 추가하려면**
```bash
python tools/i18n_export.py --add ja     # core/locales/ja.json 을 영어 값으로 프리필 생성
# ja.json 의 값을 일본어로 번역
# core/i18n.py 의 _LANGS 에 "ja" 추가(설정에서 전환 가능해짐)
```
그리고 PR을 올린다. 안 고친 키는 자동으로 영어로 폴백되므로 **부분 번역 PR도 그대로 병합 가능**하다.

**새 원문(소스)을 추가하려면(개발자)** — `core/i18n_data.py`의 `EN`에 `"한국어 원문": "English"`를 넣고
```bash
python tools/i18n_export.py              # ko/en + 모든 locales/*.json 을 새 키와 동기화
```
- **정적 문자열**: 원문을 키로 넣기만 하면 렌더 계층이 자동 번역.
- **동적 문자열**(변수 포함): 호출부를 `i18n.tf("… {n} …", n=…)`로 바꾸고 템플릿(자리표시자 포함)을 등록.
  고정 열거형(ON/OFF 등)은 각 변형을 그대로 키로 넣어도 된다(`"전체화면: ON"` → …).
- 규칙: `{자리표시자}`·`\n`·기호(`·` `—` `%` 등)는 **그대로 보존**.

**자동 검사 (CI)** — PR이 `core/locales/**` 또는 `core/i18n_data.py`를 건드리면 GitHub Actions가
`python tools/i18n_export.py --check`를 돌려 **JSON 유효성·원문에 없는 '유령 키'**를 검사하고 언어별
커버리지를 리포트한다(`.github/workflows/i18n-check.yml`). 로컬에서도 같은 명령으로 미리 확인할 수 있다.

**빌드 번들** — PyInstaller(`--add-data core/locales`)·buildozer(`include_exts=…,json`)로 EXE·APK에 포함된다.

> 기여물의 라이선스는 [`CONTRIBUTING.md`](CONTRIBUTING.md)·[`LICENSE`](LICENSE) 참고(번역 기여는 게임에
> 상업 배포 포함 사용할 수 있도록 라이선스를 부여하는 조건으로 접수된다).

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

> 씬이 자체 줄바꿈/타이핑을 쓰면(예: `story_choice.py`) 조각 단위로 렌더돼 카탈로그 키와 안 맞는다.
> 그런 곳은 **먼저 통째로 `i18n.t()` 한 뒤** `core.ui.wrap_text`로 줄바꿈해야 매칭·정확한 영어 줄바꿈이 된다.

## 커버리지

한국어 원문 기준 약 980개 문자열이 영어로 번역돼 있다(타이틀·설정·크레딧·갤러리·작물 선택·이름 입력·
업적·밭 HUD·밭일 일지·미니게임·이해도 단계·전환 화면, 그리고 **서사 전체** — 인트로(일반+악몽)·엔딩 5종·
회상 9종·수확·선택 이벤트, 4작물 문맥 치환 포함). 언어별 정확한 수치는 `--check`로 확인한다.

- 폰트 Galmuri11은 라틴 문자·한자(三光)를 모두 렌더한다(확인 완료). 새 문자권(일본어 가나·한자 등)을
  추가할 때는 폰트가 해당 글리프를 포함하는지 확인이 필요하다.
- 알려진 한계: 당근이 아닌 작물에서 일지·서사의 작물 명사가 영어로는 아직 'carrot'/원문으로 나올 수 있다
  (본문 EN 카탈로그가 리터럴이라 향후 `{crop}` 자리표시자화 필요 — `HANDOFF.md` 참고).
