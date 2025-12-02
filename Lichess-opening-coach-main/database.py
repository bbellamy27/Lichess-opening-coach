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
