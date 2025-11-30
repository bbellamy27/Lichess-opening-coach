import pandas as pd

def process_games(games, username):
    """
    Process raw game data into a Pandas DataFrame suitable for analysis.
    
    This function extracts key metrics like ratings, results, and opening info,
    and enriches the data with time-based and opponent-based features.
    
    Args:
        games (list): List of game dictionaries from Lichess API.
        username (str): The username of the player to analyze (used to determine color).
        
    Returns:
        pd.DataFrame: Processed DataFrame containing one row per game.
    """
    if not games:
        return pd.DataFrame()

    processed_data = []
    
    for game in games:
        # --- Extract Basic Info ---
        game_id = game.get('id')
        rated = game.get('rated', False)
        variant = game.get('variant', 'standard')
        speed = game.get('speed')
        perf = game.get('perf')
        created_at = game.get('createdAt') # Timestamp in milliseconds
        
        # --- Extract Player Info ---
        white = game.get('players', {}).get('white', {})
        black = game.get('players', {}).get('black', {})
        
        white_user = white.get('user', {}).get('name', 'Unknown')
        black_user = black.get('user', {}).get('name', 'Unknown')
        
        white_rating = white.get('rating')
        black_rating = black.get('rating')
        
        # --- Determine User's Color & Stats ---
        # We need to know if the user played White or Black to calculate results correctly
        if white_user.lower() == username.lower():
            user_color = 'white'
            opponent_rating = black_rating
            user_rating = white_rating
        else:
            user_color = 'black'
            opponent_rating = white_rating
            user_rating = black_rating
            
        # --- Determine Result ---
        winner = game.get('winner') # 'white', 'black', or None (draw)
        if winner:
            if winner == user_color:
                result = 'Win'
            else:
                result = 'Loss'
        else:
            result = 'Draw'
            
        # --- Extract Opening Info ---
        opening = game.get('opening', {})
        eco = opening.get('eco') # ECO code (e.g., B01)
        opening_name = opening.get('name')
        
        # --- Calculate Move Count ---
        moves = game.get('moves', '')
        # Calculate ply (half-moves)
        ply_count = len(moves.split()) if moves else 0
        
        # --- Advanced Features (Phase 2) ---
        
        # 1. Game Termination Status
        status = game.get('status') # e.g., mate, resign, outoftime, draw
        
        # 2. Time Analysis
        # Convert timestamp to datetime object
        dt = pd.to_datetime(created_at, unit='ms')
        
        # 3. Opponent Rating Binning
        # Group opponents into rating ranges for analysis
        if opponent_rating:
            if opponent_rating < 1000: op_bin = "<1000"
            elif 1000 <= opponent_rating < 1200: op_bin = "1000-1200"
            elif 1200 <= opponent_rating < 1400: op_bin = "1200-1400"
            elif 1400 <= opponent_rating < 1600: op_bin = "1400-1600"
            elif 1600 <= opponent_rating < 1800: op_bin = "1600-1800"
            elif 1800 <= opponent_rating < 2000: op_bin = "1800-2000"
            elif 2000 <= opponent_rating < 2200: op_bin = "2000-2200"
            else: op_bin = "2200+"
        else:
            op_bin = "Unknown"

        # Append processed game to list
        processed_data.append({
            'game_id': game_id,
            'date': dt,
            'hour': dt.hour,
            'day_of_week': dt.day_name(),
            'variant': variant,
            'speed': speed,
            'user_color': user_color,
            'user_rating': user_rating,
            'opponent_rating': opponent_rating,
            'opponent_rating_bin': op_bin,
            'result': result,
            'termination': status,
            'eco': eco,
            'eco': eco,
            'opening_name': opening_name,
            'ply_count': ply_count
        })
        
    # Convert list of dicts to DataFrame
    df = pd.DataFrame(processed_data)
    return df

