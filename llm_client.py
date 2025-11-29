import google.generativeai as genai
import os
import json

class LLMClient:
    """
    Client for interacting with the Google Gemini API.
    
    This class handles the generation of personalized coaching reports based on
    the user's chess statistics and opening performance.
    """
    
    def __init__(self):
        """
        Initialize the LLMClient.
        
        Retrieves the API key from environment variables and configures the Gemini model.
        """
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            print("Warning: GOOGLE_API_KEY not found in environment variables.")
            self.model = None
        else:
            # Configure the Gemini API with the provided key
            genai.configure(api_key=self.api_key)
            # Use the 'gemini-1.5-flash' model for faster responses
            self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_coaching_report(self, player_stats, opening_stats):
        """
        Generate a personalized coaching report using the LLM.
        
        Args:
            player_stats (dict): Dictionary containing player metrics (rating, win rate, etc.).
            opening_stats (pd.DataFrame): DataFrame of opening statistics.
            
        Returns:
            str: The generated coaching report in Markdown format.
        """
        if not self.model:
            return "Error: Google API Key not configured."
            
        # Prepare the top openings data for the prompt
        top_openings = opening_stats.head(5).to_string(index=False)
        
        # Construct the prompt for the LLM
        # We provide context about the player and ask for specific advice sections
        prompt = f"""
        You are a Grandmaster Chess Coach. Analyze the following player statistics and generate a personalized coaching report.
        
        Player Stats:
        - Username: {player_stats.get('username')}
        - Current Rating: {player_stats.get('current_rating')}
        - Win Rate: {player_stats.get('win_rate'):.1%}
        - Total Games Analyzed: {player_stats.get('total_games')}
        
        Top Openings Played:
        {top_openings}
        
        Please provide a report with the following sections:
        1. **Playstyle Analysis**: Based on the openings and win rate, describe their style (e.g., aggressive, positional).
        2. **Strengths**: What are they doing well? (Look at high win rates).
        3. **Weaknesses**: What needs improvement? (Look at low win rates or high loss rates).
        4. **Opening Recommendations**: Suggest 1-2 new openings or variations to try based on their style.
        5. **Training Plan**: A brief bulleted list of what they should focus on next.
        
        Keep the tone encouraging but professional. Use Markdown formatting.
        """
        
        try:
            # Generate content using the Gemini model
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating report: {str(e)}"
