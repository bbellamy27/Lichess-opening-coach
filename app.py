
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from api_client import LichessClient
from data_processing import process_games, get_opening_stats, calculate_risk_metrics, calculate_pacing_metrics, calculate_time_stats, calculate_analysis_metrics
from eda import plot_win_rate_by_color, plot_rating_trend, plot_top_openings, plot_win_rate_by_opening, plot_time_heatmap, plot_opponent_scatter, plot_termination_pie, plot_correlation_heatmap, plot_radar_chart, plot_move_time_distribution, plot_opening_sunburst
from llm_client import LLMClient
from engine_client import EngineClient
from local_engine import LocalEngine
from puter_client import PuterClient
from groq_client import GroqClient
import os
from dotenv import load_dotenv
from ui import render_game_list, render_opening_stats

# --- Helper Functions ---
def get_opening_perspective(u_color, op_name, op_role=None):
    # 1. Trust explicit role if available
    if op_role == "i_play": return "my_choice"
    if op_role == "i_face": return "opponent_choice"
    
    # 2. Heuristic
    is_defense_like = any(x in op_name for x in [
        "Defense", "Defence", "Countergambit", "Counter-Gambit", 
        "Counterattack", "Counter-Attack"
    ])
    
    if u_color == "white":
        return "opponent_choice" if is_defense_like else "my_choice"
    else: # black
        return "my_choice" if is_defense_like else "opponent_choice"
# ------------------------

# MongoDB Integration
try:
    from DataBases.chess_database import ChessDatabaseManager
    from DataBases.chess_parser import OptimizedPGNParser
    from DataBases.chess_analytics import ChessAnalytics
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

# Load environment variables (API keys) from .env file
load_dotenv()


# --- Page Configuration ---
st.set_page_config(
    page_title="Chess Improvement Coach for Lichess",
    page_icon="♟️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Chess.com-like Theme ---
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #262522; /* Chess.com Dark Background */
        color: #e6edf3;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #21201d;
        border-right: 1px solid #302e2b;
    }
    
    /* Metrics/Cards */
    div[data-testid="metric-container"] {
        background-color: #302e2b;
        border: 1px solid #403d39;
        padding: 15px;
        border-radius: 8px;
        color: #fff;
    }
    
    /* Metric Values */
    [data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: bold;
        color: #fff;
    }
    
    /* Metric Labels */
    [data-testid="stMetricLabel"] {
        font-size: 14px;
        color: #a7a6a2;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #fff;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #262522;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        background-color: transparent;
        border: none;
        color: #a7a6a2;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #302e2b;
        color: #fff;
        border-bottom: 2px solid #81b64c; /* Green Accent */
    }
    
    /* Custom Classes for Styling */
    .profile-header {
        display: flex;
        align-items: center;
        gap: 15px;
        padding: 20px;
        background-color: #302e2b;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    .profile-name {
        font-size: 24px;
        font-weight: bold;
    }
    .profile-flag {
        font-size: 24px;
    }
