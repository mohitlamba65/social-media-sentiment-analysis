import pandas as pd
import numpy as np
from collections import Counter
import re
from datetime import datetime, timedelta

def analyze_market_sentiment(df):
    """
    Analyzes overall market sentiment and provides insights.
    
    Returns:
        dict: Market sentiment metrics and insights
    """
    insights = {
        'overall_sentiment': 'Neutral',
        'sentiment_score': 0,
        'confidence': 0,
        'positive_ratio': 0,
        'negative_ratio': 0,
        'neutral_ratio': 0,
        'total_mentions': len(df),
        'engagement_trend': 'Stable',
        'recommendations': []
    }
    
    if 'sentiment' not in df.columns:
        insights['recommendations'].append('No sentiment data available')
        return insights
    
    # Calculate sentiment distribution
    sentiment_counts = df['sentiment'].value_counts()
    total = len(df)
    
    if total == 0:
        return insights

    positive = sentiment_counts.get('Positive', 0)
    negative = sentiment_counts.get('Negative', 0)
    neutral = sentiment_counts.get('Neutral', 0)
    
    insights['positive_ratio'] = round((positive / total) * 100, 1)
    insights['negative_ratio'] = round((negative / total) * 100, 1)
    insights['neutral_ratio'] = round((neutral / total) * 100, 1)
    
    # Calculate overall sentiment score (-1 to 1)
    sentiment_score = (positive - negative) / total
    insights['sentiment_score'] = round(sentiment_score, 3)
    
    # Determine overall sentiment
    if sentiment_score > 0.2:
        insights['overall_sentiment'] = 'Very Positive'
        insights['confidence'] = min(95, 70 + (sentiment_score * 50))
    elif sentiment_score > 0.05:
        insights['overall_sentiment'] = 'Positive'
        insights['confidence'] = 65
    elif sentiment_score < -0.2:
        insights['overall_sentiment'] = 'Very Negative'
        insights['confidence'] = min(95, 70 + (abs(sentiment_score) * 50))
    elif sentiment_score < -0.05:
        insights['overall_sentiment'] = 'Negative'
        insights['confidence'] = 65
    else:
        insights['overall_sentiment'] = 'Neutral'
        insights['confidence'] = 55
    
    # Analyze engagement trend if likes column exists
    if 'likes' in df.columns:
        avg_engagement = df['likes'].mean()
        high_engagement_threshold = df['likes'].quantile(0.75)
        
        positive_engagement = df[df['sentiment'] == 'Positive']['likes'].mean()
        negative_engagement = df[df['sentiment'] == 'Negative']['likes'].mean()
        
        # Handle NaN values if no positive/negative posts exist
        positive_engagement = 0 if pd.isna(positive_engagement) else positive_engagement
        negative_engagement = 0 if pd.isna(negative_engagement) else negative_engagement
        
        if positive_engagement > negative_engagement * 1.5:
            insights['engagement_trend'] = 'Positive content drives higher engagement'
        elif negative_engagement > positive_engagement * 1.5:
            insights['engagement_trend'] = 'Negative content drives higher engagement'
        else:
            insights['engagement_trend'] = 'Balanced engagement across sentiments'
    
    # Generate recommendations
    if insights['positive_ratio'] > 60:
        insights['recommendations'].append('✅ Strong positive sentiment - maintain current strategy')
        insights['recommendations'].append('📈 Consider amplifying positive messaging')
    elif insights['negative_ratio'] > 40:
        insights['recommendations'].append('⚠️ High negative sentiment detected')
        insights['recommendations'].append('🔧 Immediate action recommended - investigate root causes')
        insights['recommendations'].append('💬 Increase customer engagement and support')
    elif insights['neutral_ratio'] > 50:
        insights['recommendations'].append('📊 High neutral sentiment - opportunity to create stronger emotional connection')
        insights['recommendations'].append('🎯 Focus on creating more engaging content')
    
    # Time-based insights
    date_col = next((col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()), None)
    if date_col:
        try:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df_clean = df.dropna(subset=[date_col])
            
            if not df_clean.empty:
                # Check if sentiment is improving or declining
                df_clean = df_clean.sort_values(date_col)
                
                # Split into first half and second half
                midpoint = len(df_clean) // 2
                first_half = df_clean.iloc[:midpoint]
                second_half = df_clean.iloc[midpoint:]
                
                if len(first_half) > 0 and len(second_half) > 0:
                    first_positive = (first_half['sentiment'] == 'Positive').sum() / len(first_half)
                    second_positive = (second_half['sentiment'] == 'Positive').sum() / len(second_half)
                    
                    if second_positive > first_positive + 0.1:
                        insights['recommendations'].append('📈 Sentiment is improving over time')
                    elif second_positive < first_positive - 0.1:
                        insights['recommendations'].append('📉 Sentiment is declining - requires attention')
        except:
            pass
    
    return insights

