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

# Import Services and Options
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions

# --- CONFIGURATION ---
MANUAL_EDGE_PATH = os.path.join("drivers", "msedgedriver.exe")
MANUAL_CHROME_PATH = os.path.join("drivers", "chromedriver.exe")

def get_driver(headless=True):
    """
    Initializes driver. Tries Manual Edge -> Manual Chrome -> Auto Edge.
    """
    # 1. Try Manual Edge
    if os.path.exists(MANUAL_EDGE_PATH):
        try:
            print(f"--- Found local Edge driver... ---", flush=True)
            opts = EdgeOptions()
            if headless: opts.add_argument("--headless=new")
            opts.add_argument("--log-level=3")
            service = EdgeService(executable_path=MANUAL_EDGE_PATH)
            return webdriver.Edge(service=service, options=opts)
        except: pass

    # 2. Try Manual Chrome/Brave
    if os.path.exists(MANUAL_CHROME_PATH):
        try:
            print(f"--- Found local Chrome driver... ---", flush=True)
            opts = ChromeOptions()
            # Check for Brave path
            brave_paths = [
                "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe",
                "C:/Program Files (x86)/BraveSoftware/Brave-Browser/Application/brave.exe"
            ]
            for bp in brave_paths:
                if os.path.exists(bp):
                    opts.binary_location = bp
                    break
            
            if headless: opts.add_argument("--headless=new")
            opts.add_argument("--log-level=3")
            service = ChromeService(executable_path=MANUAL_CHROME_PATH)
            return webdriver.Chrome(service=service, options=opts)
        except: pass

    # 3. Auto Fallback
    print("--- Attempting auto-driver (requires internet)... ---", flush=True)
    opts = EdgeOptions()
    if headless: opts.add_argument("--headless=new")
    return webdriver.Edge(options=opts)

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