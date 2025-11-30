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
            'improvement': "Play more games!"
        }
        
    # 1. Draw Rate Factor (0-10)
    # 50% draw rate -> Score 0 (Super Solid)
    # 0% draw rate -> Score 10 (All or Nothing)
    total_games = len(df)
    draws = len(df[df['result'] == 'Draw'])
    draw_rate = draws / total_games if total_games > 0 else 0
    
    # Invert draw rate: 0.5 -> 0, 0.0 -> 1.0
    # Formula: (1 - (draw_rate * 2)) * 10. Clamped 0-10.
    # If draw rate > 50%, score is 0.
    draw_factor = max(0, (1 - (draw_rate * 2))) * 10
    
    # 2. Game Length Factor (0-10)
    # Avg 20 moves -> Score 10 (Quick kills/deaths)
    # Avg 60 moves -> Score 0 (Long grinds)
    avg_ply = df['ply_count'].mean()
    avg_moves = avg_ply / 2
    
    # Formula: (60 - avg_moves) / 4. Clamped 0-10.
    # 20 moves -> (40)/4 = 10
    # 60 moves -> 0
    length_factor = max(0, min(10, (60 - avg_moves) / 4))
    
    # Weighted Average: 60% Draw Rate, 40% Length
    risk_score = (draw_factor * 0.6) + (length_factor * 0.4)
    risk_score = round(max(1, min(10, risk_score)), 1)
    
    # Determine Label and Feedback
    if risk_score <= 3:
        label = "Solid Rock 🪨"
        feedback = "You play very safely, minimizing risk. You likely prefer long, positional games and rarely give your opponent tactical chances."
        mistakes = "Passivity. You might miss winning tactical shots because you're too focused on safety. You may also struggle to convert advantages if you don't take risks."
        improvement = "Practice calculation exercises. Don't be afraid to complicate the position when you are better. Learn some sharper openings to expand your style."
    elif risk_score <= 7:
        label = "Balanced Tactician ⚖️"
        feedback = "You have a healthy mix of solid play and aggression. You take risks when justified but don't go crazy."
        mistakes = "Inconsistency. Sometimes you might play too passively in sharp positions or too aggressively in quiet ones."
        improvement = "Analyze your losses to see if they came from over-pressing or being too passive. Work on recognizing 'critical moments' where risk is required."
    else:
        label = "Berserker ⚔️"
        feedback = "You play extremely aggressively! You prefer sharp, chaotic positions where tactics rule. Win or lose, your games are never boring."
        mistakes = "Over-aggression. You likely sacrifice material unsoundly or neglect your king's safety. You might lose games you were winning by trying to win 'harder'."
        improvement = "Patience! Learn to sit on your hands. If there is no tactic, improve your position slowly. Study prophylactic thinking (preventing opponent's plans)."
        
    return {
        'score': risk_score,
        'label': label,
        'feedback': feedback,
        'mistakes': mistakes,
        'improvement': improvement
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
    
    tc = time_control.lower()
    
    # Thresholds (Lower Bound, Upper Bound)
    # Below Lower = Too Fast
    # Above Upper = Too Slow
    thresholds = {
        'bullet': (15, 45),
        'blitz': (20, 50),
        'rapid': (25, 60),
        'classical': (30, 70),
        'overall': (20, 60) # Generic fallback
    }
    
    lower, upper = thresholds.get(tc, (20, 60))
    
    if avg_moves < lower:
        label = "Too Fast 🐇"
        color = "#FF4B4B" # Streamlit Red
        feedback = f"You are averaging only {avg_moves} moves per game. You might be resigning too early or playing too recklessly."
    elif avg_moves > upper:
        label = "Too Slow 🐢"
        color = "#1E88E5" # Vibrant Blue
        feedback = f"You are averaging {avg_moves} moves per game. Your games are very long grinds. Work on converting advantages faster."
    else:
        label = "Just Right 🎯"
        color = "#00C853" # Vibrant Green
        feedback = f"Your average game length ({avg_moves} moves) is typical for {tc} chess. Good pacing!"
        
    else:
        label = "Just Right 🎯"
        color = "#00C853" # Vibrant Green
        feedback = f"Your average game length ({avg_moves} moves) is typical for {tc} chess. Good pacing!"
        
    return {
        'label': label,
        'color': color,
        'avg_moves': avg_moves,
        'feedback': feedback
    }

import chess
import chess.pgn
import io

def calculate_time_stats(games, username):
    """
    Calculate average time spent per move in Opening, Middlegame, and Endgame.
    
    Definitions:
    - Opening: Moves 1-10
    - Middlegame: Move 11+ while Queens are on board
    - Endgame: Move 11+ after Queens are traded
    
    Args:
        games (list): List of raw game dictionaries (must include 'clocks').
        username (str): User to analyze.
        
    Returns:
        dict: {
            'opening_avg': float (seconds),
            'middlegame_avg': float,
            'endgame_avg': float
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
        
        # Clocks list structure: [white_initial, black_initial, white_move1, black_move1, ...]
        # We need to extract the times for the user's moves.
        # User's clock times are at indices: user_index, user_index + 2, user_index + 4...
        # Wait, Lichess clocks are: [initial_white, initial_black, after_white_1, after_black_1, ...]
        # Actually, let's verify Lichess clock format.
        # It's usually: [curr_white, curr_black, curr_white, curr_black...]
        # Time spent on move N = Clock_before - Clock_after + Increment
        
        # Let's align moves with clocks.
        # clocks[0] = White initial
        # clocks[1] = Black initial
        # clocks[2] = White after move 1
        # clocks[3] = Black after move 1
        
        # User moves are at ply 0, 2, 4... if White
        # User moves are at ply 1, 3, 5... if Black
        
        for i, move_san in enumerate(moves):
            # Update board
            try:
                board.push_san(move_san)
            except ValueError:
                break
                
            # Check if this was user's move
            # Turn has already flipped after push, so if it's now NOT user's turn, then user just moved.
            # Or simpler: if i % 2 == 0 (White moved) and user is White.
            is_user_move = (i % 2 == 0) if user_color == chess.WHITE else (i % 2 != 0)
            
            if is_user_move:
                # Calculate time spent
                # Clock index for AFTER this move is i + 2 (since 0,1 are initials)
                if i + 2 >= len(clocks):
                    break
                    
                # Time before move: clocks[i] (user's clock from previous turn)
                # Time after move: clocks[i+2]
                # Wait, indices are tricky.
                # clocks = [W_init, B_init, W_1, B_1, W_2, B_2...]
                # If White moves (i=0): Time spent = W_init - W_1 + inc
                # W_init is clocks[0]. W_1 is clocks[2].
                # If Black moves (i=1): Time spent = B_init - B_1 + inc
                # B_init is clocks[1]. B_1 is clocks[3].
                
                # General formula:
                # idx_before = i
                # idx_after = i + 2
                # time_spent = (clocks[idx_before] - clocks[idx_after]) / 100 + increment
                
                time_spent = (clocks[i] - clocks[i+2]) / 100 + increment
                time_spent = max(0, time_spent) # Clamp negative times (lag compensation)
                
                move_num = (i // 2) + 1
                
                # Categorize Phase
                if move_num <= 10:
                    opening_times.append(time_spent)
                else:
                    # Check for Queens
                    # We check the board state BEFORE the move? Or currently?
                    # "Middlegame ending when most power pieces traded off like the queens"
                    # If Queens are gone NOW, it's Endgame.
                    # Note: board is already updated with the move.
                    
                    has_queens = bool(board.pieces(chess.QUEEN, chess.WHITE)) or bool(board.pieces(chess.QUEEN, chess.BLACK))
                    # User definition: "endgame after pieces traded". Usually means BOTH queens gone? Or just one?
                    # Standard def: Queens off = Endgame (often). Let's assume BOTH queens must be off? 
                    # Or if "most power pieces traded".
                    # Let's stick to: If NO Queens on board -> Endgame.
                    # If ANY Queen on board -> Middlegame.
                    
                    queens_on_board = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
                    
                    if queens_on_board > 0:
                        middlegame_times.append(time_spent)
                    else:
                        endgame_times.append(time_spent)

    def safe_avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else 0

    return {
        'opening_avg': safe_avg(opening_times),
        'middlegame_avg': safe_avg(middlegame_times),
        'endgame_avg': safe_avg(endgame_times)
    }
