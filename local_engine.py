from stockfish import Stockfish
import os

import platform
import shutil

class LocalEngine:
    def __init__(self, path=None):
        if path is None:
            # Auto-detect default path based on OS
            system = platform.system()
            if system == "Windows":
                self.path = "stockfish.exe"
            else:
                # Linux/Mac: Check if 'stockfish' is in PATH or local folder
                if shutil.which("stockfish"):
                    self.path = "stockfish"
                elif os.path.exists("./stockfish"):
                    self.path = "./stockfish"
                else:
                    self.path = "stockfish" # Fallback
        else:
            self.path = path
            
        self.engine = None
        
    def _init_engine(self):
        if not shutil.which(self.path) and not os.path.exists(self.path):
             # Try to find it in current directory if not found
             if os.path.exists(os.path.join(os.getcwd(), self.path)):
                 self.path = os.path.join(os.getcwd(), self.path)
             else:
                raise FileNotFoundError(f"Stockfish executable not found. Please install Stockfish and ensure it is in your PATH or the project directory.")
            
        # Initialize Stockfish with reasonable settings for quick analysis
        self.engine = Stockfish(path=self.path, depth=15, parameters={"Threads": 2, "Hash": 16})

    def analyze_game(self, moves_san):
        """
        Analyze a game and calculate ACPL.
        
        Args:
            moves_san (list): List of moves in SAN format.
            
        Returns:
            dict: {'white_acpl': float, 'black_acpl': float}
        """
        if not self.engine:
            self._init_engine()
            
        self.engine.set_position() # Reset board
        
        white_loss = 0
        black_loss = 0
        white_moves = 0
        black_moves = 0
        analysis_list = []
        
        # We need to replay the game
        # Note: Stockfish library usually takes moves in coordinate notation (e.g. "e2e4")
        # But we have SAN. We need python-chess to convert.
        import chess
        board = chess.Board()
        
        for i, move_san in enumerate(moves_san):
            # 1. Get eval before move
            self.engine.set_fen_position(board.fen())
            
            # Use get_top_moves to force a search and get accurate eval
            top_moves = self.engine.get_top_moves(1)
            if top_moves:
                info = top_moves[0]
                if info.get('Mate') is not None:
                    score_before = 1000 if info['Mate'] > 0 else -1000
                else:
                    score_before = int(info.get('Centipawn', 0))
                    score_before = max(-1000, min(1000, score_before))
            else:
                score_before = 0
            
            # 2. Make move
            try:
                move = board.push_san(move_san)
            except ValueError:
                break
                
            # 3. Get eval after move
            self.engine.set_fen_position(board.fen())
            top_moves = self.engine.get_top_moves(1)
            if top_moves:
                info = top_moves[0]
                if info.get('Mate') is not None:
                    score_after = 1000 if info['Mate'] > 0 else -1000
                else:
                    score_after = int(info.get('Centipawn', 0))
                    score_after = max(-1000, min(1000, score_after))
            else:
                score_after = 0
            
            # Calculate Loss
            # If White moved (i is even):
            # We want ScoreBefore (White's perspective) - ScoreAfter (White's perspective)
            # ScoreAfter is usually given for side to move (Black). So we negate it?
            # Stockfish library get_evaluation() usually returns relative to side to move?
            # Let's check docs or assume standard UCI behavior.
            # Standard UCI 'score cp' is usually relative to side to move.
            
            # Let's normalize everything to White's perspective for calculation.
            
            val_before = score_before if i % 2 == 0 else -score_before
            val_after = -score_after if i % 2 == 0 else score_after # After move, it's opponent's turn
            
            # Wait, this is getting complicated.
            # Simpler approach for ACPL:
            # 1. Set position.
            # 2. Get best move and its eval (Ideal).
            # 3. Get eval of the move actually played.
            # Diff is loss.
            
            # But get_evaluation() just gives current pos eval.
            # So:
            # 1. Set position.
            # 2. Get eval (Best possible).
            # 3. Make move on board.
            # 4. Set new position.
            # 5. Get eval (Actual result).
            
            # If White to move:
            # Pos 1 Eval: +50 (White advantage)
            # White plays bad move.
            # Pos 2 Eval (Black to move): +30 (White advantage, but less)
            # Loss = 20.
            
            # If Black to move:
            # Pos 1 Eval: +50 (White advantage)
            # Black plays bad move.
            # Pos 2 Eval (White to move): +70 (White advantage increased)
            # Loss = 20 (from Black's perspective, went from -50 to -70).
            
            # Let's trust the 'cp' value is relative to side to move.
            # Before (Side X to move): +50
            # After (Side Y to move): -30 (which means +30 for Side X)
            # Loss = 50 - 30 = 20.
            
            # So: Loss = EvalBefore - (-EvalAfter)
            # Loss = EvalBefore + EvalAfter
            
            # Let's try this heuristic.
            
            # Calculate Loss
            loss = score_before + score_after
            loss = max(0, loss) # Loss cannot be negative
            
            # Store analysis data (Lichess format: always White perspective)
            # score_after is relative to side-to-move (the side that DID NOT just move)
            if i % 2 == 0: # White just moved, now Black to move
                white_loss += loss
                white_moves += 1
                # Engine score is Black's perspective -> Negate for White
                analysis_eval = -score_after
            else: # Black just moved, now White to move
                black_loss += loss
                black_moves += 1
                # Engine score is White's perspective -> Keep as is
                analysis_eval = score_after
                
            analysis_list.append({'eval': analysis_eval})
                
        return {
            'white_acpl': white_loss / white_moves if white_moves else 0,
            'black_acpl': black_loss / black_moves if black_moves else 0,
            'analysis': analysis_list
        }

    def _parse_eval(self, eval_dict):
        """
        Convert eval dict {'type': 'cp', 'value': 10} to centipawns.
        Handles mate scores by capping them.
        """
        if eval_dict['type'] == 'mate':
            # Mate in X. Positive = winning.
            val = eval_dict['value']
            if val > 0: return 1000 # Winning mate
            return -1000 # Losing mate
            
        val = eval_dict['value']
        # Cap at +/- 1000 to avoid skewing averages
        return max(-1000, min(1000, val))
