"""
Chess Analytics System - Main Application
Simple command-line interface for imports and analytics
"""

import sys
import logging
from chess_database import ChessDatabaseManager
from chess_parser import OptimizedPGNParser
from chess_analytics import ChessAnalytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_database(db):
    """Setup database with indexes and time-series collection"""
    print("\n🔧 Setting up database...")
    db.setup_timeseries_collection()
    db.create_indexes()
    print("✅ Database setup complete!\n")


def import_games(db, filepath, max_games=None):
    """Import games from PGN file"""
    print(f"\n📥 Importing games from: {filepath}")
    parser = OptimizedPGNParser(db, batch_size=1000, max_memory_mb=500)
    parser.ingest_pgn_file(filepath, max_games=max_games)
    print("✅ Import complete!\n")


def show_opening_stats(analytics, min_games=100):
    """Display opening statistics"""
    print(f"\n📊 Opening Success Rates (min {min_games} games):")
    print("=" * 80)
    
    openings = analytics.get_opening_success_rates(min_games=min_games)
    
    for i, opening in enumerate(openings[:20], 1):
        print(f"\n{i}. {opening['eco_code']}: {opening['opening_name']}")
        print(f"   Games: {opening['total_games']:,}")
        print(f"   White: {opening['win_rate_white']:.1%} | "
              f"Black: {opening['win_rate_black']:.1%} | "
              f"Draws: {opening['draw_rate']:.1%}")
        print(f"   Avg Rating: {opening['avg_rating']:.0f}")
        print(f"   White Advantage: {opening['white_advantage']:+.1%}")


def show_time_control_stats(analytics):
    """Display time control statistics"""
    print("\n⏱️  Performance by Time Control:")
    print("=" * 80)
    
    results = analytics.get_performance_by_time_control()
    
    for tc in results:
        print(f"\n{tc['time_control'].upper()}:")
        print(f"   Games: {tc['total_games']:,}")
        print(f"   Avg Rating: {tc['avg_rating']:.0f}")
        print(f"   White: {tc['white_win_rate']:.1%} | "
              f"Black: {tc['black_win_rate']:.1%} | "
              f"Draws: {tc['draw_rate']:.1%}")


def show_player_stats(analytics, username):
    """Display player statistics"""
    print(f"\n👤 Player Analysis: {username}")
    print("=" * 80)
    
    # Rating trends
    ratings = analytics.get_rating_trends(username, limit=20)
    if ratings:
        print("\n📈 Recent Rating History:")
        for entry in ratings[:10]:
            print(f"   {entry['timestamp']}: {entry['rating']}")
    else:
        print(f"   No rating history found for {username}")
    
    # Opening repertoire
    print("\n♟️  Opening Repertoire (White):")
    repertoire = analytics.get_player_opening_repertoire(username, "white", min_games=3)
    
    if repertoire:
        for i, opening in enumerate(repertoire[:10], 1):
            print(f"\n   {i}. {opening['eco_code']}: {opening['opening_name']}")
            print(f"      Games: {opening['games_played']} | "
                  f"Score: {opening['score_rate']:.1%} | "
                  f"Win Rate: {opening['win_rate']:.1%}")
    else:
        print(f"   No games found for {username}")


def show_database_status(analytics):
    """Display database status"""
    print("\n📊 Database Status:")
    print("=" * 80)
    
    stats = analytics.get_database_stats()
    print(f"   Players: {stats['players']:,}")
    print(f"   Games: {stats['games']:,}")
    print(f"   Openings: {stats['openings']:,}")
    print(f"   Rating History Entries: {stats['rating_history']:,}")
    print()


def print_help():
    """Print help message"""
    print("""
Chess Analytics System - Command Line Interface

USAGE:
    python main.py <command> [options]

COMMANDS:
    setup                          - Setup database with indexes
    import <file> [max_games]      - Import PGN file
    openings [min_games]           - Show opening statistics
    timecontrol                    - Show time control statistics
    player <username>              - Show player statistics
    status                         - Show database status
    help                           - Show this help message

EXAMPLES:
    python main.py setup
    python main.py import games.pgn 10000
    python main.py openings 100
    python main.py timecontrol
    python main.py player "Magnus"
    python main.py status

CONFIGURATION:
    Edit connection_string in main.py to connect to your MongoDB instance.
    Default: mongodb://localhost:27017/
    """)


def main():
    """Main entry point"""
    
    # Configuration
    CONNECTION_STRING = "mongodb://localhost:27017/"
    DATABASE_NAME = "chess_analysis"
    
    # Parse command
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1].lower()
    
    # Handle help
    if command == "help":
        print_help()
        return
    
    # Initialize database
    try:
        db = ChessDatabaseManager(CONNECTION_STRING, DATABASE_NAME)
        analytics = ChessAnalytics(db)
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        print("Make sure MongoDB is running and accessible.")
        return
    
    try:
        # Execute command
        if command == "setup":
            setup_database(db)
        
        elif command == "import":
            if len(sys.argv) < 3:
                print("❌ Error: Please specify PGN file path")
                print("Usage: python main.py import <file> [max_games]")
                return
            
            filepath = sys.argv[2]
            max_games = int(sys.argv[3]) if len(sys.argv) > 3 else None
            
            # Setup database if not already done
            setup_database(db)
            import_games(db, filepath, max_games)
        
        elif command == "openings":
            min_games = int(sys.argv[2]) if len(sys.argv) > 2 else 100
            show_opening_stats(analytics, min_games)
        
        elif command == "timecontrol":
            show_time_control_stats(analytics)
        
        elif command == "player":
            if len(sys.argv) < 3:
                print("❌ Error: Please specify username")
                print("Usage: python main.py player <username>")
                return
            
            username = sys.argv[2]
            show_player_stats(analytics, username)
        
        elif command == "status":
            show_database_status(analytics)
        
        else:
            print(f"❌ Unknown command: {command}")
            print_help()
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
