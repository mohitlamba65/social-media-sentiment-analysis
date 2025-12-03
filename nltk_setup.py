import nltk
import os

print("Downloading NLTK data...")
try:
    nltk.download('stopwords')
    nltk.download('punkt')
    nltk.download('punkt_tab')
    print("NLTK data downloaded successfully.")
except Exception as e:
    print(f"Error downloading NLTK data: {e}")
