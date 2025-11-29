import streamlit as st
import pandas as pd
from api_client import LichessClient
from data_processing import process_games, get_opening_stats
from eda import plot_win_rate_by_color, plot_rating_trend, plot_top_openings, plot_win_rate_by_opening, plot_time_heatmap, plot_opponent_scatter, plot_termination_pie
from llm_client import LLMClient
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

# --- Custom CSS for Dark Dashboard Theme ---
# This CSS overrides Streamlit's default styles to create a custom "Dark Mode" look
# with orange accents, matching the user's requested design.
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Sidebar Background and Border */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Metric Values (Big Numbers) - Orange Accent */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #ff9f1c; 
    }
    
    /* Headers (H1, H2, H3) - Light Gray */
    h1, h2, h3 {
        color: #e6edf3;
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        color: #8b949e;
    }
    .stTabs [aria-selected="true"] {
        background-color: transparent;
        color: #ff9f1c;
        border-bottom: 2px solid #ff9f1c; /* Orange underline for active tab */
    }
    
    /* Custom Container Styling (for Cards) */
    .css-1r6slb0 {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Title and Header ---
st.title("♟️ Lichess Opening Insights")
st.markdown("### Data-Driven Chess Coaching with AI Support")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Settings")
    # Input for Lichess Username
    username = st.text_input("Lichess Username", value="DrNykterstein")
    # Slider for number of games to fetch
    max_games = st.slider("Games to Analyze", 50, 500, 100)
    
    # Main Action Button
    analyze_btn = st.button("Analyze Games", type="primary")
    
    st.markdown("---")
    st.markdown("Created by: Brian & Harold")

# --- Main Application Logic ---
if analyze_btn:
    # Show a spinner while fetching data
    with st.spinner(f"Fetching games for {username}..."):
        client = LichessClient()
        games = client.get_user_games(username, max_games=max_games)
        
    if not games:
        st.error(f"No games found for user '{username}' or API error.")
    else:
        # --- Data Processing ---
        # Convert raw game data to DataFrame and calculate stats
        df = process_games(games, username)
        opening_stats = get_opening_stats(df)
        
        # --- Calculate Player Metrics ---
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
        
        # --- Dashboard Metrics Grid ---
        # Display key stats in a 4-column layout
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Games", total_games)
        col2.metric("Current Rating", current_rating)
        col3.metric("Win Rate", f"{win_rate:.1%}")
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
            
        # Tab 2: Basic Visualizations
        with tab2:
            st.subheader("Performance Overview")
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(plot_win_rate_by_color(df), use_container_width=True)
                st.plotly_chart(plot_top_openings(df), use_container_width=True)
            with col2:
                st.plotly_chart(plot_rating_trend(df), use_container_width=True)
                st.plotly_chart(plot_win_rate_by_opening(opening_stats), use_container_width=True)
        
        # Tab 3: Advanced Analytics (Phase 2 Features)
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
                
        # Tab 4: AI Coach (Gemini Integration)
        with tab4:
            st.subheader("🤖 Personalized Coaching Report")
            if not os.getenv("GOOGLE_API_KEY"):
                st.warning("⚠️ Please enter a Google API Key in the sidebar to generate the AI report.")
                st.info("You can get a free key from [Google AI Studio](https://aistudio.google.com/app/apikey).")
            else:
                with st.spinner("Generating insights with Gemini..."):
                    llm = LLMClient()
                    report = llm.generate_coaching_report(player_stats, opening_stats)
                    st.markdown(report)
else:
    # Initial State Message
    st.info("👈 Enter a username and click 'Analyze Games' to start.")
