import requests
import json

class PuterClient:
    """
    Client for interacting with the Free AI API (via Pollinations.ai).
    This replaces the old Puter implementation which was 403 blocked.
    """
    
    def __init__(self):
        self.url = "https://text.pollinations.ai/"
        self.model = "openai" # Uses their default best available model

    def generate_coaching_report(self, player_stats, opening_stats):
        """
        Generate a personalized coaching report using Free AI.
        """
        top_openings = opening_stats.head(5).to_string(index=False)
        
        prompt = f"""
        You are a Chess Coach. Analyze these stats:
        
        Player: {player_stats.get('username')}
        Rating: {player_stats.get('current_rating')}
        Win Rate: {player_stats.get('win_rate'):.1%}
        Total Games: {player_stats.get('total_games')}
        
        Top Openings:
        {top_openings}
        
        Provide a brief report with:
        1. Playstyle
        2. Strengths
        3. Weaknesses
        4. Recommendations
        5. Training Plan
        
        Use Markdown. Be encouraging.
        """

        payload = {
            "messages": [
                {"role": "system", "content": "You are a helpful chess coach."},
                {"role": "user", "content": prompt}
            ],
            "model": self.model
        }
        
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            return response.text
        except Exception as e:
            return f"⚠️ Error generating report with Free AI: {e}"

    def chat(self, messages, context=None):
        """
        Send a chat history to Free AI and get a response.
        """
        system_content = (
            "You are 'Coach', a friendly chess coach. "
            "Explain clearly, give practical advice, and be supportive."
        )
        
        if context:
            system_content += f"\n\nUSER DATA:\n{context}"

        # Construct messages for Pollinations
        full_messages = [{"role": "system", "content": system_content}]
        
        for msg in messages:
            if msg["role"] != "system":
                full_messages.append(msg)

        payload = {
            "messages": full_messages,
            "model": self.model
        }
        
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            return response.text
        except Exception as e:
            return f"⚠️ Error contacting Coach: {e}"

if __name__ == "__main__":
    client = PuterClient()
    print("PuterClient (Pollinations) initialized.")
