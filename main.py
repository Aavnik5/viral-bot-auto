import os
import random
import sys
import cloudscraper # Ye hai wo Jadui Tool
import pickle
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

# --- 2. REDDIT DOWNLOADER (CLOUDSCRAPER - NO KEYS NEEDED) ---
def get_video():
    print("🕵️ Scanning Reddit (Bypassing Security)...")
    
    # Cloudscraper create kar rahe hain (Fake Browser)
    scraper = cloudscraper.create_scraper()
    
    random.shuffle(TARGET_SUBS)
    posted_ids = get_posted_ids()
    
    for sub in TARGET_SUBS:
        print(f"   Checking r/{sub}...")
        try:
            # Seedha JSON URL hit karenge
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=30"
            resp = scraper.get(url) # Requests ki jagah Scraper use kiya
            
            if resp.status_code != 200:
                print(f"   ⚠️ Blocked/Skip r/{sub} (Status: {resp.status_code})")
                continue
            
            data = resp.json()
            posts = data['data']['children']
            
            for post in posts:
                p_data = post['data']
                pid = p_data['id']
                title = p_data['title']
                p_url = f"https://www.reddit.com{p_data['permalink']}"
                
                # Filter: Video + Not NSFW + Not Posted
                is_video = p_data.get('is_video', False) or 'v.redd.it' in p_data.get('url', '')
                is_nsfw = p_data.get('over_18', False)
                
                if is_video and not is_nsfw and pid not in posted_ids:
                    print(f"   🎯 Video Found: {title}")
                    
                    # Download Command
                    cmd = f'yt-dlp "{p_url}" -o "video.mp4" --merge-output-format mp4'
                    exit_code = os.system(cmd)
                    
                    if exit_code == 0 and os.path.exists("video.mp4"):
                        if os.path.getsize("video.mp4") > 50000:
                            return "video.mp4", title, pid, sub
                        else:
                            print("   ❌ File too small, skipping...")
                    else:
                        print("   ❌ Download fail...")
                        
        except Exception as e:
            print(f"   ⚠️ Error in r/{sub}: {e}")
            continue
            
    return None, None, None, None

# --- 3. YOUTUBE UPLOAD ---
def upload_youtube(video, title, sub):
    print("▶️ Uploading to YouTube...")
    
    if not os.path.exists('token.pickle'):
        print("❌ Error: 'token.pickle' missing! Upload it again.")
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
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }
        
        media = MediaFileUpload(video, chunksize=-1, resumable=True)
        youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        print("✅ SUCCESS! Video Uploaded.")
        return True
        
    except Exception as e:
        print(f"❌ YouTube Upload Error: {e}")
        return False

# --- MAIN ---
if __name__ == "__main__":
    vid, title, pid, source = get_video()
    
    if vid:
        success = upload_youtube(vid, title, source)
        if success:
            save_id(pid)
            if os.path.exists(vid): os.remove(vid)
        else:
            sys.exit(1)
    else:
        print("🔴 All checked. No NEW video found.")
        sys.exit(1)
