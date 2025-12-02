"""
Chess Analytics - Advanced Analytics Queries
Optimized aggregation pipelines for fast queries
"""

import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChessAnalytics:
    """Advanced analytics with optimized queries"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_opening_success_rates(
        self,
        min_games: int = 100,
        time_control: Optional[str] = None
    ) -> List[Dict]:
        """Get opening statistics with optimization"""
        # Build match filter
        match_filter = {}
        if time_control:
            match_filter["time_control"] = time_control
        
        # Optimized pipeline with early filtering
        pipeline = []
        
        if match_filter:
            pipeline.append({"$match": match_filter})
        
        # Project only needed fields
        pipeline.append({
            "$project": {
                "eco_code": 1,
                "opening_name": 1,
                "result": 1,
                "white_elo": 1,
                "black_elo": 1
            }
        })
        
        pipeline.extend([
            {
                "$group": {
                    "_id": "$eco_code",
                    "opening_name": {"$first": "$opening_name"},
                    "total_games": {"$sum": 1},
                    "white_wins": {
                        "$sum": {"$cond": [{"$eq": ["$result", "1-0"]}, 1, 0]}
                    },
                    "black_wins": {
                        "$sum": {"$cond": [{"$eq": ["$result", "0-1"]}, 1, 0]}
                    },
                    "draws": {
                        "$sum": {"$cond": [{"$eq": ["$result", "1/2-1/2"]}, 1, 0]}
                    },
                    "avg_rating": {"$avg": {"$avg": ["$white_elo", "$black_elo"]}}
                }
            },
            {"$match": {"total_games": {"$gte": min_games}}},
            {
                "$project": {
                    "eco_code": "$_id",
                    "opening_name": 1,
                    "total_games": 1,
                    "win_rate_white": {"$divide": ["$white_wins", "$total_games"]},
                    "win_rate_black": {"$divide": ["$black_wins", "$total_games"]},
                    "draw_rate": {"$divide": ["$draws", "$total_games"]},
                    "avg_rating": 1,
                    "white_advantage": {
                        "$subtract": [
                            {"$divide": ["$white_wins", "$total_games"]},
                            {"$divide": ["$black_wins", "$total_games"]}
                        ]
                    }
                }
            },
            {"$sort": {"total_games": -1}},
            {"$limit": 50}
        ])
        
        return list(self.db.games.aggregate(pipeline, allowDiskUse=True))
    
    def get_performance_by_time_control(self) -> List[Dict]:
        """Analyze performance across time controls"""
        pipeline = [
            {
                "$project": {
                    "time_control": 1,
                    "result": 1,
                    "white_elo": 1,
                    "black_elo": 1
                }
            },
            {
                "$group": {
                    "_id": "$time_control",
                    "total_games": {"$sum": 1},
                    "avg_white_rating": {"$avg": "$white_elo"},
                    "avg_black_rating": {"$avg": "$black_elo"},
                    "white_wins": {
                        "$sum": {"$cond": [{"$eq": ["$result", "1-0"]}, 1, 0]}
                    },
                    "black_wins": {
                        "$sum": {"$cond": [{"$eq": ["$result", "0-1"]}, 1, 0]}
                    },
                    "draws": {
                        "$sum": {"$cond": [{"$eq": ["$result", "1/2-1/2"]}, 1, 0]}
                    }
                }
            },
            {
                "$project": {
                    "time_control": "$_id",
                    "total_games": 1,
                    "avg_rating": {"$avg": ["$avg_white_rating", "$avg_black_rating"]},
                    "white_win_rate": {"$divide": ["$white_wins", "$total_games"]},
                    "black_win_rate": {"$divide": ["$black_wins", "$total_games"]},
                    "draw_rate": {"$divide": ["$draws", "$total_games"]}
                }
            },
            {"$sort": {"total_games": -1}}
        ]
        
        return list(self.db.games.aggregate(pipeline, allowDiskUse=True))
    
    def get_rating_trends(
        self,
        username: str,
        limit: int = 100
    ) -> List[Dict]:
        """Get rating history for a player"""
        player = self.db.players.find_one({"username": username})
        if not player:
            logger.warning(f"Player not found: {username}")
            return []
        
        ratings = list(
            self.db.rating_history.find({"player_id": player["_id"]})
            .sort("timestamp", -1)
            .limit(limit)
        )
        
        return ratings
    
    def get_player_opening_repertoire(
        self,
        username: str,
        color: str = "white",
        min_games: int = 5
    ) -> List[Dict]:
        """Analyze player's opening repertoire"""
        player = self.db.players.find_one({"username": username})
        if not player:
            return []
        
        player_field = f"{color}_player_id"
        
        pipeline = [
            {"$match": {player_field: player["_id"]}},
            {
                "$project": {
                    "eco_code": 1,
                    "opening_name": 1,
                    "result": 1,
                    "date": 1
                }
            },
            {
                "$group": {
                    "_id": "$eco_code",
                    "opening_name": {"$first": "$opening_name"},
                    "games_played": {"$sum": 1},
                    "wins": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$result", "1-0" if color == "white" else "0-1"]},
                                1,
                                0
                            ]
                        }
                    },
                    "losses": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$result", "0-1" if color == "white" else "1-0"]},
                                1,
                                0
                            ]
                        }
                    },
                    "draws": {
                        "$sum": {"$cond": [{"$eq": ["$result", "1/2-1/2"]}, 1, 0]}
                    },
                    "last_played": {"$max": "$date"}
                }
            },
            {"$match": {"games_played": {"$gte": min_games}}},
            {
                "$project": {
                    "eco_code": "$_id",
                    "opening_name": 1,
                    "games_played": 1,
                    "wins": 1,
                    "losses": 1,
                    "draws": 1,
                    "win_rate": {"$divide": ["$wins", "$games_played"]},
                    "score_rate": {
                        "$divide": [
                            {"$add": ["$wins", {"$multiply": ["$draws", 0.5]}]},
                            "$games_played"
                        ]
                    },
                    "last_played": 1
                }
            },
            {"$sort": {"games_played": -1}}
        ]
        
        return list(self.db.games.aggregate(pipeline, allowDiskUse=True))
    
    def get_rating_volatility(self, min_games: int = 10) -> List[Dict]:
        """Calculate rating volatility for players"""
        pipeline = [
            {
                "$group": {
                    "_id": "$player_id",
                    "avg_rating": {"$avg": "$rating"},
                    "rating_stddev": {"$stdDevPop": "$rating"},
                    "game_count": {"$sum": 1},
                    "min_rating": {"$min": "$rating"},
                    "max_rating": {"$max": "$rating"}
                }
            },
            {"$match": {"game_count": {"$gte": min_games}}},
            {
                "$lookup": {
                    "from": "players",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "player_info"
                }
            },
            {"$unwind": "$player_info"},
            {
                "$project": {
                    "username": "$player_info.username",
                    "avg_rating": 1,
                    "rating_stddev": 1,
                    "game_count": 1,
                    "rating_range": {"$subtract": ["$max_rating", "$min_rating"]},
                    "volatility_ratio": {"$divide": ["$rating_stddev", "$avg_rating"]}
                }
            },
            {"$sort": {"volatility_ratio": -1}},
            {"$limit": 100}
        ]
        
        return list(self.db.rating_history.aggregate(pipeline, allowDiskUse=True))
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        return {
            "players": self.db.players.count_documents({}),
            "games": self.db.games.count_documents({}),
            "openings": self.db.openings.count_documents({}),
            "rating_history": self.db.rating_history.count_documents({})
        }


if __name__ == "__main__":
    print("This is the analytics module. Import it in your main script.")
