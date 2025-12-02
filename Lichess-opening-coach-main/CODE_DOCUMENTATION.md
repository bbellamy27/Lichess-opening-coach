# Chess Improvement Coach for Lichess - Code Documentation

The **Chess Improvement Coach for Lichess** is a Streamlit web application designed to help chess players analyze their games, visualize their performance, and receive personalized coaching advice using AI.

## Module Breakdown

### 1. `app.py` (Frontend)
- **Purpose**: The main entry point of the application. It handles the UI layout, user inputs, and displays visualizations and reports.
- **Key Features**:
    - **Sidebar**: Configuration for username, game count, and API keys.
    - **Dashboard**: A grid layout showing key metrics (Rating, Win Rate).
    - **Tabs**: Organized sections for Data, EDA, Advanced Analytics, and AI Coaching.
    - **Custom CSS**: Implements a "Dark Dashboard" theme.

### 2. `api_client.py` (Backend - Data Fetching)
- **Purpose**: Handles all interactions with the Lichess API.
- **Key Functions**:
    - `get_user_games(username, max_games)`: Fetches recent games in NDJSON format.
    - Uses `requests` and `ndjson` libraries to stream and parse data efficiently.

### 3. `data_processing.py` (Backend - Data Logic)
- **Purpose**: Cleans and transforms raw API data into a structured Pandas DataFrame.
- **Key Functions**:
    - `process_games(games, username)`: Extracts relevant fields (color, result, opening, time) and adds derived features (Hour of Day, Opponent Rating Bin).
    - `get_opening_stats(df)`: Aggregates performance metrics by opening.

### 4. `eda.py` (Visualization)
- **Purpose**: Generates interactive charts using Plotly.
- **Key Functions**:
    - `plot_rating_trend`: Line chart of rating history.
    - `plot_win_rate_by_opening`: Bar chart of opening performance.
    - `plot_time_heatmap`: Heatmap of playing activity (Day vs Hour).
    - `plot_termination_pie`: Breakdown of how games ended.

### 5. `llm_client.py` (AI Integration)
- **Purpose**: Interfaces with Google's Gemini API to generate coaching reports.
- **Key Functions**:
    - `generate_coaching_report(player_stats, opening_stats)`: Constructs a prompt with player data and retrieves a structured analysis from the LLM.

## Requirements
- **Python 3.8+**
- **Libraries**: `streamlit`, `pandas`, `requests`, `plotly`, `google-generativeai`, `python-dotenv`, `ndjson`

## How to Run
1. Install dependencies: `pip install -r requirements.txt`
2. Run the app: `streamlit run app.py`
