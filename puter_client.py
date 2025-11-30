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

    def generate_coaching_report(self, player_stats, opening_stats, risk_data=None, pacing_data=None, time_stats=None, analysis_stats=None):
        """
        Generate a personalized coaching report using Free AI.
        """
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
        You are a Chess Coach. Analyze these stats:
        
        Player: {player_stats.get('username')}
        Rating: {player_stats.get('current_rating')}
        Win Rate: {player_stats.get('win_rate'):.1%}
        Total Games: {player_stats.get('total_games')}
        {risk_info}
        {pacing_info}
        {time_info}
        {analysis_info}
        
        Top Openings:
        {top_openings}
        
        Provide a brief report with:
        1. Playstyle (Mention Risk & Pacing)
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
                # Ensure content is a string
                content = str(msg.get("content", ""))
                full_messages.append({"role": msg["role"], "content": content})

        payload = {
            "messages": full_messages,
            "model": self.model,
            "jsonMode": False # Explicitly disable JSON mode to avoid 400s on some endpoints
        }
        
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            return response.text
        except Exception as e:
            # Fallback for 400 errors (often due to context length or format)
            if "400" in str(e):
                try:
                    # Retry with a simpler payload (just the last message)
                    last_msg = messages[-1]["content"]
                    simple_payload = {
                        "messages": [
                            {"role": "system", "content": "You are a helpful chess coach."},
                            {"role": "user", "content": f"Context: {context}\n\nQuestion: {last_msg}"}
                        ],
                        "model": self.model
                    }
                    response = requests.post(self.url, headers=headers, json=simple_payload)
                    response.raise_for_status()
                    return response.text
                except Exception as e2:
                    return f"⚠️ Error (Retry Failed): {e2}"
            return f"⚠️ Error contacting Coach: {e}"

if __name__ == "__main__":
    client = PuterClient()
    print("PuterClient (Pollinations) initialized.")
