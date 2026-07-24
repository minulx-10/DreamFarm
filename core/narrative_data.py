import random
import pygame

# --- Narrative Data Tables ---

UNDERSTANDING_STAGES = [
    (0, "낯선 흙냄새", 0),
    (16, "물 주는 이유", 1),
    (31, "기다림의 무게", 2),
    (46, "손등의 온기", 3),
    (56, "한 조각의 시간", 4),
]

EPIPHANY_THRESHOLDS = {
    15: "흙은 차갑지만, 씨앗은 따뜻했다.",
    30: "물을 기다리는 시간이 가장 긴 시간이다.",
    45: "밀어낸 것을 다시 돌려놓을 수 있을까.",
    55: "아버지의 하루가, 내 한 끼였다.",
}

ACTION_ECHOES = {
    "물 주기": {
        "low": ["이 흙에 왜 물을 줘야 하는 거지?", "당근이 이 정도 물을 원하는 건가?",
                "물 한 바가지가 이렇게 무거웠나."],
        "mid": ["아버지도 이 새벽에 물을 주었을까.", "하루에 몇 번이나 이걸 했을까.",
                "흙이 물을 머금는 데에도 시간이 걸리는구나."],
        "high": ["물소리가 자장가 같다.", "이 흙이 마르지 않게, 매일 이렇게.",
                 "물을 준다는 건 내일을 믿는 일이었다."],
    },
    "잡초 뽑기": {
        "low": ["잡초가 이렇게 빨리 자라나?", "이거 끝이 있기는 한 건가.",
                "뿌리가 생각보다 깊게 박혀 있다."],
        "mid": ["손이 아프다. 매일 이걸 했다니.", "뽑아도 뽑아도 자라는구나.",
                "그냥 두면 당근 몫까지 빼앗아 간다."],
        "high": ["이것도 농사의 일부였구나.", "잡초와 싸우는 게 아니라, 당근을 지키는 거였어.",
                 "쓸 것과 버릴 것을 가리는 일은 늘 손이 많이 간다."],
    },
    "해충 살피기": {
        "low": ["벌레가 이렇게 많다고?", "이런 걸 맨손으로?",
                "잎 뒤는 들여다본 적도 없었는데."],
        "mid": ["잎 하나하나 뒤집어 보는 게 이런 거였구나.", "작은 것도 그냥 지나치면 안 되는 거구나.",
                "눈에 안 띄는 것이 더 무섭다."],
        "high": ["지키는 일은 늘 조용하고 반복적이다.", "아버지의 손이 거칠었던 이유를 알 것 같다.",
                 "매일 살피는 마음, 그게 사랑이었구나."],
    },
    "배수로 정리": {
        "low": ["물길도 관리해야 하는 거야?", "농사가 이렇게 복잡한 건가.",
                "땅 밑까지 신경 쓸 줄은 몰랐다."],
        "mid": ["물이 빠질 곳이 없으면 뿌리가 썩는구나.", "보이지 않는 곳까지 신경 써야 하다니.",
                "비가 오기 전에 미리 해 둬야 하는 일이었다."],
        "high": ["물 한 줄기도 흘러갈 곳이 필요하다.", "정성이란 이런 거였구나.",
                 "보이지 않는 곳을 돌보는 게 진짜 손길이었다."],
    },
    "흙 북돋기": {
        "low": ["흙을 왜 또 만져야 하지?", "이게 뭐가 달라지는 건지 모르겠다.",
                "흙도 손이 가야 하는 거였나."],
        "mid": ["흙을 다독이는 일이 이렇게 조용한 일이었구나.", "손끝에 흙이 묻는 감각이 익숙해진다.",
                "딱딱해진 흙을 풀어 주면 숨통이 트인다."],
        "high": ["이 흙 아래에 기다림이 묻혀 있다.", "아버지의 하루는 이런 조용함으로 가득했겠지.",
                 "흙을 만지는 손이, 어느새 아버지를 닮아 간다."],
    },
    "기다리기": {
        "low": ["그냥 기다리면 되는 건가?", "아무것도 안 해도 괜찮을까.",
                "이 시간이 가장 견디기 어렵다."],
        "mid": ["기다린다는 건, 믿는다는 뜻이었구나.", "조급함을 참는 것도 일의 일부구나.",
                "재촉한다고 빨리 자라는 게 아니었다."],
        "high": ["기다림 속에서 자라는 건 당근만이 아니었다.", "아버지도 이렇게 기다렸겠지, 매일.",
                 "고요를 견디는 법을, 흙이 가르쳐 준다."],
    },
}

FAILURE_ECHOES = {
    "물 주기": "아버지의 말이 떠오른다. '물이 많다고 좋은 게 아니란다.'",
    "잡초 뽑기": "'필요한 것과 필요 없는 것, 구분이 쉽지 않지.'",
    "해충 살피기": "'서두르면 놓치는 법이다. 천천히 봐라.'",
    "배수로 정리": "'지금 당장 급한 것만 보면, 나중에 더 큰 일이 생긴단다.'",
    "흙 북돋기": "'흙도 쉴 때가 있어야 한다.'",
    "기다리기": "'기다려도 되는 때와 안 되는 때가 있단다.'",
}

