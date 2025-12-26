import os
import random
import sys
import feedparser # RSS Reader
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

# --- 2. REDDIT DOWNLOADER (VIA RSS FEED - NO KEYS) ---
def get_video():
    print("🕵️ Scanning Reddit via RSS Feeds (Smart Mode)...")
    
    random.shuffle(TARGET_SUBS)
    posted_ids = get_posted_ids()
    
    # User-Agent lagana zaroori hai taaki Reddit ko lage Browser hai
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    
    for sub in TARGET_SUBS:
        print(f"   Checking r/{sub}...")
        try:
            # RSS URL (No API needed)
            rss_url = f"https://www.reddit.com/r/{sub}/hot.rss?limit=25"
            
            # Feed Fetch karna
            feed = feedparser.parse(rss_url, agent=USER_AGENT)
            
            if not feed.entries:
                print(f"   ⚠️ Blocked/Empty r/{sub}")
                continue
            
            for entry in feed.entries:
                # RSS mein ID link se nikalni padti hai
                # Link format: https://www.reddit.com/r/sub/comments/ID/title/
                try:
                    pid = entry.link.split('/comments/')[1].split('/')[0]
                except:
                    pid = entry.id
                
                title = entry.title
                p_url = entry.link
                
                # Filter: Check karo content mein video tag hai ya link
                # RSS mein exact "is_video" nahi hota, to hum content guess karte hain
                content_str = str(entry.content[0].value) if 'content' in entry else ""
                
                # Smart Check: Agar link "v.redd.it" hai ya content mein video player hai
                is_video_candidate = 'v.redd.it' in content_str or 'video' in content_str or 'v.redd.it' in p_url
                
                if is_video_candidate and pid not in posted_ids:
                    print(f"   🎯 Potential Video Found: {title}")
                    
                    # yt-dlp ko bolenge check kare aur download kare
                    cmd = f'yt-dlp "{p_url}" -o "video.mp4" --merge-output-format mp4'
                    exit_code = os.system(cmd)
                    
                    if exit_code == 0 and os.path.exists("video.mp4"):
                        # Size Check (Choti files glitch ho sakti hain)
                        if os.path.getsize("video.mp4") > 50000:
                            print("   ✅ Video Validated!")
                            return "video.mp4", title, pid, sub
                        else:
                            print("   ❌ File too small/Image found, skipping...")
                            if os.path.exists("video.mp4"): os.remove("video.mp4")
                    else:
                        print("   ❌ Not a video or Download fail...")
                        
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
        print("🔴 All RSS Feeds checked. No NEW video found.")
        sys.exit(1)
