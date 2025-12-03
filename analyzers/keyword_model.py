import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import Counter
import re

# Download NLTK data if not present
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

def extract_keywords_analysis(df):
    """
    Finds the most common keywords in a text column.
    
    Accepts:
        df (pd.DataFrame): The input DataFrame.
    Returns:
        dict: A dictionary of keywords and their counts, or empty dict.
    """
    
    # Try to find a text column
    text_col = next((col for col in df.columns if col.lower() in ['feedback', 'review', 'comment', 'content', 'text']), None)
    
    if not text_col:
        return {}

    print(f"--- Running keyword extraction on column: {text_col} ---")
    
    # Combine all text into one giant string
    all_text = " ".join(df[text_col].dropna().astype(str))
    
    # Tokenize and clean
    tokens = word_tokenize(all_text.lower())
    stop_words = set(stopwords.words('english'))
    
    # Basic cleaning: remove punctuation, short words, and stopwords
    keywords = [
        word for word in tokens 
        if re.match(r'^[a-z]+$', word) and len(word) > 2 and word not in stop_words
    ]
    
    # Get top 20 most common keywords
    keyword_counts = Counter(keywords).most_common(20)
    
    return dict(keyword_counts)