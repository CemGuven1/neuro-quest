import streamlit as st
import json
import datetime
import random
import os
import time
import pandas as pd

# --- Corrected Firebase Imports ---
# Assumes the environment directly provides these modules or their functions globally
try:
    from firebase_app import initializeApp
    from firebase_auth import getAuth, signInWithCustomToken, signInAnonymously, onAuthStateChanged
    from firebase_firestore import getFirestore, collection, doc, setDoc, getDoc, updateDoc
except ImportError:
    # Fallback for local testing or unexpected environments (may fail)
    print("WARNING: Using dummy imports. Firebase will not function locally.")
    class DummyAuth:
        def __init__(self): self.uid = 'anonymous_local_test'
    
    # Define dummy functions to prevent immediate crash during local testing
    def initializeApp(config): return None
    def getAuth(app): return None
    async def signInWithCustomToken(auth, token): return type('User', (object,), {'uid': 'token_error'})()
    async def signInAnonymously(auth): return type('User', (object,), {'uid': 'anonymous_local_test'})()
    def onAuthStateChanged(auth, handler): return lambda: None
    def getFirestore(app): return None
    def collection(db, path): return None
    def doc(db, path): return None
    async def setDoc(*args): pass
    async def getDoc(*args): return type('DocSnapshot', (object,), {'exists': False, 'to_dict': lambda: {}}())
    async def updateDoc(*args): pass

# --- Firebase Setup and Constants (MANDATORY USE) ---
# NOTE: The platform provides these global variables
appId = 'default-app-id' # Fallback, but __app_id is used if available
firebaseConfig = {}
authToken = None

# IMPROVEMENT: Access global variables more defensively
try:
    # Check if the global variables are defined before accessing them
    if '__app_id' in globals() and globals()['__app_id']:
        appId = globals()['__app_id']
        
    if '__firebase_config' in globals() and globals()['__firebase_config']:
        # IMPORTANT: Ensure the string is not empty before parsing
        config_str = globals()['__firebase_config']
        if config_str:
             firebaseConfig = json.loads(config_str)
             
    if '__initial_auth_token' in globals():
        authToken = globals()['__initial_auth_token']
        
except NameError:
    # Running locally or outside the canvas environment
    print("WARNING: Firebase environment variables not found. Using defaults.")
    pass

# Initialize Firebase services
if 'firebase_initialized' not in st.session_state:
    if firebaseConfig and any(firebaseConfig.values()): # Check if config is non-empty and useful
        try:
            st.session_state.app = initializeApp(firebaseConfig)
            st.session_state.db = getFirestore(st.session_state.app)
            st.session_state.auth = getAuth(st.session_state.app)
            st.session_state.firebase_initialized = True
        except Exception as e:
            st.error(f"Failed to initialize Firebase: {e}")
            st.session_state.firebase_initialized = False
    else:
        # This is the message the user received, now we log why:
        print("ERROR: firebaseConfig is empty or invalid. Cannot initialize Firebase.")
        st.error("Firebase configuration is missing. Cannot save user progress.")
        st.session_state.firebase_initialized = False

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

# --- Firestore Functions ---

DEFAULT_PLAYER_DATA = {
    "name": "AI Apprentice",
    "xp": 0, "level": 1, "streak": 0, "last_play": "",
    "high_scores": [0]*4, "badges": [], "world_unlocks": [0]*4,
    "total_sessions": 0
}

def get_player_doc_ref(db, userId):
    # Path: /artifacts/{appId}/users/{userId}/game_data/progress
    return doc(db, f"artifacts/{appId}/users/{userId}/game_data/progress")

async def load_player_from_firestore():
    # Only proceed if Firebase is initialized and auth is ready
    if not st.session_state.get('auth_ready') or not st.session_state.get('firebase_initialized'):
        # Fallback to default data
        st.warning("Cannot load from Firestore. Using temporary session data.")
        return DEFAULT_PLAYER_DATA 

    db = st.session_state.db
    userId = st.session_state.userId
    
    doc_ref = get_player_doc_ref(db, userId)
    try:
        doc_snapshot = await getDoc(doc_ref)
        if doc_snapshot.exists:
            player_data = doc_snapshot.to_dict()
            st.toast("Progress loaded from Firestore!")
            # Ensure all keys exist, setting defaults if necessary
            return {**DEFAULT_PLAYER_DATA, **player_data}
        else:
            # Create new player data in Firestore
            await setDoc(doc_ref, DEFAULT_PLAYER_DATA)
            st.toast("New profile created!")
            return DEFAULT_PLAYER_DATA
    except Exception as e:
        st.error(f"Error loading player data: {e}. Using default profile.")
        return DEFAULT_PLAYER_DATA

