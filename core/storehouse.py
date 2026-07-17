# -*- coding: utf-8 -*-
"""아버지의 창고 — 회차 성과로 하나씩 되찾는 물건 컬렉션.

갤러리 '창고' 탭이 그리고, 업적(`storehouse_full`)이 완성 여부를 검사한다.
해금 조건은 전부 회차 메타(save_data.json)에서 계산한다 — 별도 저장 없음(파생 상태).
"""
from core import save_system

# (id, 이름, 아이콘 스프라이트 키, 사연, 잠김 힌트)
ITEMS = [
    {
        "id": "hoe", "name": "낡은 호미", "icon": "item_hoe",
        "story": "손잡이가 반질반질하다.\n한 사람의 손이 몇천 번 감긴 자리다.\n창고의 첫 물건은, 역시 이것이었다.",
        "hint": "어느 밭이든 한 번 끝까지 길러 보자.",
    },
    {
        "id": "seed_pouch", "name": "씨앗 봉투", "icon": "item_seed_pouch",
        "story": "귀퉁이가 닳은 종이 봉투.\n'당근'이라고 아버지 글씨가 적혀 있다.\n모든 밭은 이 한 줌에서 시작됐다.",
        "hint": "당근을 끝까지 길러 수확한다.",
    },
    {
        "id": "shears", "name": "전정가위", "icon": "item_shears",
        "story": "날이 잘 벼려진 가지치기 가위.\n자르는 일이 기르는 일이라는 걸\n나무를 돌본 뒤에야 알았다.",
        "hint": "사과나무를 끝까지 길러 수확한다.",
    },
    {
        "id": "basket", "name": "대바구니", "icon": "item_basket",
        "story": "감자 흙이 마른 채 눌어붙어 있다.\n보이지 않는 곳에서 굵어진 것들을\n이 바구니가 받아 올렸다.",
        "hint": "감자를 끝까지 길러 수확한다.",
    },
    {
        "id": "boots", "name": "물장화", "icon": "item_boots",
        "story": "무릎까지 오는 검은 장화.\n안쪽에 아직 논물 자국이 남아 있다.\n새벽 물꼬는 늘 이 장화가 먼저 알았다.",
        "hint": "벼를 끝까지 길러 수확한다.",
    },
    {
        "id": "radio", "name": "낡은 라디오", "icon": "item_radio",
        "story": "다이얼이 하나뿐인 트랜지스터 라디오.\n지지직거리는 일기예보 소리가\n아버지의 새벽을 열던 소리였다.",
        "hint": "서로 다른 사건을 여섯 가지 겪는다.",
    },
    {
        "id": "bojagi", "name": "새참 보자기", "icon": "item_bojagi",
        "story": "네 귀퉁이를 묶던 자국이 선명하다.\n이 매듭 속에 들어 있던 것은\n밥이 아니라 기다림이었다.",
        "hint": "기억 조각을 열 개 되찾는다.",
    },
    {
        "id": "key", "name": "경운기 열쇠", "icon": "item_key",
        "story": "고무줄로 나무패에 묶인 열쇠.\n'내일 새벽, 같이 가자'던 약속은\n이 열쇠에서 시작될 것이다.",
        "hint": "진엔딩에 닿는다.",
    },
    {
        "id": "black_hat", "name": "검은 밀짚모자", "icon": "item_black_hat",
        "story": "챙이 그을린 검은 밀짚모자.\n붉은 하늘 아래에서도\n끝까지 밭을 지킨 이의 것이다.",
        "hint": "악)몽중농원을 끝까지 버텨 낸다.",
    },
]


def unlocked_ids():
    """메타 기록으로부터 해금된 물건 id 집합을 계산한다."""
    meta = save_system.load_meta()
    endings = meta.get("endings_seen", [])
    clears = meta.get("crop_clears", {})
    stories = meta.get("stories_seen", [])
    memories = meta.get("memories_seen", {})
    got = set()
    if endings:
        got.add("hoe")
    if clears.get("carrot"):
        got.add("seed_pouch")
    if clears.get("apple"):
        got.add("shears")
    if clears.get("potato"):
        got.add("basket")
    if clears.get("rice"):
        got.add("boots")
    if len(stories) >= 6:
        got.add("radio")
    if len(memories) >= 10:
        got.add("bojagi")
    if "true" in endings:
        got.add("key")
    if "nightmare" in endings:
        got.add("black_hat")
    return got


def is_complete():
    return len(unlocked_ids()) >= len(ITEMS)
