import os
import requests
import random
import pickle
import sys
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- CONFIGURATION ---
# Zyada pages add kiye hain taaki video milne ke chances 100% ho
TARGET_SUBS = ["FunnyAnimals", "AnimalsBeingDerps", "animalsdoingstuff", "AnimalsBeingFunny", "aww", "MadeMeSmile", "BeAmazed"]
HISTORY_FILE = "posted_history.txt"

# --- 1. HISTORY CHECK ---
def get_posted_ids():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE, "r") as f: return f.read().splitlines()

def save_id(post_id):
    with open(HISTORY_FILE, "a") as f: f.write(post_id + "\n")

# --- 2. DOWNLOADER (Updated Limit) ---
def get_video():
    print("🕵️ Scanning Reddit (Deep Search)...")
    random.shuffle(TARGET_SUBS)
    posted_ids = get_posted_ids()
    
    # Fake Browser Header (Zaroori hai)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0'}
    
    for sub in TARGET_SUBS:
        print(f"   Checking r/{sub}...")
        try:
            # CHANGE: Limit 50 kar di hai (Pehle 15 thi)
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=50"
            resp = requests.get(url, headers=headers)
            
            if resp.status_code != 200:
                print(f"   ⚠️ Skip r/{sub} (Status: {resp.status_code})")
                continue
            
            data = resp.json()
            posts = data['data']['children']
            
            for post in posts:
                p_data = post['data']
                pid = p_data['id']
                title = p_data['title']
                p_url = f"https://www.reddit.com{p_data['permalink']}"
                
                # Filter: Sirf Video + Not Posted + Not NSFW
                is_video = p_data.get('is_video', False) or 'v.redd.it' in p_data.get('url', '')
                is_nsfw = p_data.get('over_18', False)
                
                if is_video and not is_nsfw and pid not in posted_ids:
                    print(f"   🎯 Video Found: {title}")
                    
                    # Download Command
                    # yt-dlp best quality download karega
                    cmd = f'yt-dlp "{p_url}" -o "video.mp4" --merge-output-format mp4'
                    exit_code = os.system(cmd)
                    
                    if exit_code == 0 and os.path.exists("video.mp4"):
                        # File size check (Too small = glitch)
                        if os.path.getsize("video.mp4") > 50000: 
                            return "video.mp4", title, pid, sub
                        else:
                            print("   ❌ File too small (Glitch), skipping...")
                    else:
                        print("   ❌ Download fail, Next try...")
                        
        except Exception as e:
            print(f"   ⚠️ Error scanning {sub}: {e}")
            continue
    
    return None, None, None, None

# --- 3. YOUTUBE UPLOAD ---
def upload_youtube(video, title, sub):
    print("▶️ Uploading to YouTube...")
    
    if not os.path.exists('token.pickle'):
        print("❌ CRITICAL: 'token.pickle' file missing in Repository!")
        return False
        
    try:
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        
        # Token Refresh Logic
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        youtube = build('youtube', 'v3', credentials=creds)
        
        # Metadata
        body = {
            "snippet": {
                "title": f"{title[:90]} #shorts", 
                "description": f"Funny moment from r/{sub}\n#funny #shorts #animals #cute #viral",
                "tags": ["funny", "animals", "shorts", "cute", "viral"],
                "categoryId": "15" # Pets & Animals
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }
        
        media = MediaFileUpload(video, chunksize=-1, resumable=True)
        youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        print("✅ SUCCESS: Video Uploaded Successfully!")
        return True
        
    except Exception as e:
        print(f"❌ UPLOAD ERROR: {e}")
        return False

# --- MAIN ---
if __name__ == "__main__":
    vid, title, pid, source = get_video()
    
    if vid:
        success = upload_youtube(vid, title, source)
        if success:
            save_id(pid)
            if os.path.exists(vid): os.remove(vid) # Cleanup
        else:
            sys.exit(1) # Fail Workflow
    else:
        print("🔴 All Pages Checked. No NEW video found.")
        sys.exit(1) # Fail Workflow so you know
