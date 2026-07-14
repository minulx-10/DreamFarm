# 안드로이드 정식 출시(플레이스토어) 서명 가이드

이 저장소의 CI(`.github/workflows/release.yml`)는 **keystore 시크릿이 등록돼 있으면**
태그를 push할 때 **서명된 AAB**(Android App Bundle, 플레이스토어 업로드 형식)를 자동으로
빌드해 릴리스에 첨부합니다. 시크릿이 없으면 지금처럼 **디버그 APK**만 나옵니다(빌드는 안 깨짐).

> 디버그 APK는 "출처를 알 수 없는 앱" 설치 경고가 뜹니다. 이 경고는 **플레이스토어를 통해
> 설치할 때** 사라집니다. 그래서 정식 배포는 아래처럼 서명된 AAB를 플레이 콘솔에 올리는 흐름입니다.

---

## 1) 업로드 keystore(서명 키) 만들기 — **한 번만**, 내 PC에서

```bash
keytool -genkey -v -keystore dreamfarm-release.keystore \
  -alias dreamfarm -keyalg RSA -keysize 2048 -validity 10000
```
- 실행하면 keystore 비밀번호와 키(alias) 정보를 물어봅니다. **비밀번호를 꼭 기억/백업하세요.**
- `-alias`(여기선 `dreamfarm`)와 두 비밀번호(keystore/alias)를 아래 시크릿에 그대로 씁니다.

> ⚠️ **이 keystore 파일과 비밀번호는 절대 잃어버리면 안 됩니다.** 이 키로 서명해야 앱을
> 계속 업데이트할 수 있고, 잃어버리면 같은 앱으로 업데이트를 못 올립니다. 저장소에 커밋하지 말고
> 안전한 곳에 백업하세요. (`.gitignore`에 `*.keystore`가 들어 있습니다.)

keystore를 base64 문자열로 변환(시크릿에 넣기 위함):
```bash
# Linux/Mac
base64 -w0 dreamfarm-release.keystore
# Windows(PowerShell)
[Convert]::ToBase64String([IO.File]::ReadAllBytes("dreamfarm-release.keystore"))
```

## 2) GitHub 저장소에 시크릿 4개 등록

저장소 → **Settings → Secrets and variables → Actions → New repository secret** 에서:

| 시크릿 이름 | 값 |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | 위에서 만든 base64 문자열 |
| `ANDROID_KEYSTORE_PASSWORD` | keystore 비밀번호 |
| `ANDROID_KEY_ALIAS` | 키 alias (예: `dreamfarm`) |
| `ANDROID_KEY_PASSWORD` | 키(alias) 비밀번호 |

## 3) 태그 push → 서명된 AAB 자동 생성

```bash
git tag v2.2.2 && git push origin v2.2.2
```
빌드가 끝나면 릴리스에 `*.aab`(서명됨)가 EXE·APK와 함께 붙습니다.

## 4) 플레이 콘솔에 올리기

1. [Google Play Console](https://play.google.com/console)에서 앱 생성(최초 1회, 개발자 계정 $25 등록비).
2. 테스트 트랙(내부 테스트 → 비공개 테스트)에 `*.aab` 업로드.
3. 처음엔 **Play 앱 서명**을 켜두면 구글이 배포용 키를 관리하고, 위에서 만든 건 "업로드 키"가 됩니다(권장).
4. 비공개 테스트는 최근 정책상 **테스터 12명 이상 · 14일 유지** 조건이 있을 수 있으니 확인하세요.

---

## 참고
- 서명 관련 CI 단계는 시크릿이 있을 때만 실행됩니다. 없으면 아무 일도 안 하고 디버그 APK만 나옵니다.
- 로컬에서 직접 서명 빌드를 뽑고 싶으면(맥/리눅스):
  ```bash
  export P4A_RELEASE_KEYSTORE=$PWD/dreamfarm-release.keystore
  export P4A_RELEASE_KEYSTORE_PASSWD=... P4A_RELEASE_KEYALIAS=dreamfarm P4A_RELEASE_KEYALIAS_PASSWD=...
  echo "android.release_artifact = aab" >> buildozer.spec   # AAB로 뽑을 때
  buildozer android release
  ```
