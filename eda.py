import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def plot_win_rate_by_color(df):
    """
    Generate a bar chart showing the result distribution (Win/Loss/Draw) by color.
    
    Args:
        df (pd.DataFrame): The processed games DataFrame.
        
    Returns:
        plotly.graph_objects.Figure: The Plotly figure.
    """
    if df.empty:
        return None
        
    # Group by color and result to get counts
    win_rates = df.groupby(['user_color', 'result']).size().reset_index(name='count')
    
    # Create a bar chart with custom colors for results
    fig = px.bar(win_rates, x='user_color', y='count', color='result', 
                 title="Result Distribution by Color",
                 color_discrete_map={'Win': 'green', 'Loss': 'red', 'Draw': 'gray'})
    return fig

def plot_rating_trend(df):
    """
    Generate a line chart showing the user's rating over time.
    
    Args:
        df (pd.DataFrame): The processed games DataFrame.
        
    Returns:
        plotly.graph_objects.Figure: The Plotly figure.
    """
    if df.empty:
        return None
        
    # Sort by date to ensure the line flows correctly
    df_sorted = df.sort_values('date')
    
    fig = px.line(df_sorted, x='date', y='user_rating', title="Rating Trend Over Time",
                  markers=True)
    return fig

def plot_top_openings(df, n=10):
    """
    Generate a horizontal bar chart of the most frequently played openings.
    
    Args:
        df (pd.DataFrame): The processed games DataFrame.
        n (int): Number of top openings to show.
        
    Returns:
        plotly.graph_objects.Figure: The Plotly figure.
    """
    if df.empty:
        return None
        
    # Count occurrences of each opening
    top_openings = df['opening_name'].value_counts().head(n).reset_index()
    top_openings.columns = ['opening_name', 'count']
    
    fig = px.bar(top_openings, x='count', y='opening_name', orientation='h',
                 title=f"Top {n} Openings Played",
                 labels={'opening_name': 'Opening', 'count': 'Games'})
    
    # Ensure the most played is at the top
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    return fig

def plot_win_rate_by_opening(opening_stats, min_games=5):
    """
    Generate a bar chart of win rates for openings with a minimum number of games.
    
    Args:
        opening_stats (pd.DataFrame): The opening statistics DataFrame.
        min_games (int): Minimum games required to be included.
        
    Returns:
        plotly.graph_objects.Figure: The Plotly figure.
    """
    if opening_stats.empty:
        return None
        
    # Filter for openings with enough data
    filtered = opening_stats[opening_stats['games'] >= min_games].head(15)
    
    # Create bar chart colored by win rate (Red to Green)
    fig = px.bar(filtered, x='win_rate', y='opening_name', orientation='h',
                 title=f"Win Rate by Opening (min {min_games} games)",
                 labels={'opening_name': 'Opening', 'win_rate': 'Win Rate'},
                 color='win_rate', color_continuous_scale='RdYlGn')
                 
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    return fig

def plot_time_heatmap(df):
    """
    Generate a heatmap showing activity by Hour of Day and Day of Week.
    
    Args:
        df (pd.DataFrame): The processed games DataFrame.
        
    Returns:
        plotly.graph_objects.Figure: The Plotly figure.
    """
    if df.empty:
        return None
        
    # Group by Day and Hour to get game counts
    heatmap_data = df.groupby(['day_of_week', 'hour']).size().reset_index(name='count')
    
    # Pivot the data to create a matrix (Rows: Days, Cols: Hours)
    heatmap_pivot = heatmap_data.pivot(index='day_of_week', columns='hour', values='count').fillna(0)
    
    # Ensure all days are present and in correct order
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_pivot = heatmap_pivot.reindex(days_order)
    
    fig = px.imshow(heatmap_pivot, 
                    labels=dict(x="Hour of Day", y="Day of Week", color="Games Played"),
                    x=heatmap_pivot.columns,
                    y=heatmap_pivot.index,
                    title="Activity Heatmap: When do you play?",
                    color_continuous_scale='Viridis')
    return fig

def plot_opponent_scatter(df):
    """
    Generate a stacked bar chart of results against different opponent rating bins.
    
    Args:
        df (pd.DataFrame): The processed games DataFrame.
        
    Returns:
        plotly.graph_objects.Figure: The Plotly figure.
    """
    if df.empty:
        return None
        
    # Group by rating bin and result
    bin_stats = df.groupby(['opponent_rating_bin', 'result']).size().reset_index(name='count')
    
    # Define the logical order for rating bins
    bin_order = ["<1000", "1000-1200", "1200-1400", "1400-1600", "1600-1800", "1800-2000", "2000-2200", "2200+"]
    
    fig = px.bar(bin_stats, x='opponent_rating_bin', y='count', color='result',
                 title="Performance vs Opponent Rating",
                 category_orders={"opponent_rating_bin": bin_order},
                 color_discrete_map={'Win': 'green', 'Loss': 'red', 'Draw': 'gray'})
    return fig

def plot_termination_pie(df):
    """
    Generate a pie chart showing how games ended (Mate, Resign, etc.).
    
    Args:
        df (pd.DataFrame): The processed games DataFrame.
        
    Returns:
        plotly.graph_objects.Figure: The Plotly figure.
    """
    if df.empty:
        return None
        
    # Count occurrences of each termination type
    term_counts = df['termination'].value_counts().reset_index()
    term_counts.columns = ['termination', 'count']
    
    fig = px.pie(term_counts, values='count', names='termination', 
                 title="Game Termination Types",
                 hole=0.4) # Donut chart style
    return fig
