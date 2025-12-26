import os
import random
import sys
import feedparser
import requests
import pickle
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- CONFIG ---
TARGET_SUBS = ["FunnyAnimals", "AnimalsBeingDerps", "animalsdoingstuff", "AnimalsBeingFunny", "aww", "MadeMeSmile", "BeAmazed"]
HISTORY_FILE = "posted_history.txt"

# --- NEW: Working Cobalt Servers List (Backup ke saath) ---
COBALT_INSTANCES = [
    "https://co.wuk.sh/api/json",          # Sabse reliable
    "https://cobalt.kwiatekmiki.pl/api/json",
    "https://cobalt.kanzen.moe/api/json",
    "https://api.cobalt.tools/api/json"    # Official (kabhi kabhi chalta hai)
]

# --- 1. HISTORY CHECK ---
def get_posted_ids():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE, "r") as f: return f.read().splitlines()

def save_id(post_id):
    with open(HISTORY_FILE, "a") as f: f.write(post_id + "\n")

# --- 2. DOWNLOADER (MULTI-SERVER COBALT) ---
def download_via_cobalt(url):
    print(f"   🚀 Trying to download: {url}")
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ViralBot/2.0"
    }
    
    body = {
        "url": url,
        "vCodec": "h264",
        "videoQuality": "720"
    }

    # Har server try karega
    for instance in COBALT_INSTANCES:
        try:
            print(f"      Trying Server: {instance} ...")
            response = requests.post(instance, headers=headers, json=body, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Link dhundna
                video_link = None
                if "url" in data:
                    video_link = data["url"]
                elif "picker" in data: # Kabhi kabhi picker format aata hai
                    for item in data["picker"]:
                        if item["type"] == "video":
                            video_link = item["url"]
                            break
                
                if video_link:
                    print("      ✅ Link mil gaya! Downloading video...")
                    video_content = requests.get(video_link).content
                    with open("video.mp4", "wb") as f:
                        f.write(video_content)
                    return True
                else:
                    print(f"      ⚠️ Server replied but no URL: {data}")
            else:
                print(f"      ⚠️ Server Error: {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ Connection Error with {instance}")
            continue # Agla server try karo
            
    print("   ❌ All Cobalt servers failed.")
    return False

def get_video():
    print("🕵️ Scanning Reddit via RSS...")
    random.shuffle(TARGET_SUBS)
    posted_ids = get_posted_ids()
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    
    for sub in TARGET_SUBS:
        print(f"   Checking r/{sub}...")
        try:
            rss_url = f"https://www.reddit.com/r/{sub}/hot.rss?limit=25"
            feed = feedparser.parse(rss_url, agent=USER_AGENT)
            
            if not feed.entries: continue
            
            for entry in feed.entries:
                try:
                    pid = entry.link.split('/comments/')[1].split('/')[0]
                except: continue
                
                title = entry.title
                p_url = entry.link
                
                # Check agar video hai
                is_video_candidate = 'v.redd.it' in p_url or 'v.redd.it' in str(entry)
                
                if is_video_candidate and pid not in posted_ids:
                    print(f"   🎯 Target Found: {title}")
                    
                    # Download Step
                    success = download_via_cobalt(p_url)
                    
                    if success and os.path.exists("video.mp4"):
                        # Size Check
                        if os.path.getsize("video.mp4") > 50000:
                            return "video.mp4", title, pid, sub
                        else:
                            print("   ❌ File too small...")
                            os.remove("video.mp4")
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
                "description": f"Funny video from r/{sub}\n#funny #shorts #animals #cute",
                "tags": ["funny", "animals", "shorts", "cute"],
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
