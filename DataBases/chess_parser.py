"""
Chess Analytics - Optimized PGN Parser
Includes bounded buffers, checkpointing, and validation
"""

import chess.pgn
import io
import sys
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime
from bson import ObjectId

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_pgn_date(date_string: str) -> Optional[datetime]:
    """Parse PGN date string to datetime"""
    if not date_string or date_string == "????.??.??":
        return None
    try:
        date_cleaned = date_string.replace('?', '01')
        parts = date_cleaned.split('.')
        if len(parts) == 3:
            year, month, day = parts
            return datetime(int(year), int(month), int(day))
    except:
        pass
    return None


def extract_title(username: str) -> Optional[str]:
    """Extract chess title from username"""
    titles = ["GM", "IM", "FM", "CM", "WGM", "WIM", "WFM", "WCM"]
    username_upper = username.upper()
    for title in titles:
        if (username_upper.startswith(title + "_") or
            username_upper.startswith(title + "-") or
            username_upper.endswith("_" + title) or
            username_upper.endswith("-" + title)):
            return title
    return None


def categorize_time_control(time_control_str: str) -> str:
    """Categorize time control into standard categories"""
    if not time_control_str or time_control_str == "-":
        return "unknown"
    
    try:
        if '+' in time_control_str:
            base, increment = time_control_str.split('+')
            total_seconds = int(base) + 40 * int(increment)
        else:
            total_seconds = int(time_control_str)
        
        if total_seconds < 180:
            return "bullet"
        elif total_seconds < 600:
            return "blitz"
        elif total_seconds < 1500:
            return "rapid"
        else:
            return "classical"
    except:
        return "unknown"


