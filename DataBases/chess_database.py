"""
Chess Analytics - Complete Database Manager
All-in-one file for easy deployment
"""

import logging
import os
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
        connection_string: str = None,
        database_name: str = "chess_analysis"
    ):
        if connection_string is None:
            connection_string = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
            
        # Set a shorter timeout (5s) so we don't hang if DB is down
        self.client = MongoClient(connection_string, maxPoolSize=100, serverSelectionTimeoutMS=5000)
        self.db = self.client[database_name]
        
        # Collections
        self.players = self.db.players
        self.games = self.db.games
        self.openings = self.db.openings
        self.rating_history = self.db.rating_history
        self.metadata = self.db.metadata
        self.checkpoints = self.db.import_checkpoints
        
        self.studies = self.db.studies
        
        logger.info(f"Connected to MongoDB: {database_name}")

    @property
    def connected(self) -> bool:
        """Check if database is connected by pinging it"""
        try:
            # Real check: ping the server
            self.client.admin.command('ping')
            return True
        except Exception:
            return False
    
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
        
        # Studies
        self.studies.create_index([("name", ASCENDING)], unique=True)
        
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
            
    # --- Personal Studies Methods ---
    def create_study(self, name: str, description: str = "") -> ObjectId:
        """Create a new study"""
        study = {
            "name": name,
            "description": description,
            "game_ids": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        try:
            result = self.studies.insert_one(study)
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error creating study: {e}")
            return None

    def get_studies(self) -> List[Dict]:
        """Get all studies"""
        return list(self.studies.find().sort("updated_at", DESCENDING))

    def add_games_to_study(self, study_id: ObjectId, game_ids: List[ObjectId]) -> int:
        """Add games to a study"""
        try:
            result = self.studies.update_one(
                {"_id": study_id},
                {
                    "$addToSet": {"game_ids": {"$each": game_ids}},
                    "$set": {"updated_at": datetime.now()}
                }
            )
            return result.modified_count
        except Exception as e:
            logger.error(f"Error adding games to study: {e}")
            return 0

    def get_games_in_study(self, study_id: ObjectId) -> List[Dict]:
        """Get all games in a study"""
        study = self.studies.find_one({"_id": study_id})
        if not study or not study.get("game_ids"):
            return []
        
        return list(self.games.find({"_id": {"$in": study["game_ids"]}}))

    def delete_study(self, study_id: ObjectId) -> bool:
        """Delete a study"""
        try:
            result = self.studies.delete_one({"_id": study_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting study: {e}")
            return False

    def get_stats(self) -> Dict:
        """Get basic database statistics"""
        try:
            # Check connection
            self.client.admin.command('ping')
            game_count = self.games.count_documents({})
            return {
                "status": "Connected",
                "games": game_count
            }
        except Exception:
            return {
                "status": "Disconnected",
                "games": 0
            }

    def save_games(self, df) -> int:
        """Save games from DataFrame to MongoDB"""
        if df.empty:
            return 0
            
        games_to_insert = []
        for _, row in df.iterrows():
            # Get Player IDs
            white_id = self.get_or_create_player(row['white_user'], row['white_rating'], row['date'])
            black_id = self.get_or_create_player(row['black_user'], row['black_rating'], row['date'])
            
            # Construct Game Document
            game_doc = {
                "game_id": row['game_id'], # Lichess ID
                "site": f"https://lichess.org/{row['game_id']}",
                "date": row['date'],
                "white_player_id": white_id,
                "black_player_id": black_id,
                "white": row['white_user'],
                "black": row['black_user'],
                "white_elo": row['white_rating'],
                "black_elo": row['black_rating'],
                "result": row['result'],
                "eco_code": row.get('eco'),
                "opening_name": row['opening_name'],
                "time_control": row['speed'],
                "moves": row['moves'],
                "clocks": row.get('clocks', []),
                "clock": row.get('clock_settings', {}),
                "analysis": row.get('analysis', []),
                "white_analysis": row.get('white_analysis', {}),
                "black_analysis": row.get('black_analysis', {}),
                "created_at": datetime.now()
            }
            games_to_insert.append(game_doc)
            
        # Bulk Insert (ignoring duplicates by game_id if we had a unique index on it, 
        # but we don't have a unique index on game_id yet, only compound. 
        # Let's add a check or just insert. 
        # Ideally we should have a unique index on game_id.
        # For now, we'll just insert.
        return self.bulk_insert_games(games_to_insert)

    def insert_game(self, game_data: Dict):
        """Insert a single game and return result with inserted_id (Compatibility wrapper)"""
        return self.games.insert_one(game_data)

    def update_game(self, game_id: str, updates: Dict) -> bool:
        """Update a game document with new fields"""
        try:
            result = self.games.update_one(
                {"game_id": game_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating game {game_id}: {e}")
            return False

    def load_games(self, username: str, limit: int = 100):
        """Load games for a user from MongoDB into DataFrame"""
        import pandas as pd
        
        # Find player
        player = self.players.find_one({"username": username})
        if not player:
            return pd.DataFrame()
            
        player_id = player["_id"]
        
        # Query games where player is white or black
        query = {
            "$or": [
                {"white_player_id": player_id},
                {"black_player_id": player_id}
            ]
        }
        
        cursor = self.games.find(query).sort("date", DESCENDING).limit(limit)
        games = list(cursor)
        
        if not games:
            return pd.DataFrame()
            
        # Convert to DataFrame format expected by app
        processed_games = []
        for g in games:
            # Determine user color
            if g['white_player_id'] == player_id:
                user_color = 'white'
                user_rating = g['white_elo']
                opponent_rating = g['black_elo']
            else:
                user_color = 'black'
                user_rating = g['black_elo']
                opponent_rating = g['white_elo']
                
            # Extract ID from site if missing
            g_id = g.get('game_id') or g.get('id')
            if not g_id and g.get('site'):
                g_id = g.get('site').split('/')[-1]

            processed_games.append({
                'game_id': g_id,
                'date': g['date'],
                'user_color': user_color,
                'user_rating': user_rating,
                'opponent_rating': opponent_rating,
                'result': g['result'],
                'opening_name': g.get('opening_name'),
                'eco': g.get('eco_code'),
                'moves': g.get('moves'),
                'speed': g.get('time_control'),
                'white_user': g.get('white'),
                'black_user': g.get('black'),
                'white_rating': g.get('white_elo'),
                'black_rating': g.get('black_elo'),
                'ply_count': len(g.get('moves', '').split()) if isinstance(g.get('moves'), str) else len(g.get('moves', [])),
                # Raw Data for Metrics
                'clocks': g.get('clocks', []),
                'clock': g.get('clock', {}),
                'analysis': g.get('analysis', []),
                'white_analysis': g.get('white_analysis', {}),
                'black_analysis': g.get('black_analysis', {})
            })
            
        return pd.DataFrame(processed_games)

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
