"""
MongoDB Database Manager for Lichess Opening Coach.
Adapted from the provided chess_database.py.
"""

import logging
import os
from pymongo import MongoClient, ASCENDING, DESCENDING, UpdateOne
from pymongo.errors import BulkWriteError, ConnectionFailure
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChessDatabaseManager:
    """MongoDB database manager for chess analytics"""
    
    def __init__(self, connection_string: Optional[str] = None):
        # Use env var if not provided, default to local if neither
        if not connection_string:
            connection_string = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
            
        try:
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            # Check connection
            self.client.admin.command('ping')
            
            self.db = self.client["lichess_coach"]
            
            # Collections
            self.games = self.db.games
            self.players = self.db.players
            self.openings = self.db.openings
            
            logger.info("Connected to MongoDB successfully.")
            self.connected = True
            
            # Ensure indexes exist
            self.create_indexes()
            
        except ConnectionFailure:
            logger.error("Could not connect to MongoDB. Database features disabled.")
            self.connected = False
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            self.connected = False

    def create_indexes(self):
        """Create necessary indexes for performance"""
        if not self.connected: return
        
        # Games indexes
        self.games.create_index([("game_id", ASCENDING)], unique=True)
        self.games.create_index([("white_user", ASCENDING)])
        self.games.create_index([("black_user", ASCENDING)])
        self.games.create_index([("date", DESCENDING)])
        self.games.create_index([("speed", ASCENDING)])
        self.games.create_index([("opening_name", ASCENDING)])
        
        logger.info("Indexes verified.")

    def save_games(self, df: pd.DataFrame):
        """Save a dataframe of games to MongoDB"""
        if not self.connected or df.empty:
            return 0
            
        games_dict = df.to_dict('records')
        operations = []
        
        for game in games_dict:
            # Convert Timestamp to datetime for MongoDB
            if isinstance(game.get('date'), pd.Timestamp):
                game['date'] = game['date'].to_pydatetime()
                
            # Use game_id as unique identifier for upsert
            operations.append(
                UpdateOne(
                    {"game_id": game['game_id']},
                    {"$set": game},
                    upsert=True
                )
            )
            
        try:
            result = self.games.bulk_write(operations, ordered=False)
            logger.info(f"Saved {len(games_dict)} games to MongoDB.")
            return result.upserted_count + result.modified_count
        except BulkWriteError as e:
            logger.error(f"Error saving games: {e}")
            return 0

    def load_games(self, username: str, limit: int = 1000) -> pd.DataFrame:
        """Load games for a specific user from MongoDB"""
        if not self.connected:
            return pd.DataFrame()
            
        # Query for games where user is white OR black
        query = {
            "$or": [
                {"white_user": username},
                {"black_user": username}
            ]
        }
        
        cursor = self.games.find(query).sort("date", DESCENDING).limit(limit)
        games = list(cursor)
        
        if not games:
            return pd.DataFrame()
            
        df = pd.DataFrame(games)
        
        # Drop MongoDB _id
        if '_id' in df.columns:
            df = df.drop('_id', axis=1)
            
        # Ensure date is datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Calculate derived columns if missing
        if 'hour' not in df.columns:
            df['hour'] = df['date'].dt.hour
            
        if 'day_of_week' not in df.columns:
            df['day_of_week'] = df['date'].dt.day_name()
            
        if 'ply_count' not in df.columns:
            df['ply_count'] = df['moves'].apply(lambda x: len(x.split()) if isinstance(x, str) else 0)
            
        # Ensure other columns exist with defaults
        required_cols = {
            'variant': 'standard',
            'termination': 'Normal',
            'acpl': None,
            'eco': '',
            'opening_name': 'Unknown'
        }
        
        for col, default in required_cols.items():
            if col not in df.columns:
                df[col] = default

        # Calculate opponent_rating_bin
        if 'opponent_rating_bin' not in df.columns:
            def get_bin(rating):
                if pd.isna(rating): return "Unknown"
                try:
                    r = int(rating)
                    if r < 1000: return "<1000"
                    elif 1000 <= r < 1200: return "1000-1200"
                    elif 1200 <= r < 1400: return "1200-1400"
                    elif 1400 <= r < 1600: return "1400-1600"
                    elif 1600 <= r < 1800: return "1600-1800"
                    elif 1800 <= r < 2000: return "1800-2000"
                    elif 2000 <= r < 2200: return "2000-2200"
                    else: return "2200+"
                except:
                    return "Unknown"
            
            df['opponent_rating_bin'] = df['opponent_rating'].apply(get_bin)
        
        logger.info(f"Loaded {len(df)} games for {username} from MongoDB.")
        return df

    def get_stats(self):
        """Get basic database stats"""
        if not self.connected:
            return {"status": "Disconnected", "games": 0}
            
        return {
            "status": "Connected",
            "games": self.games.count_documents({}),
            "players": self.players.count_documents({})
        }
