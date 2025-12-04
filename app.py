import os
import sys
import pandas as pd
import json
import plotly
import plotly.express as px
import plotly.graph_objects as go
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
import subprocess
import time
import io
import threading

# Local Modules
from analyzers.sentiment_model import analyze_sentiment, get_sentiment_trends
from analyzers.keyword_model import extract_keywords_analysis
from analyzers.market_analyzer import analyze_market_sentiment, get_trending_topics
from chat.retriever import get_summary
from chat.chatbot import get_ollama_response, get_ai_insights

# --- Configuration ---
UPLOAD_FOLDER = 'data'
PROCESSED_FOLDER = os.path.join(UPLOAD_FOLDER, 'processed')
ALLOWED_EXTENSIONS = {'csv', 'json', 'xls', 'xlsx'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.secret_key = 'your-secret-key-replace-in-production'

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# --- Global Scraper State ---
scraper_process = None
scraper_log = []
scraper_thread = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_and_normalize_data(df):
    """Auto-clean data logic."""
    df.dropna(how='all', axis=0, inplace=True)
    df.dropna(how='all', axis=1, inplace=True)
    df.columns = [str(col).strip().lower() for col in df.columns]
    for col in df.columns:
        if any(x in col for x in ['date', 'time', 'created', 'timestamp']):
            try: df[col] = pd.to_datetime(df[col], errors='coerce')
            except: pass
    return df

def load_dataframe(filepath):
    """Loads dataframe with robust encoding handling."""
    try:
        if filepath.endswith('.csv'):
            try: df = pd.read_csv(filepath, encoding='utf-8')
            except UnicodeDecodeError: df = pd.read_csv(filepath, encoding='latin1')
        elif filepath.endswith('.json'): df = pd.read_json(filepath)
        elif filepath.endswith(('.xls', '.xlsx')): df = pd.read_excel(filepath)
        else: return None
        return clean_and_normalize_data(df) if df is not None else None
    except Exception as e:
        print(f"Error loading file: {e}")
        return None

def generate_advanced_charts(df):
    charts = {}
    if 'sentiment' in df.columns:
        counts = df['sentiment'].value_counts()
        colors = {'Positive': '#10b981', 'Neutral': '#6b7280', 'Negative': '#ef4444'}
        fig = go.Figure(data=[go.Pie(labels=counts.index, values=counts.values, marker=dict(colors=[colors.get(s, '#888') for s in counts.index]), hole=0.4)])
        fig.update_layout(title="Sentiment Distribution", template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)')
        charts['sentiment_pie'] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    trend_data = get_sentiment_trends(df)
    if trend_data:
        try:
            trend_df = pd.DataFrame(trend_data)
            fig = px.line(trend_df, x='date_str', y=list(set(trend_df.columns) - {'date_str'}),
                          title="Sentiment Trends Over Time",
                          color_discrete_map={'Positive': '#10b981', 'Neutral': '#6b7280', 'Negative': '#ef4444'})
            fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)')
            charts['sentiment_trend'] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        except: pass

    # Sentiment Histogram
    if 'sentiment_score' in df.columns:
        fig = px.histogram(df, x='sentiment_score', nbins=20, title="Sentiment Score Distribution",
                           color_discrete_sequence=['#6366f1'])
        fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
                          xaxis_title="Sentiment Score (-1 to 1)", yaxis_title="Count")
        charts['sentiment_histogram'] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    # Keywords Bar Chart
    trending_topics = get_trending_topics(df, top_n=10)
    if trending_topics:
        keywords = list(trending_topics.keys())
        counts = [data['mentions'] for data in trending_topics.values()]
        
        fig = px.bar(x=keywords, y=counts, title="Top Trending Keywords",
                     color_discrete_sequence=['#10b981'])
        fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
                          xaxis_title="Keyword", yaxis_title="Mentions")
        charts['keywords'] = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return charts

# --- Background Log Reader ---
def monitor_scraper(process):
    global scraper_log
    for line in iter(process.stdout.readline, ''):
        scraper_log.append(line)
    process.stdout.close()

# --- Helper Functions ---
def save_processed_df(df, filename):
    """Saves the processed dataframe to the processed folder."""
    filepath = os.path.join(app.config['PROCESSED_FOLDER'], f"{filename}.json")
    df.to_json(filepath, orient='split', date_format='iso')

