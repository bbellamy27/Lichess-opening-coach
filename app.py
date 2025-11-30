import streamlit as st
import pandas as pd
from api_client import LichessClient
from data_processing import process_games, get_opening_stats
from eda import plot_win_rate_by_color, plot_rating_trend, plot_top_openings, plot_win_rate_by_opening, plot_time_heatmap, plot_opponent_scatter, plot_termination_pie, plot_correlation_heatmap
from llm_client import LLMClient
from engine_client import EngineClient
from puter_client import PuterClient
from groq_client import GroqClient
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
                
                # --- Generate Context for Chatbot ---
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
            # Prepare Game Data for Display
            display_df = df[['date', 'variant', 'speed', 'user_color', 'result', 'opening_name', 'eco', 'termination']].head(100).copy()
            display_df.columns = ['Date', 'Variant', 'Time Control', 'Color Played', 'Result', 'Opening Played', 'ECO', 'Termination']
            st.dataframe(display_df, use_container_width=True)
            
            st.subheader("Opening Statistics")
            # Prepare Opening Stats for Display
            display_stats = opening_stats.copy()
            display_stats['avg_rating'] = display_stats['avg_rating'].fillna(0).astype(int)
            display_stats['win_rate'] = display_stats['win_rate'].apply(lambda x: f"{x:.1%}")
            
            # Rename columns
            display_stats.columns = ['Opening Name', 'Games Played', 'Wins', 'Draws', 'Losses', 'Average Rating', 'Win Rate']
            st.dataframe(display_stats, use_container_width=True)
            
            st.divider()
            st.subheader("Stats by Time Control")
            
            tc_tabs = st.tabs(["Rapid", "Blitz", "Classical"])
            
            for i, tc in enumerate(['rapid', 'blitz', 'classical']):
                with tc_tabs[i]:
                    df_tc = df[df['speed'] == tc]
                    if not df_tc.empty:
                        # Metrics
                        tc_games = len(df_tc)
                        tc_wins = len(df_tc[df_tc['result'] == 'Win'])
                        tc_rate = tc_wins / tc_games
                        tc_rating = df_tc.iloc[0]['user_rating']
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Rating", tc_rating)
                        c2.metric("Win Rate", f"{tc_rate:.1%}")
                        c3.metric("Games", tc_games)
                        
                        st.markdown("#### Top Openings")
                        tc_openings = get_opening_stats(df_tc).head(5)
                        if not tc_openings.empty:
                            tc_display = tc_openings.copy()
                            tc_display['avg_rating'] = tc_display['avg_rating'].fillna(0).astype(int)
                            tc_display['win_rate'] = tc_display['win_rate'].apply(lambda x: f"{x:.1%}")
                            tc_display.columns = ['Opening Name', 'Games Played', 'Wins', 'Draws', 'Losses', 'Average Rating', 'Win Rate']
                            st.dataframe(tc_display, use_container_width=True)
                        else:
                            st.info("No opening stats available.")
                    else:
                        st.info(f"No {tc.capitalize()} games found.")
            
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
            
            # Check for API Key based on provider
            if ai_provider == "Google Gemini" and os.getenv("GOOGLE_API_KEY"):
                with st.spinner("Generating insights with Gemini..."):
                    llm = LLMClient()
                    report = llm.generate_coaching_report(player_stats, opening_stats)
                    st.markdown(report)
            elif ai_provider == "Groq (Llama 3)" and os.getenv("GROQ_API_KEY"):
                with st.spinner("Generating insights with Groq (Llama 3)..."):
                    llm = GroqClient()
                    report = llm.generate_coaching_report(player_stats, opening_stats)
                    st.markdown(report)
            elif ai_provider == "Free Llama (Default)":
                 with st.spinner("Generating insights with Free Llama..."):
                    llm = PuterClient()
                    report = llm.generate_coaching_report(player_stats, opening_stats)
                    st.markdown(report)
            else:
                st.warning(f"⚠️ Please enter your {ai_provider} API Key in the sidebar.")
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