def get_opening_stats(df):
    """
    Calculate aggregate statistics for each opening played.
    
    Args:
        df (pd.DataFrame): The processed games DataFrame.
        
    Returns:
        pd.DataFrame: DataFrame with columns [opening_name, games, wins, draws, losses, avg_rating, win_rate]
    """
    if df.empty:
        return pd.DataFrame()
        
    # Group by opening name and aggregate results
    stats = df.groupby('opening_name').agg(
        games=('game_id', 'count'),
        wins=('result', lambda x: (x == 'Win').sum()),
        draws=('result', lambda x: (x == 'Draw').sum()),
        losses=('result', lambda x: (x == 'Loss').sum()),
        avg_rating=('user_rating', 'mean')
    ).reset_index()
    
    # Calculate Win Rate
    stats['win_rate'] = stats['wins'] / stats['games']
    
    # Sort by most played openings
    stats = stats.sort_values('games', ascending=False)
    
    return stats

def calculate_risk_metrics(df):
    """
    Calculate a 'Risk/Aggressiveness' score (1-10) based on game data.
    
    Heuristic:
    - Low Draw Rate = Higher Risk
    - Short Game Length = Higher Risk
    
    Returns:
        dict: {
            'score': float (1-10),
            'label': str,
            'feedback': str,
            'mistakes': str,
            'improvement': str
        }
    """
    if df.empty:
        return {
            'score': 0, 
            'label': "N/A", 
            'feedback': "Not enough data.",
            'mistakes': "N/A",
            'improvement': "Play more games!",
            'explanation': "Not enough data to calculate volatility."
        }
        
    # 1. Draw Rate Factor (0-10)
    # Online chess has fewer draws. We calibrate so ~10% draw rate is "Balanced" (Score 5).
    # >20% draw rate -> Score 0 (Solid)
    # <2% draw rate -> Score 9-10 (Berserker)
    total_games = len(df)
    draws = len(df[df['result'] == 'Draw'])
    draw_rate = draws / total_games if total_games > 0 else 0
    
    # Formula: (1 - (draw_rate * 5)) * 10. Clamped 0-10.
    draw_factor = max(0, (1 - (draw_rate * 5))) * 10
    
    # 2. Game Length Factor (0-10)
    # Avg 20 moves -> Score 10 (Quick kills/deaths)
    # Avg 60 moves -> Score 0 (Long grinds)
    avg_ply = df['ply_count'].mean()
    avg_moves = avg_ply / 2
    
    # Formula: (60 - avg_moves) / 4. Clamped 0-10.
    length_factor = max(0, min(10, (60 - avg_moves) / 4))
    
    # Weighted Average: 50% Draw Rate, 50% Length
    risk_score = (draw_factor * 0.5) + (length_factor * 0.5)
    risk_score = round(max(1, min(10, risk_score)), 1)
    
    # Determine Label and Feedback
    # Determine Label and Feedback based on 1-10 Score
    int_score = int(risk_score)
    
    risk_profiles = {
        1: {
            "label": "The Wall 🧱",
            "feedback": "You are incredibly hard to beat. You take zero risks.",
            "improvement": "You might be missing wins by being too passive. Try to complicate the game when you have an advantage."
        },
        2: {
            "label": "Safety First 🛡️",
            "feedback": "You prioritize safety above all else. You rarely blunder.",
            "improvement": "Don't be afraid of ghosts. Sometimes the sharpest move is the safest path to victory."
        },
        3: {
            "label": "Cautious Player 🔒",
            "feedback": "You prefer solid, positional games. You avoid complications.",
            "improvement": "Work on your tactical vision. You need to be able to calculate sharp lines when forced."
        },
        4: {
            "label": "Solid & Steady 🗿",
            "feedback": "You play sound chess. You don't give away free gifts.",
            "improvement": "Expand your opening repertoire to include some semi-open games to practice dynamic play."
        },
        5: {
            "label": "Balanced ⚖️",
            "feedback": "You have a perfect mix of solid play and aggression.",
            "improvement": "Maintain this balance. Focus on deep strategic understanding to improve further."
        },
        6: {
            "label": "Calculated Risk 📐",
            "feedback": "You are willing to take risks, but only when you've calculated them.",
            "improvement": "Trust your intuition in complex positions where you can't calculate everything."
        },
        7: {
            "label": "Aggressive ⚔️",
            "feedback": "You actively look for attacking chances. You put pressure on opponents.",
            "improvement": "Ensure your attacks are sound. Don't attack just for the sake of attacking."
        },
        8: {
            "label": "Attacker 🏹",
            "feedback": "You are always moving forward. You hate defending.",
            "improvement": "Learn to defend! Sometimes the best way to win is to weather the storm and counter-attack."
        },
        9: {
            "label": "Daredevil 🧨",
            "feedback": "You live on the edge. You sacrifice material for initiative frequently.",
            "improvement": "Calm down. Not every position requires a sacrifice. Learn to play quiet moves."
        },
        10: {
            "label": "Chaos Agent 🌪️",
            "feedback": "You want the board to burn. Win or lose, it will be spectacular.",
            "improvement": "You are gambling, not playing chess. Focus on 'prophylaxis' and king safety."
        }
    }
    
    profile = risk_profiles.get(int_score, risk_profiles[5])
    label = profile['label']
    feedback = profile['feedback']
    improvement = profile['improvement']
    mistakes = "N/A" # Deprecated in favor of specific improvement
    
    explanation = "Calculated based on your Draw Rate (lower = higher volatility) and Average Game Length (shorter = higher volatility)."
        
    return {
        'score': risk_score,
        'label': label,
        'feedback': feedback,
        'mistakes': mistakes,
        'improvement': improvement,
        'explanation': explanation
    }