def get_current_df():
    """Retrieves the current dataframe based on session filename."""
    if 'current_filename' not in session:
        return None
    
    filename = session['current_filename']
    filepath = os.path.join(app.config['PROCESSED_FOLDER'], f"{filename}.json")
    
    if not os.path.exists(filepath):
        return None
        
    try:
        return pd.read_json(filepath, orient='split')
    except Exception as e:
        print(f"Error loading processed DF: {e}")
        return None

# --- Routes ---

@app.route('/')
def index():
    if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
    files = [f for f in os.listdir(UPLOAD_FOLDER) if allowed_file(f)]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(UPLOAD_FOLDER, x)), reverse=True)
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '': return redirect(url_for('index'))
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    df = load_dataframe(filepath)
    if df is None or df.empty:
        flash('Error reading file.', 'error')
        return redirect(url_for('index'))

    df = analyze_sentiment(df)
    
    # Save processed DF to disk instead of session
    save_processed_df(df, filename)
    session['current_filename'] = filename
    
    return redirect(url_for('dashboard'))

@app.route('/load/<filename>')
def load_existing_file(filename):
    # FIX: Use os.path.basename instead of secure_filename to allow spaces
    safe_filename = os.path.basename(filename) 
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
    
    if not os.path.exists(filepath):
        flash(f'File not found: {safe_filename}', 'error')
        return redirect(url_for('index'))

    df = load_dataframe(filepath)
    if df is None:
        flash('File corrupted or unreadable.', 'error')
        return redirect(url_for('index'))
        
    df = analyze_sentiment(df)
    
    # Save processed DF to disk instead of session
    save_processed_df(df, safe_filename)
    session['current_filename'] = safe_filename
    
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    df = get_current_df()
    if df is None:
        return redirect(url_for('index'))
        
    try:
        filename = session.get('current_filename', 'Data')
        return render_template('dashboard.html', 
                             summary=get_summary(df, filename), 
                             charts=generate_advanced_charts(df), 
                             market_insights=analyze_market_sentiment(df), 
                             trending=get_trending_topics(df))
    except Exception as e:
        print(f"Dashboard error: {e}")
        return redirect(url_for('index'))

@app.route('/reset')
def reset_app():
    session.clear()
    return redirect(url_for('index'))

# --- Scraper API ---
@app.route('/scrape')
def scrape_page(): return render_template('scrape.html')

@app.route('/api/run-scrape', methods=['POST'])
def run_scrape():
    global scraper_process, scraper_log, scraper_thread
    if scraper_process and scraper_process.poll() is None:
        return jsonify({'status': 'error', 'message': 'Scraper is already running.'}), 400

    data = request.json
    cmd = [sys.executable, 'scraper.py', data['url'], 
           '--filter_keywords', data.get('filter_keywords',''), 
           '--min_length', str(data.get('min_length',10))]

    try:
        scraper_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', bufsize=1)
        scraper_log = ["--- Starting Scraper... ---\n"]
        scraper_thread = threading.Thread(target=monitor_scraper, args=(scraper_process,))
        scraper_thread.daemon = True
        scraper_thread.start()
        return jsonify({'status': 'success', 'message': 'Scraper started.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/scrape-status')
def scrape_status():
    global scraper_process, scraper_log
    status = 'idle'
    if scraper_process:
        if scraper_process.poll() is None: status = 'running'
        else: status = 'finished'; scraper_process = None
    return jsonify({'status': status, 'log': "".join(scraper_log)})

@app.route('/api/stop-scrape', methods=['POST'])
def stop_scrape():
    global scraper_process
    if scraper_process: scraper_process.kill(); scraper_process = None
    return jsonify({'status': 'success', 'message': 'Stopped'})

@app.route('/api/chat', methods=['POST'])
def chat_api():
    df = get_current_df()
    if df is None:
        return jsonify({'error': 'No data'}), 400
        
    summary = get_summary(df, session['current_filename'], for_llm=True)
    return jsonify({'response': get_ollama_response(request.json['message'], summary)})

@app.route('/api/get-insights', methods=['POST'])
def get_insights_api():
    df = get_current_df()
    if df is None:
        return jsonify({'error': 'No data'}), 400
        
    return jsonify({'insights': get_ai_insights(df, session['current_filename'])})

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)