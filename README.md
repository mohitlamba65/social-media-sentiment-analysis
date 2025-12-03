# Social Media Sentiment Analysis Dashboard

A comprehensive data analytics dashboard designed to analyze customer feedback, social media comments, and market data using AI.

## Features

*   **Data Ingestion**: Upload CSV/Excel/JSON files or scrape YouTube comments.
*   **Sentiment Analysis**: Automatic classification of text (Positive, Negative, Neutral) using VADER.
*   **Market Insights**: Identify trending topics, engagement patterns, and emerging issues.
*   **AI Chatbot**: Chat with your data using Groq's Llama 3 model (RAG implementation).
*   **Interactive Dashboard**: Dynamic visualizations using Plotly.

## Tech Stack

*   **Backend**: Python (Flask), Pandas, NLTK
*   **AI/LLM**: LangChain, Groq API
*   **Frontend**: HTML, CSS, Plotly.js
*   **Scraping**: Selenium

## Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/mohitlamba65/social-media-sentiment-analysis.git
    cd social-media-sentiment-analysis
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Mac/Linux
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Environment Variables:**
    Create a `.env` file in the root directory and add your Groq API key:
    ```
    GROQ_API_KEY=your_groq_api_key_here
    ```

5.  **Run the application:**
    ```bash
    # Windows
    run_app.bat
    # Or manually:
    python app.py
    ```

## Deployment

This application is ready to be deployed on services like Render or Railway.
Ensure you set the `GROQ_API_KEY` in your deployment environment variables.

**Build Command:** `pip install -r requirements.txt`
**Start Command:** `gunicorn app:app`
