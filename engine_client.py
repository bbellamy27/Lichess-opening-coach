import requests

class EngineClient:
    """
    Client for interacting with the chess-api.com engine.
    """
    
    def __init__(self):
        self.url = "https://chess-api.com/api/engine"

    def get_best_move(self, fen, depth=18):
        """
        Sends a FEN position to chess-api.com and returns the engine's best move.
        
        Args:
            fen (str): The FEN string of the chess position.
            depth (int): The search depth for the engine.
            
        Returns:
            str: A formatted string with the best move and evaluation, or an error message.
        """
        payload = {
            "fen": fen,
            "depth": depth
        }

        try:
            response = requests.post(self.url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if data.get("type") == "bestmove":
                best_move = data.get("move", "Unknown")
                evaluation = data.get("eval", "Unknown")
                return f"**Best Move:** {best_move} | **Eval:** {evaluation}"
            else:
                return f"Unexpected response: {data}"
                
        except Exception as e:
            return f"Error calling API: {e}"

if __name__ == "__main__":
    # Test with starting position
    client = EngineClient()
    starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    print(client.get_best_move(starting_fen))
