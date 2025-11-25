import streamlit as st
import json
import datetime
import random
import os
import time

# --- APP CONFIGURATION ---
st.set_page_config(
    page_title="NeuroAI Quest",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS to make it look more like a mobile app
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        font-weight: bold;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    /* Hide Streamlit default menu/footer for app-feel */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- LOGIC & DATA MANAGER ---

class GameLogic:
    def __init__(self):
        self.thinking_modes = {
            "white_room": "Strip context, think abstractly",
            "recursive": "Break into sub-problems", 
            "hypothesis_driven": "Generate-test-invalidate",
            "multi_modal": "Cross-domain connections"
        }
        self.puzzles = self.load_puzzles()

    def load_player(self):
        if 'player' not in st.session_state:
            if os.path.exists('neuroai.json'):
                with open('neuroai.json', 'r') as f:
                    st.session_state.player = json.load(f)
            else:
                st.session_state.player = {
                    "name": "Apprentice", "xp": 0, "level": 1, 
                    "streak": 0, "last_play": "", "high_scores": [0]*4, 
                    "badges": [], "world_unlocks": [0]*4, "total_sessions": 0
                }

    def save_player(self):
        with open('neuroai.json', 'w') as f:
            json.dump(st.session_state.player, f, indent=2)

    def update_streak(self):
        p = st.session_state.player
        today = datetime.date.today().isoformat()
        if p["last_play"] == today:
            return
        
        try:
            last_date = datetime.date.fromisoformat(p["last_play"])
            if (datetime.date.today() - last_date).days == 1:
                p["streak"] += 1
            else:
                p["streak"] = 1
        except:
            p["streak"] = 1
        
        p["last_play"] = today
        p["total_sessions"] = p.get("total_sessions", 0) + 1
        self.save_player()

    def load_puzzles(self):
        return {
            "letters": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J'],
            "positions": ["Top-Left", "Top-Mid", "Top-Right", "Mid-Left", "Center", "Mid-Right", "Bot-Left", "Bot-Mid", "Bot-Right"],
            "scenarios": [
                "Fix a broken spaceship", "Plan a city escape", 
                "Solve world hunger", "Build AI stock predictor"
            ],
            "perspectives": ["Engineer", "Mayor", "Child", "Alien", "Chef", "Soldier"],
            "prompt_targets": [
                "Cat solving quantum physics", "Robot chef inventing fusion food", 
                "Dragon writing Python code", "Pirate AI trading crypto"
            ]
        }

    def gain_xp(self, pts, world_idx=None):
        p = st.session_state.player
        bonus = p["streak"] * 5
        total = pts + bonus
        p["xp"] += total
        
        if world_idx is not None:
            p["high_scores"][world_idx] = max(p["high_scores"][world_idx], pts)
            
        # Level Up Logic
        old_level = p["level"]
        while p["xp"] >= p["level"] * 100:
            p["level"] += 1
        
        self.save_player()
        
        msg = f"+{pts} XP (+{bonus} streak bonus)"
        if p["level"] > old_level:
            st.balloons()
            return f"{msg} | 🌟 LEVEL UP! You are Level {p['level']}!"
        return msg

# --- UI COMPONENTS ---

def draw_sidebar(logic):
    p = st.session_state.player
    with st.sidebar:
        st.title(f"👤 {p['name']}")
        st.write(f"**Level:** {p['level']}")
        st.progress(min(100, (p['xp'] % (p['level']*100)) / p['level']))
        st.write(f"**XP:** {p['xp']}")
        st.write(f"**🔥 Streak:** {p['streak']} days")
        
        st.divider()
        st.write("🏅 **Badges:**")
        if not p['badges']:
            st.caption("No badges yet.")
        for b in p['badges']:
            st.write(f"- {b}")
            
        if st.button("Reset / Main Menu"):
            st.session_state.current_view = "menu"
            st.rerun()

def view_menu(logic):
    p = st.session_state.player
    st.title("🧠 NeuroAI Quest")
    
    # Stats Header
    col1, col2, col3 = st.columns(3)
    col1.metric("Level", p['level'])
    col2.metric("XP", p['xp'])
    col3.metric("Streak", f"{p['streak']} 🔥")
    
    st.divider()
    st.subheader("Select Training Module")
    
    c1, c2 = st.columns(2)
    if c1.button("🧠 Memory\nBoost", type="primary"):
        st.session_state.current_view = "game_memory"
        st.session_state.game_state = {"step": 0, "history": [], "score": 0, "n": 2}
        st.rerun()
        
    if c2.button("🔄 Perspective\nSwitch", type="primary"):
        st.session_state.current_view = "game_perspective"
        st.session_state.game_state = {"step": 0, "score": 0}
        st.rerun()
        
    c3, c4 = st.columns(2)
    if c3.button("⚙️ Step\nLogic"):
        st.session_state.current_view = "game_logic"
        st.rerun()
        
    if c4.button("🤖 Prompt\nForge"):
        st.session_state.current_view = "game_prompt"
        st.rerun()

# --- GAME VIEWS ---

def view_memory(logic):
    st.header("🧠 Dual N-Back")
    st.caption("Does the Position or Letter match N steps ago?")
    
    gs = st.session_state.game_state
    N = gs['n']
    MAX_TRIALS = 15
    
    if gs['step'] >= MAX_TRIALS:
        # Game Over
        final_score = int((gs['score'] / (MAX_TRIALS * 5)) * 100)
        st.success(f"Training Complete! Score: {final_score}%")
        if st.button("Claim XP"):
            msg = logic.gain_xp(final_score, 0)
            st.toast(msg)
            st.session_state.current_view = "menu"
            st.rerun()
        return

    # Generate new round data if needed
    if 'current_card' not in gs:
        pos = random.randint(0, 8)
        let = random.choice(logic.puzzles['letters'])
        gs['current_card'] = {'pos': pos, 'let': let}
        
    card = gs['current_card']
    
    # Visual Grid
    grid_cols = st.columns(3)
    for i in range(9):
        with grid_cols[i % 3]:
            if i == card['pos']:
                st.markdown(f"<div style='background-color:#4CAF50;color:white;text-align:center;padding:20px;border-radius:10px;font-size:24px;'>{card['let']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background-color:#333;text-align:center;padding:20px;border-radius:10px;font-size:24px;'>&nbsp;</div>", unsafe_allow_html=True)
    
    st.write("")
    
    # Logic Checks
    has_n_back = len(gs['history']) >= N
    match_pos = has_n_back and card['pos'] == gs['history'][-N]['pos']
    match_let = has_n_back and card['let'] == gs['history'][-N]['let']
    
    with st.form("mem_form"):
        st.write(f"**Trial {gs['step']+1}/{MAX_TRIALS}** (N={N})")
        c1, c2 = st.columns(2)
        user_pos = c1.checkbox("Position Match?")
        user_let = c2.checkbox("Letter Match?")
        
        submitted = st.form_submit_button("Next Step ➡️")
        
        if submitted:
            # Score
            round_score = 0
            if user_pos == match_pos: round_score += 2.5
            if user_let == match_let: round_score += 2.5
            
            gs['score'] += round_score
            gs['history'].append(card)
            del gs['current_card'] # Clear to generate new one
            gs['step'] += 1
            st.rerun()

def view_perspective(logic):
    st.header("🔄 Perspective Switch")
    
    if 'scenario' not in st.session_state.game_state:
        st.session_state.game_state['scenario'] = random.choice(logic.puzzles['scenarios'])
        st.session_state.game_state['role'] = random.choice(logic.puzzles['perspectives'])
    
    scenario = st.session_state.game_state['scenario']
    role = st.session_state.game_state['role']
    
    st.info(f"**Scenario:** {scenario}")
    st.warning(f"**Adopt Perspective:** {role}")
    
    response = st.text_area("Analyze this scenario from this viewpoint:", height=150)
    
    if st.button("Submit Analysis"):
        if len(response) < 20:
            st.error("Too short! Think deeper.")
        else:
            score = min(100, len(response.split()) * 3)
            msg = logic.gain_xp(score, 1)
            st.balloons()
            st.success(f"Insightful! Score: {score}")
            st.toast(msg)
            time.sleep(2)
            st.session_state.current_view = "menu"
            st.rerun()

def view_prompt(logic):
    st.header("🤖 Killer Prompt Forge")
    
    if 'target' not in st.session_state.game_state:
        st.session_state.game_state['target'] = random.choice(logic.puzzles['prompt_targets'])
    
    target = st.session_state.game_state['target']
    st.info(f"**Goal:** Write a prompt to make AI generate: '{target}'")
    
    user_prompt = st.text_area("Enter your System Prompt:", height=150)
    
    if st.button("Run Simulation"):
        # Simulated Scoring Logic
        score = 0
        feedback = []
        lower_p = user_prompt.lower()
        
        if len(user_prompt) > 20: score += 20
        if "act as" in lower_p or "you are" in lower_p: 
            score += 20
            feedback.append("✅ defined role")
        if "step" in lower_p: 
            score += 20
            feedback.append("✅ step-by-step")
        if "format" in lower_p or "json" in lower_p: 
            score += 20
            feedback.append("✅ defined output format")
            
        final_score = min(100, score + 20)
        
        st.write("### Analysis")
        for f in feedback:
            st.write(f)
            
        st.progress(final_score)
        
        if final_score > 60:
            msg = logic.gain_xp(final_score, 3)
            st.success(f"Great prompt! +{final_score} XP")
            st.toast(msg)
            if st.button("Back to Menu"):
                st.session_state.current_view = "menu"
                st.rerun()
        else:
            st.error(f"Weak prompt (Score: {final_score}). Try adding roles, steps, or formats.")

# --- MAIN APP LOOP ---

def main():
    logic = GameLogic()
    logic.load_player()
    logic.update_streak()
    
    if 'current_view' not in st.session_state:
        st.session_state.current_view = "menu"
        
    # Draw Sidebar on all pages
    draw_sidebar(logic)
    
    # Router
    if st.session_state.current_view == "menu":
        view_menu(logic)
    elif st.session_state.current_view == "game_memory":
        view_memory(logic)
    elif st.session_state.current_view == "game_perspective":
        view_perspective(logic)
    elif st.session_state.current_view == "game_prompt":
        view_prompt(logic)
    elif st.session_state.current_view == "game_logic":
        st.info("Logic Module Under Construction 🚧")
        if st.button("Back"):
            st.session_state.current_view = "menu"
            st.rerun()

if __name__ == "__main__":
    main()
