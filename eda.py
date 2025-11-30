import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Chess.com Color Palette
COLORS = {
    'Win': '#81b64c',   # Green
    'Loss': '#ca3431',  # Red
    'Draw': '#a7a6a2',  # Gray
    'Background': '#262522',
    'Text': '#e6edf3'
}

def plot_win_rate_by_color(df):
    """
    Generate a bar chart showing the result distribution (Win/Loss/Draw) by color.
    """
    if df.empty:
        return None
        
    win_rates = df.groupby(['user_color', 'result']).size().reset_index(name='count')
    
    fig = px.bar(win_rates, x='user_color', y='count', color='result', 
                 title="Games Played by Color",
                 color_discrete_map=COLORS,
                 labels={'user_color': 'Color', 'count': 'Games'})
    
    fig.update_layout(
        plot_bgcolor=COLORS['Background'],
        paper_bgcolor=COLORS['Background'],
        font_color=COLORS['Text']
    )
    return fig

def plot_rating_trend(df):
    """
    Generate a line chart showing the user's rating over time.
    """
    if df.empty:
        return None
        
    df_sorted = df.sort_values('date')
    
    fig = px.line(df_sorted, x='date', y='user_rating', title="Rating Trend",
                  markers=True)
    
    fig.update_traces(line_color=COLORS['Win'])
    fig.update_layout(
        plot_bgcolor=COLORS['Background'],
        paper_bgcolor=COLORS['Background'],
        font_color=COLORS['Text']
    )
    return fig

def plot_top_openings(df, n=10):
    """
    Generate a horizontal bar chart of the most frequently played openings.
    """
    if df.empty:
        return None
        
    top_openings = df['opening_name'].value_counts().head(n).reset_index()
    top_openings.columns = ['opening_name', 'count']
    
    fig = px.bar(top_openings, x='count', y='opening_name', orientation='h',
                 title=f"Top {n} Openings",
                 labels={'opening_name': 'Opening', 'count': 'Games'})
    
    fig.update_traces(marker_color=COLORS['Draw'])
    fig.update_layout(
        yaxis={'categoryorder':'total ascending'},
        plot_bgcolor=COLORS['Background'],
        paper_bgcolor=COLORS['Background'],
        font_color=COLORS['Text']
    )
    return fig

def plot_win_rate_by_opening(opening_stats, min_games=5):
    """
    Generate a bar chart of win rates for openings.
    """
    if opening_stats.empty:
        return None
        
    filtered = opening_stats[opening_stats['games'] >= min_games].head(15).copy()
    
    if filtered.empty:
        # Return a blank figure with annotation
        fig = go.Figure()
        fig.update_layout(
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=[
                {
                    "text": "Not enough games played<br>(Must have at least 5 games per opening)",
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {"size": 16, "color": COLORS['Text']}
                }
            ],
            plot_bgcolor=COLORS['Background'],
            paper_bgcolor=COLORS['Background'],
            title=f"Win Rate by Opening (min {min_games} games)"
        )
        return fig

    filtered['win_rate_pct'] = filtered['win_rate'] * 100
    
    fig = px.bar(filtered, x='win_rate_pct', y='opening_name', orientation='h',
                 title=f"Win Rate by Opening (min {min_games} games)",
                 labels={'opening_name': 'Opening', 'win_rate_pct': 'Win Rate (%)'},
                 color='win_rate', 
                 color_continuous_scale=[(0, COLORS['Loss']), (0.5, COLORS['Draw']), (1, COLORS['Win'])],
                 text_auto='.1f') # Show value on bar
                 
    fig.update_layout(
        yaxis={'categoryorder':'total ascending'},
        xaxis_title="Win Rate (%)",
        xaxis=dict(range=[0, 100]), # Fix range to 0-100
        plot_bgcolor=COLORS['Background'],
        paper_bgcolor=COLORS['Background'],
        font_color=COLORS['Text']
    )
    return fig

