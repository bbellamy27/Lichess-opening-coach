import pandas as pd
import streamlit as st
import textwrap

def render_game_list(df):
    """
    Render a list of recent games with checkboxes for selection.
    Returns a list of selected game IDs.
    """
    if df.empty:
        st.info("No games to display.")
        return []

    # CSS for the game list (injected once)
    st.markdown(textwrap.dedent("""
    <style>
        .game-row {
            display: grid;
            grid-template-columns: 50px 2fr 1fr 1fr 1fr 1fr 100px;
            align-items: center;
            background-color: #302e2b;
            padding: 10px;
            border-radius: 4px;
            color: #e6edf3;
            border-bottom: 1px solid #403d39;
            margin-bottom: 2px;
        }
        .game-row:hover {
            background-color: #383531;
        }
        .game-icon {
            font-size: 24px;
            text-align: center;
            color: #a7a6a2;
        }
        .player-info {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .player-row {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }
        .player-name {
            font-weight: 600;
            color: #fff;
        }
        .player-rating {
            color: #a7a6a2;
            font-size: 12px;
        }
        .result-column {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14px;
        }
        .win-badge {
            background-color: #81b64c;
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
        }
        .loss-badge {
            background-color: #ca3431;
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
        }
        .draw-badge {
            background-color: #a7a6a2;
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
        }
        .review-btn {
            background-color: #403d39;
            color: #fff;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            text-decoration: none;
            font-size: 12px;
            font-weight: 600;
            text-align: center;
            display: inline-block;
        }
        .review-btn:hover {
            background-color: #4f4c48;
            color: #fff;
        }
        .accuracy-column {
            text-align: center;
            color: #a7a6a2;
            font-size: 14px;
        }
        .moves-column {
            text-align: center;
            color: #a7a6a2;
            font-size: 14px;
        }
        .date-column {
            text-align: right;
            color: #a7a6a2;
            font-size: 12px;
        }
        .color-indicator {
            width: 10px;
            height: 10px;
            border-radius: 2px;
            display: inline-block;
        }
        .white-indicator { background-color: #fff; border: 1px solid #a7a6a2; }
        .black-indicator { background-color: #000; border: 1px solid #a7a6a2; }
        
        /* Checkbox alignment fix */
        div[data-testid="stCheckbox"] {
            padding-top: 20px;
        }
    </style>
    """), unsafe_allow_html=True)

    # Header
    st.markdown(textwrap.dedent("""
    <div class="game-row" style="background-color: #262522; border-bottom: 2px solid #403d39; font-weight: bold; color: #a7a6a2; margin-left: 30px;">
        <div>Type</div>
        <div>Players</div>
        <div style="text-align: center;">Result</div>
        <div style="text-align: center;">Review</div>
        <div style="text-align: center;">Accuracy</div>
        <div style="text-align: center;">Moves</div>
        <div style="text-align: right;">Date</div>
    </div>
    """), unsafe_allow_html=True)

    selected_games = []

    for index, row in df.iterrows():
        # Layout: Checkbox | Game Row
        c1, c2 = st.columns([0.05, 0.95])
        
        with c1:
            # Use game_id as key to ensure uniqueness
            if st.checkbox("", key=f"chk_{row['game_id']}"):
                selected_games.append(row['game_id'])

        with c2:
            # Icon based on speed
            speed = row['speed']
            icon = "♟️"
            if speed == 'bullet': icon = "🚀"
            elif speed == 'blitz': icon = "⚡"
            elif speed == 'rapid': icon = "⏱️"
            elif speed == 'classical': icon = "🐢"
            
            # Players
            white_name = row['white_user']
            black_name = row['black_user']
            white_rating = int(row['white_rating']) if pd.notnull(row['white_rating']) else "?"
            black_rating = int(row['black_rating']) if pd.notnull(row['black_rating']) else "?"
            
            # Result Badge
            result = row['result']
            if result == 'Win':
                badge_class = "win-badge"
                badge_text = "+"
            elif result == 'Loss':
                badge_class = "loss-badge"
                badge_text = "-"
            else:
                badge_class = "draw-badge"
                badge_text = "="
                
            # Accuracy
            acpl = row.get('acpl')
            accuracy = f"{acpl}" if pd.notnull(acpl) else "-"
            
            # Moves
            moves = int(row['ply_count'] / 2)
            
            # Date
            date_str = row['date'].strftime("%b %d")
            
            # Game Link
            game_id = row.get('game_id', '')
            game_url = f"https://lichess.org/{game_id}"
            
            st.markdown(textwrap.dedent(f"""
            <div class="game-row">
                <div class="game-icon">{icon}<br><span style="font-size: 10px;">{speed}</span></div>
                <div class="player-info">
                    <div class="player-row">
                        <span class="color-indicator white-indicator"></span>
                        <span class="player-name">{white_name}</span>
                        <span class="player-rating">({white_rating})</span>
                    </div>
                    <div class="player-row">
                        <span class="color-indicator black-indicator"></span>
                        <span class="player-name">{black_name}</span>
                        <span class="player-rating">({black_rating})</span>
                    </div>
                </div>
                <div class="result-column">
                    <span class="{badge_class}">{badge_text}</span>
                </div>
                <div style="text-align: center;">
                    <a href="{game_url}" target="_blank" class="review-btn">Review</a>
                </div>
                <div class="accuracy-column">
                    {accuracy}
                </div>
                <div class="moves-column">
                    {moves}
                </div>
                <div class="date-column">
                    {date_str}
                </div>
            </div>
            """), unsafe_allow_html=True)
            
    return selected_games