def get_trending_topics(df, top_n=10):
    """
    Extracts trending topics and keywords from the data.
    
    Returns:
        dict: Trending topics with sentiment breakdown
    """
    text_col = next((col for col in df.columns if col.lower() in 
                    ['feedback', 'review', 'comment', 'content', 'text']), None)
    
    if not text_col:
        return {}
    
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    import nltk
    import os
    
    # Add local nltk_data directory to path
    nltk_data_dir = os.path.join(os.getcwd(), 'nltk_data')
    if os.path.exists(nltk_data_dir):
        nltk.data.path.append(nltk_data_dir)
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', download_dir=nltk_data_dir)
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', download_dir=nltk_data_dir)
    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        nltk.download('punkt_tab', download_dir=nltk_data_dir)
    
    stop_words = set(stopwords.words('english'))
    
    # Extract keywords with sentiment
    trending_topics = {}
    
    for idx, row in df.iterrows():
        val = row[text_col]
        if pd.isna(val) or val is pd.NaT:
            continue
            
        text = str(val).lower()
        sentiment = row.get('sentiment', 'Neutral')
        
        # Tokenize and clean
        try:
            tokens = word_tokenize(text)
            keywords = [
                word for word in tokens 
                if re.match(r'^[a-z]+$', word) and len(word) > 3 and word not in stop_words
            ]
            
            for keyword in keywords:
                if keyword not in trending_topics:
                    trending_topics[keyword] = {
                        'count': 0,
                        'positive': 0,
                        'negative': 0,
                        'neutral': 0
                    }
                
                trending_topics[keyword]['count'] += 1
                trending_topics[keyword][sentiment.lower()] += 1
        except:
            continue
    
    # Sort by count and get top N
    sorted_topics = sorted(trending_topics.items(), key=lambda x: x[1]['count'], reverse=True)[:top_n]
    
    # Calculate sentiment ratios
    result = {}
    for topic, data in sorted_topics:
        total = data['count']
        if total == 0: continue
        
        result[topic] = {
            'mentions': total,
            'positive_ratio': round((data['positive'] / total) * 100, 1),
            'negative_ratio': round((data['negative'] / total) * 100, 1),
            'neutral_ratio': round((data['neutral'] / total) * 100, 1),
            'dominant_sentiment': max(
                [('Positive', data['positive']), 
                 ('Negative', data['negative']), 
                 ('Neutral', data['neutral'])],
                key=lambda x: x[1]
            )[0]
        }
    
    return result

def detect_emerging_issues(df):
    """
    Detects emerging issues or concerns from negative sentiment.
    
    Returns:
        list: List of potential issues with severity scores
    """
    if 'sentiment' not in df.columns:
        return []
    
    text_col = next((col for col in df.columns if col.lower() in 
                    ['feedback', 'review', 'comment', 'content', 'text']), None)
    
    if not text_col:
        return []
    
    # Filter negative comments
    negative_df = df[df['sentiment'] == 'Negative']
    
    if len(negative_df) == 0:
        return []
    
    # Common issue keywords
    issue_patterns = {
        'quality': ['quality', 'broken', 'defect', 'faulty', 'poor'],
        'service': ['service', 'support', 'customer service', 'help', 'response'],
        'price': ['price', 'expensive', 'cost', 'overpriced', 'refund'],
        'delivery': ['delivery', 'shipping', 'late', 'delayed', 'never arrived'],
        'performance': ['slow', 'lag', 'crash', 'bug', 'error', 'not working']
    }
    
    issues = []
    
    for issue_type, keywords in issue_patterns.items():
        count = 0
        for idx, row in negative_df.iterrows():
            val = row[text_col]
            if pd.isna(val) or val is pd.NaT:
                continue
                
            text = str(val).lower()
            if any(keyword in text for keyword in keywords):
                count += 1
        
        if count > 0:
            severity = 'High' if count > len(negative_df) * 0.3 else 'Medium' if count > len(negative_df) * 0.1 else 'Low'
            issues.append({
                'issue': issue_type.title(),
                'mentions': count,
                'severity': severity,
                'percentage': round((count / len(negative_df)) * 100, 1)
            })
    
    # Sort by mentions
    issues.sort(key=lambda x: x['mentions'], reverse=True)
    
    return issues[:5]  # Return top 5 issues