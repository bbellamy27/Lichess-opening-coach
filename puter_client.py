import requests
import json

class PuterClient:
    """
    Client for interacting with the free Puter Llama API.
    """
    
    def __init__(self):
        self.url = "https://api.puter.com/v2/ai/chat/completions"
        self.model = "meta-llama/llama-3.1-8b-instruct"

    def generate_coaching_report(self, player_stats, opening_stats):
        """
        Generate a personalized coaching report using Llama 3.1 via Puter.
        
        Args:
            player_stats (dict): Dictionary containing player metrics.
            opening_stats (pd.DataFrame): DataFrame of opening statistics.
            
        Returns:
            str: The generated coaching report in Markdown format.
        """
        # Prepare the top openings data
        top_openings = opening_stats.head(5).to_string(index=False)
        
        # Construct the prompt (same structure as Gemini client for consistency)
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
        1. **Playstyle Analysis**: Based on the openings and win rate, describe their style.
        2. **Strengths**: What are they doing well?
        3. **Weaknesses**: What needs improvement?
        4. **Opening Recommendations**: Suggest 1-2 new openings or variations.
        5. **Training Plan**: A brief bulleted list of what to focus on next.
        
        Keep the tone encouraging but professional. Use Markdown formatting.
        """

        system_prompt = (
            "You are 'coach', a friendly chess coach and study assistant. "
            "You explain concepts clearly, give practical improvement advice, "
            "and stay supportive."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"⚠️ Error generating report with Llama: {e}"

if __name__ == "__main__":
    # Test client
    client = PuterClient()
    print("PuterClient initialized.")
