import os
import sys
import pickle
import io
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request

# --- CONFIG ---
# Aapka Folder ID (Maine set kar diya hai)
DRIVE_FOLDER_ID = "1YmOj9mjty1dUgbZnlmTRsCGbnUL96Kcd"

# --- AUTHENTICATION ---
def get_creds():
    if not os.path.exists('token.pickle'):
        print("❌ Error: token.pickle missing! Make sure to upload the NEW token.")
        return None
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

# --- 1. DOWNLOAD FROM DRIVE ---
def get_video_from_drive():
    try:
        creds = get_creds()
        if not creds: return None, None, None

        service = build('drive', 'v3', credentials=creds)
        
        print(f"📂 Scanning Drive Folder: {DRIVE_FOLDER_ID}")
        
        # Folder mein MP4 files dhundho jo Trash mein na hon
        query = f"'{DRIVE_FOLDER_ID}' in parents and mimeType contains 'video/' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])

        if not files:
            print("😴 Drive Folder khali hai. Koi video nahi mili.")
            return None, None, None

        # Pehli video uthao
        file = files[0]
        file_id = file['id']
        file_name = file['name']
        
        # File name se '.mp4' hata kar Title banao
        title = os.path.splitext(file_name)[0].replace("_", " ")
        
        print(f"⬇️ Downloading: {file_name}")
        
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO("video.mp4", "wb")
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            # print(f"Download {int(status.progress() * 100)}%.")
        
        print("✅ Download Complete.")
        return "video.mp4", title, file_id
        
    except Exception as e:
        print(f"❌ Drive Error: {e}")
        return None, None, None

# --- 2. UPLOAD TO YOUTUBE ---
def upload_youtube(video_path, title):
    try:
        creds = get_creds()
        youtube = build('youtube', 'v3', credentials=creds)
        
        print(f"▶️ Uploading to YouTube: {title}")
        
        body = {
            "snippet": {
                "title": f"{title[:90]} #shorts", 
                "description": f"Enjoy this video!\n#shorts #funny #viral #trending",
                "tags": ["shorts", "viral", "funny", "trending"],
                "categoryId": "23" # Comedy
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        print("✅ SUCCESS! Video Uploaded to YouTube.")
        return True
    
    except Exception as e:
        print(f"❌ YouTube Upload Error: {e}")
        return False

# --- 3. DELETE FROM DRIVE ---
def delete_from_drive(file_id):
    try:
        creds = get_creds()
        service = build('drive', 'v3', credentials=creds)
        
        # File ko Trash mein move karein
        service.files().update(fileId=file_id, body={'trashed': True}).execute()
        print("🗑️ Video Drive se delete kar di gayi hai (Moved to Trash).")
    except Exception as e:
        print(f"⚠️ Delete Error: {e}")

# --- MAIN RUNNER ---
if __name__ == "__main__":
    vid_path, title, file_id = get_video_from_drive()
    
    if vid_path:
        success = upload_youtube(vid_path, title)
        if success:
            delete_from_drive(file_id) # Kaam hone ke baad delete
            if os.path.exists(vid_path): os.remove(vid_path) # GitHub cleanup
        else:
            sys.exit(1) # Fail action if upload fails
    else:
        # Agar video nahi mili, toh Action ko fail mat karo, bas ruk jao
        print("🔴 No videos to upload today.")
