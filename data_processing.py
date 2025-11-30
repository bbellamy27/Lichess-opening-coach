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

def calculate_time_stats(games, username, time_control="overall"):
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
    
    # --- Generate Feedback ---
    tc = time_control.lower()
    
    # Thresholds: (Min Ideal, Max Ideal)
    # Below Min = Too Fast, Above Max = Too Slow
    thresholds = {
        'bullet': {'op': (0.5, 2.0), 'mid': (0.8, 3.0), 'end': (0.8, 3.0)},
        'blitz':  {'op': (2.0, 6.0), 'mid': (3.0, 10.0), 'end': (3.0, 10.0)},
        'rapid':  {'op': (4.0, 15.0), 'mid': (8.0, 25.0), 'end': (8.0, 25.0)},
        'classical': {'op': (10.0, 40.0), 'mid': (30.0, 120.0), 'end': (20.0, 90.0)},
        'overall': {'op': (3.0, 10.0), 'mid': (5.0, 20.0), 'end': (5.0, 20.0)}
    }
    
    t = thresholds.get(tc, thresholds['overall'])
    
    def get_feedback(val, limits, phase):
        low, high = limits
        
        # Advice Dictionary
        advice = {
            'opening': {
                'fast': "Reason: Rushing openings leads to poor structures.\nTip: Check for tactical refutations before moving.",
                'slow': "Reason: Over-thinking theory wastes clock.\nTip: Trust your prep and develop pieces naturally.",
                'good': "Reason: You are balancing development and caution well."
            },
            'middlegame': {
                'fast': "Reason: Speed here causes tactical blunders.\nTip: Calculate at least 2 candidate moves in complex positions.",
                'slow': "Reason: Time trouble will ruin your endgame.\nTip: Don't calculate everything; rely on patterns.",
                'good': "Reason: You are allocating time correctly for calculations."
            },
            'endgame': {
                'fast': "Reason: Endgames require precision, not speed.\nTip: Count tempos and calculate pawn races carefully.",
                'slow': "Reason: You risk flagging in winning positions.\nTip: If it's theoretical, play confidently.",
                'good': "Reason: You are navigating the technical phase well."
            }
        }
        
        if val < low:
            status = f"Too Fast! 🐇"
            details = advice[phase]['fast']
        elif val > high:
            status = f"Too Slow! 🐢"
            details = advice[phase]['slow']
        else:
            status = f"Perfect Pace! 🎯"
            details = advice[phase]['good']
            
        return f"**{status}**\n\n{details}\n\n**Target:** {low}-{high}s"

    return {
        'opening_avg': op_avg,
        'opening_feedback': get_feedback(op_avg, t['op'], "opening"),
        'middlegame_avg': mid_avg,
        'middlegame_feedback': get_feedback(mid_avg, t['mid'], "middlegame"),
        'endgame_avg': end_avg,
        'endgame_feedback': get_feedback(end_avg, t['end'], "endgame")
    }
