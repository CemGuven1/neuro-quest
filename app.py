import streamlit as st
import json
import datetime
import random
import time
import pandas as pd
import io # Needed for handling file downloads/uploads

# --- CORE GAME LOGIC CLASS (ADAPTED FOR STREAMLIT) ---

class NeuroAIQuest:
    def __init__(self):
        # Data that is safe to initialize once
        self.daily_seed = str(datetime.date.today())
        self.thinking_modes = {
            "white_room": "Strip context, think abstractly",
            "recursive": "Break into sub-problems", 
            "hypothesis_driven": "Generate-test-invalidate",
            "multi_modal": "Cross-domain connections"
        }
        self.puzzles = self.load_puzzles()
        
    def initialize_session_state(self):
        """Initializes all necessary state variables for Streamlit."""
        if 'player' not in st.session_state:
            st.session_state.player = self.default_player()
        if 'current_view' not in st.session_state:
            st.session_state.current_view = 'main_menu'
        if 'game_output' not in st.session_state:
            st.session_state.game_output = []
        if 'current_challenge' not in st.session_state:
            st.session_state.current_challenge = {}

        self.update_streak()
        
    def default_player(self):
        return {
            "name": "AI Apprentice",
            "xp": 0, "level": 1, "streak": 0, "last_play": "",
            "high_scores": [0]*4, "badges": [], "world_unlocks": [0]*4,
            "total_sessions": 0
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
            "abstraction_levels": [
                "Literal/Concrete",
                "Functional/Practical", 
                "System/Network",
                "Metaphorical/Analogical",
                "Fundamental/Philosophical"
            ]
        }

    def log(self, message):
        """Custom logger to display output in Streamlit UI."""
        st.session_state.game_output.append(message)

    def update_streak(self):
        """Updates the streak and session count."""
        player = st.session_state.player
        today = datetime.date.today().isoformat()
        
        if player["last_play"] == today:
            return

        try:
            last_date = datetime.date.fromisoformat(player["last_play"])
            if (datetime.date.today() - last_date).days == 1:
                player["streak"] += 1
            else:
                player["streak"] = 1
        except:
            player["streak"] = 1
            
        player["last_play"] = today
        player["total_sessions"] = player.get("total_sessions", 0) + 1
        st.session_state.player = player
        self.log(f"🔥 Streak: {player['streak']} days (+{player['streak']*10} XP bonus!)")

    def award_badge(self, badge):
        player = st.session_state.player
        if badge not in player["badges"]:
            player["badges"].append(badge)
            self.log(f"\n🎉 NEW BADGE UNLOCKED: {badge}! +50 XP bonus!")
            player["xp"] += 50
            st.session_state.player = player

    def gain_xp(self, pts, world=None):
        player = st.session_state.player
        bonus = player["streak"] * 10
        total = pts + bonus
        player["xp"] += total
        
        if world is not None:
            player["high_scores"][world] = max(player["high_scores"][world], pts)
        
        old_level = player["level"]
        while player["xp"] >= player["level"] * 100:
            player["level"] += 1
        
        if player["level"] > old_level:
            self.log(f"\n🌟 LEVEL UP! You are now Level {player['level']}!")
            if player["level"] % 5 == 0:
                self.award_badge(f"Level {player['level']} Master")
        
        st.session_state.player = player
        self.log(f"   +{pts} XP | +{bonus} streak bonus = {total} total XP")

    # --- GAME MODE IMPLEMENTATIONS ---

    def memory_boost_init(self, world_level):
        """Sets up the state for the Memory Boost (Dual N-Back) game."""
        n = max(2, world_level // 3 + 2)
        trials = min(15 + world_level * 2, 30)
        
        st.session_state.current_challenge = {
            'mode': 'memory_boost',
            'world_index': 0,
            'n': n,
            'trials': trials,
            'current_trial': 0,
            'score': 0,
            'pos_hist': [],
            'let_hist': [],
            'start_time': None
        }
        self.log(f"🧠 MEMORY BOOST: Dual N-Back Palace! Training at N={n} with {trials} trials.")
        self.log("Remember if position OR letter matches N steps back!")
        st.session_state.current_view = 'memory_boost_game'

    # The submission logic now takes the user inputs directly
    def memory_boost_next_trial(self, user_pos, user_let):
        c = st.session_state.current_challenge
        
        if c['current_trial'] == 0:
            c['start_time'] = time.time() # Start timer
        
        if c['current_trial'] > 0:
            # Score previous trial based on user input from form
            t = c['current_trial'] - 1
            n = c['n']
            pos_match = len(c['pos_hist']) >= n and c['pos_hist'][-1-n] == c['pos_hist'][-1]
            let_match = len(c['let_hist']) >= n and c['let_hist'][-1-n] == c['let_hist'][-1]
            
            # Use the inputs passed to the function
            user_pos = user_pos
            user_let = user_let
            
            if user_pos == pos_match and user_let == let_match:
                c['score'] += 5
                self.log(f"   Trial {t+1}: ✅ Perfect! Double hit! (+5)")
            elif user_pos == pos_match or user_let == let_match:
                c['score'] += 2
                self.log(f"   Trial {t+1}: ✅ Half correct! (+2)")
            else:
                self.log(f"   Trial {t+1}: ❌ Miss. Correct: Pos={pos_match}, Let={let_match}")
                
            # Adaptive difficulty (only check if it's past the first 5 trials)
            if (c['current_trial']) >= 5 and (c['current_trial'] % 5 == 0):
                # Calculate accuracy over the last 5 trials
                last_five_trials = c['current_trial']
                score_last_five = sum([5 if c['score'] == 5 else 2 if c['score'] == 2 else 0 for _ in range(last_five_trials)]) # Simplification
                accuracy = (c['score'] / (c['current_trial'] * 5)) * 100
                
                if accuracy > 80 and c['n'] < 5:
                    c['n'] += 1
                    self.log(f"   🎯 Increasing difficulty to N={c['n']}!")
                elif accuracy < 50 and c['n'] > 2:
                    c['n'] -= 1
                    self.log(f"   📉 Decreasing difficulty to N={c['n']}")
                    
        # Check for end of game
        if c['current_trial'] >= c['trials']:
            self.memory_boost_end(c)
            return

        # Prepare next trial
        pos = random.randint(1, 9)
        let = random.choice(self.puzzles["letters"])
        
        c['pos_hist'].append(pos)
        c['let_hist'].append(let)
        c['current_trial'] += 1
        
        st.session_state.current_challenge = c
        # The Streamlit UI will render the next state

    def memory_boost_end(self, c):
        final_score_percent = (c['score'] / (c['trials'] * 5)) * 100
        self.log(f"\n🏁 FINAL SCORE: {final_score_percent:.1f}% at N={c['n']}")
        
        success = final_score_percent > 70
        self.gain_xp(int(final_score_percent * 2), c['world_index'])
        
        # Badge awards
        if final_score_percent > 90:
            self.award_badge(f"Memory N{c['n']} Grandmaster")
        elif final_score_percent > 80:
            self.award_badge(f"Memory N{c['n']} Master")
        elif final_score_percent > 70:
            self.award_badge(f"Memory N{c['n']} Adept")
        
        self.log("--- Memory Boost Finished ---")
        self.go_to_menu_after_delay()
        
    def view_switch_init(self, world_level):
        scenario = random.choice(self.puzzles["scenarios"])
        num_views = min(3 + world_level // 2, 6)
        views = random.sample(self.puzzles["perspectives"], num_views)
        max_per_view = 25
        
        st.session_state.current_challenge = {
            'mode': 'view_switch',
            'world_index': 1,
            'scenario': scenario,
            'views': views,
            'num_views': num_views,
            'current_view_index': 0,
            'score': 0,
            'max_per_view': max_per_view,
            'responses': []
        }
        self.log(f"🔄 VIEW SWITCH: Multi-Perspective Puzzle!")
        self.log(f"📝 SCENARIO: {scenario}")
        self.log(f"Analyze this from {num_views} perspectives.")
        st.session_state.current_view = 'view_switch_game'

    def view_switch_next(self, response_text):
        c = st.session_state.current_challenge
        
        if c['current_view_index'] > 0:
            # Score the previous response
            points = 0
            
            if len(response_text) < 10:
                self.log(f"   ❌ Too brief - try to think deeper! (+5)")
                points = 5
            else:
                points = 10  # Base points
                if len(response_text.split()) > 15: points += 5
                if any(word in response_text.lower() for word in ['because', 'therefore', 'however']): points += 5
                if any(word in response_text.lower() for word in ['cost', 'benefit', 'risk', 'opportunity']): points += 5
                
                points = min(points, c['max_per_view'])
                self.log(f"   ✅ Insightful! +{points} points")
                
            c['score'] += points
            c['responses'].append(response_text)
        
        # Check for end of game
        if c['current_view_index'] >= c['num_views']:
            self.view_switch_end(c)
            return

        c['current_view_index'] += 1
        st.session_state.current_challenge = c
        
    def view_switch_end(self, c):
        final_score_percent = min(100, (c['score'] / (c['num_views'] * c['max_per_view'])) * 100)
        self.log(f"\n🏁 PERSPECTIVE MASTERY: {final_score_percent:.1f}%")
        
        success = final_score_percent > 65
        self.gain_xp(int(final_score_percent), c['world_index'])
        
        if final_score_percent > 85:
            self.award_badge("Perspective Polymath")
        elif final_score_percent > 70:
            self.award_badge("Multi-View Thinker")
            
        self.log("--- View Switch Finished ---")
        self.go_to_menu_after_delay()

    def step_logic_init(self, world_level):
        riddle, solution_keys = random.choice(self.puzzles["riddles"])
        num_steps = min(3 + world_level // 2, 6)
        
        st.session_state.current_challenge = {
            'mode': 'step_logic',
            'world_index': 2,
            'riddle': riddle,
            'solution_keys': solution_keys,
            'num_steps': num_steps,
            'current_step': 0,
            'steps_score': 0,
            'key_hits': 0,
            'responses': []
        }
        self.log(f"⚙️ STEP LOGIC: Riddle Breaker!")
        self.log(f"❓ RIDDLE: {riddle}")
        self.log(f"\nBreak it down into {num_steps} logical steps:")
        st.session_state.current_view = 'step_logic_game'

    def step_logic_next(self, response_text):
        c = st.session_state.current_challenge
        
        if c['current_step'] > 0:
            # Score the previous response
            step_points = 10  # Base for attempting
            
            # Check for key solution concepts
            for key in c['solution_keys']:
                if key in response_text.lower():
                    c['key_hits'] += 1
                    step_points += 5
            
            # Check for logical connectors
            if any(connector in response_text.lower() for connector in ['then', 'next', 'after', 'first', 'second']):
                step_points += 3
                
            c['steps_score'] += step_points
            c['responses'].append(response_text)
            self.log(f"      Step quality: +{step_points}")
        
        # Check for end of game
        if c['current_step'] >= c['num_steps']:
            self.step_logic_end(c)
            return

        c['current_step'] += 1
        st.session_state.current_challenge = c
        
    def step_logic_end(self, c):
        base_score = c['steps_score']
        key_bonus = (c['key_hits'] / len(c['solution_keys'])) * 50 if c['solution_keys'] else 0
        final_score = min(150, base_score + key_bonus)
        
        self.log(f"\n🔍 SOLUTION ANALYSIS:")
        self.log(f"   Step quality: {base_score}")
        self.log(f"   Key concepts found: {c['key_hits']}/{len(c['solution_keys'])} (+{key_bonus:.0f})")
        self.log(f"   FINAL SCORE: {final_score:.0f}")
        
        success = final_score > 80
        self.gain_xp(int(final_score), c['world_index'])
        
        if c['key_hits'] == len(c['solution_keys']):
            self.award_badge("Logic Legend")
        elif c['key_hits'] >= len(c['solution_keys']) * 0.7:
            self.award_badge("Analytical Thinker")
            
        self.log("--- Step Logic Finished ---")
        self.go_to_menu_after_delay()
        
    def evaluate_prompt_advanced(self, prompt):
        """More sophisticated prompt analysis for AI Play"""
        scores = {
            "systematicity": 0,    # Step-by-step structure
            "role_specificity": 0,  # Defined perspective/role
            "output_format": 0,     # Clear output specification
            "constraint_clarity": 0, # Clear boundaries and rules
            "abstraction": 0,      # How well it abstracts the core problem
            "creativity_bonus": 0   # Innovative approach
        }
        
        prompt_lower = prompt.lower()
        
        # Systematicity: Step-by-step thinking
        if any(word in prompt_lower for word in ['step', 'first', 'then', 'next', 'finally', 'chain of thought']):
            scores["systematicity"] += 30
            
        # Role specificity
        if any(phrase in prompt_lower for phrase in ['as a', 'act as', 'you are', 'expert', 'specialist']):
            scores["role_specificity"] += 30
            
        # Output format
        if any(word in prompt_lower for word in ['table', 'format', 'json', 'outline', 'bullet', 'structure']):
            scores["output_format"] += 30
            
        # Constraint clarity
        if any(word in prompt_lower for word in ['constraint', 'limit', 'within', 'boundary']):
            scores["constraint_clarity"] += 15
            
        # Abstraction
        if any(word in prompt_lower for word in ['fundamental', 'core principle', 'abstract', 'essence']):
            scores["abstraction"] += 15
            
        # Creativity bonus
        unusual_approaches = ['metaphor', 'analogy', 'unconventional', 'creative', 'innovative']
        if len(prompt.split()) > 30: scores["creativity_bonus"] += 10 # Length bonus
        if any(approach in prompt_lower for approach in unusual_approaches):
            scores["creativity_bonus"] += 20
            
        total_score = sum(scores.values())
        return min(150, total_score), scores

    def ai_play_init(self, world_level):
        target = random.choice(self.puzzles["prompt_targets"])
        
        st.session_state.current_challenge = {
            'mode': 'ai_play',
            'world_index': 3,
            'target': target,
        }
        self.log(f"🤖 AI PLAY: Killer Prompt Forge!")
        self.log(f"\n🎯 TARGET: {target}")
        self.log("Craft the perfect prompt to get amazing AI results!")
        self.log("Tips: Use roles, steps, constraints, and clear output formats.")
        st.session_state.current_view = 'ai_play_game'

    def ai_play_end(self, prompt):
        c = st.session_state.current_challenge
        
        if len(prompt) < 10:
            self.log("❌ Prompt too short! Be more specific. +20 XP")
            self.gain_xp(20, c['world_index'])
            self.go_to_menu_after_delay()
            return
            
        # Advanced evaluation
        total_score, score_breakdown = self.evaluate_prompt_advanced(prompt)
        
        self.log(f"\n📊 PROMPT ANALYSIS:")
        for category, points in score_breakdown.items():
            if points > 0:
                self.log(f"   - **{category.replace('_', ' ').title()}**: +{points}")
        
        # Quality assessment
        if total_score > 120:
            assessment = "🎯 PERFECT! AI will excel at this"
            response = "The AI produces a brilliant, detailed response that perfectly addresses all aspects of your carefully crafted prompt!"
        elif total_score > 90:
            assessment = "✅ EXCELLENT! Clear and structured"
            response = "The AI understands your request clearly and provides a well-organized, comprehensive response."
        elif total_score > 60:
            assessment = "⚠️ GOOD, but could be clearer"
            response = "The AI gets the general idea but might need some clarification on specific details or format."
        else:
            assessment = "❌ BASIC - needs more structure"
            response = "The AI seems confused and provides a generic, unfocused response. Try adding more specific instructions."
        
        self.log(f"\n**🏁 PROMPT SCORE**: {total_score}/150")
        self.log(f"**ASSESSMENT**: {assessment}")
        self.log(f"\n**🤖 SIMULATED AI RESPONSE**: '{response}'")
        
        success = total_score > 70
        self.gain_xp(total_score, c['world_index'])
        
        # Badge awards
        if total_score > 130:
            self.award_badge("Prompt God")
        elif total_score > 110:
            self.award_badge("Prompt Architect")
        elif total_score > 85:
            self.award_badge("Prompt Engineer")
            
        self.log("--- AI Play Finished ---")
        self.go_to_menu_after_delay()

    def meta_cognition_init(self):
        problems = [
            "How would you teach a dolphin to play chess?",
            "Design a government system for a colony on Mars",
            "Create a new sport that combines swimming and programming",
            "How would you explain the internet to Leonardo da Vinci?",
            "Design a house for someone who can teleport"
        ]
        
        problem = random.choice(problems)
        selected_modes = random.sample(list(self.thinking_modes.items()), 3)

        st.session_state.current_challenge = {
            'mode': 'meta_cognition',
            'problem': problem,
            'selected_modes': selected_modes,
            'current_mode_index': 0,
            'total_score': 0,
            'responses': []
        }
        self.log(f"🤔 META-COGNITION: Thinking About Thinking!")
        self.log(f"\n💡 PROBLEM: **{problem}**")
        self.log("Apply different thinking modes to this problem:")
        st.session_state.current_view = 'meta_cognition_game'

    def meta_cognition_next(self, response_text):
        c = st.session_state.current_challenge
        
        if c['current_mode_index'] > 0:
            mode, _ = c['selected_modes'][c['current_mode_index'] - 1]
            points = 0

            if len(response_text) < 15:
                self.log("   ❌ Surface-level thinking (+15)")
                points = 15
            else:
                points = 25  # Good attempt
                # Bonus for mode-specific indicators
                if mode == "white_room" and any(word in response_text.lower() for word in ['abstract', 'essence', 'core']):
                    points += 10
                elif mode == "recursive" and any(word in response_text.lower() for word in ['break down', 'sub-problem', 'step']):
                    points += 10
                elif mode == "hypothesis_driven" and any(word in response_text.lower() for word in ['test', 'validate', 'assume']):
                    points += 10
                elif mode == "multi_modal" and any(word in response_text.lower() for word in ['connect', 'cross', 'domain']):
                    points += 10
                    
                self.log(f"   ✅ Good application! +{points} points")
            
            c['total_score'] += points
            c['responses'].append(response_text)

        # Check for end of game
        if c['current_mode_index'] >= len(c['selected_modes']):
            self.meta_cognition_end(c)
            return

        c['current_mode_index'] += 1
        st.session_state.current_challenge = c

    def meta_cognition_end(self, c):
        final_score = c['total_score']
        self.log(f"\n**🏁 META-COGNITION SCORE**: {final_score}/105")
        
        success = final_score > 70
        self.gain_xp(final_score)
        
        if final_score > 80:
            self.award_badge("Meta-Thinker")
            
        self.log("--- Meta-Cognition Drill Finished ---")
        self.go_to_menu_after_delay()

    # --- WORLD/BOSS FLOWS ---

    def play_world(self, world_index):
        world_names = ["Memory Boost", "Perspective Switch", "Step Logic", "AI Prompting"]
        current_level = st.session_state.player["world_unlocks"][world_index]
        
        self.log(f"\n🎯 Entering **{world_names[world_index]}** - Level {current_level + 1}")
        
        # Reset attempts and initiate the specific game mode
        st.session_state.player['attempts_remaining'] = 3
        
        if world_index == 0:
            self.memory_boost_init(current_level)
        elif world_index == 1:
            self.view_switch_init(current_level)
        elif world_index == 2:
            self.step_logic_init(current_level)
        elif world_index == 3:
            self.ai_play_init(current_level)

    def advance_world_level(self, world_index, success):
        player = st.session_state.player
        world_names = ["Memory Boost", "Perspective Switch", "Step Logic", "AI Prompting"]
        
        if success:
            player["world_unlocks"][world_index] += 1
            new_level = player["world_unlocks"][world_index]
            self.log(f"\n🎉 **{world_names[world_index]}** advanced to Level {new_level}!")
            
            # Boss fight every 3 levels
            if new_level % 3 == 0:
                self.boss_arena_init(world_index)
            else:
                self.go_to_menu_after_delay()
        else:
            self.log(f"\n😔 Level not advanced. Keep training!")
            self.go_to_menu_after_delay()
            
        st.session_state.player = player


    def boss_arena_init(self, world_index=None):
        if world_index is None:
            world_index = random.randint(0, 3)
            
        st.session_state.current_challenge = {
            'mode': 'boss_arena',
            'world_index': world_index,
            'challenge_stage': 0, # 0: Memory, 1: Perspective, 2: Meta
            'score': 0,
            # Memory data
            'n': 3,
            'trials': 5,
            'current_trial': 0,
            'pos_hist': [],
            'let_hist': [],
            # Perspective data
            'scenario': random.choice(self.puzzles["scenarios"]),
            'perspective': random.choice(self.puzzles["perspectives"]),
        }
        
        self.log("\n👑 **BOSS ARENA**: Ultimate Cognitive Challenge!")
        self.log("The Boss requires you to demonstrate mastery across multiple domains!")
        st.session_state.current_view = 'boss_arena_game'

    def boss_arena_next(self, user_inputs={}):
        c = st.session_state.current_challenge
        
        # Process results from previous stage
        if c['challenge_stage'] == 0: # Memory (N-back)
            if c['current_trial'] > 0:
                # Score the user's input from the memory trial (t-1)
                t = c['current_trial'] - 1
                n = c['n']
                pos_match = len(c['pos_hist']) >= n and c['pos_hist'][-1-n] == c['pos_hist'][-1]
                let_match = len(c['let_hist']) >= n and c['let_hist'][-1-n] == c['let_hist'][-1]
                
                user_pos = user_inputs.get('user_pos_match', False)
                user_let = user_inputs.get('user_let_match', False)

                trial_score = 0
                if user_pos == pos_match and user_let == let_match:
                    trial_score = 5
                    self.log(f"   Trial {t+1}: ✅ Double hit!")
                elif user_pos == pos_match or user_let == let_match:
                    trial_score = 2
                    self.log(f"   Trial {t+1}: ✅ Half correct!")
                else:
                    self.log(f"   Trial {t+1}: ❌ Miss. Correct: Pos={pos_match}, Let={let_match}")
                
                c['score'] += trial_score
            
            # Check for end of Memory Challenge
            if c['current_trial'] >= c['trials']:
                memory_score = (c['score'] / (c['trials'] * 5)) * 50  # Convert to 50 point scale
                c['score'] = memory_score # Reset score to be the stage score (out of 50)
                c['challenge_stage'] = 1 # Move to next stage
                self.log(f"\n   **Memory Score**: {memory_score:.0f}/50")
                c['current_trial'] = 0 # Reset trial counter for new stage
            else:
                # Prepare next memory trial
                pos = random.randint(1, 9)
                let = random.choice(self.puzzles["letters"])
                c['pos_hist'].append(pos)
                c['let_hist'].append(let)
                c['current_trial'] += 1
                st.session_state.current_challenge = c
                return # Stay on the memory UI
                
        if c['challenge_stage'] == 1: # Perspective
            response = user_inputs.get('response_text', '')
            if response:
                perspective_score = min(50, len(response.split()) * 2)  # Rough score based on depth
                c['score'] += perspective_score
                c['challenge_stage'] = 2 # Move to next stage
                self.log(f"\n   **Perspective Score**: {perspective_score:.0f}/50")
            else:
                # If no response, stay on stage 1 (first run or user hasn't submitted)
                st.session_state.current_challenge = c
                return
                
        if c['challenge_stage'] == 2: # Meta-cognition
            response = user_inputs.get('response_text', '')
            if response:
                meta_score = min(50, len(response.split()) * 2)
                c['score'] += meta_score
                c['challenge_stage'] = 3 # Move to end
                self.log(f"\n   **Meta-cognition Score**: {meta_score:.0f}/50")
            else:
                # If no response, stay on stage 2
                st.session_state.current_challenge = c
                return
                
        if c['challenge_stage'] == 3: # End
            self.boss_arena_end(c)
            return

        st.session_state.current_challenge = c
        
    def boss_arena_end(self, c):
        # c['score'] now holds the sum of the three challenges (max 50+50+50=150)
        final_boss_score = min(200, c['score'] + 50)  # Base bonus
        self.log(f"\n**🏁 BOSS ARENA TOTAL**: {final_boss_score:.0f}/200")
        
        if final_boss_score > 150:
            self.log("🎉 BOSS DEFEATED! Ultimate Victory!")
            self.award_badge("Cognitive Champion")
        elif final_boss_score > 120:
            self.log("✅ Boss challenged met! Good work!")
            self.award_badge("Arena Master")
        else:
            self.log("💪 Boss gave you a good fight. Train more!")
            
        self.gain_xp(int(final_boss_score))
        self.go_to_menu_after_delay()

    def daily_challenge_init(self):
        random.seed(self.daily_seed)
        challenge_type = random.randint(0, 4)  # 0-3 for worlds, 4 for meta
        world_index = challenge_type if challenge_type < 4 else -1
        
        self.log("\n⚡ DAILY CHALLENGE!")
        self.log("\nToday's special challenge awaits!")
        
        # Set level to a high value (8) to ensure hard mode
        level_for_challenge = 8 
        
        # Initiate the chosen game mode in 'daily' mode
        if challenge_type == 0:
            self.memory_boost_init(level_for_challenge)
            st.session_state.current_challenge['mode'] = 'daily_memory'
        elif challenge_type == 1:
            self.view_switch_init(level_for_challenge)
            st.session_state.current_challenge['mode'] = 'daily_view_switch'
        elif challenge_type == 2:
            self.step_logic_init(level_for_challenge)
            st.session_state.current_challenge['mode'] = 'daily_step_logic'
        elif challenge_type == 3:
            self.ai_play_init(level_for_challenge)
            st.session_state.current_challenge['mode'] = 'daily_ai_play'
        else:
            self.meta_cognition_init()
            st.session_state.current_challenge['mode'] = 'daily_meta_cognition'
            
        st.session_state.current_challenge['world_index'] = world_index
        st.session_state.current_challenge['is_daily'] = True

    def complete_daily_challenge(self, success):
        # Generic completion logic for any daily mode
        if success:
            self.log("\n🎉 DAILY CHALLENGE COMPLETED! +100 XP")
            self.gain_xp(100)
            self.award_badge("Daily Champion")
        else:
            self.log("\n💪 Good attempt! +50 XP for trying")
            self.gain_xp(50)
            
        st.session_state.current_challenge['is_daily'] = False # Cleanup
        self.go_to_menu_after_delay()
        
    def go_to_menu_after_delay(self):
        # We use a button to transition back to the main menu for better UI flow
        st.session_state.current_view = 'results_summary'
        

# --- STREAMLIT UI FUNCTIONS ---

def set_view(view_name):
    st.session_state.current_view = view_name
    st.session_state.game_output = [] # Clear output for new screen

def go_to_menu():
    set_view('main_menu')
    st.session_state.game_output = [] # Clear output for new screen

def render_stats_dashboard(game_instance):
    player = st.session_state.player
    st.subheader(f"👋 Welcome back, {player['name']}!")
    
    col_level, col_xp, col_streak = st.columns(3)
    col_level.metric("🏆 Level", player['level'])
    col_xp.metric("✨ XP", player['xp'])
    col_streak.metric("🔥 Streak", f"{player['streak']} days", player.get('total_sessions', 1))

    st.markdown("---")
    st.markdown("#### 🧠 Cognitive Mastery")
    
    names = ["Memory Boost", "Perspective Switch", "Step Logic", "AI Prompting"]
    data = []
    for i, hs in enumerate(player["high_scores"]):
        level = player["world_unlocks"][i] + 1
        avg_score = hs # Simplified, terminal used an average
        mastery = "⭐" * min(5, level // 3) + "✩" * (5 - min(5, level // 3))
        data.append({
            "Technique": names[i], 
            "High Score": hs, 
            "Level": level, 
            "Mastery": mastery
        })

    df = pd.DataFrame(data)
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "High Score": st.column_config.NumberColumn(format="%d"),
            "Level": st.column_config.NumberColumn(format="%d")
        }
    )

    if player["badges"]:
        st.markdown(f"#### 🎖️ Badges")
        st.info(" | ".join(player["badges"]))


def render_game_output(placeholder):
    """Renders the game log in a dedicated placeholder."""
    # Use Markdown for formatting, especially for the log
    markdown_output = "\n".join(st.session_state.game_output)
    placeholder.markdown(f'<div style="max-height: 250px; overflow-y: auto; padding: 10px; border: 1px solid #333; border-radius: 8px; background-color: #0e1117; font-family: monospace;">{markdown_output}</div>', unsafe_allow_html=True)
    # Scroll to the bottom of the log (simulated)
    # Streamlit doesn't natively support scrolling to the bottom of a container without custom JS, 
    # but the style above helps contain the log.


def render_main_menu(game_instance):
    st.title("🌟 NeuroAI Quest")
    st.markdown("Train Your Brain to Think Like AI")
    st.markdown("---")

    col_menu, col_stats = st.columns([1, 2])
    
    with col_stats:
        render_stats_dashboard(game_instance)

    with col_menu:
        st.header("🎮 Training Selection")
        
        # Use a consistent function to trigger the world/mode init
        def start_world(index):
            game_instance.play_world(index)

        st.button("🧠 World 1: Memory Boost", on_click=start_world, args=[0], use_container_width=True)
        st.button("🔄 World 2: Perspective Switch", on_click=start_world, args=[1], use_container_width=True)
        st.button("⚙️ World 3: Step Logic", on_click=start_world, args=[2], use_container_width=True)
        st.button("🤖 World 4: AI Prompting", on_click=start_world, args=[3], use_container_width=True)
        
        st.divider()
        st.button("🤔 Meta-Cognition Training", on_click=game_instance.meta_cognition_init, use_container_width=True)
        st.button("⚡ Daily Challenge", on_click=game_instance.daily_challenge_init, use_container_width=True)
        
        boss_disabled = st.session_state.player['level'] < 3
        st.button("👑 Boss Arena", 
                  on_click=game_instance.boss_arena_init, 
                  disabled=boss_disabled,
                  help="Unlocks at Level 3!", 
                  use_container_width=True)
        
        st.divider()
        st.download_button(
            label="⬇️ Save Game",
            data=json.dumps(st.session_state.player, indent=2),
            file_name="neuroai_save.json",
            mime="application/json",
            use_container_width=True
        )
        
    st.markdown("---")
    st.header("Game Log")


def render_memory_boost_game(game_instance):
    c = st.session_state.current_challenge
    
    st.title("🧠 Memory Boost (Dual N-Back)")
    st.subheader(f"N={c['n']} | Trial {c['current_trial']}/{c['trials']} | Score: {c['score']}")
    
    # Check if we are ready to display the first stimulus (after the first click)
    if c['current_trial'] > 0:
        pos_index = c['pos_hist'][-1] - 1
        letter = c['let_hist'][-1]
        
        # Grid visualization
        st.markdown("### 🎯 Current Stimulus")
        grid_html = """
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; width: 300px; margin: 20px auto;">
        """
        # Create the 3x3 grid
        for i in range(9):
            is_active = (i == pos_index)
            # Conditional styling for the active cell
            style = "background-color: #ff4b4b; color: white; font-size: 24px; font-weight: bold;" if is_active else "background-color: #0e1117; color: #444; border: 1px solid #444;"
            
            # Display the letter only in the active cell
            cell_content = letter if is_active else str(i+1)
            
            grid_html += f'<div style="{style} padding: 10px; height: 50px; text-align: center; border-radius: 5px; display: flex; align-items: center; justify-content: center;">{cell_content}</div>'
        
        grid_html += "</div>"
        st.markdown(grid_html, unsafe_allow_html=True)

        # --- Input form for the CURRENT trial's check (for the stimulus that appeared N trials ago) ---

        # Determine the form key
        form_key = f"memory_form_{c['current_trial']}"
        button_label = "Finish Challenge" if c['current_trial'] == c['trials'] else f"Submit Trial {c['current_trial']} & Next Stimulus"
        
        # If this is the first trial (current_trial = 1), there is no check yet, so skip the form
        if c['current_trial'] > c['n']: 
            
            # Check for the submission of the previous trial
            with st.form(key=form_key):
                st.markdown(f"#### Trial {c['current_trial'] - 1} Check (For stimulus that appeared {c['n']} steps ago)")
                
                col_pos, col_let = st.columns(2)
                # We use internal keys here which Streamlit automatically manages in session_state upon submission
                user_pos_match = col_pos.checkbox(f"Position match (N={c['n']} back)?", key=f'check_pos_{c["current_trial"]}')
                user_let_match = col_let.checkbox(f"Letter match (N={c['n']} back)?", key=f'check_let_{c["current_trial"]}')
                
                # IMPORTANT: Use the lambda function to pass the inputs to the core logic on button click
                submitted = st.form_submit_button(
                    button_label, 
                    on_click=game_instance.memory_boost_next_trial,
                    args=[user_pos_match, user_let_match],
                    use_container_width=True
                )
        
        # If we are past N, but before the end of the trials, we just need a button to move to the next trial
        elif c['current_trial'] <= c['n'] and c['current_trial'] < c['trials']:
            # For the first N trials, we just display the stimulus and move on without a match check.
            st.info(f"Displaying stimulus. Match check will start after trial {c['n']}.")
            
            # Create a simple button outside a form just to advance the stimulus during the initial N steps
            st.button(f"Next Stimulus ({c['current_trial']}/{c['trials']})", 
                      on_click=game_instance.memory_boost_next_trial, 
                      args=[False, False], # Pass dummy values since no checking is done
                      key=f'advance_stimulus_{c["current_trial"]}',
                      use_container_width=True)
            
        elif c['current_trial'] == c['trials']:
             # This is the very last submission, which needs to be a check. It is handled by the form above.
             st.info("Last stimulus displayed. Check your matches and click 'Finish Challenge'.")


    else:
        # Initial screen to start the first trial (current_trial = 0)
        st.info(f"The Dual N-Back test requires you to track the position and the letter shown on the grid, and report if the current one matches the one from {c['n']} steps back.")
        # This button starts the first trial (c['current_trial'] becomes 1)
        st.button("Start First Trial", 
                  on_click=game_instance.memory_boost_next_trial, 
                  args=[False, False], # Dummy arguments for the first call
                  use_container_width=True)

    st.markdown("---")
    st.header("Game Log")


def render_view_switch_game(game_instance):
    c = st.session_state.current_challenge
    
    st.title("🔄 View Switch: Multi-Perspective Puzzle")
    st.subheader(f"Scenario: {c['scenario']}")
    
    # Handle the initial click (current_view_index = 0)
    if c['current_view_index'] == 0:
        st.info("Click 'Start Analysis' to begin the first perspective.")
        st.button("Start Analysis", on_click=game_instance.view_switch_next, args=[""], use_container_width=True)
        st.markdown("---")
        st.header("Game Log")
        return
    
    # Display the current perspective prompt
    view_index = c['current_view_index'] - 1
    view_name = c['views'][view_index]
    
    st.markdown(f"#### Perspective {c['current_view_index']}/{c['num_views']}: **{view_name}**")
    
    with st.form(key=f"view_switch_form_{c['current_view_index']}"):
        response_text = st.text_area(f"What are the key considerations from the **{view_name}** viewpoint?", height=150)
        
        is_final_step = c['current_view_index'] == c['num_views']
        button_label = "Finish Challenge" if is_final_step else "Next Perspective"
        
        submitted = st.form_submit_button(button_label, use_container_width=True)
        
        if submitted:
            if response_text.strip() == "":
                 st.error("Please provide an analysis before moving on.")
            else:
                game_instance.view_switch_next(response_text)
                st.rerun()

    st.markdown("---")
    st.header("Game Log")


def render_step_logic_game(game_instance):
    c = st.session_state.current_challenge
    
    st.title("⚙️ Step Logic: Riddle Breaker")
    st.subheader(f"Riddle: {c['riddle']}")
    
    # Handle the initial click (current_step = 0)
    if c['current_step'] == 0:
        st.info("Click 'Start Logic' to begin breaking down the riddle.")
        st.button("Start Logic", on_click=game_instance.step_logic_next, args=[""], use_container_width=True)
        st.markdown("---")
        st.header("Game Log")
        return

    step_index = c['current_step']
    
    with st.form(key=f"step_logic_form_{step_index}"):
        response_text = st.text_input(f"Step {step_index}/{c['num_steps']}: Describe the next logical action.")
        
        is_final_step = c['current_step'] == c['num_steps']
        button_label = "Finish Challenge" if is_final_step else "Submit Step"
        
        submitted = st.form_submit_button(button_label, use_container_width=True)
        
        if submitted:
            if response_text.strip() == "":
                 st.error("Please describe your step before moving on.")
            else:
                game_instance.step_logic_next(response_text)
                st.rerun()
                
    st.markdown("---")
    st.header("Game Log")


def render_ai_play_game(game_instance):
    c = st.session_state.current_challenge
    
    st.title("🤖 AI Play: Killer Prompt Forge")
    st.subheader(f"🎯 Target: **{c['target']}**")
    st.info("Craft the perfect prompt to get amazing AI results! Use roles, steps, constraints, and clear output formats.")
    
    with st.form(key="ai_play_form"):
        prompt = st.text_area("Your killer prompt:", height=200)
        
        submitted = st.form_submit_button("Simulate AI Response & Score Prompt", use_container_width=True)
        
        if submitted:
            if prompt.strip() == "":
                 st.error("Please enter a prompt to be scored.")
            else:
                game_instance.ai_play_end(prompt)
                st.rerun()
                
    st.markdown("---")
    st.header("Game Log")


def render_meta_cognition_game(game_instance):
    c = st.session_state.current_challenge
    
    st.title("🤔 Meta-Cognition Training")
    st.subheader(f"💡 Problem: **{c['problem']}**")
    
    # Handle the initial click (current_mode_index = 0)
    if c['current_mode_index'] == 0:
        st.info("Click 'Start Meta-Analysis' to begin applying the first thinking mode.")
        st.button("Start Meta-Analysis", on_click=game_instance.meta_cognition_next, args=[""], use_container_width=True)
        st.markdown("---")
        st.header("Game Log")
        return

    mode_index = c['current_mode_index'] - 1
    
    if mode_index < len(c['selected_modes']):
        mode_name, mode_desc = c['selected_modes'][mode_index]
        st.markdown(f"#### 🔄 Mode {c['current_mode_index']}/{len(c['selected_modes'])}: **{mode_name.upper()}**")
        st.info(mode_desc)
    
        with st.form(key=f"meta_cognition_form_{c['current_mode_index']}"):
            response_text = st.text_area(f"Apply the **{mode_name}** mode to the problem:", height=150)
            
            is_final_step = c['current_mode_index'] == len(c['selected_modes'])
            button_label = "Finish Challenge" if is_final_step else "Next Thinking Mode"
            
            submitted = st.form_submit_button(button_label, use_container_width=True)
            
            if submitted:
                if response_text.strip() == "":
                    st.error("Please enter your analysis before moving on.")
                else:
                    game_instance.meta_cognition_next(response_text)
                    st.rerun()

    st.markdown("---")
    st.header("Game Log")


def render_boss_arena_game(game_instance):
    c = st.session_state.current_challenge
    st.title("👑 Boss Arena")
    
    # Handle the initial click (current_trial = 0)
    if c['challenge_stage'] == 0 and c['current_trial'] == 0:
        st.info("The Boss Arena is a multi-stage challenge. Click below to begin the first stage.")
        st.button("Start Boss Arena", on_click=lambda: game_instance.boss_arena_next(), use_container_width=True)
        st.markdown("---")
        st.header("Game Log")
        return

    if c['challenge_stage'] == 0:
        # --- Memory N-Back ---
        
        st.subheader(f"⚡ Challenge 1/3: Lightning Memory (N={c['n']})")
        st.markdown(f"**Trial {c['current_trial']}/{c['trials']}** | Score: {c['score']:.0f}/50")
        
        # Display the current stimulus
        pos_index = c['pos_hist'][-1] - 1
        letter = c['let_hist'][-1]
        
        st.markdown("### 🎯 Current Stimulus")
        col_pos, col_let = st.columns(2)
        col_pos.metric("Position", pos_index + 1)
        col_let.metric("Letter", letter)

        # Input form for the NEXT trial
        form_key = f"boss_memory_form_{c['current_trial']}"
        button_label = "Finish Memory Stage" if c['current_trial'] == c['trials'] else "Submit & Next Stimulus"

        # Check only for the trials where checking is necessary (i.e., past N)
        if c['current_trial'] > c['n']:
            with st.form(key=form_key):
                st.markdown(f"#### Submit Match for Previous Stimulus")
                
                col_pos_check, col_let_check = st.columns(2)
                # Use unique keys within the form
                user_pos_match = col_pos_check.checkbox(f"Position match (N={c['n']} back)?", key=f'boss_check_pos_{c["current_trial"]}')
                user_let_match = col_let_check.checkbox(f"Letter match (N={c['n']} back)?", key=f'boss_check_let_{c["current_trial"]}')
                
                submitted = st.form_submit_button(
                    button_label, 
                    on_click=game_instance.boss_arena_next,
                    args=[{'user_pos_match': user_pos_match, 'user_let_match': user_let_match}],
                    use_container_width=True
                )
        else:
            # For the first N trials, just advance the stimulus
            st.info(f"Displaying stimulus. Match check will start after trial {c['n']}.")
            st.button(f"Next Stimulus ({c['current_trial']}/{c['trials']})", 
                      on_click=game_instance.boss_arena_next, 
                      args=[{'user_pos_match': False, 'user_let_match': False}],
                      key=f'boss_advance_stimulus_{c["current_trial"]}',
                      use_container_width=True)


    elif c['challenge_stage'] == 1:
        # --- Perspective Shift ---
        st.subheader("🔄 Challenge 2/3: Instant Perspective Shift")
        st.markdown(f"**Scenario**: {c['scenario']}")
        st.markdown(f"**Perspective**: {c['perspective']}")
        
        with st.form(key="boss_perspective_form"):
            response_text = st.text_area("Your quick analysis from this perspective:", height=150)
            
            submitted = st.form_submit_button("Submit Analysis & Next Challenge", use_container_width=True)
            
            if submitted:
                if response_text.strip() == "":
                    st.error("Please enter your analysis before moving on.")
                else:
                    game_instance.boss_arena_next({'response_text': response_text})
                    st.rerun()

    elif c['challenge_stage'] == 2:
        # --- Meta-cognition ---
        st.subheader("🤔 Challenge 3/3: Thinking About Thinking")
        st.markdown("How would you improve your own approach to the two previous challenges (Memory & Perspective)?")
        
        with st.form(key="boss_meta_form"):
            response_text = st.text_area("Your reflection:", height=150)
            
            submitted = st.form_submit_button("Finish Boss Arena", use_container_width=True)
            
            if submitted:
                if response_text.strip() == "":
                    st.error("Please enter your reflection before finishing.")
                else:
                    game_instance.boss_arena_next({'response_text': response_text})
                    st.rerun()

    st.markdown("---")
    st.header("Game Log")


def render_results_summary(game_instance):
    st.title("Challenge Complete")
    st.markdown("Review the log below for your results and rewards.")
    
    st.markdown("---")
    st.header("Game Log")
    
    st.button("Back to Main Menu", on_click=go_to_menu, use_container_width=True)

# --- MAIN APP EXECUTION ---

def main():
    # Streamlit configuration
    st.set_page_config(
        page_title="NeuroAI Quest",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Apply custom, modern styling
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            
            html, body, [class*="st-emotion-"] {
                font-family: 'Inter', sans-serif;
            }
            .main-header {
                font-size: 3em;
                color: #ff4b4b; /* Streamlit red/pink */
                font-weight: 700;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
                text-align: center;
                margin-bottom: 20px;
            }
            .stButton>button {
                border-radius: 8px;
                border: 1px solid #ff4b4b;
                color: #ff4b4b;
                background-color: #1c1c1c;
                transition: all 0.2s;
                font-weight: 600;
                box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.3);
            }
            .stButton>button:hover:enabled {
                background-color: #ff4b4b;
                color: white;
                box-shadow: 4px 4px 10px rgba(255, 75, 75, 0.5);
                transform: translateY(-2px);
            }
            .stDataFrame {
                border-radius: 8px;
            }
            /* Custom log box styling */
            div[data-testid="stMarkdownContainer"] div {
                 white-space: pre-wrap;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="main-header">🌟 NEUROAI QUEST</div>', unsafe_allow_html=True)
    
    # Initialize game instance and session state
    game = NeuroAIQuest()
    game.initialize_session_state()

    # Create a persistent placeholder for the game log
    log_placeholder = st.empty() 

    # --- UI Renderer Dispatch ---
    view = st.session_state.current_view
    
    if view == 'main_menu':
        render_main_menu(game)
    elif view == 'memory_boost_game':
        render_memory_boost_game(game)
    elif view == 'view_switch_game':
        render_view_switch_game(game)
    elif view == 'step_logic_game':
        render_step_logic_game(game)
    elif view == 'ai_play_game':
        render_ai_play_game(game)
    elif view == 'meta_cognition_game':
        render_meta_cognition_game(game)
    elif view == 'boss_arena_game':
        render_boss_arena_game(game)
    elif view == 'results_summary':
        render_results_summary(game)

    # Always render the log at the end of the script execution to capture all updates
    render_game_output(log_placeholder)
    
# Function to load game from uploaded file
def handle_load_game(uploaded_file):
    if uploaded_file is not None:
        try:
            player_data = json.load(uploaded_file)
            st.session_state.player = player_data
            st.session_state.current_view = 'main_menu'
            st.session_state.game_output = ["Game loaded successfully! Welcome back."]
            st.rerun()
        except Exception as e:
            st.error(f"Error loading game file: {e}")

# Separate file uploader logic must be run outside of the main loop to initialize session state correctly
if 'player' not in st.session_state:
    st.sidebar.title("Load Game")
    uploaded_file = st.sidebar.file_uploader("Upload your neuroai_save.json", type="json")
    st.sidebar.button("Load Game", on_click=handle_load_game, args=[uploaded_file])
    
    # If not loading a game, run the main app
    if 'player' in st.session_state:
        main()
    else:
        # Initial screen for new user/first run setup
        st.title("NeuroAI Quest - Setup")
        st.info("Welcome, new AI Apprentice! Press the button below to start a new game or use the sidebar to load a previous save.")
        
        if st.button("Start New Game"):
            # Initialize the session state and start the game
            game = NeuroAIQuest()
            game.initialize_session_state()
            # Rerun the script to move to main() with initialized state
            st.rerun()

else:
    main()
