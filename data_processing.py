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
