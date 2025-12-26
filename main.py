import os
import requests
import random
import pickle
import sys
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# --- SETTINGS ---
# In pages se video lega
TARGET_SUBS = ["FunnyAnimals", "AnimalsBeingDerps", "animalsdoingstuff", "AnimalsBeingFunny"]
HISTORY_FILE = "posted_history.txt"

# --- 1. HISTORY SYSTEM (Taaki video repeat na ho) ---
def get_posted_ids():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE, "r") as f: return f.read().splitlines()

def save_id(post_id):
    with open(HISTORY_FILE, "a") as f: f.write(post_id + "\n")

# --- 2. REDDIT DOWNLOADER (Bina API Key ke) ---
def get_video():
    print("🕵️ Reddit Scan kar raha hu...")
    random.shuffle(TARGET_SUBS)
    posted_ids = get_posted_ids()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for sub in TARGET_SUBS:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=15"
            data = requests.get(url, headers=headers).json()
            posts = data['data']['children']
            
            for post in posts:
                p_data = post['data']
                pid = p_data['id']
                title = p_data['title']
                p_url = f"https://www.reddit.com{p_data['permalink']}"
                
                # Check agar Video hai aur Pehle Upload nahi hui
                is_video = p_data.get('is_video', False) or 'v.redd.it' in p_data.get('url', '')
                
                if is_video and pid not in posted_ids:
                    print(f"🎯 Video Mili: {title}")
                    
                    # Download High Quality
                    os.system(f'yt-dlp "{p_url}" -o "video.mp4" --merge-output-format mp4')
                    
                    if os.path.exists("video.mp4"):
                        return "video.mp4", title, pid, sub
        except: continue
    return None, None, None, None

# --- 3. YOUTUBE UPLOAD (Permanent Token se) ---
def upload_youtube(video, title, sub):
    print("▶️ YouTube par upload kar raha hu...")
    
    if not os.path.exists('token.pickle'):
        print("❌ Error: token.pickle nahi mili!")
        return False
        
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    
    # Refresh logic (Published App ke liye zaroori)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    youtube = build('youtube', 'v3', credentials=creds)
    
    body = {
        "snippet": {
            "title": f"{title[:90]} #shorts", 
            "description": f"Funny video from r/{sub}\n#funny #shorts #animals #cute",
            "tags": ["funny", "animals", "shorts", "cute"],
            "categoryId": "15" # Pets & Animals
        },
        "status": {
            "privacyStatus": "public", # Direct Public
            "selfDeclaredMadeForKids": False
        }
    }
    
    media = MediaFileUpload(video, chunksize=-1, resumable=True)
    youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    print("✅ SUCCESS! Video Upload Ho Gayi.")
    return True

# --- MAIN RUNNER ---
if __name__ == "__main__":
    vid, title, pid, source = get_video()
    
    if vid:
        success = upload_youtube(vid, title, source)
        if success:
            save_id(pid) # History update
            if os.path.exists(vid): os.remove(vid) # Cleanup
        else:
            sys.exit("Upload Failed")
    else:
        print("😴 Koi nayi video nahi mili.")