FATHER_ECHOES = {
    "물 주기": ["아이가 먹을 당근이니까.", "오늘도 안 먹겠지. 그래도."],
    "잡초 뽑기": ["이 밭만큼은 깨끗하게.", "아이는 모르겠지만, 이것도 사랑이다."],
    "해충 살피기": ["잎 하나도 함부로 놔둘 수 없다.", "내가 지키지 않으면 누가 지키겠나."],
    "배수로 정리": ["비가 오기 전에 해야 한다.", "준비하는 사람은 늘 보이지 않는 법이지."],
    "흙 북돋기": ["이 흙에 내 시간이 쌓인다.", "아이가 언젠가 이 흙을 만져볼까."],
    "기다리기": ["조급해하면 안 된다. 당근도, 아이도.", "기다릴 줄 아는 게 농부의 일이다."],
    "살펴보기": ["오늘도 무사히 자라고 있구나.", "이 밭이 내 하루의 전부다."],
}

# ── 행동 성향 문구 — 플레이어의 습관을 밭이 알아본다 (core/behavior.profile 기반) ──
BEHAVIOR_ECHOES = {
    "diligent": [   # diligence >= 0.75
        "너 새벽마다 물을 주더라. 아버지가 그랬듯이.",
        "하루도 거르지 않는 손이 있다. 흙은 그걸 기억한다.",
    ],
    "neglect": [    # neglect >= 0.75
        "밭은 기다림도 안다. 다만 너무 긴 기다림은 목마름이 된다.",
        "며칠 손이 뜸했다. 잎이 먼저 알아챘다.",
    ],
    "skilled": [    # skill >= 0.8
        "손끝이 야물어졌다. 처음 잡던 호미가 아니다.",
    ],
    "responsive": [ # reaction >= 0.8
        "잡초가 오래 버티지 못하는 밭이 됐다.",
    ],
}


def pick_behavior_echo(profile):
    """성향이 뚜렷할 때만 문구 하나 (없으면 None). 호출부가 빈도를 조절한다."""
    keys = []
    if profile.get("diligence", 0.5) >= 0.75:
        keys.append("diligent")
    if profile.get("neglect", 0.5) >= 0.75:
        keys.append("neglect")
    if profile.get("skill", 0.5) >= 0.8:
        keys.append("skilled")
    if profile.get("reaction", 0.5) >= 0.8:
        keys.append("responsive")
    if not keys:
        return None
    return pick_fresh(BEHAVIOR_ECHOES[random.choice(keys)])


WEATHER_WISDOM = {
    "맑음": "맑은 날이 오래가면 오히려 조심해야 한단다.",
    "흐림": "구름은 비를 데려오기도, 막아주기도 한다.",
    "비": "비가 오면 쉬어야 할 것 같지만, 배수로는 비 올 때 정리해야 한단다.",
    "가뭄": "메마른 땅도 기다림을 안다. 급한 마음이 더 해롭다.",
    "강풍": "바람은 약한 뿌리를 먼저 시험한다.",
}

WEATHER_DATA = {
    "맑음": {"moisture": -2, "stress": -3, "desc": "하늘이 맑다."},
    "흐림": {"moisture": 0, "stress": 0, "desc": "구름이 끼어 있다."},
    "비": {"moisture": 10, "drainage": -3, "desc": "빗방울이 떨어진다."},
    "가뭄": {"moisture": -8, "health": -3, "desc": "땅이 갈라지고 있다."},
    "강풍": {"pests": -5, "stress": 5, "desc": "바람이 세차게 분다."},
}

# ── '해(年)의 성격' — 회차마다 그 해의 날씨 기질이 달라진다 ─────────────────────
# w: 날씨 추첨 가중치 배수(없으면 1.0). desc: 첫날 일지/밭 안내에 실리는 한 줄.
YEAR_SEEDS = {
    "평년": {"w": {}, "desc": "올해는 무던한 해가 되겠다."},
    "가뭄해": {"w": {"가뭄": 2.4, "비": 0.5},
               "desc": "올해는 비가 귀하겠다. 물을 아껴 다뤄야 한다."},
    "장마해": {"w": {"비": 2.4, "가뭄": 0.4},
               "desc": "올해는 비가 잦겠다. 물길을 미리 봐 두자."},
    "풍년해": {"w": {"맑음": 1.8, "강풍": 0.6},
               "desc": "볕이 좋은 해다. 하늘이 절반은 거들어 준다."},
    "바람 많은 해": {"w": {"강풍": 2.2, "흐림": 1.3},
                    "desc": "바람 잘 날이 드문 해다. 잎이 상하지 않게 살피자."},
}


def roll_year_seed():
    """새 회차의 '해의 성격'을 뽑는다 — 평년이 살짝 흔하고 나머지는 고르게."""
    names = list(YEAR_SEEDS.keys())
    weights = [2.0 if n == "평년" else 1.0 for n in names]
    return random.choices(names, weights=weights, k=1)[0]

