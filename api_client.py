import requests
import ndjson
import pandas as pd
from datetime import datetime

class LichessClient:
    """
    Client for interacting with the Lichess API.
    
    This class handles fetching user games and parsing the NDJSON response.
    """
    
    def __init__(self):
        """Initialize the LichessClient."""
        self.base_url = "https://lichess.org/api"

    def get_user_games(self, username, max_games=100):
        """
        Fetch recent games for a specific user.
        
        Args:
            username (str): The Lichess username to fetch games for.
            max_games (int): The maximum number of games to retrieve (default: 100).
            
        Returns:
            list: A list of game dictionaries. Returns an empty list if the request fails.
        """
        # Endpoint for fetching games by user
        url = f"{self.base_url}/games/user/{username}"
        
        # Parameters for the API request
        params = {
            'max': max_games,      # Limit number of games
            'perfType': 'blitz,rapid,bullet,classical', # Filter by game types
            'opening': 'true',     # Include opening information
            'rated': 'true',       # Only include rated games
            'clocks': 'true'       # Include clock data for move times
        }
        
        # Headers to specify the content type
        headers = {
            'Accept': 'application/x-ndjson'
        }

        try:
            # Make the GET request to Lichess API
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status() # Raise an error for bad status codes (4xx, 5xx)
            
            # Parse the NDJSON (Newline Delimited JSON) response
            # Lichess returns multiple JSON objects separated by newlines
            games = response.json(cls=ndjson.Decoder)
            return games
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching games: {e}")
            return []

if __name__ == "__main__":
    # Test the client
    client = LichessClient()
    games = client.get_user_games("DrNykterstein", max_games=5)
    print(f"Fetched {len(games)} games.")
    if games:
        print(games[0].keys())
