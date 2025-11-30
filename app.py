
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from api_client import LichessClient
from data_processing import process_games, get_opening_stats, calculate_risk_metrics, calculate_pacing_metrics, calculate_time_stats
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

# --- Main Navigation ---
# (Navigation removed as there is only one mode now)

# ==========================================
# MODE 1: HOME / ANALYZER (Original App)
# ==========================================
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
                st.session_state['raw_games'] = games
                
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
                return f"{best['opening_name']} ({best['win_rate']:.0%})"

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
        col4.metric("Best as White", best_white, help="Highest win rate opening as White (min 5 games)")
        col5.metric("Best as Black", best_black, help="Highest win rate opening as Black (min 5 games)")
        
        st.divider()
        
        # Override main variables for downstream use (Charts/Tables)
        # This ensures all tabs use the filtered data
        df = filtered_df
        opening_stats = filtered_opening_stats
        
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
            if not opening_stats.empty:
                # Prepare Opening Stats for Display
                display_stats = opening_stats.copy()
                display_stats['avg_rating'] = display_stats['avg_rating'].fillna(0).astype(int)
                display_stats['win_rate'] = display_stats['win_rate'].apply(lambda x: f"{x:.1%}")
                
                # Rename columns
                display_stats.columns = ['Opening Name', 'Games Played', 'Wins', 'Draws', 'Losses', 'Average Rating', 'Win Rate']
                st.dataframe(display_stats, use_container_width=True)
            else:
                st.info("No opening statistics available for this selection.")
            
            st.divider()
            st.subheader("Stats by Time Control")
            
            tc_tabs = st.tabs(["Rapid", "Blitz", "Classical", "Bullet"])
            
            for i, tc in enumerate(['rapid', 'blitz', 'classical', 'bullet']):
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
                    st.success(f"**Improvement:** {risk_data['improvement']}")
                
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
                        
                    time_stats = calculate_time_stats(filtered_games, username, time_control=rating_category)
                    
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
            else:
                st.info(f"No games available for **{rating_category}**. Play some games to see stats!")
                
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