SILENT_GIFTS = [
    "밭 옆에 물통이 미리 채워져 있다.",
    "흙 위에 장갑이 놓여 있다. 내 사이즈다.",
    "삽 손잡이에 테이프가 감겨 있다. 손이 안 아프게.",
    "그늘에 도시락이 놓여 있다. 아직 따뜻하다.",
    "밭 가장자리에 돌이 치워져 있다. 누가 했을까.",
    "이 밭의 이랑이 유난히 반듯하다. 오래된 손길.",
    "호미 옆에 작은 쪽지. '힘들면 쉬어라.'",
]

SENSORY_DATA = {
    "low": {
        "물 주기": ["차가운 물이 손등을 적신다.", "물뿌리개가 묵직하게 기운다."],
        "잡초 뽑기": ["풀 냄새가 손에 밴다.", "잎 끝이 손바닥을 스친다."],
        "해충 살피기": ["잎 뒤에서 뭔가 꿈틀거린다.", "작은 다리들이 잎맥을 따라 움직인다."],
        "배수로 정리": ["진흙이 장화에 달라붙는다.", "삽 끝에 물기가 무겁게 묻어난다."],
        "흙 북돋기": ["흙이 손톱 사이로 들어온다.", "마른 흙덩이가 손안에서 부서진다."],
        "기다리기": ["바람 소리만 들린다.", "해가 조금씩 기울어 간다."],
    },
    "mid": {
        "물 주기": ["물이 흙에 스며드는 소리가 조용하다.", "젖은 흙에서 비 온 뒤 같은 냄새가 난다."],
        "잡초 뽑기": ["뿌리가 끊어지는 감각이 손끝에 남는다.", "한 움큼 뽑고 나니 이랑이 한결 넓어 보인다."],
        "해충 살피기": ["잎의 뒷면은 생각보다 부드럽다.", "한 잎 한 잎 넘기는 손이 차분해진다."],
        "배수로 정리": ["물길이 잡히자 흙 냄새가 달라진다.", "고였던 물이 천천히 빠져나간다."],
        "흙 북돋기": ["차가운 흙 사이로 따뜻한 게 올라온다.", "북돋운 흙이 폭신하게 부푼다."],
        "기다리기": ["흙 속에서 아주 작은 소리가 나는 것 같다.", "숨을 고르자 밭 전체가 눈에 들어온다."],
    },
    "high": {
        "물 주기": ["이 물소리는 아버지가 일할 때 나던 냄새와 닮았다.", "물줄기 끝에서 새벽의 아버지가 보이는 듯하다."],
        "잡초 뽑기": ["손이 거칠어진다. 아버지의 손등이 떠오른다.", "이 자리를 매일 지킨 손이 있었다."],
        "해충 살피기": ["조용히 지키는 일. 이게 매일의 사랑이었구나.", "아무도 보지 않는 곳에서의 돌봄이었다."],
        "배수로 정리": ["보이지 않는 곳을 돌보는 손길의 온기.", "비를 미리 헤아리는 마음이 여기 있었다."],
        "흙 북돋기": ["이 흙에는 누군가의 시간이 켜켜이 쌓여 있다.", "흙을 다독이는 손에 아버지의 하루가 겹쳐진다."],
        "기다리기": ["고요 속에서 자라는 것은 당근만이 아니다.", "기다림의 무게를, 이제 조금 알 것 같다."],
    },
}

FATHER_DAY_NARRATIONS = {
    40: [
        "새벽 4시.\n아직 어두운 하늘 아래, 아버지는 장화를 신었다.\n오늘도 아이는 당근을 먹지 않겠지.\n그래도 물은 줘야 한다.\n이 흙이 기다리니까.",
        "밭에 도착하면 먼저 하는 일.\n이랑 사이를 걸으며 어젯밤 사이 달라진 것을 살핀다.\n무릎이 아프다.\n하지만 이 당근은 아이의 식탁에 올라갈 것이다.\n그것만으로 충분하다.",
    ],
    50: [
        "오늘은 비가 올 것 같다.\n아버지는 배수로를 미리 정리하고,\n아이가 쓸 장갑을 밭 옆에 놓아 둔다.\n혹시나 하는 마음으로.\n아이는 모르겠지만, 괜찮다.\n알아주길 바라고 한 일이 아니니까.",
    ],
}

ENDING_JOURNAL_CLOSINGS = {
    "true": ("[마지막 장 · 수확의 날]\n흙을 처음 만지던 날이 떠오른다. 그땐 아무것도 몰랐다.\n이제는 안다 — 이 밭의 모든 새벽이 누군가의 사랑이었다는 걸.\n내일 새벽, 아버지 곁에서 다시 흙을 만질 것이다."),
    "normal": ("[마지막 장 · 수확의 날]\n잘한 것도 못한 것도 있던 하루였다.\n조금은 알 것 같은, 그런 마음으로 밭을 나선다."),
    "bad": ("[마지막 장 · 수확의 날]\n끝내 입에 넣지 못한 당근.\n그래도 예전처럼 밀어내지는 않았다. 그거면, 시작은 된 셈이다."),
    "wither": ("[마지막 장 · 시든 밭]\n수확은 없었다. 흙만 남았다.\n아버지가 매일 무엇과 싸웠는지, 이제야 조금 안다.\n다음 새벽엔, 조금 다르게 해볼 수 있을 것 같다."),
    "nightmare": ("[마지막 장 · 비워진 식탁]\n갈라진 붉은 하늘 아래에서도 밭은 밭이었다.\n마지막 한 조각까지 남기지 않았다.\n아침 식탁은, 처음으로 말끔히 비어 있었다."),
}

