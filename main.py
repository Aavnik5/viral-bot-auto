import os
import random
import sys
import feedparser # RSS Reader
import requests   # API calling
import pickle
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- CONFIG ---
TARGET_SUBS = ["FunnyAnimals", "AnimalsBeingDerps", "animalsdoingstuff", "AnimalsBeingFunny", "aww", "MadeMeSmile", "BeAmazed"]
HISTORY_FILE = "posted_history.txt"

# --- 1. HISTORY CHECK ---
def get_posted_ids():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE, "r") as f: return f.read().splitlines()

def save_id(post_id):
    with open(HISTORY_FILE, "a") as f: f.write(post_id + "\n")

# --- 2. DOWNLOADER (USING COBALT API - The Middleman) ---
def download_via_cobalt(url):
    print(f"   🚀 Cobalt API ko bhej raha hu: {url}")
    try:
        # Cobalt API Request
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "ViralBot/1.0"
        }
        body = {
            "url": url,
            "vCodec": "h264" # MP4 format ensure karne ke liye
        }
        
        # API Hit
        response = requests.post("https://api.cobalt.tools/api/json", headers=headers, json=body)
        data = response.json()
        
        if "url" in data:
            video_link = data["url"]
            print("   ✅ Cobalt se link mil gaya! Downloading...")
            
            # Final Video Download
            video_content = requests.get(video_link).content
            with open("video.mp4", "wb") as f:
                f.write(video_content)
            return True
        else:
            print(f"   ❌ Cobalt failed: {data}")
            return False
            
    except Exception as e:
        print(f"   ⚠️ Cobalt Error: {e}")
        return False

def get_video():
    print("🕵️ Scanning Reddit via RSS...")
    random.shuffle(TARGET_SUBS)
    posted_ids = get_posted_ids()
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    
    for sub in TARGET_SUBS:
        print(f"   Checking r/{sub}...")
        try:
            rss_url = f"https://www.reddit.com/r/{sub}/hot.rss?limit=20"
            feed = feedparser.parse(rss_url, agent=USER_AGENT)
            
            if not feed.entries: continue
            
            for entry in feed.entries:
                try:
                    pid = entry.link.split('/comments/')[1].split('/')[0]
                except: continue
                
                title = entry.title
                p_url = entry.link
                
                # Filter: Link check + Not posted
                is_video_candidate = 'v.redd.it' in p_url or 'v.redd.it' in str(entry)
                
                if is_video_candidate and pid not in posted_ids:
                    print(f"   🎯 Target Found: {title}")
                    
                    # Yahan hum yt-dlp ki jagah COBALT use karenge
                    success = download_via_cobalt(p_url)
                    
                    if success and os.path.exists("video.mp4"):
                        if os.path.getsize("video.mp4") > 50000:
                            return "video.mp4", title, pid, sub
                        else:
                            print("   ❌ File too small...")
                    else:
                        print("   ❌ Download fail...")
                        
        except Exception as e:
            continue
            
    return None, None, None, None

# --- 3. YOUTUBE UPLOAD ---
def upload_youtube(video, title, sub):
    print("▶️ Uploading to YouTube...")
    if not os.path.exists('token.pickle'):
        print("❌ Error: 'token.pickle' missing!")
        return False
        
    try:
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        youtube = build('youtube', 'v3', credentials=creds)
        body = {
            "snippet": {
                "title": f"{title[:90]} #shorts", 
                "description": f"Funny video from r/{sub}\n#funny #shorts #animals",
                "tags": ["funny", "animals", "shorts"],
                "categoryId": "15"
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
        }
        media = MediaFileUpload(video, chunksize=-1, resumable=True)
        youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        print("✅ SUCCESS! Video Uploaded.")
        return True
    except Exception as e:
        print(f"❌ Upload Error: {e}")
        return False

# --- MAIN ---
if __name__ == "__main__":
    vid, title, pid, source = get_video()
    if vid:
        if upload_youtube(vid, title, source):
            save_id(pid)
            if os.path.exists(vid): os.remove(vid)
        else:
            sys.exit(1)
    else:
        print("🔴 No video found.")
        sys.exit(1)
