import sqlite3
import json
import pandas as pd
from datetime import datetime
import os
import logging
from typing import Dict, List, Optional, Any, Union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PortableDatabaseManager:
    """
    SQLite-based database manager for portable use.
    Implements the same interface as ChessDatabaseManager.
    """
    
    def __init__(self, db_path="chess_data.db"):
        self.db_path = db_path
        self.conn = None
        self._init_db()

    def _get_conn(self):
        """Get or create connection"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            # Return rows as dicts (sort of)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def _init_db(self):
        """Initialize tables"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Players Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            current_rating INTEGER,
            peak_rating INTEGER,
            games_played INTEGER DEFAULT 0,
            updated_at TIMESTAMP
        )
        ''')
        
        # Games Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT UNIQUE,
            site TEXT,
            date TIMESTAMP,
            white_user TEXT,
            black_user TEXT,
            white_rating INTEGER,
            black_rating INTEGER,
            result TEXT,
            eco TEXT,
            opening_name TEXT,
            time_control TEXT,
            moves TEXT,
            ply_count INTEGER,
            acpl INTEGER,
            clocks TEXT,
            clock_settings TEXT,
            analysis TEXT,
            white_analysis TEXT,
            black_analysis TEXT,
            white_player_id INTEGER,
            black_player_id INTEGER,
            created_at TIMESTAMP,
            FOREIGN KEY(white_player_id) REFERENCES players(id),
            FOREIGN KEY(black_player_id) REFERENCES players(id)
        )
        ''')
        
        # Studies Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS studies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        ''')
        
        # Study Games Link Table (Many-to-Many)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_games (
            study_id INTEGER,
            game_id TEXT,
            added_at TIMESTAMP,
            PRIMARY KEY (study_id, game_id),
            FOREIGN KEY(study_id) REFERENCES studies(id),
            FOREIGN KEY(game_id) REFERENCES games(game_id)
        )
        ''')
        
        conn.commit()

    @property
    def connected(self) -> bool:
        """Check if database is connected (always true for SQLite if file accessible)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            return True
        except Exception:
            return False

    def get_or_create_player(self, username, rating, date=None):
        """Get or create player and return ID"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, peak_rating FROM players WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        now = datetime.now()
        
        if row:
            player_id = row['id']
            current_peak = row['peak_rating'] or 0
            new_peak = max(current_peak, rating) if rating else current_peak
            
            cursor.execute('''
                UPDATE players 
                SET current_rating = ?, peak_rating = ?, games_played = games_played + 1, updated_at = ?
                WHERE id = ?
            ''', (rating, new_peak, now, player_id))
            return player_id
        else:
            cursor.execute('''
                INSERT INTO players (username, current_rating, peak_rating, games_played, updated_at)
                VALUES (?, ?, ?, 1, ?)
            ''', (username, rating, rating, now))
            return cursor.lastrowid

    def save_games(self, df) -> int:
        """Save games from DataFrame to SQLite"""
        if df.empty:
            return 0
            
        conn = self._get_conn()
        cursor = conn.cursor()
        count = 0
        
        for _, row in df.iterrows():
            try:
                # Get Player IDs
                white_id = self.get_or_create_player(row['white_user'], row['white_rating'])
                black_id = self.get_or_create_player(row['black_user'], row['black_rating'])
                
                # Check if game exists
                cursor.execute("SELECT id FROM games WHERE game_id = ?", (row['game_id'],))
                if cursor.fetchone():
                    continue # Skip duplicates
                
                # Insert Game
                cursor.execute('''
                    INSERT INTO games (
                        game_id, site, date, white_user, black_user, 
                        white_rating, black_rating, result, eco, opening_name, 
                        time_control, moves, ply_count, acpl, 
                        clocks, clock_settings, analysis, white_analysis, black_analysis,
                        white_player_id, black_player_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['game_id'], 
                    f"https://lichess.org/{row['game_id']}",
                    row['date'].to_pydatetime() if hasattr(row['date'], 'to_pydatetime') else row['date'],
                    row['white_user'], row['black_user'],
                    row['white_rating'], row['black_rating'],
                    row['result'], row.get('eco'), row['opening_name'],
                    row['speed'], row['moves'], 
                    len(row['moves'].split()) if row.get('moves') else 0,
                    row.get('acpl'),
                    json.dumps(row.get('clocks', [])),
                    json.dumps(row.get('clock_settings', {})),
                    json.dumps(row.get('analysis', [])),
                    json.dumps(row.get('white_analysis', {})),
                    json.dumps(row.get('black_analysis', {})),
                    white_id, black_id,
                    datetime.now()
                ))
                count += 1
            except Exception as e:
                logger.error(f"Error saving game {row.get('game_id')}: {e}")
                
        conn.commit()
        return count

    def load_games(self, username: str, limit: int = 100):
        """Load games for a user from SQLite into DataFrame"""
        conn = self._get_conn()
        
        # Query games where player is white or black
        query = f'''
            SELECT * FROM games 
            WHERE white_user = ? OR black_user = ?
            ORDER BY date DESC
            LIMIT ?
        '''
        
        try:
            # Use pandas to read directly
            df = pd.read_sql_query(query, conn, params=(username, username, limit))
            
            if df.empty:
                return pd.DataFrame()
                
            # Post-process to match app expectations
            # SQLite stores dates as strings usually, need to convert back
            df['date'] = pd.to_datetime(df['date'])
            
            # Map 'time_control' back to 'speed' for app compatibility
            if 'time_control' in df.columns:
                df['speed'] = df['time_control']
            
            # Add user_color, user_rating, opponent_rating
            def enrich_row(row):
                if row['white_user'] == username:
                    row['user_color'] = 'white'
                    row['user_rating'] = row['white_rating']
                    row['opponent_rating'] = row['black_rating']
                else:
                    row['user_color'] = 'black'
                    row['user_rating'] = row['black_rating']
                    row['opponent_rating'] = row['white_rating']
                
                # Deserialize JSON fields
                try:
                    row['clocks'] = json.loads(row['clocks']) if row['clocks'] else []
                    row['clock'] = json.loads(row['clock_settings']) if row['clock_settings'] else {}
                    row['analysis'] = json.loads(row['analysis']) if row['analysis'] else []
                    
                    # Reconstruct nested player analysis
                    w_analysis = json.loads(row['white_analysis']) if row['white_analysis'] else {}
                    b_analysis = json.loads(row['black_analysis']) if row['black_analysis'] else {}
                    
                    row['players'] = {
                        'white': {'user': {'name': row['white_user']}, 'rating': row['white_rating'], 'analysis': w_analysis},
                        'black': {'user': {'name': row['black_user']}, 'rating': row['black_rating'], 'analysis': b_analysis}
                    }
                except Exception as e:
                    logger.error(f"Error deserializing game {row['game_id']}: {e}")
                    
                return row
                
            df = df.apply(enrich_row, axis=1)
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading games: {e}")
            return pd.DataFrame()

    def get_stats(self):
        """Get basic database statistics"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM games")
            count = cursor.fetchone()[0]
            return {
                "status": "Connected (Portable)",
                "games": count
            }
        except Exception:
            return {
                "status": "Disconnected",
                "games": 0
            }

    # --- Personal Studies Methods ---
    def create_study(self, name: str, description: str = ""):
        """Create a new study"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO studies (name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (name, description, datetime.now(), datetime.now()))
            conn.commit()
            return cursor.lastrowid # Returns ID (int)
        except Exception as e:
            logger.error(f"Error creating study: {e}")
            return None

    def get_studies(self):
        """Get all studies"""
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row # Ensure dict-like access
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM studies ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        # Convert to list of dicts
        return [dict(row) for row in rows]

    def add_games_to_study(self, study_id, game_ids):
        """Add games to a study"""
        conn = self._get_conn()
        cursor = conn.cursor()
        count = 0
        now = datetime.now()
        
        # In SQLite implementation, game_ids might be strings (game_id) or ints (id)
        # The interface in app.py passes what?
        # In app.py: added_game_ids.append(res.inserted_id)
        # In Mongo, inserted_id is ObjectId.
        # In SQLite, it's int (rowid) or we might have returned game_id string?
        # Let's check save_games logic. It doesn't return IDs.
        # Wait, app.py logic for "Save to Personal Study":
        # It calls parser.parse_game -> db_manager.games.insert_one -> gets ID.
        # We need to support `db_manager.games.insert_one` if we want to keep app.py compatible?
        # OR we update app.py to use `save_games` or a generic method.
        # The app.py code uses `db_manager.games.insert_one(game_data)`.
        # This accesses the underlying collection directly! This breaks encapsulation.
        # I need to handle this.
        
        # Option 1: Mock `games` attribute to have `insert_one`.
        # Option 2: Update app.py to use a method like `insert_single_game`.
        
        # I will update app.py to use a method `insert_game(game_data)` on the manager,
        # and implement that in both managers.
        
        # But for now, let's implement this method assuming we get game_ids (which are likely the 'game_id' strings or internal IDs).
        # In app.py, `added_game_ids` are collected from `res.inserted_id`.
        # If I implement `insert_game` to return the internal ID, this works.
        
        for g_id in game_ids:
            try:
                # If g_id is an ObjectId (from Mongo), this will fail in SQLite.
                # But if we are using PortableDB, we won't have ObjectIds.
                # We need to ensure consistency.
                
                # Check if game exists in games table first?
                # The logic in app.py inserts it first.
                
                # We need to link study_id to game_id (string) or internal id?
                # My schema uses game_id (TEXT) as FK in study_games?
                # "FOREIGN KEY(game_id) REFERENCES games(game_id)" -> Yes, references the TEXT column.
                
                # So we need to pass the game_id string.
                # If `insert_game` returns the internal ID (int), we might need to fetch the game_id string?
                # Or we just use the internal ID for linking?
                # Let's change schema to use internal ID for linking to be cleaner.
                # "FOREIGN KEY(game_id) REFERENCES games(id)" -> Integer FK.
                
                cursor.execute('''
                    INSERT OR IGNORE INTO study_games (study_id, game_id, added_at)
                    VALUES (?, ?, ?)
                ''', (study_id, g_id, now))
                if cursor.rowcount > 0:
                    count += 1
            except Exception as e:
                logger.error(f"Error adding game to study: {e}")
                
        # Update study timestamp
        cursor.execute("UPDATE studies SET updated_at = ? WHERE id = ?", (now, study_id))
        conn.commit()
        return count

    def get_games_in_study(self, study_id):
        """Get all games in a study"""
        conn = self._get_conn()
        query = '''
            SELECT g.* 
            FROM games g
            JOIN study_games sg ON g.game_id = sg.game_id
            WHERE sg.study_id = ?
        '''
        # Note: Schema above had game_id as TEXT FK. I should change it to use ID (int) for consistency if insert_one returns ID.
        # Let's stick to using the internal ID (int) for the link.
        
        df = pd.read_sql_query(query, conn, params=(study_id,))
        # Convert to list of dicts
        return df.to_dict('records')

    def delete_study(self, study_id):
        """Delete a study"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM study_games WHERE study_id = ?", (study_id,))
            cursor.execute("DELETE FROM studies WHERE id = ?", (study_id,))
            conn.commit()
            return True
        except Exception:
            return False

    def close(self):
        if self.conn:
            self.conn.close()

    # --- Compatibility Helpers ---
    # app.py accesses db.games.insert_one. We need to support this or change app.py.
    # I will add a dummy 'games' property that has an 'insert_one' method?
    # Better: Update app.py to call `db.insert_game(game_data)`.
    
    def insert_game(self, game_data):
        """
        Insert a single game dict (from parser).
        Returns an object with .inserted_id
        """
        # Adapt game_data (which is Mongo-style) to SQLite columns
        # Mongo: "white_elo", "eco_code"
        # SQLite: "white_rating", "eco" (based on my schema above)
        # Wait, my save_games used "white_rating".
        # game_data from parser likely has "white_elo" etc.
        # I need to map it.
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Extract fields
        g_id = game_data.get('game_id')
        
        # Check if exists
        cursor.execute("SELECT id FROM games WHERE game_id = ?", (g_id,))
        row = cursor.fetchone()
        if row:
            class Result:
                inserted_id = row[0]
            return Result()
            
        # Insert
        # Need to handle players too?
        # Yes, FK constraints.
        w_user = game_data.get('white')
        b_user = game_data.get('black')
        w_elo = game_data.get('white_elo')
        b_elo = game_data.get('black_elo')
        
        w_id = self.get_or_create_player(w_user, w_elo)
        b_id = self.get_or_create_player(b_user, b_elo)
        
        cursor.execute('''
            INSERT INTO games (
                game_id, site, date, white_user, black_user, 
                white_rating, black_rating, result, eco, opening_name, 
                time_control, moves, ply_count, acpl, 
                clocks, clock_settings, analysis, white_analysis, black_analysis,
                white_player_id, black_player_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            g_id, 
            game_data.get('site'),
            game_data.get('date'), # datetime object?
            w_user, b_user,
            w_elo, b_elo,
            game_data.get('result'),
            game_data.get('eco_code'), # parser uses eco_code
            game_data.get('opening_name'),
            game_data.get('time_control'),
            game_data.get('moves'),
            0, # ply_count
            None, # acpl
            json.dumps(game_data.get('clocks', [])),
            json.dumps(game_data.get('clock', {})),
            json.dumps(game_data.get('analysis', [])),
            json.dumps(game_data.get('players', {}).get('white', {}).get('analysis', {})),
            json.dumps(game_data.get('players', {}).get('black', {}).get('analysis', {})),
            w_id, b_id,
            datetime.now()
        ))
        conn.commit()
        
        class Result:
            inserted_id = cursor.lastrowid
        return Result()

    def get_stats(self):
        """Get basic database statistics"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM games")
            count = cursor.fetchone()[0]
            return {
                "status": "Connected (Portable)",
                "games": count
            }
        except Exception:
            return {
                "status": "Disconnected",
                "games": 0
            }

    # --- Personal Studies Methods ---
    def create_study(self, name: str, description: str = ""):
        """Create a new study"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO studies (name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (name, description, datetime.now(), datetime.now()))
            conn.commit()
            return cursor.lastrowid # Returns ID (int)
        except Exception as e:
            logger.error(f"Error creating study: {e}")
            return None

    def get_studies(self):
        """Get all studies"""
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row # Ensure dict-like access
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM studies ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        # Convert to list of dicts
        return [dict(row) for row in rows]

    def add_games_to_study(self, study_id, game_ids):
        """Add games to a study"""
        conn = self._get_conn()
        cursor = conn.cursor()
        count = 0
        now = datetime.now()
        
        # In SQLite implementation, game_ids might be strings (game_id) or ints (id)
        # The interface in app.py passes what?
        # In app.py: added_game_ids.append(res.inserted_id)
        # In Mongo, inserted_id is ObjectId.
        # In SQLite, it's int (rowid) or we might have returned game_id string?
        # Let's check save_games logic. It doesn't return IDs.
        # Wait, app.py logic for "Save to Personal Study":
        # It calls parser.parse_game -> db_manager.games.insert_one -> gets ID.
        # We need to support `db_manager.games.insert_one` if we want to keep app.py compatible?
        # OR we update app.py to use `save_games` or a generic method.
        # The app.py code uses `db_manager.games.insert_one(game_data)`.
        # This accesses the underlying collection directly! This breaks encapsulation.
        # I need to handle this.
        
        # Option 1: Mock `games` attribute to have `insert_one`.
        # Option 2: Update app.py to use a method like `insert_single_game`.
        
        # I will update app.py to use a method `insert_game(game_data)` on the manager,
        # and implement that in both managers.
        
        # But for now, let's implement this method assuming we get game_ids (which are likely the 'game_id' strings or internal IDs).
        # In app.py, `added_game_ids` are collected from `res.inserted_id`.
        # If I implement `insert_game` to return the internal ID, this works.
        
        for g_id in game_ids:
            try:
                # If g_id is an ObjectId (from Mongo), this will fail in SQLite.
                # But if we are using PortableDB, we won't have ObjectIds.
                # We need to ensure consistency.
                
                # Check if game exists in games table first?
                # The logic in app.py inserts it first.
                
                # We need to link study_id to game_id (string) or internal id?
                # My schema uses game_id (TEXT) as FK in study_games?
                # "FOREIGN KEY(game_id) REFERENCES games(game_id)" -> Yes, references the TEXT column.
                
                # So we need to pass the game_id string.
                # If `insert_game` returns the internal ID (int), we might need to fetch the game_id string?
                # Or we just use the internal ID for linking?
                # Let's change schema to use internal ID for linking to be cleaner.
                # "FOREIGN KEY(game_id) REFERENCES games(id)" -> Integer FK.
                
                cursor.execute('''
                    INSERT OR IGNORE INTO study_games (study_id, game_id, added_at)
                    VALUES (?, ?, ?)
                ''', (study_id, g_id, now))
                if cursor.rowcount > 0:
                    count += 1
            except Exception as e:
                logger.error(f"Error adding game to study: {e}")
                
        # Update study timestamp
        cursor.execute("UPDATE studies SET updated_at = ? WHERE id = ?", (now, study_id))
        conn.commit()
        return count

    def get_games_in_study(self, study_id):
        """Get all games in a study"""
        conn = self._get_conn()
        query = '''
            SELECT g.* 
            FROM games g
            JOIN study_games sg ON g.game_id = sg.game_id
            WHERE sg.study_id = ?
        '''
        # Note: Schema above had game_id as TEXT FK. I should change it to use ID (int) for consistency if insert_one returns ID.
        # Let's stick to using the internal ID (int) for the link.
        
        df = pd.read_sql_query(query, conn, params=(study_id,))
        # Convert to list of dicts
        return df.to_dict('records')

    def delete_study(self, study_id):
        """Delete a study"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM study_games WHERE study_id = ?", (study_id,))
            cursor.execute("DELETE FROM studies WHERE id = ?", (study_id,))
            conn.commit()
            return True
        except Exception:
            return False

    def close(self):
        if self.conn:
            self.conn.close()

    # --- Compatibility Helpers ---
    # app.py accesses db.games.insert_one. We need to support this or change app.py.
    # I will add a dummy 'games' property that has an 'insert_one' method?
    # Better: Update app.py to call `db.insert_game(game_data)`.
    
    def insert_game(self, game_data):
        """
        Insert a single game dict (from parser).
        Returns an object with .inserted_id
        """
        # Adapt game_data (which is Mongo-style) to SQLite columns
        # Mongo: "white_elo", "eco_code"
        # SQLite: "white_rating", "eco" (based on my schema above)
        # Wait, my save_games used "white_rating".
        # game_data from parser likely has "white_elo" etc.
        # I need to map it.
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Extract fields
        g_id = game_data.get('game_id')
        
        # Check if exists
        cursor.execute("SELECT id FROM games WHERE game_id = ?", (g_id,))
        row = cursor.fetchone()
        if row:
            class Result:
                inserted_id = row[0]
            return Result()
            
        # Insert
        # Need to handle players too?
        # Yes, FK constraints.
        w_user = game_data.get('white')
        b_user = game_data.get('black')
        w_elo = game_data.get('white_elo')
        b_elo = game_data.get('black_elo')
        
        w_id = self.get_or_create_player(w_user, w_elo)
        b_id = self.get_or_create_player(b_user, b_elo)
        
        cursor.execute('''
            INSERT INTO games (
                game_id, site, date, white_user, black_user, 
                white_rating, black_rating, result, eco, opening_name, 
                time_control, moves, ply_count, acpl, 
                clocks, clock, analysis, white_analysis, black_analysis,
                white_player_id, black_player_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            g_id, 
            game_data.get('site'),
            game_data.get('date'), # datetime object?
            w_user, b_user,
            w_elo, b_elo,
            game_data.get('result'),
            game_data.get('eco_code'), # parser uses eco_code
            game_data.get('opening_name'),
            game_data.get('time_control'),
            game_data.get('moves'),
            0, # ply_count
            None, # acpl
            json.dumps(game_data.get('clocks', [])),
            json.dumps(game_data.get('clock', {})),
            json.dumps(game_data.get('analysis', [])),
            json.dumps(game_data.get('players', {}).get('white', {}).get('analysis', {})),
            json.dumps(game_data.get('players', {}).get('black', {}).get('analysis', {})),
            w_id, b_id,
            datetime.now()
        ))
        conn.commit()
        
        class Result:
            inserted_id = cursor.lastrowid
        return Result()

    def update_game(self, game_id: str, updates: Dict) -> bool:
        """Update a game record with new fields"""
        if not updates:
            return False
            
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Prepare fields
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            # Handle JSON fields
            if key in ['clocks', 'clock', 'analysis', 'white_analysis', 'black_analysis']:
                val_to_store = json.dumps(value)
                if key == 'clock':
                    col_name = 'clock_settings' # Map to schema column
                else:
                    col_name = key
            else:
                val_to_store = value
                col_name = key
                
            set_clauses.append(f"{col_name} = ?")
            params.append(val_to_store)
            
        params.append(game_id)
        
        query = f"UPDATE games SET {', '.join(set_clauses)} WHERE game_id = ?"
        
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating game {game_id}: {e}")
            return False