JOURNAL_RETROSPECTIVES = {
    "이걸 왜 해야 하는지 아직 모르겠다.": "→ 지금은 안다. 그때의 '모르겠다'가 시작이었다.",
    "조금씩 알 것 같기도 하다.": "→ 알 것 같다는 느낌이 맞았다.",
    "이 일의 무게가 느껴진다.": "→ 그 무게는 사랑의 무게였다.",
    "실수가 잦았다. 아직 모르는 것이 많다.": "→ 서툴렀지만, 포기하지 않았다.",
    "당근이 많이 힘들어 보였다.": "→ 힘들어 보이는 것도 볼 줄 알게 되었다.",
    "수분은 적당했다.": "→ '적당함'을 아는 것이 농부의 눈이다.",
    "오늘 물을 너무 많이 줬다.": "→ 넘치는 것도 부족한 것만큼 해롭다는 걸 배웠다.",
    "흙이 바짝 말라 있었다.": "→ 마른 흙을 기억하기에, 물의 소중함을 안다.",
}

STORY_EVENTS = [
    {
        "title": "이웃 밭의 물난리",
        "text": "이웃 밭에서 물이 넘쳐 흘러오고 있다.\n우리 밭도 위험할 수 있다.\n어떻게 해야 할까?",
        "choice_a": ("우리 밭 배수로를 먼저 지킨다", {
            "understanding": 0,
            "result_text": "우리 밭은 안전하지만, 이웃 밭이 걱정된다.",
            "impact_text": "이웃 밭의 어린 싹 몇 줄기는 끝내 물에 잠겼다.",
        }),
        "choice_b": ("이웃 밭의 물길을 함께 막는다", {
            "understanding": 8,
            "result_text": "함께 막으니 오히려 물길이 잘 잡혔다. 혼자가 아니었다.",
            "impact_text": "함께 막은 물길 덕분에 이웃 밭도 장마를 버텼다.",
            "task": {"kind": "hold", "theme": "water", "prompt": "터진 물길을 꾹 눌러 막으세요!", "count": 4, "time": 8.0,
                     "fail_text": "몇 군데는 미처 막지 못해 물이 스몄다."},
        }),
    },
    {
        "title": "쓰러진 허수아비",
        "text": "강풍에 허수아비가 쓰러졌다.\n새들이 모여들기 시작한다.\n시간이 많지 않다.",
        "choice_a": ("허수아비를 급히 다시 세운다", {
            "understanding": 2,
            "result_text": "허수아비를 세웠지만, 대충 세워서 금방 또 쓰러질 것 같다.",
            "impact_text": "급히 세운 허수아비는 다시 쓰러졌고, 새들이 밭을 훑고 갔다.",
        }),
        "choice_b": ("단단히 고정할 수 있게 돌을 모은다", {
            "understanding": 6,
            "result_text": "시간은 걸렸지만 튼튼해졌다. 급할수록 돌아가라는 말이 떠오른다.",
            "impact_text": "돌로 고정한 허수아비는 강풍 뒤에도 밭을 지켰다.",
            "task": {"kind": "tap", "prompt": "밭가의 돌을 주워 모으세요!", "count": 5, "time": 9.0,
                     "fail_text": "돌이 모자라 받침이 조금 헐거워졌다."},
        }),
    },
    {
        "title": "길 잃은 벌",
        "text": "꽃밭을 찾지 못하는 벌 한 마리가\n당근 잎 위에서 힘없이 쉬고 있다.\n해충은 아닌 것 같다.",
        "choice_a": ("내버려 두고 밭일을 계속한다", {
            "understanding": 1,
            "result_text": "밭일은 진행되었지만, 자꾸 벌이 신경 쓰인다.",
            "impact_text": "길 잃은 벌은 꽃밭을 찾지 못했고, 밭가의 꽃도 조용히 시들었다.",
        }),
        "choice_b": ("근처 꽃밭 쪽으로 조심히 옮겨 준다", {
            "understanding": 7,
            "result_text": "벌이 날아간 뒤, 밭 위로 따뜻한 바람이 불었다.",
            "impact_text": "옮겨 준 벌은 꽃밭을 찾아갔고, 밭가에는 작은 열매가 맺혔다.",
            "task": {"kind": "trail", "prompt": "벌이 앉을 잎을 순서대로 눌러 꽃밭까지 이끄세요.", "count": 4, "time": 9.0,
                     "fail_text": "벌이 놀라 몇 번 날아올랐지만, 끝내는 꽃밭 쪽으로 향했다."},
        }),
    },
    {
        "title": "무너진 이랑",
        "text": "간밤의 비에 이랑 한 켠이 무너져 내렸다.\n뿌리가 드러난 곳도 보인다.\n손을 대면 한나절은 걸릴 일이다.",
        "choice_a": ("급한 일부터 하고 나중에 손본다", {
            "understanding": 1,
            "result_text": "무너진 자리를 지날 때마다 마음이 쓰인다.",
            "impact_text": "미뤄 둔 이랑은 다음 비에 조금 더 무너졌다.",
        }),
        "choice_b": ("지금 흙을 퍼 올려 다시 쌓는다", {
            "understanding": 6,
            "result_text": "손바닥이 얼얼하다. 아버지는 이 일을 몇 번이나 했을까.",
            "impact_text": "다시 쌓은 이랑은 장마를 버텼다.",
            "task": {"kind": "hold", "theme": "soil", "prompt": "무너진 자리에 흙을 꾹 눌러 다지세요!", "count": 4, "time": 9.0,
                     "fail_text": "다 다지지 못한 자리가 조금 주저앉았다."},
        }),
    },
    {
        "title": "새벽의 고라니",
        "text": "울타리 틈으로 고라니 한 마리가 서성인다.\n어린 잎을 노리는 눈치다.\n쫓아도 틈이 있으면 또 온다.",
        "choice_a": ("소리를 질러 당장 쫓아낸다", {
            "understanding": 2,
            "result_text": "고라니는 달아났지만, 울타리 틈은 그대로다.",
            "impact_text": "고라니는 며칠 뒤 다시 찾아와 가장자리 잎을 뜯어 갔다.",
        }),
        "choice_b": ("울타리 틈을 나뭇가지로 막는다", {
            "understanding": 7,
            "result_text": "쫓는 것보다 막는 것이 먼저였다. 아버지라면 그렇게 했을 것이다.",
            "impact_text": "막아 둔 울타리 덕에 어린 잎들이 무사히 자랐다.",
            "task": {"kind": "hold", "theme": "fence", "prompt": "울타리 틈을 꾹 눌러 막으세요!", "count": 4, "time": 8.0,
                     "fail_text": "한 군데는 엉성하게 막혔지만, 큰 틈은 사라졌다."},
        }),
    },
    {
        "title": "아버지의 낡은 호미",
        "text": "창고 구석에서 손잡이가 반질반질한 호미를 찾았다.\n날은 녹슬었지만, 손에 감기는 각도가 묘하게 편하다.\n오래 쓰인 물건의 각도다.",
        "choice_a": ("새 호미를 꺼내 쓴다", {
            "understanding": 1,
            "result_text": "새 호미는 잘 든다. 그런데 어딘가 낯설다.",
            "impact_text": "낡은 호미는 창고에서 계속 녹슬어 갔다.",
        }),
        "choice_b": ("녹을 닦아내고 그 호미를 쓴다", {
            "understanding": 6,
            "result_text": "녹을 닦자 날이 살아났다. 손잡이의 닳은 자리가 내 손에 꼭 맞았다.",
            "impact_text": "손질한 호미는 밭일 내내 손에서 떠나지 않았다.",
            "task": {"kind": "rub", "prompt": "녹슨 자리를 문질러(마우스를 비벼) 닦으세요!", "count": 4, "time": 9.0,
                     "fail_text": "녹이 조금 남았지만, 쓰기엔 충분했다."},
        }),
    },
    # ── 범용 이벤트 확장 (회차 반복감 완화) ──────────────────────────────────
    {
        "title": "무너진 돌담",
        "text": "간밤 바람에 돌담 한 켠이 무너져\n이랑까지 돌이 굴러 들어왔다.\n그대로 두면 호미 날이 상한다.",
        "choice_a": ("눈에 띄는 큰 돌만 치운다", {
            "understanding": 1,
            "result_text": "큰 돌은 치웠지만, 흙 속 잔돌이 자꾸 밟힌다.",
            "impact_text": "잔돌이 남은 이랑에서는 뿌리가 자꾸 비껴 자랐다.",
        }),
        "choice_b": ("허리 숙여 잔돌까지 골라낸다", {
            "understanding": 6,
            "result_text": "허리는 아팠지만, 골라낸 자리의 흙이 한결 곱다.",
            "impact_text": "돌 없는 이랑에서 뿌리가 곧게 내렸다.",
            "task": {"kind": "tap", "prompt": "이랑에 굴러온 돌을 주워 내세요!", "count": 5, "time": 9.0,
                     "fail_text": "잔돌 몇 개는 끝내 못 찾았다."},
        }),
    },
    {
        "not_crop": "apple",   # 과수원(나무)에는 물꼬·이랑 서사가 어울리지 않는다
        "title": "막힌 물꼬",
        "text": "낙엽과 검불이 물꼬를 막았다.\n고인 물이 이랑 사이로 번지고 있다.\n장화 속까지 물이 스며드는 날이다.",
        "choice_a": ("물길이 알아서 뚫리길 기다린다", {
            "understanding": 1,
            "result_text": "물은 조금씩 빠졌지만, 반나절을 잃었다.",
            "impact_text": "물이 오래 고였던 자리는 며칠 내내 질척였다.",
        }),
        "choice_b": ("소매를 걷고 손으로 걷어낸다", {
            "understanding": 7,
            "result_text": "검불을 걷어내자 물이 시원하게 빠져나갔다.\n손은 시렸지만 개운했다.",
            "impact_text": "물길이 잡힌 이랑은 비 온 뒤에도 무르지 않았다.",
            "task": {"kind": "hold", "theme": "water", "prompt": "막힌 물꼬를 꾹 눌러 터 주세요!", "count": 3, "time": 8.0,
                     "fail_text": "한 군데는 덜 뚫렸지만 물은 흘렀다."},
        }),
    },
    {
        "title": "읍내 장날",
        "text": "오늘은 읍내 장날.\n아버지가 다니던 종묘상이 문을 여는 날이다.\n다녀오면 한나절이 빈다.",
        "choice_a": ("자리를 뜰 수 없어 가지 않는다", {
            "understanding": 2,
            "result_text": "일은 밀리지 않았지만, 종묘상 골목이 자꾸 눈에 밟힌다.",
            "impact_text": "장날을 거른 대신, 이랑은 하루 종일 손길을 받았다.",
        }),
        "choice_b": ("한나절 비워 두고 장에 다녀온다", {
            "understanding": 5,
            "result_text": "종묘상 주인이 아버지의 안부를 물었다.\n'그 어른 단골이었지.' 그 말이 오래 남았다.",
            "impact_text": "장에서 얻어 온 볍씨 봉투 하나가 창고에 놓였다.",
        }),
    },
    {
        "title": "낡은 라디오",
        "text": "창고 선반에서 지지직거리는 라디오를 찾았다.\n주파수를 맞추니 일기예보가 흘러나온다.\n아버지가 새벽마다 듣던 소리다.",
        "choice_a": ("그냥 꺼 둔다", {
            "understanding": 1,
            "result_text": "조용한 게 편하다. 그래도 어딘가 허전하다.",
            "impact_text": "라디오는 다시 선반 구석에서 먼지를 썼다.",
        }),
        "choice_b": ("고쳐서 일하는 옆에 둔다", {
            "understanding": 5,
            "result_text": "지지직 소리 사이로 예보가 또렷해졌다.\n하늘을 미리 헤아리는 습관이 이렇게 시작됐구나.",
            "impact_text": "일하는 내내 라디오가 나직하게 곁을 지켰다.",
        }),
    },
    # ── 작물 서사 팩 — 그 작물을 기를 때만 나온다 ("crop" 키) ─────────────────
    {
        "crop": "apple",
        "title": "무거워진 가지",
        "text": "열매 무게로 가지 하나가 축 처졌다.\n이대로 두면 찢어질지도 모른다.\n나무는 제 무게를 말하지 못한다.",
        "choice_a": ("열매를 몇 개 솎아낸다", {
            "understanding": 3,
            "result_text": "솎아낸 자리의 가지가 한결 가벼워 보인다.\n남은 열매가 그만큼 굵어질 것이다.",
            "impact_text": "솎아낸 풋열매는 거름이 되어 나무 밑으로 돌아갔다.",
        }),
        "choice_b": ("받침목을 괴어 가지를 받친다", {
            "understanding": 6,
            "result_text": "받침을 괴자 가지가 숨을 돌렸다.\n지탱해 주는 일은 티가 나지 않는다.",
            "impact_text": "받침목을 얻은 가지는 열매를 끝까지 지켜냈다.",
            "task": {"kind": "tap", "prompt": "가지를 받칠 돌과 굄목을 모으세요!", "count": 5, "time": 9.0,
                     "fail_text": "받침이 조금 낮았지만 가지는 버텼다."},
        }),
    },
    {
        "crop": "apple",
        "title": "첫 낙과",
        "text": "밤사이 바람에 풋사과 몇 알이 떨어졌다.\n아직 시고 떫은 열매들이다.\n버리자니 아깝고, 두자니 벌레가 꼬인다.",
        "choice_a": ("아깝지만 거름으로 묻는다", {
            "understanding": 6,
            "result_text": "떨어진 것은 흙으로 돌려보낸다.\n아버지도 그렇게 했을 것이다.",
            "impact_text": "묻은 자리의 흙이 다음 해를 위해 깊어졌다.",
        }),
        "choice_b": ("주워서 식초를 담가 본다", {
            "understanding": 4,
            "result_text": "떫은 열매도 쓰임이 있다.\n항아리에서 천천히 익어 갈 것이다.",
            "impact_text": "창고 구석 항아리에서 사과 식초가 익어 갔다.",
        }),
    },
    {
        "crop": "potato",
        "title": "두더지 굴",
        "text": "이랑 아래로 두더지 굴이 지나갔다.\n흙이 들떠 뿌리가 마르기 쉽다.\n굴 입구가 여기저기 뚫려 있다.",
        "choice_a": ("소리 나는 바람개비를 꽂아 둔다", {
            "understanding": 2,
            "result_text": "바람개비가 돌 때만 조용하다.\n바람 없는 날이 문제다.",
            "impact_text": "두더지는 바람 없는 밤에 다시 다녀갔다.",
        }),
        "choice_b": ("굴 입구를 찾아 하나하나 메운다", {
            "understanding": 6,
            "result_text": "입구를 메우자 들뜬 흙이 가라앉았다.\n발밑을 살피는 눈이 조금 자랐다.",
            "impact_text": "메운 이랑의 감자가 마르지 않고 굵어졌다.",
            "task": {"kind": "hold", "prompt": "굴 입구를 꾹 눌러 메우세요!", "count": 4, "time": 8.0,
                     "fail_text": "한 군데는 다시 뚫렸지만 큰 굴은 막았다."},
        }),
    },
    {
        "crop": "potato",
        "title": "북주기 가르침",
        "text": "지나가던 이웃 어른이 북주기를 보고 걸음을 멈췄다.\n'자네 아버지는 북을 더 높이 줬지.'\n낯선 손놀림이 눈에 밟히셨나 보다.",
        "choice_a": ("하던 방식대로 마저 한다", {
            "understanding": 2,
            "result_text": "내 속도로 하는 게 편하다.\n그래도 그 말이 귓가에 남는다.",
            "impact_text": "이랑 몇 줄은 북이 낮아 초록 감자가 몇 알 나왔다.",
        }),
        "choice_b": ("어른의 방식을 따라 해 본다", {
            "understanding": 6,
            "result_text": "북을 높이자 이랑이 듬직해졌다.\n아버지의 손놀림을 흉내 낸 셈이다.",
            "impact_text": "높이 준 북 덕에 감자가 볕에 상하지 않았다.",
        }),
    },
    {
        "crop": "rice",
        "title": "물꼬 순서",
        "text": "위 논과 물 대는 순서가 겹쳤다.\n물은 한 줄기, 논은 여럿.\n먼저 대면 편하지만, 이웃 논이 마른다.",
        "choice_a": ("우리 논부터 물을 댄다", {
            "understanding": 1,
            "result_text": "논은 찰랑해졌지만, 위 논 어른의 헛기침이 들린 것 같다.",
            "impact_text": "그날 위 논 모서리가 하루 늦게 물을 받았다.",
        }),
        "choice_b": ("순서를 양보하고 물길을 같이 손본다", {
            "understanding": 7,
            "result_text": "함께 손본 물길로 두 논이 나란히 찰랑해졌다.\n물은 나눠도 줄지 않았다.",
            "impact_text": "물길을 같이 손본 뒤로, 위 논 어른이 먼저 물을 밀어 주곤 했다.",
            "task": {"kind": "hold", "theme": "water", "prompt": "물길을 꾹 눌러 다잡으세요!", "count": 4, "time": 8.0,
                     "fail_text": "물길 한 곳이 덜 잡혔지만 물은 고루 갔다."},
        }),
    },
    {
        "crop": "rice",
        "title": "우렁이 손님",
        "text": "논물 속을 우렁이 몇 마리가 기어간다.\n잎을 갉는 건지, 잡초를 먹는 건지\n아직은 알 수 없다.",
        "choice_a": ("해가 될까 봐 걷어낸다", {
            "understanding": 2,
            "result_text": "걷어낸 우렁이를 도랑에 놓아주었다.\n영 개운치가 않다.",
            "impact_text": "우렁이가 사라진 자리엔 잡풀이 조금 더 올라왔다.",
        }),
        "choice_b": ("잡초를 먹게 그냥 둔다", {
            "understanding": 6,
            "result_text": "우렁이는 어린 잡풀만 골라 먹었다.\n논은 생각보다 많은 손을 빌리고 있었다.",
            "impact_text": "우렁이 덕에 김매기가 한결 수월해졌다.",
        }),
    },
]