def render_opening_stats(stats):
    """
    Render opening statistics in a clean table.
    """
    if stats.empty:
        st.info("No opening stats available.")
        return

    st.markdown(textwrap.dedent("""
    <style>
        .opening-table {
            width: 100%;
            border-collapse: collapse;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            color: #e6edf3;
        }
        .opening-table th {
            text-align: left;
            padding: 12px;
            background-color: #262522;
            border-bottom: 2px solid #403d39;
            color: #a7a6a2;
            font-weight: 600;
        }
        .opening-table td {
            padding: 12px;
            border-bottom: 1px solid #403d39;
            background-color: #302e2b;
        }
        .opening-table tr:hover td {
            background-color: #383531;
        }
        .opening-name {
            font-weight: 600;
            color: #fff;
        }
        .stat-bar-container {
            display: flex;
            height: 6px;
            width: 100px;
            background-color: #403d39;
            border-radius: 3px;
            overflow: hidden;
            margin-top: 4px;
        }
        .stat-bar-win { background-color: #81b64c; }
        .stat-bar-draw { background-color: #a7a6a2; }
        .stat-bar-loss { background-color: #ca3431; }
    </style>
    """), unsafe_allow_html=True)
    
    html = textwrap.dedent("""
    <table class="opening-table">
        <thead>
            <tr>
                <th>Opening</th>
                <th>Games</th>
                <th>Performance</th>
                <th>Win Rate</th>
            </tr>
        </thead>
        <tbody>
    """)
    
    for index, row in stats.iterrows():
        name = row['opening_name']
        games = row['games']
        wins = row['wins']
        draws = row['draws']
        losses = row['losses']
        win_rate = row['win_rate']
        
        # Calculate percentages for bar
        win_pct = (wins / games) * 100
        draw_pct = (draws / games) * 100
        loss_pct = (losses / games) * 100
        
        html += textwrap.dedent(f"""
        <tr>
            <td><span class="opening-name">{name}</span></td>
            <td>{games}</td>
            <td>
                <div style="display: flex; gap: 5px; align-items: center;">
                    <span style="font-size: 12px; color: #a7a6a2;">{wins}W {draws}D {losses}L</span>
                </div>
                <div class="stat-bar-container">
                    <div class="stat-bar-win" style="width: {win_pct}%;"></div>
                    <div class="stat-bar-draw" style="width: {draw_pct}%;"></div>
                    <div class="stat-bar-loss" style="width: {loss_pct}%;"></div>
                </div>
            </td>
            <td>{win_rate:.1%}</td>
        </tr>
        """)
        
    html += textwrap.dedent("""
        </tbody>
    </table>
    """)
    st.markdown(html, unsafe_allow_html=True)