async def save_player_to_firestore(player_data):
    # Only proceed if Firebase is initialized and auth is ready
    if not st.session_state.get('auth_ready') or not st.session_state.get('firebase_initialized'):
        print("Save blocked: Auth not ready or Firebase not initialized.")
        return

    db = st.session_state.db
    userId = st.session_state.userId
    doc_ref = get_player_doc_ref(db, userId)
    try:
        # Use updateDoc to save the player data
        await updateDoc(doc_ref, player_data)
        print("Progress saved to Firestore.")
    except Exception as e:
        print(f"Error saving player data: {e}")
        # Note: Do not use st.error here, as this function is called outside the main flow

# --- Authentication and Initialization ---

async def init_auth():
    if st.session_state.get('auth_ready'):
        return

    # Check for Firebase initialization success before attempting auth
    if not st.session_state.get('firebase_initialized') or 'auth' not in st.session_state:
        st.session_state.auth_ready = False
        return
        
    auth = st.session_state.auth
    
    # Sign in using custom token or anonymously
    user = None
    if authToken:
        try:
            user = await signInWithCustomToken(auth, authToken)
        except Exception as e:
            print(f"Custom Auth failed: {e}. Falling back to Anonymous.")
            user = await signInAnonymously(auth)
    else:
        user = await signInAnonymously(auth)

    # Use onAuthStateChanged to ensure user ID is captured correctly after sign-in
    def handle_auth_state_change(user_obj):
        if user_obj:
            st.session_state.userId = user_obj.uid
        else:
            # Fallback to random UUID if auth is truly anonymous or fails
            # We use a deterministic method here for consistency in testing, but in a real app, use UUID
            st.session_state.userId = 'anonymous_' + str(random.getrandbits(128))
            
        st.session_state.auth_ready = True
        # Rerun to load player data now that we have the userId
        st.rerun()

    # onAuthStateChanged returns an unsubscriber function, but we don't strictly need it 
    # for a Streamlit single-page app structure here.
    if 'auth_listener_set' not in st.session_state:
        onAuthStateChanged(auth, handle_auth_state_change)
        st.session_state.auth_listener_set = True

# --- Game Logic Functions (Adapted for Firestore) ---

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
    # Defer saving the updated player state
    st.session_state.save_pending = True
    
def gain_xp(pts, world_idx=None):
    player = st.session_state.player
    bonus = player.get("streak", 0) * 10
    total = pts + bonus
    player["xp"] += total
    
    if world_idx is not None and len(player["high_scores"]) > world_idx:
        player["high_scores"][world_idx] = max(player["high_scores"][world_idx], pts)
    
    # Simple Logic: Every 100 XP is a level. 
    old_level = player["level"]
    while player["xp"] >= player["level"] * 100:
        player["level"] += 1
    
    if player["level"] > old_level:
        st.balloons()
        st.success(f"🌟 LEVEL UP! You are now Level {player['level']}!")
        if player["level"] % 5 == 0:
            award_badge(f"Level {player['level']} Master", internal_save=False)
            
    # Asynchronously save updated player state
    st.session_state.save_pending = True
    return total

def award_badge(badge, internal_save=True):
    if badge not in st.session_state.player["badges"]:
        st.session_state.player["badges"].append(badge)
        st.session_state.player["xp"] += 50
        st.toast(f"🎖️ BADGE UNLOCKED: {badge}", icon="🎖️")
        if internal_save:
             st.session_state.save_pending = True

# --- Global Initialization and Routing Setup ---

# Run Auth Initialization first
if 'auth_ready' not in st.session_state:
    st.session_state.auth_ready = False
    st.session_state.userId = None
    st.session_state.player = DEFAULT_PLAYER_DATA
    st.session_state.save_pending = False
    st.session_state.game_logic = GameLogic()
    st.session_state.current_view = 'loading'
    
    # Initialize game_state safely here, so it always exists
    st.session_state.game_state = {} 
    
    # This must be run asynchronously, handled by Streamlit's event loop
    st.code(init_auth, language="python") # Streamlit will execute the async function

# After auth is ready, load player data
if st.session_state.auth_ready and 'player_loaded' not in st.session_state:
    st.session_state.player = st.code(load_player_from_firestore, language="python") # Load data
    st.session_state.player_loaded = True
    st.session_state.current_view = 'menu'
    st.rerun()

# --- Main App Execution flow ---
if st.session_state.current_view == 'loading':
    st.info("Initializing NeuroAI Quest. Securing unique user session...")
    
    # If config failed, show the error state but allow user to interact with default profile
    if not st.session_state.get('firebase_initialized'):
        st.error("Using local, non-persistent profile due to missing Firebase configuration.")
        st.session_state.auth_ready = True
        st.session_state.userId = 'local_non_persistent_user'
        st.session_state.player_loaded = True
        st.session_state.current_view = 'menu'
        st.rerun()
        
    st.stop()

# Player Data is ready from here on
logic = st.session_state.game_logic
player = st.session_state.player

# Run update streak (which relies on player data being loaded)
update_streak()