# --- Helper Functions ---

def get_understanding_stage(value):
    stage = UNDERSTANDING_STAGES[0]
    for threshold, name, phase in UNDERSTANDING_STAGES:
        if value >= threshold:
            stage = (threshold, name, phase)
    return stage


def get_understanding_tier(value):
    if value < 18:
        return "low"
    elif value < 45:
        return "mid"
    else:
        return "high"


def pick_fresh(options):
    from core.game_state import game_state
    if not options:
        return ""
    fresh = [o for o in options if o not in game_state.recent_lines]
    if not fresh:
        last = game_state.recent_lines[-1] if game_state.recent_lines else None
        fresh = [o for o in options if o != last] or list(options)
    choice = random.choice(fresh)
    game_state.recent_lines.append(choice)
    if len(game_state.recent_lines) > 6:
        game_state.recent_lines.pop(0)
    return choice


def pick_action_echo(action):
    from core.game_state import game_state
    if game_state.dad_mode:
        return pick_fresh(FATHER_ECHOES.get(action, []))
    tier = get_understanding_tier(game_state.understanding)
    return pick_fresh(ACTION_ECHOES.get(action, {}).get(tier, []))


def pick_failure_echo(action):
    from core.game_state import game_state
    echo = FAILURE_ECHOES.get(action, "")
    if echo and action not in game_state.dad_lessons:
        game_state.dad_lessons[action] = echo
    return echo


