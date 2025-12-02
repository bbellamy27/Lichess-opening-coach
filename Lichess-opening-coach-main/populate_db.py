import os
from dotenv import load_dotenv
from api_client import LichessClient
from data_processing import process_games
from database import ChessDatabaseManager
import pandas as pd

# Load environment variables
load_dotenv()

def populate_database():
    # Users to fetch games for
    users = ["BBStudying", "Ruptzy"]
    max_games = 100  # Number of games to fetch per user
    
    # Initialize Database
    db = ChessDatabaseManager()
    if not db.connected:
        print("❌ Database not connected. Check your .env file.")
        return

    # Initialize API Client
    client = LichessClient()

    for username in users:
        print(f"\nFetching games for {username}...")
        
        # Fetch games from Lichess
        games = client.get_user_games(username, max_games=max_games)
        
        if games:
            print(f"   Found {len(games)} games.")
            
            # Process games
            try:
                df = process_games(games, username)
                
                if not df.empty:
                    # Save to MongoDB
                    saved_count = db.save_games(df)
                    print(f"   Saved {saved_count} games to MongoDB for {username}.")
                else:
                    print(f"   No valid games to process for {username}.")
            except Exception as e:
                print(f"   Error processing games for {username}: {e}")
        else:
            print(f"   No games found for {username} (or API error).")

    print("\nDatabase population complete!")
    
    # Show stats
    stats = db.get_stats()
    print(f"\nCurrent Database Stats:")
    print(f"   Games: {stats['games']}")
    print(f"   Players: {stats['players']}")

if __name__ == "__main__":
    populate_database()
