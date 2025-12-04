import sys
import os
import argparse
import pandas as pd
import yt_dlp
import tempfile
import base64
import os as _os

def parse_number(text):
    if not text: return 0
    # yt-dlp returns numbers directly, but just in case
    if isinstance(text, (int, float)): return int(text)
    text = str(text).upper().replace('LIKES', '').replace('VIEWS', '').strip()
    try:
        if 'K' in text: return int(float(text.replace('K', '')) * 1000)
        elif 'M' in text: return int(float(text.replace('M', '')) * 1000000)
        elif text.isdigit(): return int(text)
    except: pass
    return 0

def run_scraper(video_url, filter_keywords, min_length, cookies_path="", cookies_from_browser=False):
    print(f"--- Initializing yt-dlp Scraper ---", flush=True)
    print(f"--- Target URL: {video_url} ---", flush=True)

    # yt-dlp options to get comments without downloading video
    ydl_opts = {
        'skip_download': True,
        'extract_flat': True, # Don't download video
        'getcomments': True,  # Fetch comments
        'quiet': True,        # Less noise
        'no_warnings': True,
        # 'playlist_items': '1', # Only one video if it's a playlist
    }

    # If a cookies file path is provided, pass it to yt-dlp.
    # Alternatively, the user can request yt-dlp to try using browser cookies.
    if cookies_path:
        ydl_opts['cookiefile'] = cookies_path
    elif cookies_from_browser:
        # Try Chrome browser cookies by default. This requires yt-dlp's
        # browser-cookie support (e.g., the `browser_cookie3` package available
        # in many environments). If unsupported, yt-dlp will raise an error.
        ydl_opts['cookiesfrombrowser'] = 'chrome'

    comments_data = []
    video_title = "Unknown Video"
    video_likes = 0

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("--- Fetching Video Metadata & Comments... (This may take a moment) ---", flush=True)
            info = ydl.extract_info(video_url, download=False)
            
            video_title = info.get('title', 'Unknown Video')
            video_likes = info.get('like_count', 0)
            
            print(f"--- Video Found: {video_title[:50]}... ---", flush=True)
            print(f"--- Likes: {video_likes} ---", flush=True)

            # Extract comments
            raw_comments = info.get('comments', [])
            print(f"--- Found {len(raw_comments)} raw comments. Processing... ---", flush=True)

            if not raw_comments:
                print("!!! No comments found. Comments might be disabled or not loaded. !!!", flush=True)

            for c in raw_comments:
                txt = c.get('text', '')
                auth = c.get('author', 'Anonymous')
                
                if txt:
                    comments_data.append({
                        "video_title": video_title,
                        "author": auth,
                        "comment": txt,
                        "video_likes": video_likes
                    })

    except Exception as e:
        err = str(e)
        print(f"!!! yt-dlp Error: {err}", flush=True)
        # If the error looks like YouTube is asking to sign-in, give user guidance
        if 'Sign in to confirm' in err or 'Sign in to confirm you' in err:
            print("--- Hint: YouTube is blocking access. Provide cookies with `--cookies PATH`", flush=True)
            print("or enable `--cookies_from_browser` and ensure the deployment has access to browser cookie extraction.", flush=True)
            print("See: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp", flush=True)
        return

    if not comments_data:
        print("!!! No data collected. Exiting. ---", flush=True)
        return

    # --- Save Data ---
    df = pd.DataFrame(comments_data)
    
    # Filter
    df = df[df['comment'].str.len() >= min_length]
    if filter_keywords:
        kws = [k.strip().lower() for k in filter_keywords.split(',')]
        mask = df['comment'].str.lower().apply(lambda x: any(k in x for k in kws))
        df = df[~mask]
        
    print(f"--- Captured {len(df)} valid comments. ---", flush=True)

    if len(df) > 0:
        if not os.path.exists('data'): os.makedirs('data')
        # Safe filename
        safe_title = "".join([c for c in video_title if c.isalnum() or c in (' ','-')])[:20]
        # Extract ID safely
        try:
            vid_id = info.get('id', 'video')
        except:
            vid_id = 'video'
            
        filename = f"data/YT_{safe_title}_{vid_id}.csv"
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"--- Saved to: {filename} ---", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str)
    parser.add_argument("--filter_keywords", type=str, default="")
    parser.add_argument("--min_length", type=int, default=10)
    parser.add_argument("--cookies", type=str, default="", help="Path to a cookies.txt file exported from your browser")
    parser.add_argument("--cookies_from_browser", action="store_true", help="Try to extract cookies from the default browser (e.g., Chrome) on the host")
    args = parser.parse_args()
    # Environment-variable support for Render/cloud deployments:
    # - YTDLP_COOKIES_PATH: a path on disk (if you mounted a secret or persistent disk)
    # - YTDLP_COOKIES_B64: base64-encoded contents of a cookies.txt file (safer to store as a secret env var)
    env_cookies_path = _os.environ.get('YTDLP_COOKIES_PATH', '')
    env_cookies_b64 = _os.environ.get('YTDLP_COOKIES_B64', '')

    # If the user provided a base64 cookies blob via env, write it to a temp file
    temp_cookie_path = ''
    if env_cookies_b64 and not args.cookies:
        try:
            decoded = base64.b64decode(env_cookies_b64)
            tf = tempfile.NamedTemporaryFile(delete=False, prefix='yt_cookies_', suffix='.txt')
            tf.write(decoded)
            tf.close()
            temp_cookie_path = tf.name
        except Exception as e:
            print(f"Failed to decode/write YTDLP_COOKIES_B64: {e}")

    # Priority: CLI `--cookies` > env YTDLP_COOKIES_PATH > env YTDLP_COOKIES_B64-written-file
    chosen_cookies_path = args.cookies or env_cookies_path or temp_cookie_path

    try:
        run_scraper(args.url, args.filter_keywords, args.min_length, cookies_path=chosen_cookies_path, cookies_from_browser=args.cookies_from_browser)
    finally:
        # cleanup temporary file if created
        if temp_cookie_path:
            try:
                _os.remove(temp_cookie_path)
            except:
                pass