def pick_sensory(action):
    from core.game_state import game_state
    tier = get_understanding_tier(game_state.understanding)
    return pick_fresh(SENSORY_DATA.get(tier, {}).get(action, []))


def get_silent_gift():
    from core.game_state import game_state
    idx = game_state.gifts_revealed
    if idx < len(SILENT_GIFTS):
        return SILENT_GIFTS[idx]
    return None


def reveal_gift():
    from core.game_state import game_state
    game_state.gifts_revealed = min(game_state.gifts_revealed + 1, len(SILENT_GIFTS))


def check_recovery(action, is_fail):
    from core.game_state import game_state
    if not is_fail and game_state.last_failure_action == action:
        game_state.recovery_count += 1
        game_state.last_failure_action = ""
        lesson = game_state.dad_lessons.get(action, "")
        if lesson:
            return "그때 아버지가 한 말이 맞았다. 이번에는 달랐다."
    if is_fail:
        game_state.last_failure_action = action
    return ""


def track_attitude(action, is_fail, is_good_turn):
    from core.game_state import game_state
    if action == "기다리기" and not is_fail:
        game_state.patience_score += 1
    if action == "기다리기" and is_fail:
        game_state.rush_count += 1
    if action == "살펴보기" and is_good_turn:
        game_state.care_score += 1


