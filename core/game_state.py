class GameState:
    def __init__(self):
        self.player_name = "지후"
        self.understanding = 0
        self.score = 0
        self.timer = 0
        self.current_scene = "name_input"
        self.running = True
        
        self.transition_text = ""
        self.transition_next = ""
        self.is_clear_transition = False
        self.return_scene = "farm"

game_state = GameState()

def append_josa(text, josa_type):
    if not text: return text
    last_char = text[-1]
    if ord('가') <= ord(last_char) <= ord('힣'):
        has_batchim = (ord(last_char) - ord('가')) % 28 > 0
        if josa_type == "은/는": return text + ("은" if has_batchim else "는")
        if josa_type == "이/가": return text + ("이" if has_batchim else "가")
        if josa_type == "을/를": return text + ("을" if has_batchim else "를")
    
    if josa_type == "은/는": return text + "는(은)"
    if josa_type == "이/가": return text + "가(이)"
    if josa_type == "을/를": return text + "를(을)"
    return text
