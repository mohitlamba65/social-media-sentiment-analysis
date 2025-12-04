import nltk
import os

# Download to a local directory within the project
nltk_data_dir = os.path.join(os.getcwd(), 'nltk_data')
if not os.path.exists(nltk_data_dir):
    os.makedirs(nltk_data_dir)

print(f"Downloading NLTK data to {nltk_data_dir}...")

nltk.data.path.append(nltk_data_dir)

try:
    nltk.download('stopwords', download_dir=nltk_data_dir)
    nltk.download('punkt', download_dir=nltk_data_dir)
    nltk.download('punkt_tab', download_dir=nltk_data_dir)
    print("NLTK data downloaded successfully.")
except Exception as e:
    print(f"Error downloading NLTK data: {e}")
