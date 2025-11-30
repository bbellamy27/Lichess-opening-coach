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

    def generate_coaching_report(self, player_stats, opening_stats, risk_data=None, pacing_data=None, time_stats=None):
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
        
        prompt = f"""
        You are a Grandmaster Chess Coach. Analyze the following player statistics and generate a personalized coaching report.
        
        Player Stats:
        - Username: {player_stats.get('username')}
        - Current Rating: {player_stats.get('current_rating')}
        - Win Rate: {player_stats.get('win_rate'):.1%}
        - Total Games Analyzed: {player_stats.get('total_games')}
        {risk_info}
        {pacing_info}
        {time_info}
        
        Top Openings Played:
        {top_openings}
        
        Please provide a report with the following sections:
        1. **Playstyle Analysis**: Incorporate their Risk Profile ({risk_data.get('label') if risk_data else 'N/A'}) and Pacing Archetype ({pacing_data.get('label') if pacing_data else 'N/A'}). Are they a "Berserker" or a "Grinder"? Do they play too fast?
        2. **Strengths**: What are they doing well? (Look at high win rates and good time management).
        3. **Weaknesses**: What needs improvement? (Look at low win rates, time trouble, or reckless speed).
        4. **Opening Recommendations**: Suggest 1-2 new openings or variations to try based on their style.
        5. **Training Plan**: A brief bulleted list of what they should focus on next (e.g., "Slow down in the opening", "Study endgames").
        
        Keep the tone encouraging but professional. Use Markdown formatting.
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
