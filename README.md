# Lichess Opening Insights: Data-Driven Chess Coaching

**Team:**
*   Brian ([GitHub](https://github.com/brianbellamy27))
*   Harold ([GitHub](https://github.com/HaroldGonzalez21))

## Project Overview
This Streamlit web application analyzes a chess player’s recent games from Lichess.org and generates personalized opening recommendations using both statistical analysis and a Large Language Model (Google Gemini).

## Features
*   **Data Acquisition**: Fetches real-time game data from the Lichess API.
*   **EDA**: Visualizes win rates, rating trends, opening performance, and correlation heatmaps.
*   **AI Coaching**: Uses Google Gemini to analyze your style and recommend new openings.
*   **Interactive UI**: Built with Streamlit for a smooth user experience.

## Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd lichess_coach
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Get a Google API Key (Optional but recommended):**
    *   Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
    *   Create a free API key.
    *   Enter this key in the app sidebar.

4.  **Run the App:**
    ```bash
    streamlit run app.py
    ```

## Project Structure
*   `app.py`: Main application entry point.
*   `api_client.py`: Lichess API handler.
*   `data_processing.py`: Data cleaning and metrics.
*   `eda.py`: Visualization logic.
*   `llm_client.py`: Google Gemini integration.

## License
MIT License