def plot_time_heatmap(df):
    """
    Generate a heatmap showing activity by Hour of Day and Day of Week.
    """
    if df.empty:
        return None
        
    heatmap_data = df.groupby(['day_of_week', 'hour']).size().reset_index(name='count')
    heatmap_pivot = heatmap_data.pivot(index='day_of_week', columns='hour', values='count').fillna(0)
    
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_pivot = heatmap_pivot.reindex(days_order)
    
    fig = px.imshow(heatmap_pivot, 
                    labels=dict(x="Hour", y="Day", color="Games"),
                    title="Activity Heatmap",
                    color_continuous_scale='Viridis') # Keep Viridis for heatmap contrast
                    
    fig.update_layout(
        plot_bgcolor=COLORS['Background'],
        paper_bgcolor=COLORS['Background'],
        font_color=COLORS['Text']
    )
    return fig

def plot_opponent_scatter(df):
    """
    Generate a stacked bar chart of results against different opponent rating bins.
    """
    if df.empty:
        return None
        
    bin_stats = df.groupby(['opponent_rating_bin', 'result']).size().reset_index(name='count')
    bin_order = ["<1000", "1000-1200", "1200-1400", "1400-1600", "1600-1800", "1800-2000", "2000-2200", "2200+"]
    
    fig = px.bar(bin_stats, x='opponent_rating_bin', y='count', color='result',
                 title="Results by Opponent Rating",
                 category_orders={"opponent_rating_bin": bin_order},
                 color_discrete_map=COLORS,
                 labels={'opponent_rating_bin': 'Rating Range', 'count': 'Games'})
                 
    fig.update_layout(
        plot_bgcolor=COLORS['Background'],
        paper_bgcolor=COLORS['Background'],
        font_color=COLORS['Text'],
        barmode='stack'
    )
    return fig

def plot_termination_pie(df):
    """
    Generate a donut chart showing how games ended.
    """
    if df.empty:
        return None
        
    term_counts = df['termination'].value_counts().reset_index()
    term_counts.columns = ['termination', 'count']
    
    fig = px.pie(term_counts, values='count', names='termination', 
                 title="Game Results (By Type)",
                 hole=0.5,
                 color_discrete_sequence=[COLORS['Win'], COLORS['Loss'], COLORS['Draw'], '#e2b714'])
                 
    fig.update_layout(
        plot_bgcolor=COLORS['Background'],
        paper_bgcolor=COLORS['Background'],
        font_color=COLORS['Text']
    )
    return fig

def plot_correlation_heatmap(df):
    """
    Generate a correlation heatmap for numerical variables.
    """
    if df.empty:
        return None
    
    # Select numerical columns for correlation
    # We map 'result' to a numeric value for correlation: Win=1, Draw=0.5, Loss=0
    df_corr = df.copy()
    result_map = {'Win': 1, 'Draw': 0.5, 'Loss': 0}
    df_corr['result_numeric'] = df_corr['result'].map(result_map)
    
    cols = ['user_rating', 'opponent_rating', 'ply_count', 'result_numeric']
    corr_matrix = df_corr[cols].corr()
    
    # Rename for better display
    labels = {
        'user_rating': 'My Rating',
        'opponent_rating': 'Opp Rating',
        'ply_count': 'Moves (Ply)',
        'result_numeric': 'Result'
    }
    
    fig = px.imshow(corr_matrix,
                    x=[labels.get(c, c) for c in corr_matrix.columns],
                    y=[labels.get(c, c) for c in corr_matrix.columns],
                    title="Correlation Matrix",
                    color_continuous_scale='RdBu_r', # Red-Blue diverging
                    zmin=-1, zmax=1)
                    
    fig.update_layout(
        plot_bgcolor=COLORS['Background'],
        paper_bgcolor=COLORS['Background'],
        font_color=COLORS['Text']
    )
    return fig
