"""
Chess Analytics - Complete Database Manager
All-in-one file for easy deployment
"""

import logging
from pymongo import MongoClient, ASCENDING, DESCENDING, UpdateOne
from pymongo.errors import BulkWriteError
from typing import Dict, List, Optional
from datetime import datetime
from bson import ObjectId

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChessDatabaseManager:
    """MongoDB database manager for chess analytics"""
    
    def __init__(
        self,
        connection_string: str = "mongodb://localhost:27017/",
        database_name: str = "chess_analysis"
    ):
        self.client = MongoClient(connection_string, maxPoolSize=100)
        self.db = self.client[database_name]
        
        # Collections
        self.players = self.db.players
        self.games = self.db.games
        self.openings = self.db.openings
        self.rating_history = self.db.rating_history
        self.metadata = self.db.metadata
        self.checkpoints = self.db.import_checkpoints
        
        logger.info(f"Connected to MongoDB: {database_name}")
    
    def setup_timeseries_collection(self):
        """Create time-series collection for rating history"""
        try:
            if "rating_history" not in self.db.list_collection_names():
                self.db.create_collection(
                    "rating_history",
                    timeseries={
                        "timeField": "timestamp",
                        "metaField": "player_id",
                        "granularity": "hours"
                    }
                )
                logger.info("Created time-series collection")
        except Exception as e:
            logger.warning(f"Time-series setup failed: {e}")
    
    def create_indexes(self):
        """Create all necessary indexes"""
        logger.info("Creating indexes...")
        
        # Players
        self.players.create_index([("username", ASCENDING)], unique=True)
        self.players.create_index([("current_rating", DESCENDING)])
        self.players.create_index([("title", ASCENDING)], sparse=True)
        
        # Games
        self.games.create_index([("white_player_id", ASCENDING), ("date", DESCENDING)])
        self.games.create_index([("black_player_id", ASCENDING), ("date", DESCENDING)])
        self.games.create_index([("eco_code", ASCENDING), ("date", DESCENDING)])
        self.games.create_index([("time_control", ASCENDING)])
        self.games.create_index([("date", DESCENDING)])
        self.games.create_index([("result", ASCENDING)])
        
        # Openings
        self.openings.create_index([("eco_code", ASCENDING)], unique=True)
        self.openings.create_index([("total_games", DESCENDING)])
        
        logger.info("Indexes created successfully")
    
    def get_or_create_player(
        self,
        username: str,
        rating: int,
        date: Optional[datetime] = None,
        title: Optional[str] = None
    ) -> ObjectId:
        """Get or create player and return ObjectId"""
        player = self.players.find_one({"username": username})
        
        if player:
            player_id = player["_id"]
            self.players.update_one(
                {"_id": player_id},
                {
                    "$set": {"current_rating": rating, "updated_at": datetime.now()},
                    "$max": {"peak_rating": rating},
                    "$inc": {"games_played": 1}
                }
            )
            return player_id
        else:
            new_player = {
                "username": username,
                "title": title,
                "current_rating": rating,
                "peak_rating": rating,
                "games_played": 1,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            result = self.players.insert_one(new_player)
            return result.inserted_id
    
    def bulk_insert_games(self, games: List[Dict]) -> int:
        """Bulk insert games"""
        if not games:
            return 0
        try:
            result = self.games.insert_many(games, ordered=False)
            return len(result.inserted_ids)
        except BulkWriteError as e:
            return e.details['nInserted']
    
    def update_opening_statistics(self, openings_data: Dict[str, Dict]) -> int:
        """Update opening statistics incrementally"""
        if not openings_data:
            return 0
        
        operations = []
        for eco_code, data in openings_data.items():
            operations.append(
                UpdateOne(
                    {"eco_code": eco_code},
                    {
                        "$set": {
                            "opening_name": data["opening_name"],
                            "updated_at": datetime.now()
                        },
                        "$inc": {
                            "total_games": data["total_games"],
                            "white_wins": data["white_wins"],
                            "black_wins": data["black_wins"],
                            "draws": data["draws"],
                            "total_white_elo": data["total_white_elo"],
                            "total_black_elo": data["total_black_elo"]
                        }
                    },
                    upsert=True
                )
            )
        
        try:
            result = self.openings.bulk_write(operations, ordered=False)
            return result.upserted_count + result.modified_count
        except BulkWriteError as e:
            return len(operations) - len(e.details['writeErrors'])
    
    def close(self):
        """Close database connection"""
        self.client.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    # Quick test
    db = ChessDatabaseManager()
    db.setup_timeseries_collection()
    db.create_indexes()
    print("✅ Database setup complete!")
    db.close()
