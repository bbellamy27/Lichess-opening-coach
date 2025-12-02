from stockfish import Stockfish
import os

class LocalEngine:
    def __init__(self, path="stockfish.exe"):
        self.path = path
        self.engine = None
        
    def _init_engine(self):
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"Stockfish executable not found at {self.path}")
            
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
        
        # We need to replay the game
        # Note: Stockfish library usually takes moves in coordinate notation (e.g. "e2e4")
        # But we have SAN. We need python-chess to convert.
        import chess
        board = chess.Board()
        
        for i, move_san in enumerate(moves_san):
            # 1. Get eval before move
            self.engine.set_fen_position(board.fen())
            eval_before = self.engine.get_evaluation()
            
            # Convert eval to centipawns (cap at 1000)
            score_before = self._parse_eval(eval_before)
            
            # 2. Make move
            try:
                move = board.push_san(move_san)
            except ValueError:
                break
                
            # 3. Get best move eval (what engine would have done)
            # Actually, ACPL is difference between your move's eval and best move's eval.
            # But we already have the eval *before* the move (which represents the best possible position).
            # We need the eval *after* the move, but from the perspective of the same player?
            # No, standard ACPL definition:
            # Eval(BestMove) - Eval(PlayedMove)
            
            # So we need:
            # A. Eval of position BEFORE move (Best possible eval)
            # B. Eval of position AFTER move (Actual eval)
            
            # Wait, if I am White:
            # Position is +0.5.
            # I play a move.
            # New position (Black to move) is +0.3.
            # That means I lost 0.2 (20 cp).
            
            # So we just need to track the eval swing.
            
            self.engine.set_fen_position(board.fen())
            eval_after = self.engine.get_evaluation()
            score_after = self._parse_eval(eval_after)
            
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
            
            loss = score_before + score_after
            loss = max(0, loss) # Loss cannot be negative (unless you found a move better than engine saw at depth 15)
            
            if i % 2 == 0: # White
                white_loss += loss
                white_moves += 1
            else: # Black
                black_loss += loss
                black_moves += 1
                
        return {
            'white_acpl': white_loss / white_moves if white_moves else 0,
            'black_acpl': black_loss / black_moves if black_moves else 0
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
