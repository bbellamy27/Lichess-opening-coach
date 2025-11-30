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
            # Use 'gemini-2.0-flash' as it is available and fast
            self.model_name = 'gemini-2.0-flash'
            self.model = genai.GenerativeModel(self.model_name)

    def generate_coaching_report(self, player_stats, opening_stats, risk_data=None, pacing_data=None, time_stats=None, analysis_stats=None):
        """
        Generate a personalized coaching report using the LLM.
        """
        if not self.model:
            return "Error: Google API Key not configured."
            
        # Prepare data strings
        top_openings = opening_stats.head(5).to_string(index=False)
        
        risk_info = f"- Style: {risk_data.get('label', 'N/A')} (Score: {risk_data.get('score', 0)}/10)" if risk_data else ""
        pacing_info = f"- Pacing Archetype: {pacing_data.get('label', 'N/A')} (Avg {pacing_data.get('avg_moves', 0)} moves)" if pacing_data else ""
        
        time_info = ""
        if time_stats:
            time_info = f"""
        Time Management:
        - Opening: {time_stats.get('opening_avg')}s/move ({time_stats.get('opening_feedback', '').split('<br>')[0].replace('**', '')})
        - Middlegame: {time_stats.get('middlegame_avg')}s/move ({time_stats.get('middlegame_feedback', '').split('<br>')[0].replace('**', '')})
        - Endgame: {time_stats.get('endgame_avg')}s/move ({time_stats.get('endgame_feedback', '').split('<br>')[0].replace('**', '')})
            """
            
        analysis_info = ""
        if analysis_stats:
            analysis_info = f"""
        Lichess Analysis Data (Based on {analysis_stats.get('games_analyzed')} analyzed games):
        - Avg ACPL (Accuracy): {analysis_stats.get('avg_acpl')} (Lower is better)
        - Blunder Rate: {analysis_stats.get('blunder_rate')}%
        - Mistake Rate: {analysis_stats.get('mistake_rate')}%
        - Inaccuracy Rate: {analysis_stats.get('inaccuracy_rate')}%
            """
        
        # Construct the prompt for the LLM
        # Construct the prompt for the LLM
        prompt = f"""
        You are a Grandmaster Chess Coach. You are coaching a player rated **{player_stats.get('current_rating')}**.
        
        **CRITICAL INSTRUCTION:**
        Your advice MUST be tailored to their rating level:
        - **< 1200:** Focus on one-move blunders, basic opening principles, and not hanging pieces. Keep it simple.
        - **1200 - 1600:** Focus on tactics, basic plans, and stop playing "hope chess".
        - **1600 - 2000:** Focus on positional understanding, pawn structures, and specific opening theory.
        - **> 2000:** Focus on nuance, prophylaxis, and advanced endgame technique.

        **Player Profile:**
        - Username: {player_stats.get('username')}
        - Rating: {player_stats.get('current_rating')}
        - Win Rate: {player_stats.get('win_rate'):.1%}
        - Games Analyzed: {player_stats.get('total_games')}
        
        **Style & Pacing:**
        {risk_info}
        {pacing_info}
        
        **Time Management:**
        {time_info}
        
        **Accuracy & Phase Analysis:**
        {analysis_info}
        
        **Opening Repertoire:**
        {top_openings}
        
        **Task:**
        Provide a personalized coaching report. Do NOT be generic. Use the data above to diagnose their specific bottlenecks.
        
        **Report Structure:**
        1.  **Executive Summary**: A 2-sentence summary of their player identity (e.g., "You are a solid positional player who struggles with time pressure in the endgame.").
        2.  **Phase Analysis**:
            *   **Opening**: Analyze their repertoire and accuracy. Are they surviving the opening?
            *   **Middlegame**: Analyze their tactical sharpness (Blunder rate) and planning.
            *   **Endgame**: Analyze their conversion skills.
        3.  **The "One Thing"**: Identify the SINGLE biggest factor holding them back from the next rating tier (e.g., "Blundering in time trouble").
        4.  **Training Plan**: 3 specific, actionable drills based on their rating and weaknesses.
        
        Keep the tone professional, insightful, and strictly tailored to a {player_stats.get('current_rating')} rated player.
        """
        
        try:
            # Generate content using the Gemini model
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating report: {str(e)}"

    def chat(self, messages, context=None):
        """
        Send a chat history to Gemini and get a response.
        
        Args:
            messages (list): List of message dicts [{'role': 'user', 'content': '...'}, ...]
            context (str): Optional context string about the user.
            
        Returns:
            str: The assistant's response.
        """
        if not self.model:
            return "Error: Google API Key not configured."
            
        try:
            # Convert OpenAI-style messages to Gemini history
            history = []
            last_user_message = ""
            
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                if msg["role"] == "system":
                    # Prepend system prompt to the first user message or handle separately
                    continue
                
                if role == "user":
                    last_user_message = msg["content"]
                    # Inject context into the latest user message if provided
                    if context and msg == messages[-1]:
                        last_user_message = f"[Context: {context}]\n\n{last_user_message}"
                else:
                    history.append({"role": "user", "parts": [last_user_message]}) # Gemini expects user before model
                    history.append({"role": "model", "parts": [msg["content"]]})
            
            # Start chat session
            chat = self.model.start_chat(history=history)
            
            # Send the last message
            response = chat.send_message(last_user_message)
            return response.text
            
        except Exception as e:
            return f"Error with Gemini Chat: {str(e)}"
