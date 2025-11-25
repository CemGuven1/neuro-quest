import streamlit as st
import json
import datetime
import random
import os
import time
import pandas as pd
import uuid

# --- Page Configuration ---
st.set_page_config(
    page_title="NeuroAI Quest",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for App-like Feel ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #4A90E2;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #50E3C2;
        margin-top: 1rem;
    }
    .stat-card {
        background-color: #262730;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .big-number {
        font-size: 2rem;
        font-weight: bold;
        color: #FFD700;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- Game Data & Logic Classes ---

class GameLogic:
    def __init__(self):
        self.puzzles = self.load_puzzles()
        self.thinking_modes = {
            "white_room": "Strip context, think abstractly",
            "recursive": "Break into sub-problems", 
            "hypothesis_driven": "Generate-test-invalidate",
            "multi_modal": "Cross-domain connections"
        }

    def load_puzzles(self):
        return {
            "memory_items": ['apple', 'book', 'hat', 'key', 'flower', 'car', 'dog', 'tree', 'phone', 'lamp'],
            "positions": ["1 (top-left)", "2", "3 (top-right)", "4 (mid-left)", "5", "6 (mid-right)", "7 (bot-left)", "8", "9 (bot-right)"],
            "letters": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J'],
            "scenarios": [
                "Fix a broken spaceship", 
                "Plan a city escape from zombies", 
                "Solve world hunger in 1 day", 
                "Build AI to predict stocks",
                "Design a city for 10 million people",
                "Create peace between warring nations"
            ],
            "perspectives": ["Engineer", "Mayor", "Child", "Alien", "Chef", "Soldier", "Artist", "Scientist", "CEO", "Farmer"],
            "riddles": [
                ("3 switches, 1 light. Label truth/lie/random. Find safe.", ["test", "label", "swap", "on", "off", "wait"]),
                ("River: wolf, goat, cabbage. Cross all safe.", ["goat first", "back", "wolf", "cabbage", "return"]),
                ("9 dots, 4 lines no lift.", ["extend", "outside", "box", "diagonal", "think"]),
                ("2 guards: truth/lie. One door to freedom.", ["ask", "other", "door", "would", "say"]),
                ("Poison wine among 1000 bottles. 10 testers.", ["binary", "test", "bottles", "combination", "days"])
            ],
            "prompt_targets": [
                "Cat solving quantum physics", 
                "Robot chef inventing fusion food", 
                "Dragon writing Python code", 
                "Pirate AI trading crypto",
                "Ant colony building quantum computer",
                "Time-traveler explaining TikTok to Shakespeare"
            ],
            "prompt_bonuses": ['step', 'chain', 'role', 'example', 'context', 'detail', 'as if', 'few-shot', 'iterate', 'specific', 'format', 'table', 'json', 'outline'],
            "abstraction_levels": ["Literal/Concrete", "Functional/Practical", "System/Network", "Metaphorical/Analogical", "Fundamental/Philosophical"]
        }

    def evaluate_prompt_advanced(self, prompt, target):
        scores = {
            "abstraction": 0, "systematicity": 0, "constraint_clarity": 0,
            "role_specificity": 0, "output_format": 0, "creativity_bonus": 0
        }
        prompt_lower = prompt.lower()
        if any(word in prompt_lower for word in ['step', 'first', 'then', 'next', 'finally']): scores["systematicity"] += 20
        if 'chain of thought' in prompt_lower: scores["systematicity"] += 10
        if any(phrase in prompt_lower for phrase in ['as a', 'act as', 'you are']): scores["role_specificity"] += 20
        if any(role in prompt_lower for role in ['expert', 'specialist', 'consultant']): scores["role_specificity"] += 10
        if any(word in prompt_lower for word in ['table', 'format', 'json', 'outline', 'bullet']): scores["output_format"] += 20
        if 'structure' in prompt_lower: scores["output_format"] += 10
        if any(word in prompt_lower for word in ['constraint', 'limit', 'within', 'boundary']): scores["constraint_clarity"] += 15
        if any(word in prompt_lower for word in ['fundamental', 'core principle', 'abstract', 'essence']): scores["abstraction"] += 20
        unusual_approaches = ['metaphor', 'analogy', 'unconventional', 'creative', 'innovative']
        if any(approach in prompt_lower for approach in unusual_approaches): scores["creativity_bonus"] += 15
        word_count = len(prompt.split())
        if word_count > 30: scores["creativity_bonus"] += min(10, (word_count - 30) // 3)
        return min(150, sum(scores.values())), scores

# --- State Management Helper Functions ---

def get_user_id():
    """Get or generate a unique user ID for this session."""
    if 'user_id' not in st.session_state:
        # Generate a unique ID for this browser session
        # This persists for the duration of the Streamlit session
        user_id = str(uuid.uuid4())[:16]
        st.session_state.user_id = user_id
    return st.session_state.user_id

def get_player_file_path(user_id=None):
    """Get the file path for this user's save data."""
    if user_id is None:
        user_id = get_user_id()
    # Create a saves directory to keep things organized
    saves_dir = 'saves'
    if not os.path.exists(saves_dir):
        os.makedirs(saves_dir)
    return os.path.join(saves_dir, f'neuroai_{user_id}.json')

def load_player():
    """Load player data from user-specific file."""
    if 'player' not in st.session_state:
        user_id = get_user_id()
        file_path = get_player_file_path(user_id)
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    p = json.load(f)
                    p['last_play'] = p.get('last_play', '')
                    st.session_state.player = p
            except Exception as e:
                # If file is corrupted, start fresh
                st.warning("⚠️ Could not load previous save. Starting fresh!")
                st.session_state.player = create_new_player()
                st.session_state.player['user_id'] = user_id
        else:
            st.session_state.player = create_new_player()
            st.session_state.player['user_id'] = user_id

def create_new_player():
    """Create a new player profile."""
    return {
        "name": "AI Apprentice",
        "xp": 0, "level": 1, "streak": 0, "last_play": "",
        "high_scores": [0]*4, "badges": [], "world_unlocks": [0]*4,
        "total_sessions": 0
    }

def save_player():
    """Save player data to user-specific file."""
    file_path = get_player_file_path()
    try:
        with open(file_path, 'w') as f:
            json.dump(st.session_state.player, f, indent=2)
    except Exception as e:
        st.error(f"⚠️ Could not save progress: {e}")

def update_streak():
    player = st.session_state.player
    today = datetime.date.today().isoformat()
    if player["last_play"] == today:
        return
    try:
        last_date = datetime.date.fromisoformat(player["last_play"])
        if (datetime.date.today() - last_date).days == 1:
            player["streak"] += 1
            st.toast(f"🔥 Streak extended to {player['streak']} days!")
        else:
            player["streak"] = 1
    except:
        player["streak"] = 1
    player["last_play"] = today
    player["total_sessions"] = player.get("total_sessions", 0) + 1
    save_player()

def gain_xp(pts, world_idx=None):
    player = st.session_state.player
    bonus = player["streak"] * 10
    total = pts + bonus
    player["xp"] += total
    
    if world_idx is not None:
        player["high_scores"][world_idx] = max(player["high_scores"][world_idx], pts)
    
    # Simple Logic: Every 100 XP is a level. 
    # Current Level 1: 0-99. Level 2: 100-199.
    old_level = player["level"]
    while player["xp"] >= player["level"] * 100:
        player["level"] += 1
    
    if player["level"] > old_level:
        st.balloons()
        st.success(f"🌟 LEVEL UP! You are now Level {player['level']}!")
        if player["level"] % 5 == 0:
            award_badge(f"Level {player['level']} Master")
            
    save_player()
    return total

def award_badge(badge):
    if badge not in st.session_state.player["badges"]:
        st.session_state.player["badges"].append(badge)
        st.session_state.player["xp"] += 50
        st.toast(f"🎖️ BADGE UNLOCKED: {badge}", icon="🎖️")
        save_player()

# --- Initialization ---
if 'game_logic' not in st.session_state:
    st.session_state.game_logic = GameLogic()

load_player()
# Ensure persistence across re-runs for game states
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'menu'
if 'game_state' not in st.session_state:
    st.session_state.game_state = {} 

update_streak()
logic = st.session_state.game_logic
player = st.session_state.player

# --- Sidebar ---
with st.sidebar:
    st.title(f"👤 {player['name']}")
    
    # Username editor
    with st.expander("✏️ Change Name"):
        new_name = st.text_input("Your Name", value=player['name'], key="name_input")
        if st.button("Update Name"):
            player['name'] = new_name if new_name.strip() else "AI Apprentice"
            save_player()
            st.success("Name updated!")
            st.rerun()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Level", player['level'])
    with col2:
        st.metric("Streak", f"{player['streak']}🔥")
    
    # FIX: Correct logic for progress bar to be 0.0 - 1.0
    # Level 1 starts at 0 XP. Level 2 starts at 100 XP. Level 3 at 200 XP.
    # Formula: (Current XP - Previous Level Threshold) / 100
    current_level_start_xp = (player['level'] - 1) * 100
    xp_in_level = player['xp'] - current_level_start_xp
    # Ensure it's between 0.0 and 1.0, avoiding > 1.0 crashes
    progress_val = max(0.0, min(1.0, xp_in_level / 100.0))
    
    st.progress(progress_val, text=f"XP: {player['xp']}")
    
    st.divider()
    st.markdown("### 🏆 Mastery")
    df_stats = pd.DataFrame({
        "Skill": ["Memory", "Perspective", "Logic", "Prompt"],
        "Level": [x + 1 for x in player["world_unlocks"]],
        "High Score": player["high_scores"]
    })
    st.dataframe(df_stats, hide_index=True, use_container_width=True)
    
    st.divider()
    if player['badges']:
        st.markdown("### 🎖️ Badges")
        for badge in player['badges']:
            st.caption(f"• {badge}")
    
    st.divider()
    if st.button("⬅️ Back to Main Menu"):
        st.session_state.current_view = 'menu'
        st.session_state.game_state = {} # Reset specific game state
        st.rerun()

# --- Game Views ---

def view_menu():
    st.markdown("<h1 class='main-header'>🧠 NeuroAI Quest</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Train Your Brain to Think Like AI</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="stat-card">', unsafe_allow_html=True)
        st.markdown("### 🧠 Memory Boost")
        st.write("Dual N-Back Palace")
        if st.button("Enter World 1"):
            st.session_state.current_view = 'memory'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="stat-card" style="margin-top: 10px;">', unsafe_allow_html=True)
        st.markdown("### 🤖 AI Prompting")
        st.write("Killer Prompt Forge")
        if st.button("Enter World 4"):
            st.session_state.current_view = 'prompt'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="stat-card">', unsafe_allow_html=True)
        st.markdown("### 🔄 View Switch")
        st.write("Multi-Perspective Puzzle")
        if st.button("Enter World 2"):
            st.session_state.current_view = 'perspective'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="stat-card" style="margin-top: 10px;">', unsafe_allow_html=True)
        st.markdown("### 🤔 Meta-Cognition")
        st.write("Thinking About Thinking")
        if st.button("Enter Training"):
            st.session_state.current_view = 'meta'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="stat-card">', unsafe_allow_html=True)
        st.markdown("### ⚙️ Step Logic")
        st.write("Riddle Breaker")
        if st.button("Enter World 3"):
            st.session_state.current_view = 'logic'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="stat-card" style="margin-top: 10px;">', unsafe_allow_html=True)
        st.markdown("### 👑 Boss Arena")
        st.write("Ultimate Challenge")
        if player['level'] >= 3:
            if st.button("Enter Boss Arena"):
                st.session_state.current_view = 'boss'
                st.rerun()
        else:
            st.button("🔒 Locked (Lvl 3)", disabled=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    if st.button("⚡ Daily Challenge", type="primary"):
        st.session_state.current_view = 'daily'
        st.rerun()

def view_memory():
    st.header("🧠 Memory Boost: Dual N-Back")
    
    # Initialize Game State
    gs = st.session_state.game_state
    if 'active' not in gs:
        world_level = player["world_unlocks"][0]
        n = max(2, world_level // 3 + 2)
        gs.update({
            'active': True,
            'n': n,
            'trials_total': 10, # Shortened for web UX
            'current_trial': 0,
            'score': 0,
            'pos_hist': [],
            'let_hist': [],
            'phase': 'ready', # ready, show, input, feedback, end
            'current_pos': 0,
            'current_let': '',
            'feedback_msg': ''
        })

    n = gs['n']
    
    if gs['phase'] == 'ready':
        st.info(f"**Level N={n}**. Remember if position OR letter matches {n} steps back!")
        if st.button("Start Trial Loop"):
            gs['phase'] = 'show'
            st.rerun()

    elif gs['phase'] == 'show':
        # Logic to generate new items
        pos = random.randint(1, 9)
        let = random.choice(logic.puzzles["letters"])
        gs['current_pos'] = pos
        gs['current_let'] = let
        
        # Display temporarily
        placeholder = st.empty()
        with placeholder.container():
            st.markdown(f"<h1 style='text-align: center; font-size: 80px;'>{logic.puzzles['positions'][pos-1].split(' ')[0]}</h1>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='text-align: center; color: yellow;'>{let}</h2>", unsafe_allow_html=True)
            st.caption("Memorize this...")
        
        time.sleep(1.5) # Blocking sleep is okay for short flash
        placeholder.empty()
        
        gs['phase'] = 'input'
        st.rerun()

    elif gs['phase'] == 'input':
        st.write(f"Trial {gs['current_trial'] + 1} / {gs['trials_total']}")
        
        with st.form("memory_input"):
            st.write(f"Does this match the item **{n} steps ago**?")
            c1, c2 = st.columns(2)
            with c1:
                u_pos = st.checkbox("Position Match?")
            with c2:
                u_let = st.checkbox("Letter Match?")
            
            submitted = st.form_submit_button("Submit")
            
            if submitted:
                # Calculate Match Logic
                pos_match = len(gs['pos_hist']) >= n and gs['current_pos'] == gs['pos_hist'][-n]
                let_match = len(gs['let_hist']) >= n and gs['current_let'] == gs['let_hist'][-n]
                
                trial_score = 0
                msg = []
                
                if u_pos == pos_match and u_let == let_match:
                    trial_score += 5
                    msg.append("✅ Perfect!")
                elif u_pos == pos_match or u_let == let_match:
                    trial_score += 2
                    msg.append("⚠️ Partially Correct.")
                else:
                    msg.append("❌ Incorrect.")
                
                if pos_match: msg.append("(Position matched)")
                if let_match: msg.append("(Letter matched)")
                
                gs['score'] += trial_score
                gs['feedback_msg'] = " ".join(msg)
                
                # Append history
                gs['pos_hist'].append(gs['current_pos'])
                gs['let_hist'].append(gs['current_let'])
                
                gs['current_trial'] += 1
                if gs['current_trial'] >= gs['trials_total']:
                    gs['phase'] = 'end'
                else:
                    gs['phase'] = 'feedback'
                st.rerun()

    elif gs['phase'] == 'feedback':
        st.info(gs['feedback_msg'])
        time.sleep(1.5) # Show feedback briefly
        gs['phase'] = 'show'
        st.rerun()

    elif gs['phase'] == 'end':
        final_score = (gs['score'] / (gs['trials_total'] * 5)) * 100
        st.markdown(f"### 🏁 Session Complete! Score: {final_score:.1f}%")
        
        if st.button("Claim XP & Return"):
            total_xp = gain_xp(int(final_score * 2), 0)
            st.success(f"Gained {total_xp} XP")
            
            if final_score > 70:
                player["world_unlocks"][0] += 1
                st.balloons()
                st.success("World Level Up!")
            
            if final_score > 90: award_badge(f"Memory N{n} Grandmaster")
            
            st.session_state.current_view = 'menu'
            st.session_state.game_state = {}
            st.rerun()

def view_perspective():
    st.header("🔄 View Switch: Multi-Perspective")
    
    gs = st.session_state.game_state
    if 'active' not in gs:
        world_level = player["world_unlocks"][1]
        gs.update({
            'active': True,
            'scenario': random.choice(logic.puzzles["scenarios"]),
            'views': random.sample(logic.puzzles["perspectives"], min(3 + world_level // 2, 6)),
            'current_view_idx': 0,
            'answers': [],
            'phase': 'input'
        })
    
    if gs['phase'] == 'input':
        st.subheader(f"Scenario: {gs['scenario']}")
        
        current_perspective = gs['views'][gs['current_view_idx']]
        st.markdown(f"#### 👤 Perspective {gs['current_view_idx']+1}: {current_perspective}")
        
        response = st.text_area("What are the key considerations from this viewpoint?", height=150, key=f"p_{gs['current_view_idx']}")
        
        if st.button("Submit Analysis"):
            if len(response) < 10:
                st.error("Too brief! Dig deeper.")
            else:
                score = 10
                if len(response.split()) > 15: score += 5
                if any(w in response.lower() for w in ['because', 'cost', 'risk', 'benefit']): score += 5
                gs['answers'].append(score)
                
                if gs['current_view_idx'] < len(gs['views']) - 1:
                    gs['current_view_idx'] += 1
                    st.rerun()
                else:
                    gs['phase'] = 'end'
                    st.rerun()
                    
    elif gs['phase'] == 'end':
        total_possible = len(gs['views']) * 20
        total_score = sum(gs['answers'])
        percent = (total_score / total_possible) * 100
        
        st.markdown(f"### 🏁 Analysis Complete: {percent:.1f}%")
        if st.button("Complete Training"):
            gain_xp(int(percent), 1)
            if percent > 65:
                player["world_unlocks"][1] += 1
                st.success("Level Up!")
            if percent > 85: award_badge("Perspective Polymath")
            st.session_state.current_view = 'menu'
            st.session_state.game_state = {}
            st.rerun()

def view_logic():
    st.header("⚙️ Step Logic: Riddle Breaker")
    
    gs = st.session_state.game_state
    # Check if the session is in the 'finished' state
    if gs.get('phase') == 'finished':
        if st.button("Finish Training & Return to Menu"):
            st.session_state.current_view = 'menu'
            st.session_state.game_state = {}
            st.rerun()
        return

    if 'active' not in gs:
        riddle, keys = random.choice(logic.puzzles["riddles"])
        gs.update({
            'active': True,
            'riddle': riddle,
            'keys': keys,
            'steps_count': min(3 + player["world_unlocks"][2] // 2, 6)
        })
        
    st.info(f"❓ **RIDDLE:** {gs['riddle']}")
    st.write(f"Break this down into **{gs['steps_count']} logical steps**.")
    
    with st.form("logic_form"):
        steps = []
        for i in range(gs['steps_count']):
            steps.append(st.text_input(f"Step {i+1}"))
            
        if st.form_submit_button("Submit Logic Chain"):
            score = 0
            key_hits = 0
            
            for s in steps:
                s_lower = s.lower()
                step_score = 10 if len(s) > 5 else 0
                
                for k in gs['keys']:
                    if k in s_lower:
                        key_hits += 1
                        step_score += 5
                
                if any(c in s_lower for c in ['then', 'next', 'after', 'first']):
                    step_score += 3
                score += step_score
            
            final_score = min(150, score + (key_hits / len(gs['keys']) * 50))
            
            st.write("### Analysis")
            st.write(f"Base Score: {score}")
            st.write(f"Key Concepts Found: {key_hits}/{len(gs['keys'])}")
            
            gain_xp(int(final_score), 2)
            if final_score > 80:
                player["world_unlocks"][2] += 1
                st.success("Logic Level Up!")
                award_badge("Logic Legend")
                
            # FIX: Transition to a finished phase instead of using a button inside the form block
            gs['phase'] = 'finished'
            st.rerun()


def view_prompt():
    st.header("🤖 AI Prompting: Forge")
    
    gs = st.session_state.game_state
    if 'active' not in gs:
        gs['active'] = True
        gs['target'] = random.choice(logic.puzzles["prompt_targets"])
        
    st.subheader(f"🎯 Target: {gs['target']}")
    st.info("Craft a prompt using roles, steps, constraints, and formats.")
    
    prompt = st.text_area("Your Prompt:", height=200)
    
    if st.button("Evaluate Prompt"):
        if len(prompt) < 10:
            st.error("Too short.")
        else:
            score, breakdown = logic.evaluate_prompt_advanced(prompt, gs['target'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Score", f"{score}/150")
            with col2:
                st.json(breakdown)
            
            if score > 120:
                st.success("Assessment: PERFECT! AI will excel at this.")
            elif score > 90:
                st.info("Assessment: EXCELLENT! Clear and structured.")
            else:
                st.warning("Assessment: BASIC. Needs more structure.")
            
            gain_xp(score, 3)
            if score > 70:
                player["world_unlocks"][3] += 1
                st.success("Prompting Level Up!")
            
            if st.button("Back to Menu"):
                st.session_state.current_view = 'menu'
                st.session_state.game_state = {}
                st.rerun()

def view_meta():
    st.header("🤔 Meta-Cognition Drill")
    
    gs = st.session_state.game_state
    if 'active' not in gs:
        gs.update({
            'active': True,
            'problem': random.choice([
                "How would you teach a dolphin to play chess?",
                "Design a government system for a colony on Mars",
                "Create a new sport that combines swimming and programming"
            ]),
            'modes': random.sample(list(logic.thinking_modes.items()), 3)
        })
        
    st.markdown(f"### 💡 Problem: {gs['problem']}")
    
    responses = []
    with st.form("meta_form"):
        for i, (mode, desc) in enumerate(gs['modes']):
            st.markdown(f"**Mode {i+1}: {mode.upper()}** - *{desc}*")
            responses.append(st.text_input(f"Apply {mode}", key=f"meta_{i}"))
        
        if st.form_submit_button("Submit Reflections"):
            total_score = 0
            for r in responses:
                if len(r) > 15: total_score += 35
                else: total_score += 10
            
            st.success(f"Drill Complete! Score: {total_score}")
            gain_xp(total_score)
            if total_score > 80: award_badge("Meta-Thinker")
            
            st.session_state.current_view = 'menu'
            st.session_state.game_state = {}
            st.rerun()

def view_boss():
    st.header("👑 BOSS ARENA")
    st.warning("The Boss requires mastery across all domains!")
    
    # Simple simulation of boss fight for the web version
    if st.button("⚔️ CHALLENGE THE BOSS ⚔️"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Testing Memory...")
        time.sleep(1)
        progress_bar.progress(33)
        
        status_text.text("Analyzing Perspective Shifts...")
        time.sleep(1)
        progress_bar.progress(66)
        
        status_text.text("Evaluating Meta-Cognition...")
        time.sleep(1)
        progress_bar.progress(100)
        
        # Calculate result based on player stats
        avg_level = sum(player['world_unlocks']) / 4
        boss_strength = random.randint(1, 5) + player['level']
        
        if avg_level * 10 + random.randint(0, 50) > boss_strength * 5:
            st.balloons()
            st.success(f"BOSS DEFEATED! Victory Score: {int(avg_level*100)}")
            gain_xp(500)
            award_badge("Cognitive Champion")
        else:
            st.error("Defeated... Train more and return!")
            gain_xp(50)
            
        if st.button("Leave Arena"):
            st.session_state.current_view = 'menu'
            st.rerun()

# --- Main Routing ---

if st.session_state.current_view == 'menu':
    view_menu()
elif st.session_state.current_view == 'memory':
    view_memory()
elif st.session_state.current_view == 'perspective':
    view_perspective()
elif st.session_state.current_view == 'logic':
    view_logic()
elif st.session_state.current_view == 'prompt':
    view_prompt()
elif st.session_state.current_view == 'meta':
    view_meta()
elif st.session_state.current_view == 'boss':
    view_boss()
elif st.session_state.current_view == 'daily':
    st.info("Daily Challenge is a randomized specific world. Routing you now...")
    time.sleep(1)
    # Randomly pick a world
    targets = ['memory', 'perspective', 'logic', 'prompt', 'meta']
    st.session_state.current_view = random.choice(targets)
    st.rerun()
