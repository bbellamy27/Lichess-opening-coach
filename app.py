import streamlit as st
import pandas as pd
from api_client import LichessClient
from data_processing import process_games, get_opening_stats
from eda import plot_win_rate_by_color, plot_rating_trend, plot_top_openings, plot_win_rate_by_opening, plot_time_heatmap, plot_opponent_scatter, plot_termination_pie, plot_correlation_heatmap
from llm_client import LLMClient
from engine_client import EngineClient
from puter_client import PuterClient
import os
from dotenv import load_dotenv

# Load environment variables (API keys) from .env file
load_dotenv()


# --- Page Configuration ---
st.set_page_config(
    page_title="Lichess Opening Coach",
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

# --- Main Navigation ---
st.sidebar.title("Navigation")
# --- Main Navigation ---
st.sidebar.title("Navigation")
app_mode = st.sidebar.radio("Go to:", ["🏠 Home / Analyzer", "♟️ Best Move Calculator"])

# ==========================================
# MODE 1: HOME / ANALYZER (Original App)
# ==========================================
if app_mode == "🏠 Home / Analyzer":
    st.title("♟️ Lichess Opening Coach")
    st.markdown("Analyze your games, find your weaknesses, and get AI coaching.")

    # Sidebar Inputs
    st.sidebar.header("Settings")
    username = st.sidebar.text_input("Lichess Username", value="DrNykterstein")
    num_games = st.sidebar.slider("Number of Games", min_value=10, max_value=500, value=100)
    
    # Google API Key Input
    api_key = st.sidebar.text_input("Google API Key (Optional)", type="password", help="Required for Gemini. Leave empty to use free Llama.")
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key

    # Analyze Button
    if st.sidebar.button("Analyze Games"):
        with st.spinner(f"Fetching games for {username}..."):
            client = LichessClient() # Assuming LichessClient doesn't need username in constructor
            games = client.get_user_games(username, max_games=num_games)
            
            if games:
                df = process_games(games, username)
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
                st.success(f"Successfully loaded {len(df)} games!")
            else:
                st.error("No games found or API error.")

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
        
        # --- Summary Cards ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Games Played", f"{player_stats['total_games']}")
        col2.metric("Current Rating", f"{player_stats['current_rating']}")
        col3.metric("Win Rate", f"{player_stats['win_rate']:.1%}", delta=f"{len(df[df['result'] == 'Win'])} Won")
        col4.metric("Top Opening", opening_stats.iloc[0]['opening_name'] if not opening_stats.empty else "N/A")
        
        st.divider()
        
        # --- Tabs for Analysis Sections ---
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Data Overview", "📈 Basic EDA", "🧠 Advanced Insights", "🤖 AI Coach"])
        
        # Tab 1: Raw Data Tables
        with tab1:
            st.subheader("Recent Games")
            st.dataframe(df[['date', 'variant', 'speed', 'user_color', 'result', 'opening_name', 'eco', 'termination']].head(100), use_container_width=True)
            
            st.subheader("Opening Statistics")
            st.dataframe(opening_stats, use_container_width=True)
            
        # Tab 2: Basic EDA
        with tab2:
            st.subheader("Performance Overview")
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(plot_win_rate_by_color(df), use_container_width=True)
                st.plotly_chart(plot_top_openings(df), use_container_width=True)
            with col2:
                st.plotly_chart(plot_rating_trend(df), use_container_width=True)
                st.plotly_chart(plot_win_rate_by_opening(opening_stats), use_container_width=True)
        
        # Tab 3: Advanced Insights
        with tab3:
            st.subheader("Deep Dive Analytics")
            col1, col2 = st.columns(2)
            with col1:
                # Heatmap of playing times
                st.plotly_chart(plot_time_heatmap(df), use_container_width=True)
                # Pie chart of game terminations
                st.plotly_chart(plot_termination_pie(df), use_container_width=True)
            with col2:
                # Win rate vs Opponent Rating
                st.plotly_chart(plot_opponent_scatter(df), use_container_width=True)
                
                # Correlation Heatmap
                st.plotly_chart(plot_correlation_heatmap(df), use_container_width=True)
                
        # Tab 4: AI Coach
        with tab4:
            st.subheader("🤖 Personalized Coaching Report")
            
            # Check for Google API Key
            if os.getenv("GOOGLE_API_KEY"):
                with st.spinner("Generating insights with Gemini..."):
                    llm = LLMClient()
                    report = llm.generate_coaching_report(player_stats, opening_stats)
                    st.markdown(report)
            else:
                st.info("ℹ️ Using Free Llama 3.1 Coach (No Google API Key detected)")
                with st.spinner("Generating insights with Llama 3.1..."):
                    llm = PuterClient()
                    report = llm.generate_coaching_report(player_stats, opening_stats)
                    st.markdown(report)
    else:
        # Initial State Message
        st.info("👈 Enter a username and click 'Analyze Games' to start.")

# ==========================================
# MODE 2: BEST MOVE CALCULATOR (Engine)
# ==========================================
elif app_mode == "♟️ Best Move Calculator":
    st.title("♟️ Best Move Calculator")
    st.markdown("Enter a FEN position to get the best move from Stockfish.")
    
    fen_input = st.text_input("FEN String", value="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    
    if st.button("Calculate Best Move"):
        with st.spinner("Thinking..."):
            engine = EngineClient()
            result = engine.get_best_move(fen_input)
            st.success(result)

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
                    # Logic: Use Gemini if Key exists, else Puter
                    if os.getenv("GOOGLE_API_KEY"):
                        client = LLMClient()
                        response = client.chat(st.session_state.messages)
                    else:
                        client = PuterClient()
                        response = client.chat(st.session_state.messages)
                    
                    st.markdown(response)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})

# --- Sidebar Footer ---
with st.sidebar:
    st.markdown("---")
    st.markdown("Created by: Brian & Harold")
