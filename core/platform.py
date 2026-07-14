"""플랫폼 감지 및 안드로이드 관련 공용 상수.

python-for-android 부트스트랩은 실행 시 ANDROID_ARGUMENT 환경변수를 설정한다.
이걸로 '지금 안드로이드에서 도는 중인지'를 판별한다. 데스크톱/EXE 에서는 False.
"""

import os

IS_ANDROID = "ANDROID_ARGUMENT" in os.environ or "ANDROID_APP_PATH" in os.environ
