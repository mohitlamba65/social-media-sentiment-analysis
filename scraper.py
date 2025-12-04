import sys
import time
import os
import argparse
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options

def get_driver(headless=True):
    """
    Initializes Chrome driver using Selenium's built-in manager (Selenium 4.10+).
    This avoids external dependency issues like WinError 193.
    """
    print("--- Initializing Chrome Driver (Selenium Manager) ---", flush=True)
    
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    
    # Essential options for Render/Linux environments
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    try:
        # Selenium 4.6+ handles driver management automatically!
        # We do NOT need webdriver_manager anymore.
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"!!! Error initializing driver: {e}", flush=True)
        raise e

def parse_number(text):
    if not text: return 0
    text = text.upper().replace('LIKES', '').replace('VIEWS', '').strip()
    try:
        if 'K' in text: return int(float(text.replace('K', '')) * 1000)
        elif 'M' in text: return int(float(text.replace('M', '')) * 1000000)
        elif text.isdigit(): return int(text)
    except: pass
    return 0

def run_scraper(video_url, filter_keywords, min_length):
    print(f"--- Initializing WebDriver ---", flush=True)
    try:
        driver = get_driver(headless=True)
    except Exception as e:
        print(f"!!! Driver Setup Failed: {e}", flush=True)
        return

    print(f"--- Opening URL: {video_url} ---", flush=True)
    
    try:
        driver.get(video_url)
        time.sleep(2)

        # --- PART 1: Robust Metadata (Short-timeout) ---
        # We use a short wait (5s). If it fails, we MOVE ON to comments.
        print("--- Checking Metadata (Title/Likes)... ---", flush=True)
        video_title = "Unknown Video"
        video_likes = 0
        
        try:
            # Try standard video title
            title_elem = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.ytd-watch-metadata, h1.ytd-video-primary-info-renderer"))
            )
            video_title = title_elem.text.replace('\n', ' ').strip()
            print(f"--- Title Found: {video_title[:30]}... ---", flush=True)
        except:
            print("--- Could not find Title (skipping) ---", flush=True)

        # --- PART 2: Scroll Logic (The "Hang" often happens here) ---
        print("--- Locating Comments... ---", flush=True)
        try:
            # Send PAGE_DOWN to trigger loading
            body = driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(1)
            body.send_keys(Keys.PAGE_DOWN)
            
            # Wait for comment container
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#comments, ytd-comments"))
            )
            print("--- Comments section found. Scrolling... ---", flush=True)
        except:
            print("!!! Warning: Comments section not immediately found. Attempting force scroll... !!!", flush=True)

        # Force Scroll Loop
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        for i in range(30): # Max 30 scrolls
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(1.5) 
            new_height = driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                # Verify if we actually have comments loaded
                count = len(driver.find_elements(By.CSS_SELECTOR, "#content-text"))
                if count > 5:
                    break # We have data, stop scrolling
            last_height = new_height
            if i % 5 == 0: print(f"--- Scroll {i}/30... ---", flush=True)

        # --- PART 3: Extraction ---
        comments_data = []
        try:
            # Generic selectors to catch multiple YouTube layouts
            comment_elems = driver.find_elements(By.CSS_SELECTOR, "#content-text")
            author_elems = driver.find_elements(By.CSS_SELECTOR, "#author-text")
            
            # Safety check
            num = min(len(comment_elems), len(author_elems))
            print(f"--- Found {num} raw comments. Processing... ---", flush=True)

            if num == 0:
                print("!!! No comments found by selectors. YouTube layout might have changed. !!!", flush=True)
                # Fallback debug
                print(f"Debug: Page Source Length: {len(driver.page_source)}", flush=True)
            
            for i in range(num):
                try:
                    txt = comment_elems[i].text
                    auth = author_elems[i].text
                    if txt:
                        comments_data.append({
                            "video_title": video_title,
                            "author": auth,
                            "comment": txt,
                            "video_likes": video_likes
                        })
                except: continue
        except Exception as e:
            print(f"!!! Extraction Error: {e}", flush=True)

    finally:
        driver.quit()

    if not comments_data:
        print("!!! No data collected. Exiting. ---", flush=True)
        return

    # --- PART 4: Save ---
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
        safe_title = "".join([c for c in video_title if c.isalnum() or c in (' ','-')])[:20]
        vid_id = video_url.split('v=')[-1].split('&')[0]
        filename = f"data/YT_{safe_title}_{vid_id}.csv"
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"--- Saved to: {filename} ---", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str)
    parser.add_argument("--filter_keywords", type=str, default="")
    parser.add_argument("--min_length", type=int, default=10)
    args = parser.parse_args()
    run_scraper(args.url, args.filter_keywords, args.min_length)