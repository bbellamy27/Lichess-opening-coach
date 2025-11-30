import requests
import os
import json

class GroqClient:
    """
    Client for interacting with the Groq API (Llama 3).
    """
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama3-8b-8192" # Fast and efficient model

    def generate_coaching_report(self, player_stats, opening_stats, risk_data=None, pacing_data=None, time_stats=None, analysis_stats=None):
        """
        Generate a personalized coaching report using Groq.
        """
        if not self.api_key:
            return "Error: Groq API Key not configured."

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

        system_prompt = "You are a helpful chess coach."

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error generating report with Groq: {e}"

    def chat(self, messages, context=None):
        """
        Send a chat history to Groq and get a response.
        """
        if not self.api_key:
            return "Error: Groq API Key not configured."

        system_content = (
            "You are 'Coach', a friendly chess coach and study assistant. "
            "You explain concepts clearly, give practical improvement advice, "
            "and stay supportive. You can answer chess questions, study plans, "
            "emotions, mindset, or strategy. Always be helpful and positive."
        )
        
        if context:
            system_content += f"\n\nCURRENT USER DATA:\n{context}\nUse this data to personalize your advice."

        # Prepare messages list with system prompt first
        full_messages = [{"role": "system", "content": system_content}]
        
        # Append user history (filtering out any previous system messages if passed in raw)
        for msg in messages:
            if msg["role"] != "system":
                full_messages.append(msg)

        payload = {
            "model": self.model,
            "messages": full_messages
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error with Groq Chat: {e}"

if __name__ == "__main__":
    client = GroqClient()
    print("GroqClient initialized.")
