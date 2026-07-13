# 스팀(Steam) 출시 준비 체크리스트

이 문서는 **몽중농원**의 최종 목표인 **Steam 출시**를 위한 기술 준비 상태와 남은 일을 정리한다.
(플레이스토어/안드로이드 서명은 `RELEASING.md` 참고.)

---

## ✅ 이미 되어 있는 것 (코드 기반이 스팀에 맞게 갖춰짐)

- **EXE 에셋 경로 처리** — `core/assets.py`의 `resource_path()`가 PyInstaller `sys._MEIPASS`를
  인식해, 폰트(Galmuri11.ttf)·이미지(dad.png, field_bed.jpg, logo.png)·소리(`core/sound/**`)를
  묶인 exe 안에서도 찾는다.
- **세이브 저장 위치** — `core/save_system.py`가 **frozen(배포 exe)일 때 `%APPDATA%\MongjungNongwon`**
  (없으면 홈 디렉터리)에 저장한다. 스팀 설치 폴더(`Program Files`)는 보통 쓰기 금지라 exe 옆에
  저장하면 안 되는데, 이 처리가 되어 있어 안전하다.
- **Windows EXE 자동 빌드** — `.github/workflows/release.yml`의 `build-windows` 잡이 태그 push 때
  PyInstaller onefile로 `DreamFarm.exe`를 만들고 **모든 런타임 에셋을 `--add-data`로 번들**한다
  (폰트·3개 이미지·`core/sound` 트리 전부 확인됨).
- **전체화면 / 4:3 레터박스 스케일** — F11 **및 설정창 토글**로 전체화면 전환. 어떤 해상도에서도
  800×600 가상 캔버스를 4:3으로 레터박스해 그린다.
- **창 아이콘 / 작업표시줄** — `logo.png`를 창 아이콘으로, AppUserModelID로 작업표시줄 독립 표기.
- **업적·설정 시스템** — 로컬 업적(`core/achievements.py`)은 스팀 도전과제로 1:1 매핑 가능.
  음량/자동저장/세이브 관리 설정 완비.
- **스팀 도전과제 ctypes 스캐폴드 (연결 완료, App ID 대기)** — `core/steam.py`(순수 ctypes)를
  만들어 유일한 업적 해제 경로 `achievements.unlock()`에 연결했다. `steam_api64.dll` + App ID가
  없으면 완전 무해한 no-op(실제 게임 루프 5프레임 헤드리스 구동으로 무결 확인). game_main이
  시작 시 `steam.init()`, 매 프레임 `run_callbacks()`, 종료 시 `shutdown()`을 부른다.
  → **App ID만 확보되면(아래) 곧바로 실제 도전과제가 뜬다.**

## 🟡 코드로 할 수 있으나 **Steam App ID / 결정**이 필요한 것

1. **Steamworks 도전과제 연동** — *코드(`core/steam.py`)는 이미 붙여 둠. App ID 확보 후 남은 절차만*:
   - **Steam App ID 확보**(Steamworks 파트너 등록, 앱당 US$100 — 사용자만 가능). 이게 유일한 관문.
   - ⚠️ **"100% 파이썬" 준수**를 위해 이미 **ctypes로 공식 `steam_api64.dll` 직접 호출** 방식으로
     구현됨(C 래퍼 `SteamworksPy` 안 씀). DLL은 바이너리 에셋이라 언어 통계 무관.
   - App ID 확보 후 할 일:
     a. 파트너 사이트에서 각 도전과제 **API Name을 로컬 업적 id와 동일하게** 생성
        (first_harvest / grow_carrot / grow_potato / grow_rice / grow_apple / perfect_harvest /
         veteran / all_crops / true_ending / nightmare_clear / hundred_clears / nightmare_ending /
         developer_secret). 다르게 지으면 `core/steam.py`의 `ACHIEVEMENT_MAP`에 매핑.
     b. SDK의 `steam_api64.dll`을 레포/빌드에 넣고 PyInstaller `--add-binary`로 exe에 번들.
     c. 로컬 테스트: 레포 루트에 `steam_appid.txt`(App ID 한 줄) + 스팀 클라이언트 실행
        (이 파일은 `.gitignore`에 이미 추가됨).
2. **스팀 클라우드 세이브** — 이미 `%APPDATA%\MongjungNongwon`에 저장하므로, 파트너 사이트에서
   그 경로를 **Steam Auto-Cloud(UFS) 패턴**으로 등록하면 코드 변경 거의 없이 클라우드 동기화가 된다.
3. **SteamPipe 업로드 자동화** — 현재 CI는 exe를 GitHub 릴리스에 올린다. steamcmd 빌드 계정을
   시크릿으로 넣으면 GitHub Actions에서 스팀 데포까지 자동 업로드하는 스텝을 추가할 수 있다.

## 🔴 코드 밖 — **파트너 사이트·기획·자산** (사용자 몫)

- **Steamworks 파트너 계정 등록 + 앱 생성**(US$100/앱) — 위 모든 SDK 작업의 전제.
- **스토어 페이지**: 제목·설명·태그·스크린샷·트레일러·**캡슐 이미지 각 규격**(헤더 460×215,
  메인 캡슐 616×353, 세로 캡슐 374×448 등).
  - (위 "캡슐 이미지" = 스팀 스토어에 노출되는 대표 썸네일 규격들)
- **연령 등급 / 콘텐츠 설문**, 가격, 출시일.
- **지원 언어** — 현재 **한국어 전용**. 대사·UI 문구가 `core/narrative_data.py` 등에 하드코딩되어
  있어, 영어(등) 현지화를 하려면 문자열 분리(i18n) 작업이 필요하다. **큰 항목이지만 글로벌 노출을
  크게 넓힘** → 별도 결정.
- **안정성** — 스팀 검수/리뷰를 위해 크래시 없어야 함(현재 `main.py`에 크래시 로그 폴백 있음).

---

## 권장 순서

1. **Steamworks 파트너 등록 → App ID 확보** (모든 것의 시작점)
2. App ID 주면 → 파트너 사이트 도전과제 API Name 생성 + `steam_api64.dll` 번들 + `steam_appid.txt`
   (코드 `core/steam.py`는 이미 붙어 있어 이 3가지만 하면 즉시 작동)
3. 클라우드 세이브(UFS) 경로 등록
4. (선택) **영어 현지화** — 시장 크게 확대
5. SteamPipe 업로드 CI 추가

> 요약: **엔진/빌드/저장 경로는 이미 스팀 배포에 맞게 준비**되어 있다. 지금 막힌 유일한 관문은
> **Steam App ID(파트너 등록)** 이며, 그것만 확보되면 도전과제·클라우드까지 코드로 마무리할 수 있다.