def calculate_pacing_metrics(df, time_control):
    """
    Calculate a 'Pacing' score (Fast/Slow/Right) based on avg game length and Time Control.
    
    Args:
        df (pd.DataFrame): Filtered dataframe.
        time_control (str): 'rapid', 'blitz', 'bullet', 'classical', or 'overall'.
        
    Returns:
        dict: { 'label': str, 'color': str, 'avg_moves': int, 'feedback': str }
    """
    if df.empty:
        return {'label': "N/A", 'color': "gray", 'avg_moves': 0, 'feedback': "No data."}
        
    avg_ply = df['ply_count'].mean()
    avg_moves = int(avg_ply / 2)
    
    # Calculate Win Rate for Context
    wins = len(df[df['result'] == 'Win'])
    total = len(df)
    win_rate = wins / total if total > 0 else 0
    
    tc = time_control.lower()
    
    # Target Moves for "Average" Pacing (Score 5.5)
    targets = {
        'bullet': 30,
        'blitz': 35,
        'rapid': 40,
        'classical': 45,
        'overall': 35
    }
    target = targets.get(tc, 35)
    
    # Calculate Pacing Score (1-10)
    # 1 = Extremely Fast, 10 = Extremely Slow
    # Scale: +/- 15 moves from target covers the full range
    diff = avg_moves - target
    # Map diff to score: -15 -> 1, +15 -> 10
    raw_score = 5.5 + (diff / 3.5)
    pacing_score = int(max(1, min(10, round(raw_score))))
    
    # Define 10 Archetypes based on Score and Win Rate
    # High Win Rate threshold
    high_wr = 0.55
    
    if pacing_score <= 2: # Extremely Fast
        if win_rate > high_wr:
            label = "Intuitive Genius ⚡"
            color = "#00E676" # Bright Green
            feedback = f"Avg {avg_moves} moves. You play instantly and crush opponents. Your intuition is terrifying."
            improvement = "You are a natural talent. Study complex tactical patterns to sharpen your greatest weapon."
        else:
            label = "Suicidal Sprinter 🧨"
            color = "#D50000" # Deep Red
            feedback = f"Avg {avg_moves} moves. You play way too fast and lose. You are essentially gambling."
            improvement = "Stop! Sit on your hands. Force yourself to check for blunders before every single move."
            
    elif pacing_score <= 4: # Fast
        if win_rate > high_wr:
            label = "Sharp Shooter 🔫"
            color = "#66BB6A" # Light Green
            feedback = f"Avg {avg_moves} moves. You play aggressively and it pays off. You put pressure on opponents."
            improvement = "Maintain this energy. Ensure your opening repertoire supports this aggressive style."
        else:
            label = "Impulsive Mover 🐇"
            color = "#FF5252" # Red-Orange
            feedback = f"Avg {avg_moves} moves. You move a bit too quickly in critical moments, missing chances."
            improvement = "Slow down only when the position is complex. Learn to recognize 'critical moments'."
            
    elif pacing_score <= 6: # Average
        if win_rate > high_wr:
            label = "Balanced Pacer ⚖️"
            color = "#29B6F6" # Light Blue
            feedback = f"Avg {avg_moves} moves. Your pacing is perfect. You manage your time well."
            improvement = "You have a solid foundation. Focus on deep strategic understanding to improve further."
        else:
            label = "Drifting Aimlessly 🍂"
            color = "#FFA726" # Orange
            feedback = f"Avg {avg_moves} moves. Your pace is normal, but you aren't winning enough. You might be lacking a plan."
            improvement = "Work on 'planning'. Don't just make moves; have a clear goal for every stage of the game."
            
    elif pacing_score <= 8: # Slow
        if win_rate > high_wr:
            label = "Deep Thinker 🧠"
            color = "#42A5F5" # Blue
            feedback = f"Avg {avg_moves} moves. You take your time and find good moves. Your calculation is an asset."
            improvement = "Keep calculating, but practice 'pattern recognition' to speed up simple decisions."
        else:
            label = "Time Trouble Addict ⏳"
            color = "#FF7043" # Orange-Red
            feedback = f"Avg {avg_moves} moves. You think too long and likely blunder in time pressure."
            improvement = "Trust your gut on simple moves. Save your time for the complicated positions."
            
    else: # Extremely Slow (9-10)
        if win_rate > high_wr:
            label = "Grind Master 🐢"
            color = "#1E88E5" # Dark Blue
            feedback = f"Avg {avg_moves} moves. You torture opponents in long endgames. You have immense patience."
            improvement = "Your endgame technique is key. Study 'endgame studies' to perfect your grinding skills."
        else:
            label = "Paralysis by Analysis 🧊"
            color = "#B71C1C" # Dark Red
            feedback = f"Avg {avg_moves} moves. You freeze up and overthink everything. You are your own worst enemy."
            improvement = "Set a strict time limit per move in your head. A 'good' move now is better than a 'perfect' move when your flag falls."

    return {
        'label': label,
        'color': color,
        'avg_moves': avg_moves,
        'feedback': feedback,
        'improvement': improvement
    }