def get_season(growth, growth_goal):
    ratio = growth / max(1, growth_goal)
    if ratio < 0.22:
        return "이른 봄"
    elif ratio < 0.50:
        return "봄"
    elif ratio < 0.78:
        return "여름"
    else:
        return "가을"


def get_season_colors(growth, growth_goal):
    season = get_season(growth, growth_goal)
    if season == "이른 봄":
        return {
            "grass": (75, 130, 70), "grass_dark": (55, 105, 50),
            "dirt": (130, 85, 55), "dirt_dark": (105, 68, 42),
            "sky_tint": (180, 195, 210),
        }
    elif season == "봄":
        return {
            "grass": (90, 160, 70), "grass_dark": (70, 130, 50),
            "dirt": (145, 95, 60), "dirt_dark": (120, 75, 45),
            "sky_tint": (210, 225, 200),
        }
    elif season == "여름":
        return {
            "grass": (60, 145, 55), "grass_dark": (45, 115, 40),
            "dirt": (140, 90, 55), "dirt_dark": (115, 72, 42),
            "sky_tint": (200, 220, 180),
        }
    else:  # 가을
        return {
            "grass": (140, 155, 60), "grass_dark": (110, 125, 45),
            "dirt": (150, 100, 60), "dirt_dark": (125, 80, 48),
            "sky_tint": (230, 200, 140),
        }