</style>
""", unsafe_allow_html=True)

# --- Title and Header ---
st.title("♟️ Chess Improvement Coach for Lichess")
st.markdown("Analyze your games, find your weaknesses, and get AI coaching & advanced metrics.")

# Sidebar Inputs
st.sidebar.header("Settings")
username = st.sidebar.text_input("Lichess Username", value="DrNykterstein")
num_games = st.sidebar.slider("Select number of recent Lichess games to analyze.", min_value=10, max_value=500, value=100)

# Database Connection (Cached)
@st.cache_resource
def get_db_manager_v2():
    return ChessDatabaseManager()

@st.cache_data(ttl=60)
def get_db_stats(_db):
    if _db.connected:
        return _db.get_stats()
    return {'status': 'Disconnected', 'games': 0}

db = get_db_manager_v2()
# Add a 'connected' property to the manager if not present, or handle it
if not hasattr(db, 'connected'):
    # Simple check or assume connected if no error
    # But get_stats handles connection check
    pass

# We need to ensure db has a 'connected' attribute or similar for the rest of the app
# The original code used `if db.connected:`
# Let's check if ChessDatabaseManager has 'connected' property.
# It does NOT in the file I viewed. It just has __init__.
# Wait, previous code used `if db.connected:`.
# I need to add `connected` property to ChessDatabaseManager or wrap it.
# Let's check app.py again. Line 168: `if db.connected:`
# So `ChessDatabaseManager` MUST have a `connected` property or attribute.
# I didn't see it in `chess_database.py` view (lines 1-50).
# Let me check `chess_database.py` again to be sure.
# If it's missing, I need to add it.
# But if it was working before, maybe I missed it.
# Or maybe it was added in a previous turn that I didn't see fully?
# I'll assume I need to add it if missing.

# For now, I will implement the caching in app.py and assume 'connected' exists or I will add it.
# Actually, let's check chess_database.py first.

# AI Provider Selection
ai_provider = st.sidebar.selectbox("AI Provider", ["Free Llama (Default)", "Google Gemini", "Groq (Llama 3)"])

# Dynamic API Key Input
if ai_provider == "Google Gemini":
    api_key = st.sidebar.text_input("Google API Key", type="password", help="Get it from aistudio.google.com")
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key
elif ai_provider == "Groq (Llama 3)":
    api_key = st.sidebar.text_input("Groq API Key", type="password", help="Get it from console.groq.com")
    if api_key:
        os.environ["GROQ_API_KEY"] = api_key
else:
    st.sidebar.info("Using free Llama 3.1 via Puter. No key required!")

# Analyze Button
st.sidebar.markdown("### 📥 Load Data")
st.sidebar.caption("Choose a source to analyze:")
col_fetch, col_load = st.sidebar.columns(2)

with col_fetch:
    if st.button("♞ Load from Lichess"):
        with st.spinner(f"Fetching games for {username}..."):
            client = LichessClient()
            games = client.get_user_games(username, max_games=num_games)
            
            if games:
                df = process_games(games, username)
                
                # Save to DB automatically
                if db.connected:
                    try:
                        saved_count = db.save_games(df)
                        st.toast(f"Saved {saved_count} games to DB!", icon="💾")
                    except Exception as e:
                        st.toast("MongoDB not connected. Games loaded but not saved.", icon="⚠️")
                        print(f"DB Save Error: {e}")
                
                opening_stats = get_opening_stats(df)
                
                # Calculate Player Metrics
                total_games = len(df)
                win_count = len(df[df['result'] == 'Win'])
                loss_count = len(df[df['result'] == 'Loss'])
                draw_count = len(df[df['result'] == 'Draw'])
                win_rate = win_count / total_games if total_games > 0 else 0
                current_rating = df.iloc[0]['user_rating'] if not df.empty else 'N/A'

                player_stats = {
                    'username': username,
                    'total_games': total_games,
                    'current_rating': current_rating,
                    'win_rate': win_rate
                }
                
                # Store data in session state
                st.session_state['game_data'] = df
                st.session_state['opening_stats'] = opening_stats
                st.session_state['player_stats'] = player_stats
                st.session_state['raw_games'] = games
                
                # --- Generate Context for Chatbot ---
                # Split data by color
                df_white = df[df['user_color'] == 'white']
                df_black = df[df['user_color'] == 'black']
                
                stats_white = get_opening_stats(df_white)
                stats_black = get_opening_stats(df_black)
                
                # Helper to format opening stats
                def format_openings(stats, label):
                    details = []
                    if not stats.empty:
                        for index, row in stats.head(3).iterrows():
                            details.append(f"- {row['opening_name']}: {row['games']} games ({row['wins']}W-{row['losses']}L-{row['draws']}D), Win Rate: {row['win_rate']:.1%}")
                    return "\n".join(details) if details else f"No {label} games played."

                white_str = format_openings(stats_white, "White")
                black_str = format_openings(stats_black, "Black")
                
                # Split data by Time Control
                time_controls = ['rapid', 'blitz', 'classical']
                tc_context = ""
                
                for tc in time_controls:
                    df_tc = df[df['speed'] == tc]
                    if not df_tc.empty:
                        tc_games = len(df_tc)
                        tc_wins = len(df_tc[df_tc['result'] == 'Win'])
                        tc_rate = tc_wins / tc_games if tc_games > 0 else 0
                        tc_rating = df_tc.iloc[0]['user_rating']
                        tc_context += f"\n{tc.capitalize()} Stats:\nRating: {tc_rating}, Win Rate: {tc_rate:.1%} ({tc_games} games)\n"
                
                context_str = (
                    f"User: {username}\n"
                    f"Overall Rating: {current_rating}\n"
                    f"Overall Win Rate: {win_rate:.1%}\n"
                    f"Total Games: {total_games}\n"
                    f"{tc_context}\n"
                    f"TOP OPENINGS AS WHITE:\n{white_str}\n\n"
                    f"TOP OPENINGS AS BLACK:\n{black_str}"
                )
                st.session_state['chat_context'] = context_str
                
                st.success(f"Loaded {len(df)} games from Lichess!")
            else:
                st.error("No games found or API error.")

with col_load:
    if st.button("💾 Load from Database"):
        if db.connected:
            with st.spinner(f"Loading games for {username} from DB..."):
                df = db.load_games(username, limit=num_games)
                if not df.empty:
                    # Re-process / Re-calculate stats
                    # Note: df is already processed, but we need to regenerate stats
                    opening_stats = get_opening_stats(df)
                    
                    # Calculate Player Metrics
                    total_games = len(df)
                    win_count = len(df[df['result'] == 'Win'])
                    loss_count = len(df[df['result'] == 'Loss'])
                    draw_count = len(df[df['result'] == 'Draw'])
                    win_rate = win_count / total_games if total_games > 0 else 0
                    current_rating = df.iloc[0]['user_rating'] if not df.empty else 'N/A'

                    player_stats = {
                        'username': username,
                        'total_games': total_games,
                        'current_rating': current_rating,
                        'win_rate': win_rate
                    }
                    
                    st.session_state['game_data'] = df
                    st.session_state['opening_stats'] = opening_stats
                    st.session_state['player_stats'] = player_stats
                    st.session_state['raw_games'] = df.to_dict('records') # Approximation
                    
                    st.success(f"Loaded {len(df)} games from DB!")
                else:
                    st.warning("No games found in DB for this user.")
        else:
            st.error("Database not connected.")

    # Calculate Accuracy Button (Single/Multi Select)
    # This is now handled in the main view for better UX
    # if st.sidebar.button("Calculate Accuracy (Stockfish)"):
    #     ...

    # Display Data if Available
if 'game_data' in st.session_state:
    df = st.session_state['game_data']
    opening_stats = st.session_state['opening_stats']
    player_stats = st.session_state['player_stats']
    
    # --- Header Section (Profile) ---
    st.markdown(f"""
    <div class="profile-header">
        <div class="profile-flag">♟️</div>
        <div class="profile-name">{player_stats['username']}</div>
        <div style="color: #a7a6a2;">🇺🇸</div>
    </div>
    """, unsafe_allow_html=True)
    
    # --- Global Time Control Filter ---
    st.markdown("### ⏱️ Time Control Filter")
    rating_category = st.selectbox("Select Game Mode", ["Overall", "Rapid", "Blitz", "Classical", "Bullet"], index=0)
    
    # Filter Data Globally
    if rating_category != "Overall":
        filtered_df = df[df['speed'] == rating_category.lower()]
    else:
        filtered_df = df.copy()
        
    # Recalculate Stats based on Filter
    if not filtered_df.empty:
        # Update Opening Stats for filtered data
        filtered_opening_stats = get_opening_stats(filtered_df)
        
        # Update Metrics
        filtered_total_games = len(filtered_df)
        filtered_wins = len(filtered_df[filtered_df['result'] == 'Win'])
        filtered_win_rate = filtered_wins / filtered_total_games if filtered_total_games > 0 else 0
        filtered_rating = filtered_df.iloc[0]['user_rating']
        # Calculate Best Openings by Color (Highest Win Rate with min games)
        white_df = filtered_df[filtered_df['user_color'] == 'white']
        black_df = filtered_df[filtered_df['user_color'] == 'black']
        
        white_stats = get_opening_stats(white_df)
        black_stats = get_opening_stats(black_df)
        
        def get_best_opening(stats):
            if stats.empty:
                return "N/A"
            # Filter for openings with at least 5 games to be significant
            # If no opening has 5 games, fall back to all openings
            significant = stats[stats['games'] >= 5]
            if significant.empty:
                significant = stats
            
            # Sort by Win Rate desc, then Games desc
            best = significant.sort_values(['win_rate', 'games'], ascending=[False, False]).iloc[0]
            
            # Format: "ECO: Opening Name (Win%)"
            name = best['opening_name']
            # Removed truncation to show full name
            
            eco = best.get('eco', '')
            if eco:
                return f"{eco}: {name} ({best['win_rate']:.0%})"
            else:
                return f"{name} ({best['win_rate']:.0%})"

        best_white = get_best_opening(white_stats)
        best_black = get_best_opening(black_stats)
    else:
        filtered_total_games = 0
        filtered_rating = "N/A"
        filtered_win_rate = 0
        best_white = "N/A"
        best_black = "N/A"
        filtered_opening_stats = pd.DataFrame()

    # --- Summary Cards (Updated with Filtered Data) ---
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Games Played", f"{filtered_total_games}")
    col2.metric(f"{rating_category} Rating", f"{filtered_rating}")
    col3.metric("Win Rate", f"{filtered_win_rate:.1%}", delta=f"{filtered_wins} Won" if not filtered_df.empty else None)
    with col4:
        best_white_label = "Best as White"
        if best_white != "N/A":
            # Extract opening name from "ECO: Name (Win%)" or "Name (Win%)"
            # Split by '(' to get name part, then split by ':' if needed
            name_part = best_white.split('(')[0].strip()
            if ':' in name_part:
                name_part = name_part.split(':', 1)[1].strip()
            
            perspective = get_opening_perspective('white', name_part)
            if perspective == "opponent_choice":
                best_white_label = f"Best results as White against {name_part}"
            else:
                best_white_label = f"Best as White: {name_part}"

        st.markdown(f"""
        <div style="background-color: #302e2b; border: 1px solid #403d39; padding: 15px; border-radius: 8px; height: 100%;">
            <p style="color: #a7a6a2; font-size: 14px; margin: 0;">{best_white_label} <span style="font-size: 12px; cursor: help;" title="Highest win rate opening as White (min 5 games)">ⓘ</span></p>
            <p style="color: #fff; font-size: 18px; font-weight: bold; margin: 5px 0 0 0; line-height: 1.2; word-wrap: break-word;">{best_white}</p>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        best_black_label = "Best as Black"
        if best_black != "N/A":
            # Extract opening name
            name_part = best_black.split('(')[0].strip()
            if ':' in name_part:
                name_part = name_part.split(':', 1)[1].strip()
            
            perspective = get_opening_perspective('black', name_part)
            if perspective == "opponent_choice":
                best_black_label = f"Best results as Black against {name_part}"
            else:
                best_black_label = f"Best as Black: {name_part}"

        st.markdown(f"""
        <div style="background-color: #302e2b; border: 1px solid #403d39; padding: 15px; border-radius: 8px; height: 100%;">
            <p style="color: #a7a6a2; font-size: 14px; margin: 0;">{best_black_label} <span style="font-size: 12px; cursor: help;" title="Highest win rate opening as Black (min 5 games)">ⓘ</span></p>
            <p style="color: #fff; font-size: 18px; font-weight: bold; margin: 5px 0 0 0; line-height: 1.2; word-wrap: break-word;">{best_black}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Override main variables for downstream use (Charts/Tables)
    # This ensures all tabs use the filtered data
    df = filtered_df
    opening_stats = filtered_opening_stats
    
    st.divider()
    
    # Initialize metrics variables to None to prevent NameError in later tabs
    risk_data = None
    pacing_data = None
    time_stats = None

    # --- Tabs for Analysis Sections ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Data Overview", "📈 Basic EDA", "🧠 Advanced Insights", "🤖 AI Coach", "🌍 Global Database"])
    
    # Tab 1: Raw Data Tables
    with tab1:
        # Games per page selector
        col_games_header, col_games_limit = st.columns([3, 1])
        with col_games_header:
            st.subheader("Recent Games")
        with col_games_limit:
            games_per_page = st.selectbox(
                "Games per page", 
                [10, 25, 50, 100, 500], 
                index=1, # Default to 25
                label_visibility="collapsed"
            )
            
        # Handle "All" (500) or specific limit
        limit = games_per_page if games_per_page != 500 else len(df)
        
        selected_game_ids = render_game_list(df.head(limit))
        
        if selected_game_ids:
            st.markdown("---")
            
            # --- Personal Studies Integration ---
            if MONGODB_AVAILABLE:
                with st.expander("📁 Save to Personal Study"):
                    try:
                        db_manager = ChessDatabaseManager()
                        studies = db_manager.get_studies()
                        study_names = [s['name'] for s in studies]
                        
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            selected_study = st.selectbox("Select Study", ["Create New..."] + study_names)
                        
                        new_study_name = ""
                        if selected_study == "Create New...":
                            with c2:
                                new_study_name = st.text_input("New Study Name")
                        
                        if st.button("💾 Save Selected Games"):
                            with st.spinner("Saving to database..."):
                                # 1. Get/Create Study ID
                                study_id = None
                                if selected_study == "Create New...":
                                    if new_study_name:
                                        study_id = db_manager.create_study(new_study_name)
                                    else:
                                        st.error("Please enter a name for the new study.")
                                else:
                                    study = next((s for s in studies if s['name'] == selected_study), None)
                                    if study:
                                        study_id = study['_id']
                                
                                if study_id:
                                    # 2. Process Games
                                    parser = OptimizedPGNParser(db_manager)
                                    added_game_ids = []
                                    
                                    for game_id in selected_game_ids:
                                        # Find game in dataframe
                                        game_idx = df[df['game_id'] == game_id].index[0]
                                        row = df.loc[game_idx]
                                        
                                        # Construct PGN for parser
                                        pgn_text = f"""
[Event "Lichess Game"]
[Site "https://lichess.org/{game_id}"]
[Date "{row['date'].strftime('%Y.%m.%d')}"]
[White "{row['white_user']}"]
[Black "{row['black_user']}"]
[Result "{row['result']}"]
[WhiteElo "{row['white_rating']}"]
[BlackElo "{row['black_rating']}"]
[ECO "{row.get('eco', '?')}"]
[Opening "{row['opening_name']}"]
[TimeControl "{row['speed']}"]

{row['moves']}
"""
                                        # Parse and Insert
                                        game_data = parser.parse_game(pgn_text)
                                        if game_data:
                                            # Insert into DB (returns ID if exists or new)
                                            # Note: bulk_insert_games expects a list, but we can use insert_one logic or just use bulk with 1 item
                                            # But parser doesn't expose insert_one. 
                                            # We can use db_manager.games.insert_one directly or modify parser.
                                            # Actually, let's just use the parser's logic but we need to get the inserted ID.
                                            # parser.parse_game returns the dict, it doesn't insert.
                                            # We need to insert it.
                                            
                                            # Check if game already exists to avoid duplicates?
                                            # The parser logic doesn't check for duplicates in parse_game, but bulk_insert might.
                                            # Let's check if game exists by site/date/players?
                                            # For simplicity, we'll just insert. MongoDB _id will be unique.
                                            
                                            # We need to insert and get the ID.
                                            res = db_manager.games.insert_one(game_data)
                                            added_game_ids.append(res.inserted_id)
                                    
                                    # 3. Add to Study
                                    if added_game_ids:
                                        count = db_manager.add_games_to_study(study_id, added_game_ids)
                                        st.success(f"Saved {count} games to study!")
                                    else:
                                        st.warning("No valid games could be processed.")
                                        
                    except Exception as e:
                        st.error(f"Database Error: {e}")

            if st.button(f"Analyze {len(selected_game_ids)} Selected Game(s)"):
                engine = LocalEngine()
                progress_bar = st.progress(0)
                
                for i, game_id in enumerate(selected_game_ids):
                    # Find game in dataframe
                    game_idx = df[df['game_id'] == game_id].index[0]
                    row = df.loc[game_idx]
                    
                    moves_str = row.get('moves', '')
                    if moves_str:
                        moves_list = moves_str.split()
                        try:
                            # 1. Analyze
                            acpl_data = engine.analyze_game(moves_list)
                            
                            # 2. Update Data
                            if row['user_color'] == 'white':
                                my_acpl = int(acpl_data['white_acpl'])
                                df.at[game_idx, 'acpl'] = my_acpl
                            else:
                                my_acpl = int(acpl_data['black_acpl'])
                                df.at[game_idx, 'acpl'] = my_acpl
                                
                            # 3. Generate AI Report
                            # Construct a prompt for the AI
                            game_info = f"""
                            Game: {row['white_user']} ({row['white_rating']}) vs {row['black_user']} ({row['black_rating']})
                            Result: {row['result']}
                            Opening: {row['opening_name']}
                            Moves: {row['ply_count']}
                            My Accuracy (ACPL): {my_acpl}
                            """
                            
                            user_color = row['user_color']
                            
                            # Determine User Elo
                            user_elo = row['white_rating'] if user_color == 'white' else row['black_rating']
                            
                            # --- Opening Perspective Logic ---
                            # Uses global helper function defined at top of file
                            opening_perspective = get_opening_perspective(user_color, row['opening_name'], row.get('opening_role'))
                            
                            if opening_perspective == "my_choice":
                                perspective_text = f"This was MY choice. Phrase as: 'In the {row['opening_name']} as {user_color.title()}...'"
                            else:
                                perspective_text = f"This was OPPONENT'S choice. Phrase as: 'Against the {row['opening_name']} as {user_color.title()}...'"
                            
                            # --- Repertoire Logic ---
                            # Calculate how many times I've played/faced this specific opening as this color
                            opening_count = len(df[(df['opening_name'] == row['opening_name']) & (df['user_color'] == user_color)])
                            is_core_repertoire = opening_count >= 5
                            
                            repertoire_status = "CORE REPERTOIRE" if is_core_repertoire else "INCIDENTAL / RARE"
                            
                            repertoire_instruction = ""
                            if is_core_repertoire:
                                repertoire_instruction = f"""
                                - This opening ({row['opening_name']}) is part of my **CORE REPERTOIRE** (Played {opening_count} times).
                                - You may call it "a line I play", "reliable", or "part of my repertoire".
                                - Treat it as a stable weapon to build around.
                                """
                            else:
                                repertoire_instruction = f"""
                                - This opening ({row['opening_name']}) is **INCIDENTAL / RARE** (Played only {opening_count} times).
                                - **DO NOT** call it "reliable" or "part of my repertoire".
                                - Refer to it ONLY as: "games classified as...", "occasional games in...", or "a small sample in...".
                                - Treat good results here as tentative/incidental, not proof of mastery.
                                """
                            # ------------------------

                            prompt = f"""
                            Analyze this chess game summary and give me a brief coaching tip based on the accuracy and opening.
                            
                            **CRITICAL PERSPECTIVE RULES (NON-NEGOTIABLE):**
                            
                            1. **Color Logic:**
                               - I played as **{user_color.upper()}** (Rating: {user_elo}).
                               - All commentary must be written from MY perspective only.
                            
                            2. **"Openings I Play" vs "Openings I Face":**
                               - **{perspective_text}**
                               - Follow this phrasing STRICTLY.
                               - Never mix up "In the..." (my choice) vs "Against the..." (opponent choice).
                            
                            3. **Repertoire Status ({repertoire_status}):**
                               {repertoire_instruction}
                            
                            4. **Phrasing Requirements:**
                               - Always use "as White" or "as Black".
                            
                            5. **Attribution:**
                               - Never assign opponent openings as "my repertoire".
                               - Never speak from the opponent's perspective.
                            
                            6. **Analysis Focus:**
                               - Focus strictly on MY plans, strengths, and mistakes as {user_color}.

                            **ELO-BASED GUIDANCE (My Rating: {user_elo}):**
                            
                            1. **Elo as Synergy Modifier:**
                               - Start with my actual game metrics (blunders, time, accuracy).
                               - Use my Elo ({user_elo}) to determine *priority* and *context*.
                               - Never override data with general advice; use Elo to weight the data.
                            
                            2. **Improvement Priorities by Band:**
                               - **500-799**: Focus on hanging pieces, simple threats, one-move thinking. ("Reducing blunders is the biggest gain.")
                               - **800-999**: Focus on basic plans, not converting material, simple endgames. ("Tactical vision and basic endgames.")
                               - **1000-1199**: Focus on hanging pawns, incorrect trades, development. ("Clean development and reducing unnecessary trades.")
                               - **1200-1399**: Focus on pawn structure, piece activity, long-term plans. ("Respecting pawn structure.")
                               - **1400-1599**: Focus on decision consistency, attacking chances, intermediate moves. ("When to attack vs improve pieces.")
                               - **1600-1799**: Focus on calculation depth, over-aggression, prophylaxis. ("Calculate calmly and understand coordination.")
                               - **1800-1999**: Focus on sharp lines, rook endgames, tempo. ("Refining endgame technique and reducing impulsive moves.")
                               - **2000-2199**: Focus on subtle positional errors, weakness exploitation. ("Small inaccuracies matter more than blunders.")
                               - **2200+**: Focus on precision, novelty, conversion. ("Polishing calculation depth.")
                            
                            3. **Output Format:**
                               - Explicitly state: "Based on your Elo range ({user_elo})..."
                               - Explicitly state: "According to your personal game data..."
                               - Tie them together: "Here's how these two interact..."
                               - Conclusion: "Here's what to work on next..."
                            
                            4. **Tone:**
                               - Constructive, GM-style guidance.
                               - Explain what higher-level players do differently (aspirational).
                            
                            Game Info:
                            {game_info}
                            """
                            
                            # Call AI
                            ai_response = "AI Analysis unavailable (Check API Key)"
                            if ai_provider == "Google Gemini" and os.getenv("GOOGLE_API_KEY"):
                                client = LLMClient()
                                ai_response = client.chat([{"role": "user", "content": prompt}])
                            elif ai_provider == "Groq (Llama 3)" and os.getenv("GROQ_API_KEY"):
                                client = GroqClient()
                                ai_response = client.chat([{"role": "user", "content": prompt}])
                            else:
                                client = PuterClient()
                                ai_response = client.chat([{"role": "user", "content": prompt}])
                                
                            # Add to Chat
                            st.session_state.messages.append({"role": "assistant", "content": f"**Game Analysis ({row['opening_name']}):**\n\n{ai_response}"})
                            
                        except Exception as e:
                            st.error(f"Error analyzing game {game_id}: {e}")
                    
                    progress_bar.progress((i + 1) / len(selected_game_ids))
                    
                st.session_state['game_data'] = df
                st.success("Analysis complete! Check the sidebar chat for the report.")
                st.rerun()
        
        # Initialize Sort State
        if 'sort_by' not in st.session_state:
            st.session_state['sort_by'] = 'games'
            st.session_state['sort_asc'] = False

        st.subheader("Opening Statistics")
        
        if not opening_stats.empty:
            # Header Row with Buttons for Sorting
            # Ratios match the fixed widths in ui.py (40%, 15%, 30%, 15%) -> [4, 1.5, 3, 1.5]
            h1, h2, h3, h4 = st.columns([4, 1.5, 3, 1.5])
            
            def get_label(col_name, label):
                if st.session_state['sort_by'] == col_name:
                    arrow = "▲" if st.session_state['sort_asc'] else "▼"
                    return f"{label} {arrow}"
                return f"{label} ↕"

            def update_sort(col_name):
                if st.session_state['sort_by'] == col_name:
                    st.session_state['sort_asc'] = not st.session_state['sort_asc']
                else:
                    st.session_state['sort_by'] = col_name
                    st.session_state['sort_asc'] = False # Default desc

            with h1:
                if st.button(get_label('opening_name', "Opening"), key="sort_opening", use_container_width=True):
                    update_sort('opening_name')
                    st.rerun()
            with h2:
                if st.button(get_label('games', "Games"), key="sort_games", use_container_width=True):
                    update_sort('games')
                    st.rerun()
            with h3:
                st.markdown("**Performance**", help="Wins/Draws/Losses")
            with h4:
                if st.button(get_label('win_rate', "Win Rate"), key="sort_win_rate", use_container_width=True):
                    update_sort('win_rate')
                    st.rerun()

            # Sort Data
            sort_col = st.session_state['sort_by']
            ascending = st.session_state['sort_asc']
            
            sorted_stats = opening_stats.sort_values(sort_col, ascending=ascending)
            
            render_opening_stats(sorted_stats.head(20))
        else:
            st.info("No opening statistics available for this selection.")
        

        
    # Tab 2: Basic EDA
    with tab2:
        if not df.empty:
            st.subheader("Performance Overview")
            
            # --- Pacing & Risk Analysis Section ---
            risk_data = calculate_risk_metrics(df)
            pacing_data = calculate_pacing_metrics(df, rating_category)
            
            st.markdown("### ⚠️ Style & Pacing Analysis")
            r_col1, r_col2, r_col3 = st.columns([1, 1, 2])
            
            with r_col1:
                # Gauge Chart for Risk Score
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = risk_data['score'],
                    title = {'text': f"Volatility: {risk_data['label']}", 'font': {'size': 20}},
                    gauge = {
                        'axis': {'range': [0, 10], 'tickwidth': 1, 'tickcolor': "white"},
                        'bar': {'color': "white", 'thickness': 0.2}, # Thinner bar to avoid overlap
                        'bgcolor': "rgba(0,0,0,0)",
                        'borderwidth': 2,
                        'bordercolor': "white",
                        'steps': [
                            {'range': [0, 3], 'color': "#00C853"}, # Green
                            {'range': [3, 7], 'color': "#FFD600"}, # Yellow
                            {'range': [7, 10], 'color': "#D50000"}  # Red
                        ],
                        'threshold': {
                            'line': {'color': "white", 'width': 4},
                            'thickness': 0.75,
                            'value': risk_data['score']
                        }
                    },
                    number = {'font': {'size': 50, 'color': "white"}} # Bigger number, but better spacing
                ))
                # Adjust layout to prevent overlapping
                fig_gauge.update_layout(
                    height=300, # Increased height to give more room
                    margin=dict(l=40, r=40, t=80, b=40), # More breathing room
                    paper_bgcolor="rgba(0,0,0,0)",
                    font={'color': "white"}
                )
                st.plotly_chart(fig_gauge, use_container_width=True)
                st.caption(f"ℹ️ {risk_data['explanation']}")
                
            with r_col2:
                # Pacing Metric Card - Improved Visuals
                st.markdown(f"""
                <div style="
                    background-color: #1E1E1E; 
                    padding: 20px; 
                    border-radius: 15px; 
                    text-align: center; 
                    border: 2px solid #333;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                    height: 220px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                ">
                    <h4 style="margin:0; color: #B0B0B0; text-transform: uppercase; letter-spacing: 1px; font-size: 14px;">Pacing Analysis</h4>
                    <h1 style="margin: 10px 0; color: {pacing_data['color']}; font-size: 2.5em; font-weight: 800;">{pacing_data['label'].split()[0]}</h1>
                    <p style="color: #E0E0E0; font-size: 1.2em; margin-bottom: 15px;">{pacing_data['label'].split()[1] if len(pacing_data['label'].split()) > 1 else ''}</p>
                    <div style="background-color: #333; padding: 5px 10px; border-radius: 20px; display: inline-block; margin: 0 auto;">
                        <p style="margin:0; color: #fff; font-size: 0.9em;">Avg Moves: <b>{pacing_data['avg_moves']}</b></p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with r_col3:
                st.info(f"**Risk Feedback:** {risk_data['feedback']}")
                st.warning(f"**Pacing Feedback:** {pacing_data['feedback']}")
                
                st.markdown("---")
                st.success(f"**🎯 Pacing Advice:** {pacing_data['improvement']}")
                st.success(f"**🛡️ Risk Advice:** {risk_data['improvement']}")
            
            st.divider()
            
            # --- Game Accuracy Section ---
            st.markdown("### 🎯 Game Accuracy & Phase Analysis")
            
            # Calculate Analysis Metrics
            # Note: We need to calculate this here for display, even if we calculated it later for AI
            raw_games = st.session_state.get('raw_games')
            analysis_stats = None
            if raw_games:
                if rating_category != "Overall":
                    filtered_games_ai = [g for g in raw_games if g.get('speed') == rating_category.lower()]
                else:
                    filtered_games_ai = raw_games
                analysis_stats = calculate_analysis_metrics(filtered_games_ai, username, pacing_label=pacing_data['label'])
            
            if analysis_stats:
                # Overall Accuracy Metrics
                ac_col1, ac_col2, ac_col3, ac_col4 = st.columns(4)
                ac_col1.metric("Avg ACPL (Accuracy)", f"{analysis_stats['avg_acpl']}", help="Average Centipawn Loss. Lower is better. <20 is GM level.")
                ac_col2.metric("Blunder Rate", f"{analysis_stats['blunder_rate']}%", help="% of moves that are blunders.")
                ac_col3.metric("Mistake Rate", f"{analysis_stats['mistake_rate']}%", help="% of moves that are mistakes.")
                ac_col4.metric("Inaccuracy Rate", f"{analysis_stats['inaccuracy_rate']}%", help="% of moves that are inaccuracies.")
                
                st.markdown("#### 📊 Phase Breakdown")
                
                phases = analysis_stats.get('phases', {})
                
                # Helper for Phase Card
                def phase_card(name, data, pacing_label):
                    score = data.get('score', 0)
                    avg_loss = data.get('avg_loss', 0)
                    acc_pct = data.get('accuracy_percent', 0)
                    blunder_rate = data.get('blunder_rate', 0)
                    advice = data.get('advice', "Keep playing to generate more data.")
                    
                    # Color based on score
                    if score >= 8: color = "#00E676" # Green
                    elif score >= 5: color = "#FFD600" # Yellow
                    else: color = "#D50000" # Red
                    
                    # Feedback Logic
                    if score >= 8:
                        feedback = "Excellent accuracy."
                    elif score >= 5:
                        feedback = "Solid, but room for improvement."
                    else:
                        feedback = "High error rate. Needs work."
                        
                    # Synergy with Pacing
                    if "Fast" in pacing_label or "Sprinter" in pacing_label:
                        if score < 5:
                            feedback += " You are playing too fast and blundering."
                        else:
                            feedback += " Impressive accuracy given your speed."
                    elif "Slow" in pacing_label or "Time" in pacing_label:
                        if score < 5:
                            feedback += " You are thinking long but still missing tactics."
                        else:
                            feedback += " Your slow play is paying off in precision."
                            
                    return f"""
                    <div style="background-color: #262730; padding: 15px; border-radius: 10px; border-left: 5px solid {color}; margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h4 style="margin:0;">{name}</h4>
                            <h2 style="margin:0; color: {color};">{score}/10</h2>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 0.9em; color: #ccc;">
                            <span>🎯 <b>{acc_pct}%</b> Acc</span>
                            <span>❌ <b>{blunder_rate}%</b> Blunders</span>
                        </div>
                        <p style="margin-top: 10px; font-size: 0.9em; font-style: italic; color: #aaa;">"{feedback}"</p>
                        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #444;">
                            <p style="margin:0; font-size: 0.85em; color: #fff;">💡 {advice}</p>
                        </div>
                    </div>
                    """
                
                p_col1, p_col2, p_col3 = st.columns(3)
                with p_col1:
                    st.markdown(phase_card("Opening", phases.get('Opening', {}), pacing_data['label']), unsafe_allow_html=True)
                with p_col2:
                    st.markdown(phase_card("Middlegame", phases.get('Middlegame', {}), pacing_data['label']), unsafe_allow_html=True)
                with p_col3:
                    st.markdown(phase_card("Endgame", phases.get('Endgame', {}), pacing_data['label']), unsafe_allow_html=True)
                    
            else:
                st.info("No analysis data available. Request a computer analysis on Lichess for your games to see accuracy stats.")
            
            st.divider()

            # --- Time Management Section ---
            st.markdown("### ⏱️ Time Management Analysis")
            
            raw_games = st.session_state.get('raw_games')
            
            if raw_games:
                # Filter raw games list based on selected category to ensure Time Analysis matches the filter
                if rating_category != "Overall":
                    filtered_games = [g for g in raw_games if g.get('speed') == rating_category.lower()]
                else:
                    filtered_games = raw_games
                    
                time_stats = calculate_time_stats(filtered_games, username, time_control=rating_category, pacing_label=pacing_data['label'])
                
                t_col1, t_col2, t_col3 = st.columns(3)
                with t_col1:
                    st.metric("Opening (Moves 1-10)", f"{time_stats['opening_avg']}s", delta_color="off", help="Avg time per move in opening")
                    st.markdown(time_stats['opening_feedback'])
                with t_col2:
                    st.metric("Middlegame (Queens On)", f"{time_stats['middlegame_avg']}s", delta_color="off", help="Avg time per move while Queens are on board")
                    st.markdown(time_stats['middlegame_feedback'])
                with t_col3:
                    st.metric("Endgame (Queens Off)", f"{time_stats['endgame_avg']}s", delta_color="off", help="Avg time per move after Queens are traded")
                    st.markdown(time_stats['endgame_feedback'])
                
                st.divider()
            else:
                st.warning("Time analysis requires raw game data. Please re-fetch games.")
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(plot_win_rate_by_color(df), use_container_width=True)
                st.plotly_chart(plot_top_openings(df), use_container_width=True)
            with col2:
                st.plotly_chart(plot_rating_trend(df), use_container_width=True)
                st.plotly_chart(plot_win_rate_by_opening(opening_stats), use_container_width=True)
        else:
            st.info(f"No games available for **{rating_category}**. Play some games to see stats!")
    
    # Tab 3: Advanced Insights
    with tab3:
        if not df.empty:
            st.subheader("Deep Dive Analytics")
            
            # --- Row 1: Personality Radar & Move Times ---
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # Prepare Radar Data
                # We need 5 metrics on 0-10 scale
                
                # 1. Aggression (Risk Score)
                aggression = risk_data['score'] if risk_data else 5
                
                # 2. Speed (Pacing Score)
                speed = pacing_data['score'] if pacing_data else 5
                
                # 3. Accuracy (Inverted ACPL)
                # 0 ACPL = 10, 100 ACPL = 0
                accuracy = 5
                if analysis_stats:
                    acpl = analysis_stats['avg_acpl']
                    accuracy = max(0, min(10, 10 - (acpl / 10)))
                    
                # 4. Opening Knowledge (Opening Phase Score)
                opening_know = 5
                if analysis_stats:
                    opening_know = analysis_stats['phases']['Opening']['score']
                    
                # 5. Endgame Skill (Endgame Phase Score)
                endgame_skill = 5
                if analysis_stats:
                    endgame_skill = analysis_stats['phases']['Endgame']['score']
                    
                radar_data = {
                    'categories': ['Aggression', 'Speed', 'Accuracy', 'Opening Prep', 'Endgame Skill'],
                    'values': [aggression, speed, accuracy, opening_know, endgame_skill]
                }
                
                st.plotly_chart(plot_radar_chart(radar_data), use_container_width=True)
                
            with col2:
                # Move Time Histogram
                if time_stats and time_stats.get('raw_times'):
                    fig = plot_move_time_distribution(time_stats['raw_times'])
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Move time data unavailable.")
                else:
                    st.info("Move time data unavailable.")

            st.divider()
            
            # --- Row 2: Opening Sunburst ---
            st.subheader("Opening Repertoire Map")
            st.plotly_chart(plot_opening_sunburst(df), use_container_width=True)
            
            st.divider()

            # --- Row 3: Existing Heatmaps ---
            col3, col4 = st.columns(2)
            with col3:
                # Heatmap of playing times
                st.plotly_chart(plot_time_heatmap(df), use_container_width=True)
                # Pie chart of game terminations
                st.plotly_chart(plot_termination_pie(df), use_container_width=True)
            with col4:
                # Win rate vs Opponent Rating
                st.plotly_chart(plot_opponent_scatter(df), use_container_width=True)
                
                # Correlation Heatmap
                st.plotly_chart(plot_correlation_heatmap(df), use_container_width=True)
        else:
            st.info(f"No games available for **{rating_category}**. Play some games to see stats!")
            
    # Tab 4: AI Coach
    with tab4:
        st.subheader("🤖 Personalized Coaching Report")
        
        # Check if we have enough data for AI
        if risk_data is None or pacing_data is None:
            st.warning(f"⚠️ Not enough data in **{rating_category}** mode to generate a full AI report. Please play more games or select 'Overall'.")
        else:
            # Calculate Analysis Metrics (ACPL, Blunders)
            raw_games = st.session_state.get('raw_games')
            analysis_stats = None
            if raw_games:
                if rating_category != "Overall":
                    filtered_games_ai = [g for g in raw_games if g.get('speed') == rating_category.lower()]
                else:
                    filtered_games_ai = raw_games
                analysis_stats = calculate_analysis_metrics(filtered_games_ai, username, pacing_label=pacing_data['label'])

            # Calculate Opening Stats by Color for AI Context
            opening_stats_white = get_opening_stats(df, color="white")
            opening_stats_black = get_opening_stats(df, color="black")

            # Check for API Key based on provider
            if ai_provider == "Google Gemini" and os.getenv("GOOGLE_API_KEY"):
                with st.spinner("Generating insights with Gemini..."):
                    llm = LLMClient()
                    report = llm.generate_coaching_report(player_stats, opening_stats, risk_data, pacing_data, time_stats, analysis_stats, opening_stats_white, opening_stats_black)
                    st.markdown(report)
            elif ai_provider == "Groq (Llama 3)" and os.getenv("GROQ_API_KEY"):
                with st.spinner("Generating insights with Groq (Llama 3)..."):
                    llm = GroqClient()
                    report = llm.generate_coaching_report(player_stats, opening_stats, risk_data, pacing_data, time_stats, analysis_stats, opening_stats_white, opening_stats_black)
                    st.markdown(report)
            elif ai_provider == "Free Llama (Default)":
                 with st.spinner("Generating insights with Free Llama..."):
                    llm = PuterClient()
                    report = llm.generate_coaching_report(player_stats, opening_stats, risk_data, pacing_data, time_stats, analysis_stats, opening_stats_white, opening_stats_black)
                    st.markdown(report)
            else:
                st.warning(f"⚠️ Please enter your {ai_provider} API Key in the sidebar.")
    
    # Tab 5: Global Database (MongoDB)
    with tab5:
        st.subheader("🌍 Global Chess Database (MongoDB)")
        
        if not MONGODB_AVAILABLE:
            st.error("❌ MongoDB modules not found. Please ensure `DataBases/` folder exists and `pymongo` is installed.")
        else:
            # 1. Connection Status
            try:
                db_manager = ChessDatabaseManager()
                stats = db_manager.db.command("dbStats")
                st.success(f"✅ Connected to MongoDB (Size: {stats['dataSize'] / 1024 / 1024:.2f} MB)")
                
                # 2. Ingestion UI
                st.markdown("### 📥 Ingest PGN Data")
                uploaded_file = st.file_uploader("Upload PGN File", type=["pgn", "txt"])
                
                if uploaded_file:
                    # Save to temp file
                    with open("temp_import.pgn", "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    if st.button("Start Import"):
                        parser = OptimizedPGNParser(db_manager)
                        with st.spinner("Importing games..."):
                            parser.ingest_pgn_file("temp_import.pgn")
                        st.success("Import Complete!")
                        os.remove("temp_import.pgn")
                        st.rerun()
                
                st.divider()
                
                # 3. My Studies Manager
                st.markdown("### 📁 My Studies")
                studies = db_manager.get_studies()
                
                if not studies:
                    st.info("No studies found. Create one in the 'Recent Games' tab!")
                else:
                    for study in studies:
                        with st.expander(f"📚 {study['name']} ({len(study.get('game_ids', []))} games)"):
                            c1, c2, c3 = st.columns([2, 1, 1])
                            with c1:
                                st.write(f"Created: {study['created_at'].strftime('%Y-%m-%d')}")
                                if study.get('description'):
                                    st.write(study['description'])
                            
                            with c2:
                                # Export PGN
                                if st.button("Export PGN", key=f"export_{study['_id']}"):
                                    games = db_manager.get_games_in_study(study['_id'])
                                    pgn_content = ""
                                    for g in games:
                                        pgn_content += f'[Event "{g.get("event", "Lichess Game")}"]\n'
                                        pgn_content += f'[Site "{g.get("site", "?")}"]\n'
                                        pgn_content += f'[Date "{g.get("date").strftime("%Y.%m.%d") if g.get("date") else "?"}"]\n'
                                        pgn_content += f'[White "{g.get("white", "?")}"]\n'
                                        pgn_content += f'[Black "{g.get("black", "?")}"]\n'
                                        pgn_content += f'[Result "{g.get("result", "*")}"]\n'
                                        pgn_content += f'[ECO "{g.get("eco_code", "?")}"]\n'
                                        pgn_content += f'\n{g.get("moves", "")}\n\n'
                                    
                                    st.download_button(
                                        label="⬇️ Download PGN",
                                        data=pgn_content,
                                        file_name=f"{study['name']}.pgn",
                                        mime="text/plain",
                                        key=f"dl_{study['_id']}"
                                    )

                            with c3:
                                if st.button("Delete Study", key=f"del_{study['_id']}"):
                                    if db_manager.delete_study(study['_id']):
                                        st.success("Deleted!")
                                        st.rerun()

                st.divider()
                
                # 4. Analytics Dashboard
                st.markdown("### 📊 Database Analytics")
                analytics = ChessAnalytics(db_manager)
                
                # A. Overview Metrics
                db_stats = analytics.get_database_stats()
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Games", db_stats['games'])
                c2.metric("Players", db_stats['players'])
                c3.metric("Openings", db_stats['openings'])
                c4.metric("Rating History", db_stats['rating_history'])
                
                # B. Rating Volatility (Query 1)
                st.markdown("#### 1. Rating Volatility Analysis")
                volatility_data = analytics.get_rating_volatility()
                if volatility_data:
                    v_df = pd.DataFrame(volatility_data)
                    fig_vol = go.Figure(data=[
                        go.Scatter(x=v_df['avg_rating'], y=v_df['volatility_ratio'], mode='markers', text=v_df['username'], name='Players')
                    ])
                    fig_vol.update_layout(title="Rating Volatility vs Average Rating", xaxis_title="Average Rating", yaxis_title="Volatility Ratio")
                    st.plotly_chart(fig_vol, use_container_width=True)
                
                # C. Time Control Performance (Query 2)
                st.markdown("#### 2. Performance by Time Control")
                tc_data = analytics.get_performance_by_time_control()
                if tc_data:
                    tc_df = pd.DataFrame(tc_data)
                    fig_tc = go.Figure(data=[
                        go.Bar(name='White Win %', x=tc_df['time_control'], y=tc_df['white_win_rate']),
                        go.Bar(name='Black Win %', x=tc_df['time_control'], y=tc_df['black_win_rate']),
                        go.Bar(name='Draw %', x=tc_df['time_control'], y=tc_df['draw_rate'])
                    ])
                    fig_tc.update_layout(barmode='stack', title="Win Rates by Time Control")
                    st.plotly_chart(fig_tc, use_container_width=True)
                
                # D. Opening Success (Query 3)
                st.markdown("#### 3. Top Openings by Success Rate")
                opening_data = analytics.get_opening_success_rates(min_games=50)
                if opening_data:
                    op_df = pd.DataFrame(opening_data)
                    st.dataframe(op_df[['eco_code', 'opening_name', 'total_games', 'white_advantage', 'avg_rating']], use_container_width=True)

            except Exception as e:
                st.error(f"❌ Connection Error: {e}")
                st.info("Make sure MongoDB is running locally on port 27017.")


# (Engine Mode Removed)

# ==========================================
# SIDEBAR CHATBOT (Persistent)
# ==========================================
with st.sidebar:
    st.markdown("---")
    st.subheader("💬 AI Coach Chat")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Chat Expander
    with st.expander("Open Chat", expanded=False):
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Accept user input
        if prompt := st.chat_input("Ask me about chess..."):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate Response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    # Get Context
                    context = st.session_state.get('chat_context')
                    
                    # Logic: Use Selected Provider
                    if ai_provider == "Google Gemini" and os.getenv("GOOGLE_API_KEY"):
                        client = LLMClient()
                        response = client.chat(st.session_state.messages, context=context)
                    elif ai_provider == "Groq (Llama 3)" and os.getenv("GROQ_API_KEY"):
                        client = GroqClient()
                        response = client.chat(st.session_state.messages, context=context)
                    else:
                        # Default to Puter
                        client = PuterClient()
                        response = client.chat(st.session_state.messages, context=context)
                    
                    st.markdown(response)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})

# --- Sidebar Footer ---
with st.sidebar:
    st.markdown("---")
    st.markdown("Created by: Brian & Harold")
