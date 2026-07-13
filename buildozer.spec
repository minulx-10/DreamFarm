[app]
# (str) Title of your application
title = 몽중농원

# (str) Package name
package.name = dreamfarm

# (str) Package domain
package.domain = mongjung.nongwon

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
# ogg = 미리 구운 효과음/배경음(core/sound/**). 이게 있어야 런타임에 numpy 없이 소리가 난다.
source.include_exts = py,png,jpg,ttf,ogg,json

# (list) Application requirements
# numpy 는 뺐다 — 소리는 빌드 시 tools/bake_audio.py 로 .ogg 로 미리 구워 싣는다.
# numpy 를 p4a 로 매번 소스 컴파일하는 게 빌드를 느리고 취약하게 만든 주범이었다.
# pygame-ce 는 p4a 에 병합된 레시피가 없어(아래 p4a.local_recipes) 로컬 레시피로 빌드한다.
requirements = python3,pygame-ce

# (str) python-for-android 로컬 레시피 폴더 — pygame-ce 레시피(PR #2971)를 여기 담아 쓴다.
p4a.local_recipes = ./p4a-recipes

# (str) Application versioning (method 1)
version = 2.2.2

# (str) 앱 아이콘 — 여백을 잘라 아이콘 칸을 꽉 채운 투명 배경 버전(core/icon.png). 스플래시는 로고 사용.
icon.filename = %(source.dir)s/core/icon.png
presplash.filename = %(source.dir)s/core/logo.png

# (str) 스플래시 배경색 (게임 밤하늘 톤)
android.presplash_color = #14121E

# (list) Supported orientations
orientation = landscape

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 1

# (list) Permissions
# 인터넷/저장소 권한 불필요 — 폰트·소리·이미지 모두 앱에 내장, 세이브는 앱 전용 공간 사용.
android.permissions =

# (int) Minimum API your APK will support.
android.minapi = 24

# (int) Target API — 구글 플레이 정책상 34 이상 필요.
android.api = 34

# (str) Android NDK version — p4a 툴체인이 검증한 25b 로 고정(그 이상은 종종 깨진다).
android.ndk = 25b

# (list) Supported architectures
# arm64-v8a 단일 — 근래(약 2019년 이후) 모든 안드로이드폰이 arm64다. armeabi-v7a 를 빼면
# 빌드 시간이 거의 절반으로 준다. 구형 32비트 기기 지원이 필요하면 아래에 armeabi-v7a 를 더한다.
android.archs = arm64-v8a

# (bool) Use private storage for data (set to True for default behaviour)
android.private_storage = True

# (str) python-for-android 버전 고정 — v2024.01.21 은 파이썬 3.11.5 를 빌드한다.
# develop 은 파이썬 3.14 를 빌드하는데, 그 조합에서는 setuptools 가 distutils 를 현대화하며
# distutils.ccompiler.spawn 을 없애 pygame-ce 2.4.0 의 구식 빌드가 깨진다(AttributeError).
# 3.11 은 stdlib distutils(ccompiler.spawn 존재)를 갖고 있어, 아래 SETUPTOOLS_USE_DISTUTILS=stdlib
# 와 함께 pygame-ce 가 정상 컴파일된다. 이 태그는 레시피가 쓰는 최신 p4a API 도 모두 포함한다.
p4a.branch = v2024.01.21

[buildozer]
# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
