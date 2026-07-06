import pygame
from core.game_state import game_state
from core.assets import get_font, TEXT_DARK, TEXT_MUTED, WHITE, GOLD, PANEL_WARM, PANEL_EDGE
from core.ui import draw_light_panel, draw_story_backdrop, draw_button, wrap_text, mix_color, draw_panel
from core import audio
from core import save_system

class GalleryScene:
    def __init__(self):
        self.font_title = get_font(28)
        self.font_section = get_font(20)
        self.font_card_title = get_font(17)   # 엔딩 카드 제목(폭이 좁아 작은 폰트로 넘침 방지)
        self.font_body = get_font(15)
        self.font_small = get_font(13)
        self.font_btn = get_font(16)
        
        self.active_tab = "endings" # "endings" | "stories"
        
        # 탭 Rects (엔딩 / 이야기 / 업적)
        self.tab1_rect = pygame.Rect(158, 105, 158, 34)
        self.tab2_rect = pygame.Rect(322, 105, 158, 34)
        self.tab3_rect = pygame.Rect(486, 105, 158, 34)
        self.back_rect = pygame.Rect(30, 24, 100, 32)
        
        # 엔딩 슬롯 Rects (제목 2줄 + 설명 3줄 + 버튼이 겹치지 않도록 높이 확보)
        self.ending_slots = {
            "true": pygame.Rect(90, 168, 290, 160),
            "normal": pygame.Rect(420, 168, 290, 160),
            "bad": pygame.Rect(90, 338, 290, 160),
            "wither": pygame.Rect(420, 338, 290, 160)
        }

        # 리플레이 버튼 Rects — 각 카드 아래쪽에 고정
        self.replay_btns = {
            "true": pygame.Rect(230, 288, 140, 32),
            "normal": pygame.Rect(560, 288, 140, 32),
            "bad": pygame.Rect(230, 458, 140, 32),
            "wither": pygame.Rect(560, 458, 140, 32)
        }
        
        # 리스트 컬럼 영역
        self.stories_area = pygame.Rect(90, 170, 290, 360)
        self.memories_area = pygame.Rect(420, 170, 290, 360)
        
        # 선택되어 모달 팝업으로 상세 읽는 스토리/기억 데이터
        self.reading_title = None
        self.reading_text = None
        self.modal_rect = pygame.Rect(120, 120, 560, 380)
        self.modal_close_btn = pygame.Rect(452, 440, 128, 36)
        self.modal_replay_btn = pygame.Rect(220, 440, 128, 36)   # 이벤트 다시 하기
        self.star_replay_btn = pygame.Rect(290, 544, 220, 40)    # 별 잇기 다시 하기(이야기 탭)
        
        self.endings_seen = save_system.endings_seen()
        self.stories_seen = save_system.load_meta().get("stories_seen", [])
        self.memories_seen = save_system.load_meta().get("memories_seen", {})
        
        self.hovered_back = False
        self.hovered_tab1 = False
        self.hovered_tab2 = False
        self.hovered_tab3 = False
        self.hovered_modal_close = False
        
        # 리스트 아이템 마우스 오버용 위치 매핑 리스트
        self.story_item_rects = []
        self.memory_item_rects = []

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        
        # 모달 팝업이 띄워져 있는가
        if self.reading_title:
            self.hovered_modal_close = self.modal_close_btn.collidepoint(mouse_pos)
            replay_ev = self._find_replay_event(self.reading_title)
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if replay_ev is not None and self.modal_replay_btn.collidepoint(event.pos):
                        # 그 이벤트(선택형 미니게임)를 다시 플레이 — 끝나면 갤러리로 복귀
                        audio.play("click")
                        game_state.choice_data = replay_ev
                        game_state.event_replay = True
                        self.reading_title = None
                        self.reading_text = None
                        game_state.current_scene = "story_choice"
                        return
                    if self.hovered_modal_close or not self.modal_rect.collidepoint(pos := event.pos):
                        audio.play("click")
                        self.reading_title = None
                        self.reading_text = None
            return

        self.hovered_back = self.back_rect.collidepoint(mouse_pos)
        self.hovered_tab1 = self.tab1_rect.collidepoint(mouse_pos)
        self.hovered_tab2 = self.tab2_rect.collidepoint(mouse_pos)
        self.hovered_tab3 = self.tab3_rect.collidepoint(mouse_pos)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 뒤로가기
                if self.hovered_back:
                    audio.play("click")
                    game_state.current_scene = "title"
                    return
                # 탭 전환
                elif self.hovered_tab1:
                    audio.play("click")
                    self.active_tab = "endings"
                elif self.hovered_tab2:
                    audio.play("click")
                    self.active_tab = "stories"
                elif self.hovered_tab3:
                    audio.play("click")
                    self.active_tab = "achievements"
                
                # 콘텐츠별 클릭
                if self.active_tab == "endings":
                    for key, btn_rect in self.replay_btns.items():
                        if btn_rect.collidepoint(event.pos):
                            # 시듦(wither)도 endings_seen에 들어가거나 wither 여부를 세팅해야 함
                            is_wilt = (key == "wilt" or key == "wither")
                            # wither 엔딩의 잠금 해제는 bad 엔딩을 봤거나 metal에 withered 가 남아 있을 때 해금
                            unlocked = (key in self.endings_seen) or (is_wilt and "wither" in self.endings_seen)
                            if unlocked:
                                audio.play("success")
                                # EndingScene이 이 값을 읽어 해당 엔딩을 강제 재생한다
                                game_state.forced_ending = "wither" if is_wilt else key
                                game_state.crop_failed = is_wilt
                                # 메타에 저장되어 있던 작물 값을 갤러리 감상 시에도 로드해 보여준다
                                meta_crop = save_system.load_meta().get("crop", "carrot")
                                game_state.crop = meta_crop
                                game_state.current_scene = "ending"
                                return
                else:
                    # 별 잇기 다시 하기 — 특별 미니게임 재생(끝나면 갤러리로 복귀)
                    if self.star_replay_btn.collidepoint(event.pos):
                        audio.play("success")
                        game_state.return_scene = "gallery"
                        game_state.current_scene = "star_connect"
                        return
                    # 사건목록 클릭
                    for rect, title, text in self.story_item_rects:
                        if rect.collidepoint(event.pos):
                            audio.play("click")
                            self.reading_title = title
                            self.reading_text = text
                            return
                    # 기억목록 클릭
                    for rect, title, text in self.memory_item_rects:
                        if rect.collidepoint(event.pos):
                            audio.play("click")
                            self.reading_title = title
                            self.reading_text = text
                            return

    def update(self, dt):
        pass

    def draw(self, screen):
        # 1. 배경
        draw_story_backdrop(screen, "night")
        
        # 2. 타이틀
        title_surf = self.font_title.render("추억 저장소", True, WHITE)
        screen.blit(title_surf, (400 - title_surf.get_width() // 2, 40))
        
        # 뒤로가기 버튼
        draw_button(screen, self.back_rect, "돌아가기", self.font_small, hovered=self.hovered_back)
        
        # 3. 탭 바 그리기
        draw_button(screen, self.tab1_rect, "엔딩", self.font_btn,
                    hovered=self.hovered_tab1, selected=(self.active_tab == "endings"))
        draw_button(screen, self.tab2_rect, "이야기·기억", self.font_btn,
                    hovered=self.hovered_tab2, selected=(self.active_tab == "stories"))
        draw_button(screen, self.tab3_rect, "업적", self.font_btn,
                    hovered=self.hovered_tab3, selected=(self.active_tab == "achievements"))

        # 4. 콘텐츠 그리기
        if self.active_tab == "endings":
            self._draw_endings_tab(screen)
        elif self.active_tab == "achievements":
            self._draw_achievements_tab(screen)
        else:
            self._draw_stories_tab(screen)
            
        # 5. 모달 팝업 그리기 (오버레이)
        if self.reading_title:
            self._draw_modal_popup(screen)

    def _draw_endings_tab(self, screen):
        ending_meta = {
            "true": {"title": "진엔딩: 내일 새벽, 함께", "desc": "아버지의 땀과 오랜 기다림의 깊은 의미를 완벽히 이해하여, 식탁에서 남기던 당근을 비우고 함께 새벽 밭으로 나섭니다."},
            "normal": {"title": "노멀엔딩: 조금은 알 것 같은 마음", "desc": "한 조각의 당근을 입에 넣으며 아버지를 쳐다봅니다. 모든 걸 알진 못해도 다정한 침묵이 밭을 돕니다."},
            "bad": {"title": "배드엔딩: 아직은 쓰기만 한 맛", "desc": "당근을 바라보았으나 차마 입에 넣지는 못합니다. 그래도 전처럼 무작정 밀치진 않는 작은 변화가 일어납니다."},
            "wither": {"title": "시듦엔딩: 끝내 지켜내지 못한 밭", "desc": "밭의 정성과 기다림이 어긋나 작물이 시들어 버렸습니다. 그러나 아버지가 매일 새벽 무엇과 싸워왔는가 배웁니다."}
        }
        
        for key, rect in self.ending_slots.items():
            is_wilt = (key == "wither")
            unlocked = (key in self.endings_seen) or (is_wilt and "wither" in self.endings_seen)
            meta = ending_meta[key]
            
            if unlocked:
                # 해금된 카드 그리기
                draw_light_panel(screen, rect)
                btn_rect = self.replay_btns[key]
                # 제목이 카드 밖으로 튀어나오지 않게 폭에 맞춰 줄바꿈
                y = rect.y + 14
                for tline in wrap_text(meta["title"], self.font_card_title, rect.w - 36, max_lines=2):
                    title_surf = self.font_card_title.render(tline, True, GOLD)
                    screen.blit(title_surf, (rect.x + 18, y))
                    y += self.font_card_title.get_height() + 2

                # 설명줄 — 리플레이 버튼 위 공간까지만 그려 버튼과 겹치지 않게 한다
                y += 4
                avail_lines = max(1, min(3, (btn_rect.y - 8 - y) // 18))
                for line in wrap_text(meta["desc"], self.font_small, rect.w - 36, max_lines=avail_lines):
                    line_surf = self.font_small.render(line, True, TEXT_DARK)
                    screen.blit(line_surf, (rect.x + 18, y))
                    y += 18

                # 리플레이 버튼
                hovered = btn_rect.collidepoint(pygame.mouse.get_pos())
                draw_button(screen, btn_rect, "엔딩 다시보기", self.font_small, hovered=hovered)
            else:
                # 잠긴 카드 그리기
                base_c = (210, 205, 195)
                edge_c = (170, 165, 155)
                draw_panel(screen, rect, fill=base_c, border=edge_c, radius=8, shadow=False)
                
                lock_title = self.font_section.render("? ? ?", True, (120, 115, 105))
                screen.blit(lock_title, (rect.x + 18, rect.y + 14))
                
                lock_desc = self.font_body.render("아직 해금되지 않은 결말입니다.", True, (130, 125, 115))
                screen.blit(lock_desc, (rect.x + 18, rect.y + 60))

    def _draw_achievements_tab(self, screen):
        from core import achievements
        items = achievements.all_with_state()
        got = sum(1 for _, unlocked in items if unlocked)

        area = pygame.Rect(80, 160, 640, 372)
        draw_light_panel(screen, area)
        header = self.font_section.render(f"업적  {got} / {len(items)}", True, TEXT_DARK)
        screen.blit(header, (area.x + 20, area.y + 12))
        pygame.draw.line(screen, (200, 180, 150), (area.x + 20, area.y + 44),
                         (area.right - 20, area.y + 44), 1)

        # 2열 그리드
        col_w = (area.w - 50) // 2
        cell_h = 58
        ox, oy = area.x + 18, area.y + 54
        for i, (ach, unlocked) in enumerate(items):
            col = i % 2
            row = i // 2
            cx = ox + col * (col_w + 14)
            cy = oy + row * (cell_h + 4)
            cell = pygame.Rect(cx, cy, col_w, cell_h)

            base = (250, 240, 214) if unlocked else (222, 216, 206)
            edge = mix_color(achievements.TIER_COLORS.get(ach["tier"], (180, 170, 150)),
                             (0, 0, 0), 0.15) if unlocked else (188, 182, 172)
            draw_panel(screen, cell, fill=base, border=edge, radius=8, shadow=False)

            mcx, mcy = cell.x + 26, cell.centery
            if unlocked:
                achievements._draw_medal(screen, mcx, mcy, ach["tier"], r=15)
                title = self.font_body.render(ach["title"], True, TEXT_DARK)
                screen.blit(title, (cell.x + 52, cell.y + 7))
                # 등급(브론즈/실버/골드/플래티넘) 라벨
                rank = achievements.TIER_LABELS.get(ach["tier"], "")
                rk = get_font(11).render(rank, True, achievements.TIER_COLORS.get(ach["tier"], (150, 150, 150)))
                screen.blit(rk, (cell.right - rk.get_width() - 10, cell.y + 8))
                for j, line in enumerate(wrap_text(ach["desc"], self.font_small, col_w - 62, max_lines=2)):
                    ds = self.font_small.render(line, True, TEXT_MUTED)
                    screen.blit(ds, (cell.x + 52, cell.y + 27 + j * 14))
            else:
                pygame.draw.circle(screen, (170, 164, 154), (mcx, mcy), 15)
                pygame.draw.circle(screen, (140, 134, 124), (mcx, mcy), 15, 2)
                q = self.font_body.render("?", True, (120, 114, 104))
                screen.blit(q, (mcx - q.get_width() // 2, mcy - q.get_height() // 2))
                title = self.font_body.render("???", True, (140, 134, 124))
                screen.blit(title, (cell.x + 52, cell.y + 9))
                ds = self.font_small.render("아직 잠겨 있는 업적", True, (150, 144, 134))
                screen.blit(ds, (cell.x + 52, cell.y + 32))

    def _draw_stories_tab(self, screen):
        # 텃밭 사건 목록
        draw_light_panel(screen, self.stories_area)
        title1 = self.font_section.render("목격한 밭의 사건들", True, TEXT_DARK)
        screen.blit(title1, (self.stories_area.x + 16, self.stories_area.y + 12))
        pygame.draw.line(screen, (200, 180, 150), (self.stories_area.x + 16, self.stories_area.y + 36), (self.stories_area.right - 16, self.stories_area.y + 36), 1)
        
        # 회상 조각 목록
        draw_light_panel(screen, self.memories_area)
        title2 = self.font_section.render("되찾은 기억 조각", True, TEXT_DARK)
        screen.blit(title2, (self.memories_area.x + 16, self.memories_area.y + 12))
        pygame.draw.line(screen, (200, 180, 150), (self.memories_area.x + 16, self.memories_area.y + 36), (self.memories_area.right - 16, self.memories_area.y + 36), 1)
        
        mouse_pos = pygame.mouse.get_pos()
        
        # 1. 사건들 렌더링
        self.story_item_rects = []
        story_choice_descriptions = {
            "이웃 밭의 물난리": "이웃 밭에서 갑작스레 흘러드는 거센 물살을 막아내던 사건.",
            "쓰러진 허수아비": "바람에 날려간 허수아비를 단단한 돌멩이로 다독여 세웠던 날.",
            "길 잃은 벌": "밭가에 힘없이 지친 채 누워있던 꿀벌 한 마리를 꽃밭으로 이송한 기억.",
            "무너진 이랑": "비바람에 주저앉은 이랑을 마른 손바닥으로 두둑하게 고쳐 쌓던 일.",
            "새벽의 고라니": "울타리 틈새로 고라니가 밭을 헤집지 않도록 틈을 단단히 메우던 밤.",
            "아버지의 낡은 호미": "창고 먼지 쌓인 구석에서 발견해 녹을 문질러 길들였던 손때 묻은 아버지의 호미."
        }
        
        y = self.stories_area.y + 50
        for i, title in enumerate(list(story_choice_descriptions.keys())):
            unlocked = (title in self.stories_seen)
            rect = pygame.Rect(self.stories_area.x + 12, y, self.stories_area.w - 24, 46)
            
            if unlocked:
                hovered = rect.collidepoint(mouse_pos)
                bg = mix_color(PANEL_WARM, WHITE, 0.3) if hovered else (248, 235, 210)
                draw_panel(screen, rect, fill=bg, border=PANEL_EDGE, radius=6, shadow=False)
                
                txt = self.font_body.render(title, True, TEXT_DARK)
                screen.blit(txt, (rect.x + 10, rect.y + 6))
                
                sub = self.font_small.render("선택 결과 읽기", True, TEXT_MUTED)
                screen.blit(sub, (rect.x + 10, rect.y + 24))
                
                desc = story_choice_descriptions.get(title, "목격한 사건의 상세한 대화 내용입니다.")
                self.story_item_rects.append((rect, title, desc))
            else:
                draw_panel(screen, rect, fill=(225, 220, 212), border=(190, 185, 175), radius=6, shadow=False)
                txt = self.font_body.render("아직 겪지 않은 일", True, (150, 145, 135))
                screen.blit(txt, (rect.x + 10, rect.y + 14))
            y += 50

        # 2. 기억 조각들 렌더링
        self.memory_item_rects = []
        memory_titles = ["희미한 식탁", "장바구니 소리", "남긴 접시", "다시 보이는 식탁", "이른 아침", "한 조각의 무게", "따뜻한 식탁", "손등의 흙", "짧은 고개 끄덕임"]
        
        y = self.memories_area.y + 50
        for title in memory_titles:
            unlocked = (title in self.memories_seen)
            rect = pygame.Rect(self.memories_area.x + 12, y, self.memories_area.w - 24, 30)
            
            if unlocked:
                hovered = rect.collidepoint(mouse_pos)
                bg = mix_color(PANEL_WARM, WHITE, 0.3) if hovered else (248, 235, 210)
                draw_panel(screen, rect, fill=bg, border=PANEL_EDGE, radius=5, shadow=False)
                
                txt = self.font_small.render(title, True, TEXT_DARK)
                screen.blit(txt, (rect.x + 10, rect.y + 8))
                
                text_content = self.memories_seen.get(title, "기억의 조각을 찾았습니다.")
                self.memory_item_rects.append((rect, title, text_content))
            else:
                draw_panel(screen, rect, fill=(225, 220, 212), border=(190, 185, 175), radius=5, shadow=False)
                txt = self.font_small.render("잃어버린 기억", True, (150, 145, 135))
                screen.blit(txt, (rect.x + 10, rect.y + 8))
            y += 33

        # 특별 미니게임 '별 잇기' 다시 하기 (아래 여백에 배치)
        hov = self.star_replay_btn.collidepoint(mouse_pos)
        draw_button(screen, self.star_replay_btn, "★ 별 잇기 다시 하기", self.font_btn, hovered=hov)

    def _draw_modal_popup(self, screen):
        # 반투명 장막
        veil = pygame.Surface((800, 600), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 130))
        screen.blit(veil, (0, 0))
        
        draw_light_panel(screen, self.modal_rect)
        
        # 모달 타이틀
        title_surf = self.font_section.render(self.reading_title, True, GOLD)
        screen.blit(title_surf, (self.modal_rect.centerx - title_surf.get_width() // 2, self.modal_rect.y + 24))
        
        pygame.draw.line(screen, (200, 180, 150), (self.modal_rect.x + 40, self.modal_rect.y + 60), (self.modal_rect.right - 40, self.modal_rect.y + 60), 2)
        
        # 글 내용 렌더링
        y = self.modal_rect.y + 85
        for paragraph in self.reading_text.split("\n"):
            if not paragraph:
                y += 18
                continue
            for line in wrap_text(paragraph, self.font_body, self.modal_rect.w - 80):
                line_surf = self.font_body.render(line, True, TEXT_DARK)
                screen.blit(line_surf, (self.modal_rect.x + 40, y))
                y += 24
                
        # 다시 하기 버튼 (선택형 이벤트인 경우만) + 닫기 버튼
        if self._find_replay_event(self.reading_title) is not None:
            hov = self.modal_replay_btn.collidepoint(pygame.mouse.get_pos())
            draw_button(screen, self.modal_replay_btn, "다시 하기", self.font_small, hovered=hov)
        draw_button(screen, self.modal_close_btn, "닫기", self.font_small, hovered=self.hovered_modal_close)

    def _find_replay_event(self, title):
        """제목이 선택형 이벤트(STORY_EVENTS)와 일치하면 그 이벤트 데이터를 돌려준다 (다시 하기용)."""
        from core.game_state import STORY_EVENTS
        for ev in STORY_EVENTS:
            if ev.get("title") == title:
                return ev
        return None
