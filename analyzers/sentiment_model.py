import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def analyze_sentiment(df):
    """
    Analyzes sentiment for text-based columns in a DataFrame.
    """
    # Try to find a text column
    text_col = next((col for col in df.columns if col.lower() in ['feedback', 'review', 'comment', 'content', 'text', 'body']), None)
    
    if not text_col:
        # Fallback: Find column with longest average string length
        try:
            str_cols = df.select_dtypes(include=['object', 'string']).columns
            if len(str_cols) > 0:
                text_col = max(str_cols, key=lambda x: df[x].astype(str).str.len().mean())
        except:
            pass

    if not text_col:
        print("No suitable text column found. Skipping sentiment analysis.")
        return df

    print(f"--- Running sentiment analysis on column: {text_col} ---")
    analyzer = SentimentIntensityAnalyzer()
    
    def get_sentiment(text):
        if not isinstance(text, str):
            return 'Neutral'
        score = analyzer.polarity_scores(text)
        compound = score['compound']
        if compound >= 0.05: return 'Positive'
        elif compound <= -0.05: return 'Negative'
        else: return 'Neutral'
        
    def get_score(text):
        if not isinstance(text, str): return 0
        return analyzer.polarity_scores(text)['compound']

    # Apply sentiment
    df['sentiment'] = df[text_col].apply(get_sentiment)
    df['sentiment_score'] = df[text_col].apply(get_score)
    
    return df

def get_sentiment_trends(df):
    """
    Generates time-series data for sentiment.
    """
    # Find date column
    date_col = next((col for col in df.columns if 'date' in col.lower() or 'time' in col.lower() or 'created' in col.lower()), None)
    
    if not date_col or 'sentiment' not in df.columns:
        return {}
        
    try:
        # Ensure datetime format
        df['temp_date'] = pd.to_datetime(df[date_col], errors='coerce')
        df_clean = df.dropna(subset=['temp_date'])
        
        if df_clean.empty:
            return {}

        # Group by Date and Sentiment
        # Determine frequency based on time span
        time_span = df_clean['temp_date'].max() - df_clean['temp_date'].min()
        freq = 'D' if time_span.days < 60 else 'W' if time_span.days < 365 else 'M'
        
        trend = df_clean.groupby([pd.Grouper(key='temp_date', freq=freq), 'sentiment']).size().reset_index(name='count')
        trend['date_str'] = trend['temp_date'].dt.strftime('%Y-%m-%d')
        
        # Pivot for easy charting: Date | Negative | Neutral | Positive
        pivot_trend = trend.pivot(index='date_str', columns='sentiment', values='count').fillna(0).reset_index()
        
        return pivot_trend.to_dict(orient='list')
        
    except Exception as e:
        print(f"Error in sentiment trends: {e}")
        return {}