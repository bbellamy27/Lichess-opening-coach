Lichess Opening Coach
Masters of Data Science Programming for Data Science Capstone

Overview
The Lichess Opening Coach is a data driven application designed to help chess players improve by analyzing their real game data. Unlike generic advice, this tool:
1. Fetches your actual game history from Lichess.org.
2. Analyzes your performance across different openings, time controls, and game phases.
3. Visualizes your playing style using advanced metrics (Win Rate Heatmaps, Personality Radars).
4. Coaches you using a Large Language Model (Google Gemini) that interprets the data and provides a personalized training plan.

Team Members
* Brian Bellamy (GitHub: https://github.com/bbellamy27)
* Harold Gonzalez (GitHub: https://github.com/Ruptzy)

Features
* Data Pipeline: Automated fetching of games via Lichess API (NDJSON format) with local MongoDB caching.
* Interactive EDA: 
    * Win Rate by Color & Opening.
    * Time Management Histograms.
    * Personality Radar (Speed vs. Accuracy vs. Aggression).
* AI Coach: Integration with Google Gemini 1.5 Flash to generate natural language reports identifying your One Thing to improve.

Setup & Installation

Prerequisites
* Python 3.8+
* Optional MongoDB (The app falls back to a local SQLite based PortableDB if MongoDB is not detected).

Installation
1. Clone the Repository:
    git clone https://github.com/bbellamy27/Lichess-opening-coach.git
    cd Lichess-opening-coach

2. Install Dependencies:
    pip install -r requirements.txt

3. Environment Setup:
    * The app requires a Google Gemini API key for the AI Coach.
    * You can enter this key directly in the Streamlit Sidebar OR create a .env file:
    GOOGLE_API_KEY=your_api_key_here

How to Run
Run the Streamlit application:
streamlit run app.py

The app will open in your default browser at http://localhost:8501.

API & Data Sources
1. Lichess API: Used to fetch user game data.
    * Endpoint: https://lichess.org/api/games/user/{username}
    * Format: NDJSON (Newline Delimited JSON)
    * Auth: No API key required for public game data.
2. Google Gemini API: Used for the AI Coach.
    * Model: gemini-1.5-flash
    * Purpose: RAG (Retrieval Augmented Generation) on player statistics.

Project Structure
* app.py: Main Streamlit interface.
* api_client.py: Handles Lichess API connections and data ingestion.
* data_processing.py: pandas logic for cleaning and metric calculation.
* eda.py: Plotly visualization functions.
* llm_client.py: Google Gemini integration logic.
* presentation.html: Final Project Presentation slides.

Created for the Data Science Capstone, Fall 2025.