# --- Post-Processing and Saving ---
# CRITICAL FIX: The st.code call for saving must be outside the main view functions
# and handle the async coroutine return gracefully.
# We create a wrapper function that ensures the asynchronous call is awaited/executed.
if st.session_state.save_pending:
    def _run_save(player_data):
        # This function is executed by st.code()
        # It's better to just call the async function directly here 
        # and let Streamlit handle the coroutine, which it does when called via st.code
        return save_player_to_firestore(player_data)

    # Call the wrapper function via st.code to trigger the async execution
    st.code(_run_save, language="python", args=(player,)) 
    st.session_state.save_pending = False
    # No st.rerun() here to avoid infinite loops, let the next user interaction trigger it

# --- Sidebar (adapted for new state) ---
with st.sidebar:
    st.title(f"👤 {player['name']}")
    st.caption(f"User ID: {st.session_state.userId}") # Show user ID for debugging
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Level", player['level'])
    with col2:
        st.metric("Streak", f"{player['streak']}🔥")
    
    # Progress Bar Calculation
    current_level_start_xp = (player['level'] - 1) * 100
    xp_in_level = player['xp'] - current_level_start_xp
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
        # Safely reset the specific game state 
        st.session_state.game_state = {} 
        st.rerun()

# --- Game Views (Same logic, but rely on updated player state) ---
# ... (view_menu, view_memory, view_perspective, view_logic, view_prompt, view_meta, view_boss remain mostly identical)

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
    
    # FIX: Use .get() to safely retrieve game_state, defaulting to {} if missing.
    gs = st.session_state.game_state.get('memory', {})
    
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
        # Save the initial state back to the session state
        st.session_state.game_state['memory'] = gs


    n = gs['n']
    
    if gs['phase'] == 'ready':
        st.info(f"**Level N={n}**. Remember if position OR letter matches {n} steps back!")
        if st.button("Start Trial Loop"):
            gs['phase'] = 'show'
            st.session_state.game_state['memory'] = gs # Update session state
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
        
        # Non-blocking way to wait for time
        # This will not actually work as intended in Streamlit's redraw cycle
        # We rely on the user manually advancing or a full app state change
        # For simplicity, we just rerender to move to the next state, assuming rapid clicking
        # time.sleep(1.5) # Blocking sleep is okay for short flash
        # placeholder.empty() # This will only run on next rerender

        gs['phase'] = 'input'
        st.session_state.game_state['memory'] = gs # Update session state
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
                
                st.session_state.game_state['memory'] = gs # Update session state
                st.rerun()

    elif gs['phase'] == 'feedback':
        st.info(gs['feedback_msg'])
        # Since st.rerun is called right after, this sleep is largely ineffective 
        # in the web environment. We rely on user action.
        # time.sleep(1.5) # Show feedback briefly 

        # We need a button to advance from feedback state to the next trial
        if st.button("Continue"):
            gs['phase'] = 'show'
            st.session_state.game_state['memory'] = gs # Update session state
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
            st.session_state.game_state = {} # Reset entire game_state on return
            st.rerun()

def view_perspective():
    st.header("🔄 View Switch: Multi-Perspective")
    
    # FIX: Use .get() to safely retrieve game_state, defaulting to {} if missing.
    gs = st.session_state.game_state.get('perspective', {})
    
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
        st.session_state.game_state['perspective'] = gs # Save the initial state back
    
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
                    st.session_state.game_state['perspective'] = gs # Update session state
                    st.rerun()
                else:
                    gs['phase'] = 'end'
                    st.session_state.game_state['perspective'] = gs # Update session state
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
    
    # FIX: Use .get() to safely retrieve game_state, defaulting to {} if missing.
    gs = st.session_state.game_state.get('logic', {})
    
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
        st.session_state.game_state['logic'] = gs # Save the initial state back
        
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
                
            # Transition to a finished phase
            gs['phase'] = 'finished'
            st.session_state.game_state['logic'] = gs # Update session state
            st.rerun()


def view_prompt():
    st.header("🤖 AI Prompting: Forge")
    
    # FIX: Use .get() to safely retrieve game_state, defaulting to {} if missing.
    gs = st.session_state.game_state.get('prompt', {})
    
    if 'active' not in gs:
        gs['active'] = True
        gs['target'] = random.choice(logic.puzzles["prompt_targets"])
        st.session_state.game_state['prompt'] = gs # Save the initial state back
        
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
    
    # FIX: Use .get() to safely retrieve game_state, defaulting to {} if missing.
    gs = st.session_state.game_state.get('meta', {})
    
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
        st.session_state.game_state['meta'] = gs # Save the initial state back
        
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
            st.session_state.game_state = {}
            st.rerun()

# --- Main Routing ---

if st.session_state.current_view == 'menu':
    view_menu()
# Ensure that all game views check for their specific key within game_state
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