def advance_weather():
    from core.game_state import game_state
    # 도전 '한발' — 가뭄이 걷히지 않는다
    if getattr(game_state, "challenge", None) == "drought":
        game_state.weather = "가뭄"
        game_state.next_weather = "가뭄"
        game_state.weather_turns_left = 99
        return
    weathers = list(WEATHER_DATA.keys())
    game_state.weather = game_state.next_weather
    candidates = [w for w in weathers if w != game_state.weather]
    # '해의 성격'이 그 해의 날씨 기질을 만든다 (가뭄해엔 가뭄이 잦고 비가 귀한 식)
    seed = YEAR_SEEDS.get(getattr(game_state, "year_seed", "평년"), YEAR_SEEDS["평년"])
    weights = [seed["w"].get(w, 1.0) for w in candidates]
    game_state.next_weather = random.choices(candidates, weights=weights, k=1)[0]
    game_state.weather_turns_left = random.randint(2, 3)


def check_epiphany():
    from core.game_state import game_state
    u = game_state.understanding
    for threshold, text in EPIPHANY_THRESHOLDS.items():
        if u >= threshold and threshold not in game_state.epiphanies_seen:
            game_state.epiphanies_seen.add(threshold)
            game_state.pending_epiphany = text
            return True
    return False


def check_father_day():
    from core.game_state import game_state
    u = game_state.understanding
    for threshold in FATHER_DAY_NARRATIONS:
        if u >= threshold and threshold not in game_state.father_day_seen:
            game_state.father_day_seen.add(threshold)
            return threshold
    return None


def get_attitude_ending():
    from core.game_state import game_state
    p = game_state.patience_score
    e = game_state.empathy_choices
    u = game_state.understanding
    h = game_state.final_health
    m = game_state.farm_mistakes

    # 진엔딩: 솜씨·이해·인내·공감이 모두 무르익고 실수도 적음
    if u >= 40 and e >= 1 and p >= 1 and h >= 55 and m < 5:
        return "true"
    if h >= 45 and u >= 15:
        return "normal"
    return "bad"


def append_ending_journal():
    from core.game_state import game_state
    if game_state.journal_closed:
        return
    key = "wither" if game_state.crop_failed else game_state.last_ending
    text = ENDING_JOURNAL_CLOSINGS.get(key)
    if text:
        # 정본(당근·밭)으로 저장 — 표시 시점(_localize_journal_line)에 언어별 치환·번역
        game_state.journal_entries.append(text)
        game_state.journal_closed = True
