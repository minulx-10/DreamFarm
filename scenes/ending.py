import os
import math
import pygame
from core.game_state import (
    append_josa, game_state, get_understanding_stage,
    get_attitude_ending, save_progress, JOURNAL_RETROSPECTIVES,
    append_ending_journal,
)
from core.assets import BLACK, WHITE, TEXT_DARK, TEXT_MUTED, get_font, sprites, draw_crop_food
from core.ui import draw_centered_lines, draw_light_panel, draw_story_backdrop, wrap_text, draw_button
from core import audio
from core.crops import current_crop, swap_crop_word


class EndingScene:
    """Enhanced ending with attitude-based branching, table scene, journal retrospective."""

    def __init__(self):
        self.font = get_font(23)
        self.font_result = get_font(42)
        self.font_small = get_font(18)
        self.font_dad = get_font(30)
        self.printed_text = ""
        self.char_idx = 0
        self.char_timer = 0
        self.char_delay = 0.065
        self.finished = False
        # 갤러리에서 특정 엔딩을 감상하려고 들어온 경우, 그 엔딩을 강제한다.
        forced = game_state.forced_ending
        game_state.forced_ending = None
        # 갤러리 감상 모드 — 이 경우 엔딩이 끝나도 새 게임을 시작하지 않고 갤러리로 돌아간다.
        self.from_gallery = bool(forced)
        if forced:
            self.crop_failed = (forced == "wither")
            self.ending_data = self.get_ending(forced)
        else:
            # 작물이 끝내 시들었으면 수확 못 한 '시듦' 엔딩으로 강제 (연출은 아래 advance에서 단축)
            self.crop_failed = game_state.crop_failed
            self.ending_data = self.get_ending("wither" if self.crop_failed else None)
        # 이 엔딩에 맞는 '마지막 장'을 일지에 한 번 더한다 (엔딩별로 닫는 글이 달라짐)
        append_ending_journal()
        self.pages = self.build_pages()
        self.page_index = 0
        self.text_to_print = self.prepare_page(self.page_index)
        # Enhanced ending phases
        self.phase = "narration"  # narration -> table -> carrot -> golden -> dad_voice -> result -> credits -> journal
        self.phase_timer = 0
        self.table_alpha = 0
        self.golden_alpha = 0
        self.dad_text_alpha = 0
        self.show_result = False
        self.result_y = 620
        self.result_done = False
        self.is_happy = False
        self.journal_scroll = 0
        self.journal_max_scroll = 0
        self.show_journal = False
        self.carrot_pulse = 0
        self.letter_written = False
        self.credit_lines = self.build_credit_lines()
        
        # 마인크래프트 credits 스크롤을 위한 별 입자 생성
        import random
        self.credits_stars = []
        for _ in range(40):
            self.credits_stars.append({
                "x": random.randint(10, 790),
                "y": random.randint(10, 590),
                "speed": random.uniform(8.0, 22.0),
                "alpha_phase": random.uniform(0, 6.28)
            })
        self.credits_y = 620

        # 엔딩 타입에 따라 BGM 분기
        self._select_ending_bgm()

    def _select_ending_bgm(self):
        """현재 엔딩(last_ending)에 맞는 배경음으로 전환. 갤러리 감상에서도 곡이 바뀌도록 분리."""
        if game_state.last_ending in ("true", "happy", "growth"):
            audio.play_bgm("ending_warm")
        elif game_state.last_ending in ("rush", "bad", "wither"):
            audio.play_bgm("ending_sad")
        else:
            audio.play_bgm("ending")

    def write_desktop_letter(self):
        try:
            desktop = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
            if not os.path.exists(desktop):
                return
            filepath = os.path.join(desktop, "아버지의_편지.txt")
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    food = current_crop()["food"]
                    f.write("아들, 밥은 먹었냐.\n")
                    f.write(swap_crop_word("바쁘다고 굶지 말고, 당근은 몸에 좋으니까 남기지 마라.\n\n", food))
                    f.write("- 아빠가")
        except Exception:
            pass

    def get_ending(self, force_type=None):
        name = game_state.player_name
        name_eun = append_josa(name, "은/는")
        ending_type = force_type or get_attitude_ending()
        game_state.last_ending = ending_type

        # Record ending in meta save data
        from core import save_system
        save_system.record_ending(ending_type)

        # 실제 플레이로 도달한 엔딩에서만 업적을 해제한다 (갤러리 감상은 제외).
        if not getattr(self, "from_gallery", False):
            from core import achievements
            achievements.on_ending(ending_type)

        endings = {
            "true": {
                "title": "진엔딩: 내일 새벽, 함께",
                "result": "True Ending",
                "text": (
                    f"수확한 당근을 베어 문 순간, 세상이 황금빛으로 물든다.\n"
                    f"아버지의 땀과 기다림이 담긴 달콤한 맛.\n"
                    f"잠에서 깬 {name_eun} 식탁 앞에 먼저 앉아 당근을 집어 먹는다.\n"
                    f"'아빠, 내일 새벽에 같이 나갈게요. 다 알려주세요.'"
                ),
            },
            "normal": {
                "title": "노멀엔딩: 조금은 알 것 같은 마음",
                "result": "Normal Ending",
                "text": (
                    f"수확한 당근을 베어 문 순간, 다정한 침묵이 밭을 감싼다.\n"
                    f"모든 것을 완전히 알지는 못하지만, 아버지가 흘린 땀방울의 가치가 마음속에 조용히 차오른다.\n"
                    f"잠에서 깬 {name_eun} 식탁의 당근을 가만히 바라보다 천천히 씹어 넘긴다.\n"
                    f"'조금은 알 것 같아요. 아빠의 그 침묵을.'"
                ),
            },
            "bad": {
                "title": "배드엔딩: 아직은 쓰기만 한 맛",
                "result": "Bad Ending",
                "text": (
                    f"수확한 당근은 너무 작았고, 성급함이 묻어 있었다.\n"
                    f"기다리는 법도, 아버지가 매일 새벽 무엇을 홀로 마주해 왔는지도 아직 와닿지 않는다.\n"
                    f"잠에서 깬 {name_eun} 식탁 앞을 말없이 스쳐 지나가며 생각한다.\n"
                    f"'아직은 쓰다. 조금 더 서 있어야 할 것 같다.'"
                ),
            },
            "wither": {
                "title": "시듦엔딩: 끝내 지켜내지 못한 밭",
                "result": "Withered...",
                "text": (
                    f"아무리 다독여도 당근은 다시 일어서지 못했다.\n"
                    f"흙만 남은 두둑을 오래 바라보았다.\n"
                    f"그래도 이 숱한 새벽이 헛되지는 않았다.\n"
                    f"아버지가 매일 무엇과 싸웠는지, 이제 조금은 안다."
                ),
            },
        }

        data = endings.get(ending_type, endings["normal"])
        self.is_happy = ending_type == "true"
        # 고른 작물에 맞춰 '당근'을 먹기 좋은 이름으로 갈아 끼운다 (조사까지)
        food = current_crop()["food"]
        if food != "당근":
            data = dict(data)
            data["text"] = swap_crop_word(data["text"], food)
        return data

    def build_pages(self):
        text_lines = self.ending_data["text"].split("\n")
        if len(text_lines) <= 2:
            return [f"[{self.ending_data['title']}]\n\n" + "\n".join(text_lines)]
        split_at = max(1, len(text_lines) // 2)
        return [
            f"[{self.ending_data['title']}]\n\n" + "\n".join(text_lines[:split_at]),
            "\n".join(text_lines[split_at:]),
        ]

    def build_credit_lines(self):
        impact_heading = "남겨진 일들" if game_state.last_ending in ("bad", "wither") else "이어진 일들"
        
        # 플레이 타임 포맷팅 (분, 초)
        m = int(game_state.play_time // 60)
        s = int(game_state.play_time % 60)
        play_time_str = f"플레이 시간: {m}분 {s}초" if m > 0 else f"플레이 시간: {s}초"

        dialogue = [
            "«어둠 속의 목소리»",
            "그가 작물을 심었구나.",
            "그래. 흙을 길들이고, 마침내 기다림의 가치를 배웠지.",
            "그는 아버지가 이 황혼 아래 무엇을 외로이 지켜왔는지 알게 되었을까?",
            "알게 되었지. 말없는 흙 아래 묻어둔 고단한 마음을.",
            swap_crop_word("그가 정성껏 당근을 한 뿌리 거두었을 때,", current_crop()["food"]),
            "그것은 단순한 양식이 아닌, 아버지의 묵묵한 세월이었다.",
            "그가 이제 꿈에서 깨어나려 하는구나.",
            "그래. 잠에서 깨어난 뒤, 식탁에 마주 앉을 날이 올 것이다.",
            "밭의 바람은 불고, 태양은 매일 새로이 떠오르니.",
            "그의 앞에 따뜻한 아침이 기다리기를.",
            "너는 아직 꿈속에 있단다.",
            "하지만 곧 깨어나겠지. 사랑하는 이의 곁에서.",
            "",
            "---------------------------------------",
            "",
        ]

        lines = dialogue + [
            "몽중농원",
            "",
            "이번 꿈에서 남은 기록",
            play_time_str,
            f"물 뿌리기: {game_state.water_count}회",
            f"잡초 뽑기: {game_state.weed_count}회",
            f"해충 잡기: {game_state.pest_count}회",
        ]

        if game_state.choice_impacts:
            lines.extend(["", impact_heading])
            for item in game_state.choice_impacts:
                lines.append(item["title"])
                lines.append(item["impact"])

        return lines

    def _credit_content_height(self):
        height = 0
        for line in self.credit_lines:
            if not line:
                height += 26
                continue
            font = self.font_result if line == "몽중농원" else self.font_small
            height += len(wrap_text(line, font, 610)) * (font.get_height() + 6)
            height += 8
        return height + 80

    def _start_credits(self):
        self.credit_lines = self.build_credit_lines()
        self.credits_y = 620
        self.phase = "credits"
        self.phase_timer = 0

    def _finish_after_credits(self):
        if game_state.journal_entries:
            self.phase = "journal"
            self.show_journal = True
        else:
            save_progress()
            # 꺼지지 않고 다시 결과 화면으로 가서 리트라이나 다른 엔딩 구경을 할 수 있게 함
            self.phase = "result"
            self.result_done = True
            self.phase_timer = 0

    def prepare_page(self, index):
        lines = []
        for paragraph in self.pages[index].split("\n"):
            if not paragraph:
                lines.append("")
            else:
                lines.extend(wrap_text(paragraph, self.font, 610))
        return "\n".join(lines)

    def advance(self):
        if not self.finished:
            self.printed_text = self.text_to_print
            self.char_idx = len(self.text_to_print)
            self.finished = True
            return

        if self.page_index < len(self.pages) - 1:
            self.page_index += 1
            self.printed_text = ""
            self.char_idx = 0
            self.finished = False
            self.text_to_print = self.prepare_page(self.page_index)
        else:
            # 시듦 엔딩은 베어 무는 연출(테이블·당근)이 없으니 바로 결과로
            self.phase = "result" if self.crop_failed else "table"
            self.phase_timer = 0

    def retry(self):
        # 갤러리에서 감상 중이었다면 새 게임을 시작하지 않고 갤러리로 돌아간다.
        if self.from_gallery:
            game_state.forced_ending = None
            game_state.current_scene = "gallery"
            return
        # #14 Save progress before retry
        save_progress()
        game_state.reset()
        game_state.current_scene = "intro"

    def change_ending(self, ending_type):
        self.crop_failed = False   # 갤러리 감상은 늘 전체 연출
        self.ending_data = self.get_ending(ending_type)
        self.pages = self.build_pages()
        self.page_index = 0
        self.text_to_print = self.prepare_page(self.page_index)
        self.phase = "narration"
        self.printed_text = ""
        self.char_idx = 0
        self.finished = False
        self.phase_timer = 0
        self.show_result = False
        self.result_done = False
        self.result_y = 620
        self.show_journal = False
        self.letter_written = False
        self.table_alpha = 0
        self.golden_alpha = 0
        self.dad_text_alpha = 0
        self.carrot_pulse = 0
        self.credit_lines = self.build_credit_lines()
        self.credits_y = 620
        self._select_ending_bgm()   # 갤러리에서 다른 엔딩을 보면 그 엔딩 BGM으로 전환

    # 엔딩 갤러리 키 (1회 클리어 이후에만 활성화 — 첫 플레이에서는 엔딩을 직접 얻어야 함)
    GALLERY_KEYS = {
        pygame.K_1: "true", pygame.K_2: "normal", pygame.K_3: "bad",
    }

    def gallery_unlocked(self):
        return game_state.is_second_run

    # 각 엔딩에 이르게 한 까닭을 한 줄로 — 결과가 '왜' 나왔는지 보여준다
    ENDING_REASONS = {
        "true": "깊은 이해와 공감, 그리고 기다림이 모두 무르익었습니다.",
        "happy": "밭을 건강하게 지켜냈고, 마음도 함께 자랐습니다.",
        "growth": "서툴러 실수했지만, 매번 다시 흙을 만졌습니다.",
        "skill": "솜씨는 좋았지만, 마음을 헤아리는 일은 아직 남았습니다.",
        "rush": "조급함이 기다림을 앞질렀습니다.",
        "normal": "조금은 알 것 같은, 그런 하루였습니다.",
        "bad": "아직은 그 마음과의 거리를 좁히지 못했습니다.",
        "wither": "끝내 밭을 지켜내지 못했지만, 그 숱한 새벽은 남았습니다.",
    }

    # 게임이 끝난 화면에서 보이는 '메인으로' 버튼 (앱을 끄지 않고 타이틀로 돌아간다)
    EXIT_BUTTON = pygame.Rect(632, 550, 146, 40)

    def _exit_visible(self):
        return self.phase == "journal" or (self.phase == "result" and self.result_done)

    def _draw_exit_button(self, screen):
        hovered = self.EXIT_BUTTON.collidepoint(pygame.mouse.get_pos())
        label = "갤러리로" if self.from_gallery else "메인으로"
        draw_button(screen, self.EXIT_BUTTON, label, self.font_small, hovered=hovered)

    def _to_title(self):
        """엔딩을 마치고 타이틀(또는 갤러리 감상 중이면 갤러리)로 돌아간다."""
        if self.from_gallery:
            game_state.forced_ending = None
            game_state.current_scene = "gallery"
            return
        save_progress()
        game_state.reset()
        game_state.current_scene = "title"

    def handle_events(self, events):
        for event in events:
            # 끝난 화면에서는 '메인으로' 버튼으로 타이틀 화면에 돌아간다 (다른 클릭 처리보다 먼저)
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and self._exit_visible() and self.EXIT_BUTTON.collidepoint(event.pos)):
                self._to_title()
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    if self.phase in ("result", "journal") or self.finished:
                        self.retry()
                        return
                elif (event.key in self.GALLERY_KEYS
                      and self.gallery_unlocked()
                      and self.phase in ("result", "journal")):
                    self.change_ending(self.GALLERY_KEYS[event.key])

            click = (event.type == pygame.MOUSEBUTTONDOWN or
                     (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE))

            if self.phase == "narration":
                if click:
                    self.advance()
            elif self.phase == "table":
                pass
            elif self.phase == "carrot":
                if click:
                    # 베어 무는 순간의 소리: 따뜻한 엔딩은 경쾌하게, 그 외엔 둔탁하게
                    audio.play("harvest" if game_state.last_ending in ("true", "happy", "growth") else "break")
                    self.phase = "golden"
                    self.phase_timer = 0
            elif self.phase == "golden":
                pass
            elif self.phase == "dad_voice":
                if click and self.phase_timer > 2.0:
                    self.phase = "result"
                    self.phase_timer = 0
            elif self.phase == "result":
                if click:
                    if self.result_done:
                        self._start_credits()
                    else:
                        # 솟아오르던 결과 글자를 한 번에 제자리에 앉힌다 (다음 프레임에 안내가 뜸)
                        self.result_y = 260
            elif self.phase == "credits":
                if click and self.phase_timer > 1.0:
                    self._finish_after_credits()
            elif self.phase == "journal":
                # 휠(또는 휠 버튼)로 스크롤 — 나가기는 좌클릭/스페이스만
                if event.type == pygame.MOUSEWHEEL:
                    self.journal_scroll = max(0, min(self.journal_max_scroll,
                                                     self.journal_scroll - event.y * 30))
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
                    delta = -30 if event.button == 4 else 30
                    self.journal_scroll = max(0, min(self.journal_max_scroll,
                                                     self.journal_scroll + delta))
                elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1) or (
                        event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE):
                    save_progress()
                    self.retry()

    def update(self, dt):
        self.carrot_pulse += dt

        if self.phase == "narration":
            if self.finished:
                return
            self.char_timer += dt
            if self.char_timer >= self.char_delay:
                self.char_timer = 0
                if self.char_idx < len(self.text_to_print):
                    self.printed_text += self.text_to_print[self.char_idx]
                    self.char_idx += 1
                    audio.type_tick(self.text_to_print[self.char_idx - 1])
                else:
                    self.finished = True

        elif self.phase == "table":
            self.phase_timer += dt
            self.table_alpha = min(255, int(self.phase_timer * 120))
            if self.phase_timer > 2.5:
                self.phase = "carrot"
                self.phase_timer = 0

        elif self.phase == "carrot":
            self.phase_timer += dt

        elif self.phase == "golden":
            self.phase_timer += dt
            self.golden_alpha = min(255, int(self.phase_timer * 200))
            if self.phase_timer > 1.8:
                self.phase = "dad_voice"
                self.phase_timer = 0

        elif self.phase == "dad_voice":
            self.phase_timer += dt
            self.dad_text_alpha = min(255, int(self.phase_timer * 150))

        elif self.phase == "result":
            self.phase_timer += dt
            if self.result_y > 260:
                self.result_y -= 55 * dt
            else:
                self.result_y = 260
                self.result_done = True
                if self.is_happy and not self.letter_written:
                    self.write_desktop_letter()
                    self.letter_written = True

        elif self.phase == "credits":
            self.phase_timer += dt
            self.credits_y -= 26 * dt
            import random
            for star in self.credits_stars:
                star["y"] += star["speed"] * dt
                star["alpha_phase"] += 1.5 * dt
                if star["y"] > 600:
                    star["y"] = 0
                    star["x"] = random.randint(10, 790)
            if self.credits_y + self._credit_content_height() < 84:
                self._finish_after_credits()

    def draw(self, screen):
        if self.phase == "narration":
            self._draw_narration(screen)
        elif self.phase == "table":
            self._draw_table(screen)
        elif self.phase == "carrot":
            self._draw_carrot_click(screen)
        elif self.phase == "golden":
            self._draw_golden(screen)
        elif self.phase == "dad_voice":
            self._draw_dad_voice(screen)
        elif self.phase == "result":
            self._draw_result(screen)
        elif self.phase == "credits":
            self._draw_credits(screen)
        elif self.phase == "journal":
            self._draw_journal(screen)

    def _draw_narration(self, screen):
        draw_story_backdrop(screen, "night")
        dad = sprites["dad"]
        shadow = dad.copy()
        shadow.set_alpha(80)
        screen.blit(shadow, (400 - dad.get_width() // 2 + 5, 55))
        screen.blit(dad, (400 - dad.get_width() // 2, 50))
        box_rect = pygame.Rect(58, 286, 684, 256)
        draw_light_panel(screen, box_rect)
        draw_centered_lines(screen, self.printed_text.split("\n"), self.font, TEXT_DARK, 400, 318, line_gap=5)
        page = self.font_small.render(f"{self.page_index + 1}/{len(self.pages)}", True, TEXT_MUTED)
        screen.blit(page, (690, 548))
        if self.finished:
            prompt_text = "다음으로" if self.page_index < len(self.pages) - 1 else "계속"
            prompt = self.font_small.render(f"{prompt_text}: 클릭 또는 스페이스바", True, TEXT_MUTED)
            screen.blit(prompt, (400 - prompt.get_width() // 2, 562))

    def _draw_plate(self, screen, cx, cy, tc=255):
        """우묵한 백자 그릇 — 측벽 두께, 우묵한 안면, 청자색 띠, 림 광택으로 입체감."""
        def c(*v):
            return tuple(min(tc, x) for x in v)
        pw, ph = 138, 60
        x, y = cx - pw // 2, cy - ph // 2
        # 바닥 그림자
        sh = pygame.Surface((pw + 18, ph + 18), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, min(95, tc)), (0, 0, pw + 14, ph + 14))
        screen.blit(sh, (x - 7, y + 10))
        # 측벽(두께) — 살짝 아래로 깐 어두운 타원
        pygame.draw.ellipse(screen, c(196, 187, 170), (x, y + 8, pw, ph))
        # 윗면(림)
        pygame.draw.ellipse(screen, c(239, 234, 222), (x, y, pw, ph))
        # 가는 청자색 띠
        pygame.draw.ellipse(screen, c(150, 176, 173), (x + 10, y + 4, pw - 20, ph - 8), 1)
        # 우묵한 안면
        iw, ih = pw - 40, ph - 24
        ix, iy = cx - iw // 2, cy - ih // 2
        pygame.draw.ellipse(screen, c(212, 205, 189), (ix, iy, iw, ih))
        # 윗 림 광택(위쪽 호) + 안쪽 바닥 그늘(아래쪽 호)
        pygame.draw.arc(screen, c(253, 250, 241), (x + 8, y + 1, pw - 16, ph), 0.45, 2.7, 3)
        pygame.draw.arc(screen, c(178, 169, 152), (ix, iy + 1, iw, ih), 3.5, 6.0, 3)

    def _draw_chopsticks(self, screen, tc=255):
        """끝으로 갈수록 가늘어지는 나무젓가락 — 그릇 오른쪽에 자연스레 걸쳐 둠."""
        def c(*v):
            return tuple(min(tc, x) for x in v)

        def taper(ax, ay, bx, by, wa, wb):
            dx, dy = bx - ax, by - ay
            L = math.hypot(dx, dy) or 1
            px, py = -dy / L, dx / L
            return [(ax + px * wa, ay + py * wa), (bx + px * wb, by + py * wb),
                    (bx - px * wb, by - py * wb), (ax - px * wa, ay - py * wa)]

        # 받침(작은 그림자 덩이)
        pygame.draw.ellipse(screen, c(120, 86, 50), (566, 372, 30, 9))
        for (hx, hy), (tx, ty) in (((602, 344), (505, 360)), ((606, 354), (509, 370))):
            pygame.draw.polygon(screen, c(96, 64, 36), taper(hx, hy + 4, tx, ty + 4, 3.2, 1.2))  # 그림자
            pygame.draw.polygon(screen, c(156, 116, 70), taper(hx, hy, tx, ty, 3.4, 1.1))         # 몸통
            pygame.draw.polygon(screen, c(198, 160, 108), taper(hx, hy - 1, tx, ty - 1, 1.3, 0.4))  # 윗 광택
            pygame.draw.circle(screen, c(118, 82, 46), (int(tx), int(ty)), 2)                      # 짙은 끝

    def _draw_dining_table(self, screen, tc=255):
        """나무 식탁 — 빛 받는 윗 모서리 + 어두운 앞면 + 판자 이음·나뭇결로 입체감."""
        def c(*v):
            return tuple(min(tc, x) for x in v)
        front = pygame.Rect(100, 358, 600, 150)
        pygame.draw.rect(screen, c(150, 104, 62), front)                 # 앞면
        for px in (244, 400, 556):                                       # 세로 판자 이음
            pygame.draw.line(screen, c(120, 82, 48), (px, 362), (px, 504), 2)
        for gy in (398, 438, 476):                                       # 가로 나뭇결
            pygame.draw.line(screen, c(134, 92, 54), (110, gy), (690, gy), 1)
        pygame.draw.rect(screen, c(118, 80, 46), (96, 350, 608, 14))     # 윗면 그늘 단
        pygame.draw.rect(screen, c(192, 142, 90), (96, 348, 608, 9))     # 윗면 (빛 받는 밝은 띠)
        pygame.draw.line(screen, c(216, 168, 112), (100, 350), (700, 350), 2)  # 윗 모서리 광택
        pygame.draw.rect(screen, c(94, 62, 38), front, 3)               # 앞면 테두리

    def _draw_table(self, screen):
        # 몽환적인 밤하늘을 기저 배경으로 그리고 은은한 어둠 틴트 얹기
        draw_story_backdrop(screen, "night")
        dark_overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
        dark_overlay.fill((15, 10, 5, 140))
        screen.blit(dark_overlay, (0, 0))

        tc = min(255, self.table_alpha)

        # 은은한 등불 조명 (Radial Warm Glow)
        if tc > 50:
            glow_surf = pygame.Surface((340, 340), pygame.SRCALPHA)
            for r in range(160, 0, -8):
                alpha = int(45 * (1.0 - r / 160.0) * (tc / 255.0))
                pygame.draw.circle(glow_surf, (255, 210, 120, alpha), (170, 170), r)
            screen.blit(glow_surf, (400 - 170, 320 - 170))

        if self.table_alpha > 50:

            # 1. 나무 식탁
            self._draw_dining_table(screen, tc)

            # 2. 그릇 (입체 백자)
            self._draw_plate(screen, 400, 345, tc)

            # 3. 그릇에 담긴 반찬/음식 조각들 (안면 가운데)
            if tc > 120:
                crop_key = game_state.crop
                if crop_key == "apple":
                    # 사과: 붉은 사과 껍질이 살짝 보이는 초승달 모양 슬라이스들
                    # 사과 조각 1
                    pts1 = [(378, 348), (395, 340), (410, 348), (392, 355)]
                    pygame.draw.polygon(screen, (min(tc, 245), min(tc, 235), min(tc, 215)), pts1)
                    pygame.draw.arc(screen, (min(tc, 190), min(tc, 30), min(tc, 30)), (376, 338, 36, 18), 3.14, 6.28, 2)
                    # 사과 조각 2
                    pts2 = [(398, 342), (415, 334), (430, 342), (412, 349)]
                    pygame.draw.polygon(screen, (min(tc, 245), min(tc, 235), min(tc, 215)), pts2)
                    pygame.draw.arc(screen, (min(tc, 190), min(tc, 30), min(tc, 30)), (396, 332, 36, 18), 3.14, 6.28, 2)
                elif crop_key == "potato":
                    # 감자: 둥글고 파근파근한 찐감자 덩어리들 (연노랑/베이지)
                    chunks = [
                        ([(376, 349), (390, 342), (398, 350), (384, 356)], (230, 205, 150), (160, 120, 80)),
                        ([(394, 344), (412, 338), (418, 346), (402, 351)], (235, 212, 160), (165, 125, 85)),
                        ([(414, 351), (428, 345), (434, 353), (420, 358)], (225, 200, 145), (155, 115, 75)),
                    ]
                    for pts, fill, edge in chunks:
                        pygame.draw.polygon(screen, (min(tc, fill[0]), min(tc, fill[1]), min(tc, fill[2])), pts)
                        pygame.draw.polygon(screen, (min(tc, edge[0]), min(tc, edge[1]), min(tc, edge[2])), pts, 1)
                elif crop_key == "rice":
                    # 쌀밥: 그릇 위에 봉긋하게 솟아오른 소복한 흰 쌀밥 heap
                    pygame.draw.ellipse(screen, (min(tc, 248), min(tc, 246), min(tc, 240)), (360, 322, 80, 32))
                    pygame.draw.ellipse(screen, (min(tc, 255), min(tc, 255), min(tc, 255)), (370, 314, 60, 28))
                    for gx, gy in [(375, 330), (390, 322), (410, 325), (425, 332), (395, 334)]:
                        pygame.draw.ellipse(screen, (min(tc, 240), min(tc, 238), min(tc, 230)), (gx, gy, 4, 3))
                    # 사기 대접의 그릇 외벽을 그려 대접 안에 소복이 쌓인 모양으로 완성
                    bowl = pygame.Rect(356, 330, 88, 38)
                    pygame.draw.arc(screen, (min(tc, 208), min(tc, 214), min(tc, 224)), bowl, 3.30, 6.12, 5)
                    pygame.draw.arc(screen, (min(tc, 150), min(tc, 176), min(tc, 190)), bowl, 3.30, 6.12, 2)
                else:
                    # 당근 반찬
                    chunks = [
                        ([(376, 348), (392, 342), (396, 352), (380, 356)], (245, 125, 30), (205, 85, 15)),
                        ([(396, 341), (414, 337), (418, 347), (400, 351)], (255, 140, 40), (215, 95, 20)),
                        ([(416, 350), (432, 344), (438, 354), (422, 358)], (235, 115, 25), (195, 75, 10)),
                    ]
                    for pts, fill, edge in chunks:
                        pygame.draw.polygon(screen, (min(tc, fill[0]), min(tc, fill[1]), min(tc, fill[2])), pts)
                        pygame.draw.polygon(screen, (min(tc, edge[0]), min(tc, edge[1]), min(tc, edge[2])), pts, 1)
                    pygame.draw.circle(screen, (min(tc, 255), min(tc, 255), min(tc, 255)), (388, 346), 1)
                    pygame.draw.circle(screen, (min(tc, 255), min(tc, 255), min(tc, 255)), (408, 342), 1)

            # 4. 젓가락
            if tc > 150:
                self._draw_chopsticks(screen, tc)

    def _draw_carrot_click(self, screen):
        # 몽환적인 밤하늘을 기저 배경으로 그리고 은은한 어둠 틴트 얹기
        draw_story_backdrop(screen, "night")
        dark_overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
        dark_overlay.fill((15, 10, 5, 140))
        screen.blit(dark_overlay, (0, 0))

        # 은은한 등불 조명 (Radial Warm Glow)
        glow_surf = pygame.Surface((340, 340), pygame.SRCALPHA)
        for r in range(160, 0, -8):
            alpha = int(45 * (1.0 - r / 160.0))
            pygame.draw.circle(glow_surf, (255, 210, 120, alpha), (170, 170), r)
        screen.blit(glow_surf, (400 - 170, 320 - 170))
        
        # 1. 나무 식탁
        self._draw_dining_table(screen)

        # 2. 그릇 (입체 백자)
        self._draw_plate(screen, 400, 345)

        # 3. Golden Dream Sparkle Particles around the carrot
        import random
        import math
        random.seed(42) # 고정된 위치에 반짝이 배치
        for i in range(8):
            angle = i * (2 * math.pi / 8) + self.carrot_pulse * 1.5
            dist = 42 + 8 * math.sin(self.carrot_pulse * 4 + i)
            px = int(400 + dist * math.cos(angle))
            py = int(270 + dist * math.sin(angle) * 0.7)
            size = max(2, int(4 + 2 * math.sin(self.carrot_pulse * 5 + i)))
            alpha = int(150 + 100 * math.sin(self.carrot_pulse * 6 + i))
            
            sparkle = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(sparkle, (255, 235, 140, alpha), (size, size), size)
            screen.blit(sparkle, (px - size, py - size))

        # 4. 작물별 먹거리를 접시 위에 맥동시키며 그린다 (당근=스프라이트, 그 외=고유 도형)
        crop = current_crop()
        pulse = 1.0 + 0.06 * math.sin(self.carrot_pulse * 3)
        if game_state.crop == "carrot":
            carrot = sprites["carrot"]
            cw = int(carrot.get_width() * pulse)
            ch = int(carrot.get_height() * pulse)
            scaled = pygame.transform.scale(carrot, (cw, ch))
            screen.blit(scaled, (400 - cw // 2, 344 - ch))
        else:
            draw_crop_food(screen, 400, 315, game_state.crop, r=int(30 * pulse))

        # Prompt (조사 자동 처리: 사과를 / 감자를 / 쌀밥을 / 당근을)
        prompt = self.font_small.render(f"{append_josa(crop['food'], '을/를')} 클릭하세요", True, (255, 225, 130))
        screen.blit(prompt, (400 - prompt.get_width() // 2, 430))

    def _draw_golden(self, screen):
        g = self.golden_alpha
        ending = game_state.last_ending
        
        crop = game_state.crop
        if ending in ("true", "happy"):
            # Golden glow
            sound = "아삭."
            if crop == "rice":
                sound = "냠냠."
            elif crop == "potato":
                sound = "포슬."
            screen.fill((min(255, g), min(200, int(g * 0.78)), min(80, int(g * 0.3))))
            if g > 200:
                t = self.font.render(sound, True, WHITE)
                screen.blit(t, (400 - t.get_width() // 2, 290))
        elif ending == "growth":
            # Warm brown glow
            sound = "오도독."
            if crop == "rice":
                sound = "냠냠."
            elif crop == "potato":
                sound = "서걱."
            screen.fill((min(200, int(g*0.8)), min(150, int(g * 0.6)), min(100, int(g * 0.4))))
            if g > 200:
                t = self.font.render(sound, True, WHITE)
                screen.blit(t, (400 - t.get_width() // 2, 290))
        elif ending == "skill":
            # Cold white glow
            sound = "사각."
            if crop == "rice":
                sound = "우물."
            elif crop == "potato":
                sound = "스근."
            screen.fill((min(240, g), min(240, g), min(255, g)))
            if g > 200:
                t = self.font.render(sound, True, (100, 100, 100))
                screen.blit(t, (400 - t.get_width() // 2, 290))
        elif ending == "rush":
            # Fast red flash
            sound = "우적."
            if crop == "rice":
                sound = "쩝쩝."
            elif crop == "potato":
                sound = "우물."
            screen.fill((min(200, g), min(50, int(g*0.2)), min(50, int(g*0.2))))
            if g > 200:
                t = self.font.render(sound, True, WHITE)
                screen.blit(t, (400 - t.get_width() // 2, 290))
        elif ending == "normal":
            # Dim yellow
            sound = "사각."
            if crop == "rice":
                sound = "우물."
            elif crop == "potato":
                sound = "스근."
            screen.fill((min(150, int(g*0.6)), min(150, int(g*0.6)), min(100, int(g*0.4))))
            if g > 200:
                t = self.font.render(sound, True, WHITE)
                screen.blit(t, (400 - t.get_width() // 2, 290))
        else: # bad
            # Fade to gray
            screen.fill((min(80, int(g*0.3)), min(80, int(g*0.3)), min(80, int(g*0.3))))
            if g > 200:
                t = self.font.render("......", True, (150, 150, 150))
                screen.blit(t, (400 - t.get_width() // 2, 290))

    def _draw_dad_voice(self, screen):
        ending = game_state.last_ending
        a = self.dad_text_alpha
        
        if ending in ("true", "happy"):
            screen.fill((255, 200, 80))
            color = (min(a, 80), min(a, 50), min(a, 20))
            text = "...내일 새벽, 같이 가자." if ending == "true" else "...맛있냐?"
        elif ending == "growth":
            screen.fill((200, 150, 100))
            color = (min(a, 60), min(a, 40), min(a, 20))
            text = "...많이 컸네."
        elif ending == "skill":
            screen.fill((240, 240, 255))
            color = (min(a, 100), min(a, 100), min(a, 120))
            text = "...농사는 잘 지었구나. 그런데..."
        elif ending == "rush":
            screen.fill((200, 50, 50))
            color = (min(a, 255), min(a, 200), min(a, 200))
            text = "...급할 거 없다."
        elif ending == "normal":
            screen.fill((150, 150, 100))
            color = (min(a, 50), min(a, 50), min(a, 30))
            text = "...천천히 무라."
        else:
            screen.fill((80, 80, 80))
            color = (min(a, 150), min(a, 150), min(a, 150))
            text = "...그래."

        t = self.font_dad.render(text, True, color)
        screen.blit(t, (400 - t.get_width() // 2, 270))
        if self.phase_timer > 2.0:
            prompt = self.font_small.render("계속하려면 클릭하세요", True, color)
            screen.blit(prompt, (400 - prompt.get_width() // 2, 450))

    def _draw_result(self, screen):
        draw_story_backdrop(screen, "night")
        result_text = self.ending_data["result"]
        color = (255, 225, 130) if self.is_happy else (180, 180, 180)
        result = self.font_result.render(result_text, True, color)
        screen.blit(result, (400 - result.get_width() // 2, int(self.result_y)))

        _, stage_name, _ = get_understanding_stage(game_state.understanding)
        stage_surf = self.font_small.render(f"마음의 단계: {stage_name}", True, (160, 150, 120))
        screen.blit(stage_surf, (400 - stage_surf.get_width() // 2, int(self.result_y) + 60))

        # #11 Attitude summary
        att_font = get_font(14)
        att_y = int(self.result_y) + 90
        att_items = []
        if game_state.patience_score >= 3:
            att_items.append("인내")
        if game_state.care_score >= 3:
            att_items.append("세심함")
        if game_state.empathy_choices >= 2:
            att_items.append("공감")
        if game_state.recovery_count >= 2:
            att_items.append("회복력")
        if att_items:
            att_text = "당신의 태도: " + " · ".join(att_items)
            att_surf = att_font.render(att_text, True, (140, 130, 100))
            screen.blit(att_surf, (400 - att_surf.get_width() // 2, att_y))

        # 이 엔딩에 이른 까닭 한 줄
        reason = self.ENDING_REASONS.get(game_state.last_ending, "")
        if reason:
            reason_surf = att_font.render(reason, True, (158, 146, 116))
            screen.blit(reason_surf, (400 - reason_surf.get_width() // 2, att_y + 24))

        if self.result_done:
            cont = self.font_small.render("계속하려면 클릭하거나 스페이스바를 누르세요", True, (208, 198, 170))
            screen.blit(cont, (400 - cont.get_width() // 2, 516))
            sub = "R: 처음부터 다시"
            if self.gallery_unlocked():
                sub += "      1~7: 다른 엔딩 다시 보기"
            sub_surf = att_font.render(sub, True, (140, 134, 116))
            screen.blit(sub_surf, (400 - sub_surf.get_width() // 2, 548))
            self._draw_exit_button(screen)

    def _draw_credits(self, screen):
        screen.fill((10, 10, 15))
        
        # twinkling stars 그리기
        for star in self.credits_stars:
            a = int(140 + 115 * math.sin(star["alpha_phase"]))
            a = max(0, min(255, a))
            s = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(s, (220, 235, 255, a), (2, 2), 2)
            screen.blit(s, (int(star["x"]), int(star["y"])))
            
        y = self.credits_y
        for line in self.credit_lines:
            if not line:
                y += 26
                continue

            is_title = line == "몽중농원"
            is_section = line in ("이번 꿈에서 남은 기록", "남겨진 일들", "이어진 일들")
            is_narrator = line == "«어둠 속의 목소리»"
            
            if is_narrator:
                font = self.font
                color = (255, 215, 0)
            elif line in (
                "그가 작물을 심었구나.",
                "그는 아버지가 이 황혼 아래 무엇을 외로이 지켜왔는지 알게 되었을까?",
                "그가 정성껏 당근을 한 뿌리 거두었을 때,",
                "그가 이제 꿈에서 깨어나려 하는구나.",
                "너는 아직 꿈속에 있단다."
            ):
                font = self.font
                color = (154, 219, 149)
            elif line in (
                "그래. 흙을 길들이고, 마침내 기다림의 가치를 배웠지.",
                "알게 되었지. 말없는 흙 아래 묻어둔 고단한 마음을.",
                "그것은 단순한 양식이 아닌, 아버지의 묵묵한 세월이었다.",
                "그래. 잠에서 깨어난 뒤, 식탁에 마주 앉을 날이 올 것이다.",
                "밭의 바람은 불고, 태양은 매일 새로이 떠오르니.",
                "그의 앞에 따뜻한 아침이 기다리기를.",
                "하지만 곧 깨어나겠지. 사랑하는 이의 곁에서."
            ):
                font = self.font
                color = (142, 196, 237)
            else:
                font = self.font_result if is_title else self.font if is_section else self.font_small
                color = (255, 226, 150) if is_title else (232, 205, 156) if is_section else (226, 220, 198)

            max_width = 620 if not is_title else 760

            for wrapped in wrap_text(line, font, max_width):
                surf = font.render(wrapped, True, color)
                screen.blit(surf, (400 - surf.get_width() // 2, int(y)))
                y += font.get_height() + 6
            y += 8 if is_section else 4

        if self.phase_timer > 1.0:
            # 흐르는 크레딧 글자와 겹치지 않도록 오른쪽 아래 구석에 어두운 알약을 깔고 얹는다.
            prompt = self.font_small.render("클릭·스페이스바 ▸ 넘기기", True, (222, 216, 196))
            pad = 9
            box = pygame.Rect(0, 0, prompt.get_width() + pad * 2, prompt.get_height() + pad * 2)
            box.bottomright = (786, 588)
            bg = pygame.Surface((box.w, box.h), pygame.SRCALPHA)
            bg.fill((10, 10, 15, 205))
            pygame.draw.rect(bg, (60, 58, 50, 220), bg.get_rect(), 1, border_radius=8)
            screen.blit(bg, box.topleft)
            screen.blit(prompt, (box.x + pad, box.y + pad))

    def _draw_journal(self, screen):
        draw_story_backdrop(screen, "night")
        panel = pygame.Rect(70, 36, 660, 514)
        draw_light_panel(screen, panel)
        title = self.font.render("밭일 일지", True, TEXT_DARK)
        screen.blit(title, (400 - title.get_width() // 2, 64))
        pygame.draw.line(screen, (180, 141, 82), (120, 98), (680, 98), 2)

        retro_font = get_font(14)
        head_color = (150, 110, 60)
        # 스크롤 보이는 영역(클리핑) — 전체 일지를 휠로 넘겨 읽는다
        view = pygame.Rect(100, 108, 600, 404)
        prev_clip = screen.get_clip()
        screen.set_clip(view)
        start_y = 116 - self.journal_scroll
        y = start_y
        for entry in game_state.journal_entries:
            for line in entry.split("\n"):
                is_head = line.startswith("[")
                if view.top - 30 < y < view.bottom + 4:   # 보이는 범위만 그림
                    surf = self.font_small.render(line, True, head_color if is_head else TEXT_DARK)
                    screen.blit(surf, (120, y))
                y += 26 if is_head else 22
                if self.is_happy and line.strip() in JOURNAL_RETROSPECTIVES:
                    if view.top - 30 < y < view.bottom + 4:
                        rs = retro_font.render(JOURNAL_RETROSPECTIVES[line.strip()], True, TEXT_MUTED)
                        screen.blit(rs, (140, y))
                    y += 18
            y += 12
        screen.set_clip(prev_clip)

        # 스크롤 가능 범위 갱신(다음 입력에서 클램프에 사용)
        content_h = y - start_y
        self.journal_max_scroll = max(0, content_h - view.height + 12)
        if self.journal_scroll > self.journal_max_scroll:
            self.journal_scroll = self.journal_max_scroll
        if self.journal_max_scroll > 0:
            sh = retro_font.render("휠로 스크롤", True, (172, 152, 112))
            screen.blit(sh, (672 - sh.get_width(), 110))

        prompt = self.font_small.render("스페이스바 또는 클릭 ▸ 처음 화면으로", True, (214, 204, 178))
        screen.blit(prompt, (400 - prompt.get_width() // 2, 554))
        if self.gallery_unlocked():
            g = get_font(14).render("1~7: 다른 엔딩 다시 보기", True, (150, 143, 122))
            screen.blit(g, (400 - g.get_width() // 2, 578))
        self._draw_exit_button(screen)