class OptimizedPGNParser:
    """Optimized PGN Parser with memory management and checkpointing"""
    
    def __init__(self, db_manager, batch_size=1000, max_memory_mb=500):
        self.db = db_manager
        self.batch_size = batch_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        # Buffers
        self.games_buffer = []
        self.openings_buffer = {}
        
        # Statistics
        self.total_processed = 0
        self.parse_errors = 0
    
    def get_buffer_size_bytes(self) -> int:
        """Estimate buffer memory usage"""
        return sys.getsizeof(self.games_buffer) + sys.getsizeof(self.openings_buffer)
    
    def should_flush(self) -> bool:
        """Check if buffers should be flushed"""
        return (len(self.games_buffer) >= self.batch_size or
                self.get_buffer_size_bytes() >= self.max_memory_bytes)
    
    def parse_game(self, pgn_text: str) -> Optional[Dict]:
        """Parse a single PGN game"""
        try:
            pgn_io = io.StringIO(pgn_text)
            game = chess.pgn.read_game(pgn_io)
            
            if game is None:
                return None
            
            headers = game.headers
            
            # Extract player info
            white_username = headers.get("White", "Unknown")
            black_username = headers.get("Black", "Unknown")
            white_elo = int(headers.get("WhiteElo", 1500))
            black_elo = int(headers.get("BlackElo", 1500))
            
            # Get or create players
            white_title = extract_title(white_username)
            black_title = extract_title(black_username)
            game_date = parse_pgn_date(headers.get("Date", ""))
            
            white_player_id = self.db.get_or_create_player(
                white_username, white_elo, game_date, white_title
            )
            black_player_id = self.db.get_or_create_player(
                black_username, black_elo, game_date, black_title
            )
            
            # Extract moves
            moves = []
            board = game.board()
            for move in game.mainline_moves():
                moves.append(board.san(move))
                board.push(move)
            
            # Validate basic constraints
            if len(moves) > 500 or len(moves) < 2:
                return None
            
            if white_elo < 0 or white_elo > 3500 or black_elo < 0 or black_elo > 3500:
                return None
            
            # Create game document
            game_data = {
                "white_player_id": white_player_id,
                "black_player_id": black_player_id,
                "white_elo": white_elo,
                "black_elo": black_elo,
                "result": headers.get("Result", "*"),
                "date": game_date,
                "eco_code": headers.get("ECO", "A00"),
                "opening_name": headers.get("Opening", "Unknown"),
                "time_control": categorize_time_control(headers.get("TimeControl", "")),
                "moves": moves,
                "event": headers.get("Event", ""),
                "site": headers.get("Site", ""),
                "created_at": datetime.now()
            }
            
            # Buffer opening stats
            self._buffer_opening_stats(
                game_data["eco_code"],
                game_data["opening_name"],
                game_data["result"],
                white_elo,
                black_elo
            )
            
            return game_data
            
        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None
    
    def _buffer_opening_stats(self, eco_code, opening_name, result, white_elo, black_elo):
        """Buffer opening statistics"""
        if eco_code not in self.openings_buffer:
            self.openings_buffer[eco_code] = {
                "eco_code": eco_code,
                "opening_name": opening_name,
                "total_games": 0,
                "white_wins": 0,
                "black_wins": 0,
                "draws": 0,
                "total_white_elo": 0,
                "total_black_elo": 0
            }
        
        opening = self.openings_buffer[eco_code]
        opening["total_games"] += 1
        opening["total_white_elo"] += white_elo
        opening["total_black_elo"] += black_elo
        
        if result == "1-0":
            opening["white_wins"] += 1
        elif result == "0-1":
            opening["black_wins"] += 1
        elif result == "1/2-1/2":
            opening["draws"] += 1
    
    def flush_buffers(self):
        """Flush all buffers to database"""
        if not self.games_buffer and not self.openings_buffer:
            return
        
        start_time = time.time()
        
        try:
            # Insert games
            if self.games_buffer:
                self.db.bulk_insert_games(self.games_buffer)
            
            # Update opening stats
            if self.openings_buffer:
                self.db.update_opening_statistics(self.openings_buffer)
            
            elapsed = time.time() - start_time
            logger.info(f"Flushed {len(self.games_buffer)} games in {elapsed:.2f}s")
            
        except Exception as e:
            logger.error(f"Flush error: {e}")
        finally:
            self.games_buffer = []
            self.openings_buffer = {}
    
    def ingest_pgn_file(self, filepath: str, max_games: Optional[int] = None):
        """Import PGN file with optimized processing"""
        logger.info(f"Starting import: {filepath}")
        start_time = time.time()
        
        current_game = []
        games_processed = 0
        
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    
                    if not line:
                        if current_game:
                            pgn_text = '\n'.join(current_game)
                            game_data = self.parse_game(pgn_text)
                            
                            if game_data:
                                self.games_buffer.append(game_data)
                                games_processed += 1
                                
                                # Auto-flush when needed
                                if self.should_flush():
                                    self.flush_buffers()
                                
                                # Progress logging
                                if games_processed % 10000 == 0:
                                    logger.info(f"Processed {games_processed} games...")
                                
                                # Check limit
                                if max_games and games_processed >= max_games:
                                    break
                            else:
                                self.parse_errors += 1
                            
                            current_game = []
                    else:
                        current_game.append(line)
            
            # Final flush
            self.flush_buffers()
            
            # Save metadata
            duration = time.time() - start_time
            self.db.metadata.insert_one({
                "file_source": filepath,
                "import_date": datetime.now(),
                "games_imported": games_processed,
                "import_duration_seconds": duration,
                "parse_errors": self.parse_errors
            })
            
            logger.info(f"\n{'='*50}")
            logger.info(f"Import Complete!")
            logger.info(f"Games processed: {games_processed}")
            logger.info(f"Parse errors: {self.parse_errors}")
            logger.info(f"Duration: {duration:.2f}s")
            logger.info(f"Rate: {games_processed/duration:.1f} games/sec")
            logger.info(f"{'='*50}\n")
            
        except KeyboardInterrupt:
            logger.warning("Import interrupted by user")
            self.flush_buffers()
        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise


if __name__ == "__main__":
    print("This is the PGN parser module. Import it in your main script.")
