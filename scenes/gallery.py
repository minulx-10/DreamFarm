import pygame
from core.game_state import game_state
from core.assets import get_font, sprites, TEXT_DARK, TEXT_MUTED, WHITE, GOLD, PANEL_WARM, PANEL_EDGE
from core.ui import draw_light_panel, draw_story_backdrop, draw_button, wrap_text, mix_color, draw_panel
from core import audio
from core import save_system
from core import i18n

class GalleryScene:
    def __init__(self):
        self.font_title = get_font(28)
        self.font_section = get_font(20)
        self.font_card_title = get_font(17)   # 엔딩 카드 제목(폭이 좁아 작은 폰트로 넘침 방지)
        self.font_body = get_font(15)
        self.font_small = get_font(13)
        self.font_btn = get_font(16)
        
        self.active_tab = "endings"  # endings | stories | achievements | storehouse | hidden_achievements

        self.back_rect = pygame.Rect(30, 24, 100, 32)
        self.tab_rects = []          # [(rect, tab_id, label)] — _update_tab_rects 가 채운다
        self._update_tab_rects()
        
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
        self.reading_kind = None     # story | memory | item | run — '다시 하기' 버튼은 story에서만
        self.modal_rect = pygame.Rect(120, 120, 560, 380)
        self.modal_close_btn = pygame.Rect(452, 440, 128, 36)
        self.modal_replay_btn = pygame.Rect(220, 440, 128, 36)   # 이벤트 다시 하기
        self.star_replay_btn = pygame.Rect(290, 532, 220, 36)    # 별 잇기 다시 하기(이야기 탭) — 저작권 표시와 겹치지 않게 위로
        
        self.endings_seen = save_system.endings_seen()
        self.stories_seen = save_system.load_meta().get("stories_seen", [])
        self.memories_seen = save_system.load_meta().get("memories_seen", {})

        # 스크롤 상태 (사건/기억 컬럼·업적 그리드·지난 회차 목록·모달 본문)
        self.stories_scroll = 0
        self.memories_scroll = 0
        self.ach_scroll = 0
        self.runs_scroll = 0
        self.reading_scroll = 0
        self.story_item_rects = []       # (rect, 제목, 본문) — draw가 매 프레임 채움
        self.memory_item_rects = []
        self.reading_journal = None      # 창고 '지난 회차' 열람 — 일지 원문 리스트(표시 시점 번역)
        self.storehouse_item_rects = []
        self.run_item_rects = []

        self.hovered_back = False
        self.hovered_tab = None          # 호버 중인 탭 id
        self.hovered_modal_close = False

    def _update_tab_rects(self):
        from core import achievements
        hidden_unlocked = achievements.has_any_hidden_unlocked()
        tabs = [("endings", "엔딩"), ("stories", "이야기·기억"),
                ("achievements", "일반 업적" if hidden_unlocked else "업적"),
                ("storehouse", "창고")]
        if hidden_unlocked:
            tabs.append(("hidden_achievements", "히든 업적"))
        # 탭 수(4~5)에 맞춰 대칭 정렬
        n = len(tabs)
        gap = 8
        w = 150 if n <= 4 else 138
        x = (800 - (w * n + gap * (n - 1))) // 2
        self.tab_rects = []
        for tid, label in tabs:
            self.tab_rects.append((pygame.Rect(x, 105, w, 34), tid, label))
            x += w + gap
        # 주의: story/memory_item_rects는 여기서 비우면 안 된다 — handle_events 초입에서
        # 이 함수를 부르는데, 클릭 판정이 그 리스트를 쓰므로 비우면 목록 클릭이 죽는다.
        # (draw 쪽에서 매 프레임 새로 채운다.)

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        
        # 모달 팝업이 띄워져 있는가
        if self.reading_title:
            self.hovered_modal_close = self.modal_close_btn.collidepoint(mouse_pos)
            replay_ev = (self._find_replay_event(self.reading_title)
                         if getattr(self, "reading_kind", None) == "story" else None)
            for event in events:
                if event.type == pygame.MOUSEWHEEL:
                    self.reading_scroll = max(0, self.reading_scroll - event.y * 40)
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    audio.play("click")
                    self._close_modal()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if replay_ev is not None and self.modal_replay_btn.collidepoint(event.pos):
                        # 그 이벤트(선택형 미니게임)를 다시 플레이 — 끝나면 갤러리로 복귀
                        audio.play("click")
                        game_state.choice_data = replay_ev
                        game_state.event_replay = True
                        self._close_modal()
                        game_state.current_scene = "story_choice"
                        return
                    if self.hovered_modal_close or not self.modal_rect.collidepoint(event.pos):
                        audio.play("click")
                        self._close_modal()
            return

        self._update_tab_rects()
        self.hovered_back = self.back_rect.collidepoint(mouse_pos)
        self.hovered_tab = None
        for rect, tid, _label in self.tab_rects:
            if rect.collidepoint(mouse_pos):
                self.hovered_tab = tid

        for event in events:
            # 휠 스크롤 — 사건/기억 컬럼(마우스가 올라간 쪽)·지난 회차 목록
            if event.type == pygame.MOUSEWHEEL:
                if self.active_tab == "stories":
                    if self.stories_area.collidepoint(mouse_pos):
                        self.stories_scroll = max(0, self.stories_scroll - event.y * 40)
                    elif self.memories_area.collidepoint(mouse_pos):
                        self.memories_scroll = max(0, self.memories_scroll - event.y * 40)
                elif self.active_tab == "storehouse":
                    # 마우스가 '지난 회차' 목록 위에 있을 때만 그 목록을 스크롤
                    if pygame.Rect(90, 396, 380, 138).collidepoint(mouse_pos):
                        self.runs_scroll = max(0, self.runs_scroll - event.y * 30)
                elif self.active_tab == "achievements":
                    self.ach_scroll = max(0, self.ach_scroll - event.y * 40)
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 뒤로가기
                if self.hovered_back:
                    audio.play("click")
                    game_state.current_scene = "title"
                    return
                # 탭 전환
                for rect, tid, _label in self.tab_rects:
                    if rect.collidepoint(event.pos):
                        audio.play("click")
                        self.active_tab = tid
                        break

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
                elif self.active_tab == "stories":
                    # 별 잇기 다시 하기 — 특별 미니게임 재생(끝나면 갤러리로 복귀)
                    if self.star_replay_btn.collidepoint(event.pos):
                        audio.play("success")
                        game_state.return_scene = "gallery"
                        game_state.event_replay = True   # 감상용 — 끝나도 이해도 장면 없이 갤러리로
                        game_state.current_scene = "star_connect"
                        return
                    # 사건목록 클릭
                    for rect, title, text in self.story_item_rects:
                        if rect.collidepoint(event.pos):
                            audio.play("click")
                            self.reading_title = title
                            self.reading_text = text
                            self.reading_kind = "story"
                            self.reading_scroll = 0
                            return
                    # 기억목록 클릭
                    for rect, title, text in self.memory_item_rects:
                        if rect.collidepoint(event.pos):
                            audio.play("click")
                            self.reading_title = title
                            self.reading_text = text
                            self.reading_kind = "memory"
                            self.reading_scroll = 0
                            return
                elif self.active_tab == "storehouse":
                    # 물건 클릭 — 해금된 것만 사연 모달
                    for rect, item, unlocked in self.storehouse_item_rects:
                        if rect.collidepoint(event.pos):
                            if unlocked:
                                audio.play("click")
                                self.reading_title = item["name"]
                                self.reading_text = item["story"]
                                self.reading_kind = "item"
                                self.reading_scroll = 0
                            else:
                                audio.play("break")
                            return
                    # 지난 회차 클릭 — 그 회차의 일지 열람
                    for rect, run in self.run_item_rects:
                        if rect.collidepoint(event.pos):
                            audio.play("page")
                            self.reading_title = i18n.tf("{n}회차의 일지", n=run.get("n", 0))
                            self.reading_text = ""
                            self.reading_kind = "run"
                            self.reading_journal = list(run.get("journal", []))
                            self.reading_scroll = 0
                            return

    def _close_modal(self):
        self.reading_title = None
        self.reading_text = None
        self.reading_journal = None
        self.reading_kind = None
        self.reading_scroll = 0

    def update(self, dt):
        pass

    def draw(self, screen):
        # 1. 배경
        draw_story_backdrop(screen, "night")
        
        # 실시간 탭 상태 갱신
        self._update_tab_rects()
        
        # 2. 타이틀
        title_surf = self.font_title.render("추억 저장소", True, WHITE)
        screen.blit(title_surf, (400 - title_surf.get_width() // 2, 40))
        
        # 뒤로가기 버튼
        draw_button(screen, self.back_rect, "돌아가기", self.font_small, hovered=self.hovered_back)
        
        # 3. 탭 바 그리기 (4~5탭 동적)
        for rect, tid, label in self.tab_rects:
            draw_button(screen, rect, label, self.font_btn,
                        hovered=(self.hovered_tab == tid), selected=(self.active_tab == tid))

        # 4. 콘텐츠 그리기
        if self.active_tab == "endings":
            self._draw_endings_tab(screen)
        elif self.active_tab == "achievements":
            self._draw_achievements_tab(screen)
        elif self.active_tab == "hidden_achievements":
            self._draw_hidden_achievements_tab(screen)
        elif self.active_tab == "storehouse":
            self._draw_storehouse_tab(screen)
        else:
            self._draw_stories_tab(screen)
            
        # 하단 중앙 저작권(Copyright) 표시 — '별 잇기 다시 하기' 버튼 아래에 배치(겹침 방지)
        cr_font = get_font(13)
        cr_col = (130, 125, 115) if game_state.nightmare else TEXT_MUTED
        cr_surf = cr_font.render("© 2026 삼광 (三光)", True, cr_col)
        screen.blit(cr_surf, (400 - cr_surf.get_width() // 2, 580))

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

        # 악몽 엔딩 — 본 사람에게만 하단에 가로 카드로 나타난다 (못 본 사람에게는 존재 자체를 숨김)
        self._draw_nightmare_ending_card(screen)

        for key, rect in self.ending_slots.items():
            if key == "nightmare":   # 악몽 카드는 위에서 별도 가로 카드로 그림
                continue
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

    def _draw_nightmare_ending_card(self, screen):
        """다섯 번째 엔딩(악몽) — 해금된 경우에만 2x2 그리드 아래 가로 카드로."""
        if "nightmare" not in self.endings_seen:
            self.ending_slots.pop("nightmare", None)
            self.replay_btns.pop("nightmare", None)
            return
        rect = pygame.Rect(90, 508, 620, 52)
        btn = pygame.Rect(560, 518, 140, 32)
        self.ending_slots["nightmare"] = rect
        self.replay_btns["nightmare"] = btn
        draw_panel(screen, rect, fill=(46, 24, 26), border=(150, 60, 54), shadow=False)
        title = self.font_card_title.render(i18n.t("악몽의 끝: 비워진 식탁"), True, (232, 120, 104))
        screen.blit(title, (rect.x + 18, rect.y + 6))
        desc = i18n.t("붉은 하늘 아래, 마지막 한 조각까지 비워 냈습니다.")
        desc_surf = self.font_small.render(desc, True, (206, 168, 158))
        screen.blit(desc_surf, (rect.x + 18, rect.y + 28))
        hovered = btn.collidepoint(pygame.mouse.get_pos())
        draw_button(screen, btn, "엔딩 다시보기", self.font_small, hovered=hovered)

    def _draw_achievements_tab(self, screen):
        from core import achievements
        items = achievements.all_with_state()
        got = sum(1 for _, unlocked in items if unlocked)

        area = pygame.Rect(80, 160, 640, 372)
        draw_light_panel(screen, area)
        header = self.font_section.render(i18n.tf("업적  {got} / {total}", got=got, total=len(items)), True, TEXT_DARK)
        screen.blit(header, (area.x + 20, area.y + 12))
        pygame.draw.line(screen, (200, 180, 150), (area.x + 20, area.y + 44),
                         (area.right - 20, area.y + 44), 1)

        # 2열 그리드 — 업적이 늘어 세로로 넘치면 휠 스크롤
        col_w = (area.w - 50) // 2
        cell_h = 58
        rows_n = (len(items) + 1) // 2
        content_h = rows_n * (cell_h + 4)
        view = pygame.Rect(area.x + 6, area.y + 50, area.w - 12, area.h - 60)
        max_scroll = max(0, content_h - view.h)
        self.ach_scroll = min(self.ach_scroll, max_scroll)
        old_clip = screen.get_clip()
        screen.set_clip(view)
        ox, oy = area.x + 18, area.y + 54 - self.ach_scroll
        for i, (ach, unlocked) in enumerate(items):
            col = i % 2
            row = i // 2
            cx = ox + col * (col_w + 14)
            cy = oy + row * (cell_h + 4)
            cell = pygame.Rect(cx, cy, col_w, cell_h)
            if cell.bottom < view.y or cell.y > view.bottom:
                continue

            base = (250, 240, 214) if unlocked else (222, 216, 206)
            edge = mix_color(achievements.TIER_COLORS.get(ach["tier"], (180, 170, 150)),
                             (0, 0, 0), 0.15) if unlocked else (188, 182, 172)
            draw_panel(screen, cell, fill=base, border=edge, radius=8, shadow=False)

            mcx, mcy = cell.x + 26, cell.centery
            if unlocked:
                achievements._draw_medal(screen, mcx, mcy, ach["tier"], r=15)
                # 등급(브론즈/실버/골드/플래티넘) 라벨
                rank = achievements.TIER_LABELS.get(ach["tier"], "")
                rk = get_font(11).render(rank, True, achievements.TIER_COLORS.get(ach["tier"], (150, 150, 150)))
                rank_x = cell.right - rk.get_width() - 10
                # 제목은 등급 라벨 앞까지만 — 긴 영어 제목이 라벨과 겹치지 않게 폭 맞춰 축소
                title = self._fit_render(ach["title"], rank_x - 12 - (cell.x + 52),
                                         base=15, color=TEXT_DARK, min_size=11)
                screen.blit(title, (cell.x + 52, cell.y + 7))
                screen.blit(rk, (rank_x, cell.y + 8))
                for j, line in enumerate(wrap_text(ach["desc"], self.font_small, col_w - 62, max_lines=2)):
                    ds = self.font_small.render(line, True, TEXT_MUTED)
                    screen.blit(ds, (cell.x + 52, cell.y + 27 + j * 14))
            else:
                # 잠긴 메달도 도트 원으로 — 옆의 해금 메달(도트)과 톤 통일
                from core.pixelfx import pixel_disc
                pixel_disc(screen, (140, 134, 124), (mcx, mcy), 15, px=2)
                pixel_disc(screen, (170, 164, 154), (mcx, mcy), 13, px=2)
                q = self.font_body.render("?", True, (120, 114, 104))
                screen.blit(q, (mcx - q.get_width() // 2, mcy - q.get_height() // 2))
                rank = achievements.TIER_LABELS.get(ach["tier"], "")
                rk = get_font(11).render(rank, True, (170, 164, 154))
                rank_x = cell.right - rk.get_width() - 10
                # 잠겼어도 이름은 보여줘 무엇을 노려야 할지 유추할 수 있게 (설명만 감춘다)
                title = self._fit_render(ach["title"], rank_x - 12 - (cell.x + 52),
                                         base=15, color=(150, 144, 134), min_size=11)
                screen.blit(title, (cell.x + 52, cell.y + 7))
                screen.blit(rk, (rank_x, cell.y + 8))
                ds = self.font_small.render("아직 잠긴 업적 · 조건은 비밀", True, (160, 154, 144))
                screen.blit(ds, (cell.x + 52, cell.y + 30))
        screen.set_clip(old_clip)
        self._draw_column_scrollbar(screen, area, view, content_h, self.ach_scroll)

    def _fit_render(self, text, max_w, base=20, color=TEXT_DARK, min_size=12):
        """텍스트를 max_w 안에 들어가도록 폰트를 줄여 렌더한다(영어 등 긴 문구 넘침 방지)."""
        size = base
        surf = get_font(size).render(text, True, color)
        while surf.get_width() > max_w and size > min_size:
            size -= 1
            surf = get_font(size).render(text, True, color)
        return surf

    def _draw_stories_tab(self, screen):
        # 텃밭 사건 목록
        draw_light_panel(screen, self.stories_area)
        title1 = self._fit_render("목격한 밭의 사건들", self.stories_area.w - 32)
        screen.blit(title1, (self.stories_area.x + 16, self.stories_area.y + 12))
        pygame.draw.line(screen, (200, 180, 150), (self.stories_area.x + 16, self.stories_area.y + 36), (self.stories_area.right - 16, self.stories_area.y + 36), 1)

        # 회상 조각 목록
        draw_light_panel(screen, self.memories_area)
        title2 = self._fit_render("되찾은 기억 조각", self.memories_area.w - 32)
        screen.blit(title2, (self.memories_area.x + 16, self.memories_area.y + 12))
        pygame.draw.line(screen, (200, 180, 150), (self.memories_area.x + 16, self.memories_area.y + 36), (self.memories_area.right - 16, self.memories_area.y + 36), 1)
        
        mouse_pos = pygame.mouse.get_pos()

        # 1. 사건들 렌더링 — 16종으로 늘어 휠 스크롤 (컬럼에 마우스 올리고 휠)
        self.story_item_rects = []
        story_choice_descriptions = {
            "이웃 밭의 물난리": "이웃 밭에서 갑작스레 흘러드는 거센 물살을 막아내던 사건.",
            "쓰러진 허수아비": "바람에 날려간 허수아비를 단단한 돌멩이로 다독여 세웠던 날.",
            "길 잃은 벌": "밭가에 힘없이 지친 채 누워있던 꿀벌 한 마리를 꽃밭으로 이송한 기억.",
            "무너진 이랑": "비바람에 주저앉은 이랑을 마른 손바닥으로 두둑하게 고쳐 쌓던 일.",
            "새벽의 고라니": "울타리 틈새로 고라니가 밭을 헤집지 않도록 틈을 단단히 메우던 밤.",
            "아버지의 낡은 호미": "창고 먼지 쌓인 구석에서 발견해 녹을 문질러 길들였던 손때 묻은 아버지의 호미.",
            "무너진 돌담": "바람에 무너진 돌담에서 굴러온 돌을 허리 숙여 하나하나 골라내던 일.",
            "막힌 물꼬": "낙엽과 검불에 막힌 물꼬를 맨손으로 걷어내 물길을 되살린 날.",
            "읍내 장날": "아버지의 단골 종묘상이 문을 여는 읍내 장날의 기억.",
            "낡은 라디오": "창고 선반에서 찾아낸, 아버지의 새벽을 열던 지지직거리는 라디오.",
            "무거워진 가지": "열매 무게로 처진 사과나무 가지를 받침목으로 받쳐 준 일.",
            "첫 낙과": "밤바람에 떨어진 풋사과들을 흙으로, 혹은 항아리로 돌려보낸 날.",
            "두더지 굴": "감자 이랑 밑을 지나간 두더지 굴 입구를 하나하나 메우던 오후.",
            "북주기 가르침": "이웃 어른에게서 아버지의 북주기 손놀림을 건네받은 날.",
            "물꼬 순서": "위 논과 물 대는 순서가 겹친 날, 물길을 함께 손본 기억.",
            "우렁이 손님": "논물 속 우렁이 손님을 두고 볼지 말지 고민하던 일.",
        }

        story_titles = list(story_choice_descriptions.keys())
        row_h = 50
        view_s = pygame.Rect(self.stories_area.x + 6, self.stories_area.y + 44,
                             self.stories_area.w - 12, self.stories_area.h - 56)
        max_s = max(0, len(story_titles) * row_h - view_s.h)
        self.stories_scroll = min(self.stories_scroll, max_s)
        old_clip = screen.get_clip()
        screen.set_clip(view_s)
        y = view_s.y + 4 - self.stories_scroll
        for title in story_titles:
            rect = pygame.Rect(self.stories_area.x + 12, y, self.stories_area.w - 30, 46)
            if rect.bottom >= view_s.y and rect.y <= view_s.bottom:
                unlocked = (title in self.stories_seen)
                if unlocked:
                    hovered = rect.collidepoint(mouse_pos) and view_s.collidepoint(mouse_pos)
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
            y += row_h
        screen.set_clip(old_clip)
        self._draw_column_scrollbar(screen, self.stories_area, view_s, len(story_titles) * row_h,
                                    self.stories_scroll)

        # 2. 기억 조각들 렌더링 — 작물 서사 팩 포함 18편, 휠 스크롤
        self.memory_item_rects = []
        from scenes.farm_simulator import all_memory_titles
        memory_titles = all_memory_titles()

        mem_h = 33
        view_m = pygame.Rect(self.memories_area.x + 6, self.memories_area.y + 44,
                             self.memories_area.w - 12, self.memories_area.h - 56)
        max_m = max(0, len(memory_titles) * mem_h - view_m.h)
        self.memories_scroll = min(self.memories_scroll, max_m)
        screen.set_clip(view_m)
        y = view_m.y + 4 - self.memories_scroll
        for title in memory_titles:
            rect = pygame.Rect(self.memories_area.x + 12, y, self.memories_area.w - 30, 30)
            if rect.bottom >= view_m.y and rect.y <= view_m.bottom:
                unlocked = (title in self.memories_seen)
                if unlocked:
                    hovered = rect.collidepoint(mouse_pos) and view_m.collidepoint(mouse_pos)
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
            y += mem_h
        screen.set_clip(old_clip)
        self._draw_column_scrollbar(screen, self.memories_area, view_m, len(memory_titles) * mem_h,
                                    self.memories_scroll)

        # 특별 미니게임 '별 잇기' 다시 하기 (아래 여백에 배치)
        hov = self.star_replay_btn.collidepoint(mouse_pos)
        draw_button(screen, self.star_replay_btn, "★ 별 잇기 다시 하기", self.font_btn, hovered=hov)

    def _draw_column_scrollbar(self, screen, area, view, content_h, scroll):
        """리스트 컬럼 우측의 가는 스크롤바 (내용이 넘칠 때만)."""
        if content_h <= view.h:
            return
        from core.pixelfx import pixel_rect, CHAMFER_SM
        track = pygame.Rect(area.right - 10, view.y, 5, view.h)
        pixel_rect(screen, (206, 188, 158), track, chamfer=CHAMFER_SM)
        th = max(20, int(view.h * view.h / content_h))
        max_scroll = content_h - view.h
        ty = track.y + int((track.h - th) * (scroll / max_scroll))
        pixel_rect(screen, (123, 92, 65), (track.x, ty, 5, th), chamfer=CHAMFER_SM)

    def _draw_storehouse_tab(self, screen):
        """아버지의 창고 — 물건 컬렉션 + 지난 회차 일지 아카이브 + 손길의 기록(누적 통계)."""
        from core import storehouse
        from core.crops import CROPS
        got = storehouse.unlocked_ids()
        self.storehouse_item_rects = []
        self.run_item_rects = []
        mouse_pos = pygame.mouse.get_pos()

        # 1) 아버지의 물건 — 3×3 그리드
        items_area = pygame.Rect(90, 150, 620, 238)
        draw_light_panel(screen, items_area)
        head = self.font_section.render(
            i18n.tf("아버지의 물건  {got} / {total}", got=len(got), total=len(storehouse.ITEMS)),
            True, TEXT_DARK)
        screen.blit(head, (items_area.x + 20, items_area.y + 10))
        pygame.draw.line(screen, (200, 180, 150), (items_area.x + 20, items_area.y + 38),
                         (items_area.right - 20, items_area.y + 38), 1)
        cw, chh = 196, 58
        gx, gy = items_area.x + 14, items_area.y + 46
        for i, item in enumerate(storehouse.ITEMS):
            col, row = i % 3, i // 3
            cell = pygame.Rect(gx + col * (cw + 6), gy + row * (chh + 4), cw, chh)
            unlocked = item["id"] in got
            if unlocked:
                hovered = cell.collidepoint(mouse_pos)
                bg = mix_color(PANEL_WARM, WHITE, 0.3) if hovered else (248, 235, 210)
                draw_panel(screen, cell, fill=bg, border=PANEL_EDGE, radius=6, shadow=False)
                spr = sprites.get(item["icon"])
                if spr:
                    screen.blit(spr, (cell.x + 22 - spr.get_width() // 2,
                                      cell.centery - spr.get_height() // 2))
                name = self._fit_render(item["name"], cw - 56, base=15)
                screen.blit(name, (cell.x + 46, cell.y + 10))
                sub = self.font_small.render("사연 읽기", True, TEXT_MUTED)
                screen.blit(sub, (cell.x + 46, cell.y + 32))
            else:
                draw_panel(screen, cell, fill=(225, 220, 212), border=(190, 185, 175), radius=6, shadow=False)
                q = self.font_body.render("?", True, (150, 145, 135))
                screen.blit(q, (cell.x + 22 - q.get_width() // 2, cell.centery - q.get_height() // 2))
                for j, ln in enumerate(wrap_text(item["hint"], self.font_small, cw - 56, max_lines=2)):
                    hs = self.font_small.render(ln, True, (150, 145, 135))
                    screen.blit(hs, (cell.x + 46, cell.y + 12 + j * 16))
            self.storehouse_item_rects.append((cell, item, unlocked))

        # 2) 지난 회차 — 완주한 회차의 일지 아카이브 (클릭해 열람, 휠 스크롤)
        runs_area = pygame.Rect(90, 396, 380, 138)
        draw_light_panel(screen, runs_area)
        rt = self.font_section.render("지난 회차", True, TEXT_DARK)
        screen.blit(rt, (runs_area.x + 16, runs_area.y + 8))
        pygame.draw.line(screen, (200, 180, 150), (runs_area.x + 16, runs_area.y + 34),
                         (runs_area.right - 16, runs_area.y + 34), 1)
        runs = list(reversed(save_system.run_archive()))   # 최신이 위
        ENDING_SHORT = {"true": "진엔딩", "normal": "노멀", "bad": "배드",
                        "wither": "시듦", "nightmare": "악몽"}
        view_r = pygame.Rect(runs_area.x + 10, runs_area.y + 40, runs_area.w - 20, runs_area.h - 50)
        row_h = 30
        max_r = max(0, len(runs) * row_h - view_r.h)
        self.runs_scroll = min(self.runs_scroll, max_r)
        if not runs:
            es = self.font_small.render("아직 끝까지 지낸 회차가 없습니다.", True, TEXT_MUTED)
            screen.blit(es, (runs_area.centerx - es.get_width() // 2, runs_area.centery + 8))
        old_clip = screen.get_clip()
        screen.set_clip(view_r)
        y = view_r.y + 2 - self.runs_scroll
        for run in runs:
            rect = pygame.Rect(view_r.x + 2, y, view_r.w - 14, 27)
            if rect.bottom >= view_r.y and rect.y <= view_r.bottom:
                hovered = rect.collidepoint(mouse_pos) and view_r.collidepoint(mouse_pos)
                bg = mix_color(PANEL_WARM, WHITE, 0.3) if hovered else (248, 235, 210)
                draw_panel(screen, rect, fill=bg, border=PANEL_EDGE, radius=5, shadow=False)
                crop_name = CROPS.get(run.get("crop", "carrot"), CROPS["carrot"])["name"]
                label = i18n.tf("{n}회차 · {crop} · {ending} · {days}일",
                                n=run.get("n", 0), crop=i18n.t(crop_name),
                                ending=i18n.t(ENDING_SHORT.get(run.get("ending"), "노멀")),
                                days=run.get("days", 0))
                seed = run.get("seed", "평년")
                if seed != "평년":
                    label += " · " + i18n.t(seed)
                ch = run.get("challenge")
                if ch:   # 도전 규칙 회차 표시 — 기록만 하고 안 보여주면 도전한 보람이 없다
                    CH_SHORT = {"no_journal": "무일지", "drought": "한발", "seven_days": "이레"}
                    label += " · " + i18n.t(CH_SHORT.get(ch, ch))
                ls = self._fit_render(label, rect.w - 16, base=13, min_size=11)
                screen.blit(ls, (rect.x + 8, rect.centery - ls.get_height() // 2))
                self.run_item_rects.append((rect, run))
            y += row_h
        screen.set_clip(old_clip)
        self._draw_column_scrollbar(screen, runs_area, view_r, len(runs) * row_h, self.runs_scroll)

        # 3) 손길의 기록 — 누적 통계
        stats_area = pygame.Rect(478, 396, 232, 138)
        draw_light_panel(screen, stats_area)
        st = self.font_section.render("손길의 기록", True, TEXT_DARK)
        screen.blit(st, (stats_area.x + 16, stats_area.y + 8))
        pygame.draw.line(screen, (200, 180, 150), (stats_area.x + 16, stats_area.y + 34),
                         (stats_area.right - 16, stats_area.y + 34), 1)
        life = save_system.lifetime_stats()
        meta = save_system.load_meta()
        rows = [
            ("완주한 회차", meta.get("runs_completed", 0)),
            ("총 재배일", life.get("총 재배일", 0)),
            ("물 주기", life.get("물 주기", 0)),
            ("잡초 뽑기", life.get("잡초 뽑기", 0)),
            ("해충 살피기", life.get("해충 살피기", 0)),
        ]
        y = stats_area.y + 42
        for label, val in rows:
            ls = self.font_small.render(label, True, TEXT_MUTED)
            vs = self.font_small.render(str(val), True, TEXT_DARK)
            screen.blit(ls, (stats_area.x + 16, y))
            screen.blit(vs, (stats_area.right - 16 - vs.get_width(), y))
            y += 18

    def _draw_modal_popup(self, screen):
        # 반투명 장막 — 캔버스 전체(여백 포함)
        from core.ui import draw_full_veil
        draw_full_veil(screen, (0, 0, 0, 130))

        draw_light_panel(screen, self.modal_rect)

        # 모달 타이틀
        title_surf = self.font_section.render(self.reading_title, True, GOLD)
        screen.blit(title_surf, (self.modal_rect.centerx - title_surf.get_width() // 2, self.modal_rect.y + 24))

        pygame.draw.line(screen, (200, 180, 150), (self.modal_rect.x + 40, self.modal_rect.y + 60), (self.modal_rect.right - 40, self.modal_rect.y + 60), 2)

        # 본문 — 회차 일지(reading_journal)면 표시 시점 번역, 아니면 저장 텍스트.
        # 길면 휠로 스크롤 (본문 영역 클리핑)
        if self.reading_journal is not None:
            from scenes.ending import _localize_journal_line
            paragraphs = []
            for entry in self.reading_journal:
                paragraphs.extend(_localize_journal_line(raw) for raw in entry.split("\n"))
                paragraphs.append("")
        else:
            # 통째로 번역한 뒤 줄을 가른다 — 갈라 놓고 조각별로 번역하면 카탈로그 키와 안 맞아
            # EN에서 한국어가 그대로 남는다 (창고 '사연'이 그랬다).
            paragraphs = i18n.t(self.reading_text).split("\n")

        view = pygame.Rect(self.modal_rect.x + 40, self.modal_rect.y + 72,
                           self.modal_rect.w - 80, self.modal_rect.h - 130)
        lines = []
        for paragraph in paragraphs:
            if not paragraph:
                lines.append(None)
                continue
            lines.extend(wrap_text(paragraph, self.font_body, view.w))
        content_h = sum(18 if l is None else 24 for l in lines)
        max_scroll = max(0, content_h - view.h)
        self.reading_scroll = min(self.reading_scroll, max_scroll)

        old_clip = screen.get_clip()
        screen.set_clip(view)
        y = view.y - self.reading_scroll
        for line in lines:
            if line is None:
                y += 18
                continue
            if y + 24 >= view.y and y <= view.bottom:
                line_surf = self.font_body.render(line, True, TEXT_DARK)
                screen.blit(line_surf, (view.x, y))
            y += 24
        screen.set_clip(old_clip)
        if max_scroll > 0:
            self._draw_column_scrollbar(screen, pygame.Rect(self.modal_rect.x, view.y,
                                                            self.modal_rect.w - 14, view.h),
                                        view, content_h, self.reading_scroll)

        # 다시 하기 버튼 (선택형 이벤트인 경우만 — 창고 물건 이름이 이벤트 제목과 겹쳐도 안 뜨게) + 닫기 버튼
        if self.reading_kind == "story" and self._find_replay_event(self.reading_title) is not None:
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

    def _draw_hidden_achievements_tab(self, screen):
        from core import achievements
        items = achievements.hidden_with_state()
        got = sum(1 for _, unlocked in items if unlocked)

        area = pygame.Rect(80, 160, 640, 372)
        # 일반 판넬보다 살짝 더 신비롭고 어두운 틴트 얹어주기
        draw_light_panel(screen, area)
        header = self.font_section.render(i18n.tf("히든 업적  {got} / {total}", got=got, total=len(items)), True, (139, 38, 38))
        screen.blit(header, (area.x + 20, area.y + 12))
        pygame.draw.line(screen, (200, 150, 150), (area.x + 20, area.y + 44),
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

            if unlocked:
                # 해금된 히든 업적: 살짝 붉은빛이 감도는 골드/플래티넘 연출
                base = (255, 238, 238)
                edge = (180, 60, 60)
                draw_panel(screen, cell, fill=base, border=edge, radius=8, shadow=False)
                
                achievements._draw_medal(screen, cell.x + 26, cell.centery, ach["tier"], r=15)
                rank = "히든"
                rk = get_font(11).render(rank, True, (190, 48, 48))
                rank_x = cell.right - rk.get_width() - 10
                # 제목은 등급 라벨 앞까지만 (긴 영어 제목 겹침 방지 — 일반 업적 탭과 동일)
                title = self._fit_render(ach["title"], rank_x - 12 - (cell.x + 52),
                                         base=15, color=(90, 20, 20), min_size=11)
                screen.blit(title, (cell.x + 52, cell.y + 7))
                screen.blit(rk, (rank_x, cell.y + 8))
                
                for j, line in enumerate(wrap_text(ach["desc"], self.font_small, col_w - 74, max_lines=2)):
                    ds = self.font_small.render(line, True, (120, 80, 80))
                    screen.blit(ds, (cell.x + 52, cell.y + 27 + j * 14))
            else:
                # 아직 잠긴 히든 업적: "?"로 물들이고 철저히 은폐
                base = (218, 214, 210)
                edge = (168, 160, 150)
                draw_panel(screen, cell, fill=base, border=edge, radius=8, shadow=False)
                
                mcx, mcy = cell.x + 26, cell.centery
                from core.pixelfx import pixel_disc
                pixel_disc(screen, (120, 114, 104), (mcx, mcy), 15, px=2)
                pixel_disc(screen, (150, 144, 134), (mcx, mcy), 13, px=2)
                q = self.font_body.render("?", True, (90, 84, 74))
                screen.blit(q, (mcx - q.get_width() // 2, mcy - q.get_height() // 2))
                
                title = self.font_body.render("기밀 히든 업적", True, (138, 130, 120))
                screen.blit(title, (cell.x + 52, cell.y + 7))
                
                lock_desc = "비밀스러운 농가 공적을 세우면 드러납니다."
                for j, line in enumerate(wrap_text(lock_desc, self.font_small, col_w - 74, max_lines=2)):
                    ds = self.font_small.render(line, True, (148, 140, 130))
                    screen.blit(ds, (cell.x + 52, cell.y + 27 + j * 14))
