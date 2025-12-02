# Chess Analytics - Quick Reference Guide

## 🚀 Installation (1 Minute)

```bash
# Install dependencies
pip install pymongo python-chess

# Start MongoDB with replica set (required for transactions)
docker run -d -p 27017:27017 --name mongodb mongo:6.0
docker exec -it mongodb mongosh --eval "rs.initiate()"
```

---

## 📋 Common Commands

### Setup Database
```bash
python main.py setup
```

### Import Games
```bash
# Test with 1000 games
python main.py import sample.pgn 1000

# Import full file
python main.py import games.pgn

# Large file import
python main.py import lichess_2024_11.pgn
```

### View Statistics
```bash
# Opening analysis (minimum 100 games)
python main.py openings 100

# Time control comparison
python main.py timecontrol

# Player analysis
python main.py player "Magnus"
python main.py player "Hikaru"

# Database status
python main.py status
```

---

## 🔍 Quick Python Examples

### Import and Analyze
```python
from chess_database import ChessDatabaseManager
from chess_parser import OptimizedPGNParser
from chess_analytics import ChessAnalytics

# Setup
db = ChessDatabaseManager()
db.setup_timeseries_collection()
db.create_indexes()

# Import
parser = OptimizedPGNParser(db)
parser.ingest_pgn_file("games.pgn", max_games=10000)

# Analyze
analytics = ChessAnalytics(db)
openings = analytics.get_opening_success_rates(min_games=50)

# Display results
for op in openings[:10]:
    print(f"{op['eco_code']}: {op['win_rate_white']:.1%}")

db.close()
```

### Player Analysis
```python
# Get player rating trends
ratings = analytics.get_rating_trends("Magnus", limit=100)

# Get player's opening repertoire
repertoire = analytics.get_player_opening_repertoire(
    username="Magnus",
    color="white",
    min_games=5
)

# Print results
for opening in repertoire[:10]:
    print(f"{opening['eco_code']}: {opening['score_rate']:.1%}")
```

---

## 🗂️ File Structure

```
├── main.py                 # Main application CLI
├── chess_database.py       # Database manager
├── chess_parser.py         # PGN parser
├── chess_analytics.py      # Analytics queries
├── requirements.txt        # Python dependencies
└── README.md              # Full documentation
```

---

## ⚙️ Configuration

### Change Database Connection

Edit `main.py`:
```python
CONNECTION_STRING = "mongodb://user:pass@host:27017/"
DATABASE_NAME = "chess_analysis"
```

### Adjust Memory Usage

Edit `chess_parser.py`:
```python
parser = OptimizedPGNParser(
    db,
    batch_size=1000,        # Games per batch
    max_memory_mb=500       # Max memory usage
)
```

---

## 📊 MongoDB Queries

### Direct MongoDB Queries
```javascript
// Find top players
db.players.find({}).sort({peak_rating: -1}).limit(10)

// Find recent games
db.games.find({date: {$gte: ISODate("2024-01-01")}}).limit(10)

// Popular openings
db.openings.find({total_games: {$gte: 100}}).sort({total_games: -1})

// Check indexes
db.games.getIndexes()
```

---

## 🐛 Quick Fixes

### Problem: "Transaction not supported"
```bash
mongosh --eval "rs.initiate()"
```

### Problem: Out of memory
```python
# Reduce buffer size
parser = OptimizedPGNParser(db, batch_size=500, max_memory_mb=250)
```

### Problem: Slow queries
```bash
# Ensure indexes exist
python main.py setup

# Check index usage
mongosh chess_analysis --eval "db.games.explain().find({eco_code: 'B01'})"
```

---

## 📥 Download Chess Data

```bash
# Lichess database
wget https://database.lichess.org/standard/lichess_db_standard_rated_2024-11.pgn.zst

# Decompress
zstd -d lichess_db_standard_rated_2024-11.pgn.zst

# Import
python main.py import lichess_db_standard_rated_2024-11.pgn
```

---

## 📈 Performance Tips

1. **Always create indexes first**: `python main.py setup`
2. **Use batch imports**: Don't import one game at a time
3. **Monitor memory**: Use `max_memory_mb` parameter
4. **Use time controls**: Filter queries by time_control
5. **Set min_games**: Avoid low-sample-size statistics

---

## 🎯 Common Analytics Tasks

### Find Most Popular Openings
```bash
python main.py openings 100
```

### Analyze Time Controls
```bash
python main.py timecontrol
```

### Player Performance
```bash
python main.py player "YourUsername"
```

### Database Statistics
```bash
python main.py status
```

---

## 💡 Pro Tips

1. **Start small**: Test with 1000 games first
2. **Use replica set**: Required for transactions
3. **Monitor progress**: Import shows progress every 10k games
4. **Check errors**: Review logs if imports fail
5. **Backup data**: Use `mongodump` regularly

---

## 🔗 Useful Links

- **Lichess Data**: https://database.lichess.org/
- **MongoDB Docs**: https://docs.mongodb.com/
- **python-chess**: https://python-chess.readthedocs.io/

---

**Questions? Check README.md for detailed documentation!**