import chess
import chess.pgn
import io

def calculate_time_stats(games, username, time_control="overall", pacing_label="N/A"):
    """
    Calculate average time spent per move in Opening, Middlegame, and Endgame.
    
    Definitions:
    - Opening: Moves 1-10
    - Middlegame: Move 11+ while Queens are on board
    - Endgame: Move 11+ after Queens are traded
    
    Args:
        games (list): List of raw game dictionaries (must include 'clocks').
        username (str): User to analyze.
        time_control (str): 'rapid', 'blitz', 'bullet', 'classical', or 'overall'.
        pacing_label (str): The archetype from Pacing Analysis (e.g., "Suicidal Sprinter").
        
    Returns:
        dict: {
            'opening_avg': float, 'opening_feedback': str,
            'middlegame_avg': float, 'middlegame_feedback': str,
            'endgame_avg': float, 'endgame_feedback': str
        }
    """
    opening_times = []
    middlegame_times = []
    endgame_times = []
    
    for game in games:
        # Skip if no clock data
        if 'clocks' not in game:
            continue
            
        # Determine user color and index (White=0, Black=1)
        white_user = game.get('players', {}).get('white', {}).get('user', {}).get('name', 'Unknown')
        user_color = chess.WHITE if white_user.lower() == username.lower() else chess.BLACK
        user_index = 0 if user_color == chess.WHITE else 1
        
        # Get clocks (centiseconds)
        clocks = game.get('clocks', [])
        if not clocks:
            continue
            
        # Get increment (seconds)
        clock_settings = game.get('clock', {})
        increment = clock_settings.get('increment', 0)
        
        # Parse moves to track board state
        moves_str = game.get('moves', '')
        if not moves_str:
            continue
            
        board = chess.Board()
        moves = moves_str.split()
        
        for i, move_san in enumerate(moves):
            try:
                board.push_san(move_san)
            except ValueError:
                break
                
            is_user_move = (i % 2 == 0) if user_color == chess.WHITE else (i % 2 != 0)
            
            if is_user_move:
                if i + 2 >= len(clocks):
                    break
                    
                time_spent = (clocks[i] - clocks[i+2]) / 100 + increment
                time_spent = max(0, time_spent)
                
                move_num = (i // 2) + 1
                
                if move_num <= 10:
                    opening_times.append(time_spent)
                else:
                    queens_on_board = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
                    if queens_on_board > 0:
                        middlegame_times.append(time_spent)
                    else:
                        endgame_times.append(time_spent)

    def safe_avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else 0

    op_avg = safe_avg(opening_times)
    mid_avg = safe_avg(middlegame_times)
    end_avg = safe_avg(endgame_times)
    
    # --- Generate Feedback with Pacing Synergy ---
    
    # Helper to generate phase feedback
    # Helper to generate phase feedback
    def get_feedback(phase, avg_time, target_range, pacing_label):
        low, high = target_range
        
        # Rich Advice Dictionary
        phase_advice = {
            'Opening': {
                'fast': {'reason': "Rushing openings leads to poor structures.", 'tip': "Check for tactical refutations before moving."},
                'slow': {'reason': "Over-thinking theory wastes clock.", 'tip': "Trust your prep and develop pieces naturally."},
                'good': {'reason': "You are balancing development and caution well.", 'tip': "Maintain this rhythm."}
            },
            'Middlegame': {
                'fast': {'reason': "Speed here causes tactical blunders.", 'tip': "Calculate at least 2 candidate moves in complex positions."},
                'slow': {'reason': "Time trouble will ruin your endgame.", 'tip': "Don't calculate everything; rely on patterns."},
                'good': {'reason': "You are allocating time correctly for calculations.", 'tip': "Keep looking for critical moments."}
            },
            'Endgame': {
                'fast': {'reason': "Endgames require precision, not speed.", 'tip': "Count tempos and calculate pawn races carefully."},
                'slow': {'reason': "You risk flagging in winning positions.", 'tip': "If it's theoretical, play confidently."},
                'good': {'reason': "You are navigating the technical phase well.", 'tip': "Stay alert for stalemate tricks."}
            }
        }
        
        # Base Feedback
        if avg_time < low:
            status = "Too Fast"
            base = phase_advice[phase]['fast']
        elif avg_time > high:
            status = "Too Slow"
            base = phase_advice[phase]['slow']
        else:
            status = "On Target"
            base = phase_advice[phase]['good']
            
        reason = base['reason']
        tip = base['tip']
            
        # Synergy: Override/Augment based on Pacing Archetype
        if "Sprinter" in pacing_label or "Impulsive" in pacing_label or "Too Fast" in pacing_label:
            if status == "On Target":
                tip += " But given your 'Fast' style, be careful not to rush critical moments."
            elif status == "Too Fast":
                reason = f"As a '{pacing_label.split()[0]}', you are rushing this phase. {reason}"
                tip = "FORCE yourself to double-check tactics. Sit on your hands."
                
        elif "Time Trouble" in pacing_label or "Paralysis" in pacing_label or "Too Slow" in pacing_label:
            if status == "On Target":
                tip += " Good job staying on target despite your tendency to play slow."
            elif status == "Too Slow":
                reason = f"Typical '{pacing_label.split()[0]}' behavior. {reason}"
                tip = "Set a strict time limit per move. Good enough is better than perfect."
                
        return f"**{status}**\n\nReason: {reason}\n\nTip: {tip}\n\nTarget: {low}-{high}s"

    # Define Targets based on TC
    targets = {
        'bullet': {'open': (0.5, 2), 'mid': (0.5, 3), 'end': (0.5, 3)},
        'blitz': {'open': (2, 5), 'mid': (3, 8), 'end': (3, 10)},
        'rapid': {'open': (5, 10), 'mid': (8, 20), 'end': (8, 25)},
        'classical': {'open': (10, 30), 'mid': (20, 60), 'end': (20, 90)},
        'overall': {'open': (5, 15), 'mid': (10, 30), 'end': (10, 40)}
    }
    t = targets.get(time_control.lower(), targets['overall'])
    
    return {
        'opening_avg': op_avg,
        'opening_feedback': get_feedback("Opening", op_avg, t['open'], pacing_label),
        
        'middlegame_avg': mid_avg,
        'middlegame_feedback': get_feedback("Middlegame", mid_avg, t['mid'], pacing_label),
        
        'endgame_avg': end_avg,
        'endgame_feedback': get_feedback("Endgame", end_avg, t['end'], pacing_label)
    }

def get_synergized_advice(phase, score, pacing_label):
    """
    Generates specific, actionable advice based on:
    1. The Game Phase (Opening, Middlegame, Endgame)
    2. The Accuracy Score (1-10)
    3. The Player's Pacing Style (Fast vs Slow)
    """
    is_fast = "Fast" in pacing_label or "Sprinter" in pacing_label
    is_slow = "Slow" in pacing_label or "Time" in pacing_label
    
    advice = ""
    
    if phase == "Opening":
        if score <= 3:
            if is_fast:
                advice = "You are blitzing out openings and falling into traps.<br><br>👉 <b>Action:</b> Spend at least 10 seconds on move 5-10 to verify you aren't blundering."
            elif is_slow:
                advice = "You are thinking too long in the opening and still getting bad positions.<br><br>👉 <b>Action:</b> Stick to simple system openings (e.g., London, Colle) where memorization is less critical."
            else:
                advice = "Your opening play is fragile.<br><br>👉 <b>Action:</b> Review your last 5 losses. Did you blunder before move 15? If so, check an opening database."
        elif score <= 6:
            if is_fast:
                advice = "You play superficial developing moves.<br><br>👉 <b>Action:</b> Don't just develop pieces; develop them to squares where they attack or control the center."
            elif is_slow:
                advice = "You survive the opening but burn too much time.<br><br>👉 <b>Action:</b> Create a Chessable course for your main white/black repertoire to speed up recall."
            else:
                advice = "Solid but passive.<br><br>👉 <b>Action:</b> Learn one 'gambit' or sharp line to practice handling initiative early on."
        elif score <= 9:
            advice = "Strong opening play.<br><br>👉 <b>Action:</b> To reach level 10, look for 'novelties' or rare sidelines in your main opening to catch opponents off guard."
        else:
            advice = "Master-level opening prep.<br><br>👉 <b>Action:</b> Focus on transitioning to the middlegame plan. Ensure you know the <i>plans</i> not just the moves."

    elif phase == "Middlegame":
        if score <= 3:
            if is_fast:
                advice = "You are missing one-move tactics.<br><br>👉 <b>Action:</b> Sit on your hands. Literally. Do not move until you have checked for checks, captures, and threats."
            elif is_slow:
                advice = "You are hallucinating ghosts.<br><br>👉 <b>Action:</b> Trust your intuition on 'obvious' recaptures and save your calculation for critical moments."
            else:
                advice = "Tactical oversight is your main issue.<br><br>👉 <b>Action:</b> Solve 10 'Mate in 1' and 'Mate in 2' puzzles before every session."
        elif score <= 6:
            if is_fast:
                advice = "You attack prematurely.<br><br>👉 <b>Action:</b> Before launching an attack, ensure you have a piece majority in that sector."
            elif is_slow:
                advice = "You miss opportunities to simplify.<br><br>👉 <b>Action:</b> If you are up material, look for trades. Don't complicate it."
            else:
                advice = "You struggle with planning.<br><br>👉 <b>Action:</b> When no tactics are present, improve your worst-placed piece."
        elif score <= 9:
            advice = "Strong positional play.<br><br>👉 <b>Action:</b> To reach level 10, study 'prophylaxis'. Predict your opponent's plan and stop it before it starts."
        else:
            advice = "Tactical wizardry.<br><br>👉 <b>Action:</b> Ensure your sacrifices are sound. Don't play for 'hope chess' against stronger opponents."

    elif phase == "Endgame":
        if score <= 3:
            if is_fast:
                advice = "Endgames require calculation, not speed.<br><br>👉 <b>Action:</b> Slow down. Count the pawn races. Do not guess."
            elif is_slow:
                advice = "You run out of time in winning positions.<br><br>👉 <b>Action:</b> Learn the 'Lucena' and 'Philidor' positions by heart so you can play them instantly."
            else:
                advice = "You are losing winning endgames.<br><br>👉 <b>Action:</b> Review 'King Activity'. In the endgame, the King is a fighting piece. Use it!"
        elif score <= 6:
            if is_fast:
                advice = "You drift in equal endgames.<br><br>👉 <b>Action:</b> Have a plan. Create a passed pawn. Don't just shuffle."
            elif is_slow:
                advice = "You overcalculate simple endings.<br><br>👉 <b>Action:</b> Learn the rule of the square and opposition to save time."
            else:
                advice = "Solid technique.<br><br>👉 <b>Action:</b> Study 'Rook vs Pawn' endings. They are the most common and most misplayed."
        elif score <= 9:
            advice = "Excellent conversion.<br><br>👉 <b>Action:</b> To reach level 10, study 'Zugzwang'. Learn how to run your opponent out of moves."
        else:
            advice = "Machine-like precision.<br><br>👉 <b>Action:</b> You are ready for master-level endgame studies (e.g., Dvoretsky)."
            
    return advice

def calculate_analysis_metrics(games, username, pacing_label="Balanced"):
    """
    Calculate accuracy metrics (ACPL, Blunders) and phase breakdown from Lichess analysis data.
    """
    total_acpl = 0
    acpl_count = 0
    total_blunders = 0
    total_mistakes = 0
    total_inaccuracies = 0
    total_moves = 0
    analyzed_games = 0
    
    # Phase accumulators: [total_eval_loss, move_count, blunders]
    phases = {
        'Opening': {'loss': 0, 'moves': 0, 'blunders': 0},
        'Middlegame': {'loss': 0, 'moves': 0, 'blunders': 0},
        'Endgame': {'loss': 0, 'moves': 0, 'blunders': 0}
    }
    
    for game in games:
        if 'analysis' not in game:
            continue
            
        analyzed_games += 1
        
        # Determine user color
        white_user = game.get('players', {}).get('white', {}).get('user', {}).get('name', 'Unknown')
        user_color = chess.WHITE if white_user.lower() == username.lower() else chess.BLACK
        user_color_str = 'white' if user_color == chess.WHITE else 'black'
        
        # Overall Stats from Player Summary
        player_analysis = game.get('players', {}).get(user_color_str, {}).get('analysis', {})
        if player_analysis:
            total_acpl += player_analysis.get('acpl', 0)
            acpl_count += 1
            total_blunders += player_analysis.get('blunder', 0)
            total_mistakes += player_analysis.get('mistake', 0)
            total_inaccuracies += player_analysis.get('inaccuracy', 0)
            
        # Phase Breakdown from Move Analysis
        analysis = game.get('analysis', [])
        moves_san = game.get('moves', '').split()
        
        if not analysis or not moves_san:
            continue
            
        board = chess.Board()
        
        # Iterate moves and analysis
        for i, move_san in enumerate(moves_san):
            if i >= len(analysis):
                break
                
            # Check if it's user's move
            is_user_move = (i % 2 == 0) if user_color == chess.WHITE else (i % 2 != 0)
            
            # Determine Phase
            move_num = (i // 2) + 1
            phase = 'Opening'
            if move_num > 10:
                queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
                phase = 'Middlegame' if queens > 0 else 'Endgame'
            
            current_eval_data = analysis[i]
            prev_eval_data = analysis[i-1] if i > 0 else {'eval': 20}
            
            # Check for Blunder (Judgment)
            # Lichess analysis sometimes has 'judgment' key in the move stream if explicitly requested or parsed
            # But standard API 'analysis' list is just evals.
            # However, we can infer blunders from large eval drops.
            # Or better: The 'judgment' might be in the analysis stream if we are lucky, but usually it's separate.
            # Let's use eval drop > 200 as proxy for blunder if judgment missing.
            
            is_blunder = False
            # Try to find judgment in move comment or analysis data? No, simpler to use eval drop.
            
            if is_user_move:
                try:
                    curr = current_eval_data.get('eval', 0)
                    prev = prev_eval_data.get('eval', 0)
                    
                    loss = 0
                    if user_color == chess.WHITE:
                        if curr < prev: loss = prev - curr
                    else:
                        if curr > prev: loss = curr - prev
                            
                    loss = min(loss, 1000) # Cap at 1000
                    
                    if loss >= 300: # Blunder threshold
                        phases[phase]['blunders'] += 1
                        is_blunder = True
                        
                    phases[phase]['loss'] += loss
                    phases[phase]['moves'] += 1
                    
                except Exception:
                    pass
            
            try:
                board.push_san(move_san)
            except:
                break
                
            total_moves += 1 if is_user_move else 0

    if acpl_count == 0:
        return None
        
    # Calculate Phase Scores (1-10)
    def get_score(avg_loss):
        if avg_loss == 0: return 0
        if avg_loss < 15: return 10
        if avg_loss < 25: return 9
        if avg_loss < 35: return 8
        if avg_loss < 45: return 7
        if avg_loss < 55: return 6
        if avg_loss < 65: return 5
        if avg_loss < 75: return 4
        if avg_loss < 90: return 3
        if avg_loss < 110: return 2
        return 1

    phase_stats = {}
    for p, data in phases.items():
        moves = data['moves']
        avg_loss = data['loss'] / moves if moves > 0 else 0
        blunders = data['blunders']
        
        score = get_score(avg_loss)
        
        # Metrics
        accuracy_percent = max(0, round(100 - (avg_loss / 1.5), 1)) # Heuristic: 150 ACPL = 0% acc
        blunder_rate = round((blunders / moves) * 100, 1) if moves > 0 else 0.0
        
        # Sophisticated Advice Generation
        advice = get_synergized_advice(p, score, pacing_label)
            
        phase_stats[p] = {
            'avg_loss': round(avg_loss, 1), 
            'score': score,
            'accuracy_percent': accuracy_percent,
            'blunder_rate': blunder_rate,
            'advice': advice
        }

    return {
        'games_analyzed': analyzed_games,
        'avg_acpl': round(total_acpl / acpl_count, 1),
        'blunder_rate': round((total_blunders / total_moves) * 100, 1) if total_moves > 0 else 0,
        'mistake_rate': round((total_mistakes / total_moves) * 100, 1) if total_moves > 0 else 0,
        'inaccuracy_rate': round((total_inaccuracies / total_moves) * 100, 1) if total_moves > 0 else 0,
        'phases': phase_stats
    }
