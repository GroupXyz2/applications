import os
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
from collections import deque
import threading
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"], # Change to your server urls which are allowed to connect to the backend.
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

request_times = deque() 
DOWNLOAD_FOLDER = "downloads"

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)


RATE_LIMIT = 10  
TIME_FRAME = 60 

class VideoRequest(BaseModel):
    url: str
    format: str 

def delete_downloads_folder():
    while True:
        time.sleep(300) 
        for file in os.listdir(DOWNLOAD_FOLDER):
            file_path = os.path.join(DOWNLOAD_FOLDER, file)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"File deleted: {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")

threading.Thread(target=delete_downloads_folder, daemon=True).start()                 

def check_rate_limit():
    current_time = time.time()

    while request_times and request_times[0] < current_time - TIME_FRAME:
        request_times.popleft()

    if len(request_times) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")

    request_times.append(current_time)

def sanitize_filename(file_path):
    sanitized_filename = ''.join(c for c in file_path if c.isalnum() or c in ['_', '-'])
    return sanitized_filename

def is_valid_youtube_url(url):
    youtube_regex = r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+'
    return re.match(youtube_regex, url) is not None

@app.post("/download/")
async def download_video(request: VideoRequest):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Download-Request: URL={request.url}, Format={request.format}")

    if not is_valid_youtube_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid YouTube-URL.")
    check_rate_limit()

    if request.format == "mp3":
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        }
    else:
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(request.url, download=True)
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=500, detail=f"Download-Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unknown Error: {str(e)}")

    file_extension = "mp3" if request.format == "mp3" else result['ext']
    file_path = os.path.join(DOWNLOAD_FOLDER, f"{result['title']}.{file_extension}")
    
    return {"message": f"{request.format.upper()} downloaded: {result['title']}", "file_path": file_path}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081,
                ssl_keyfile="/etc/letsencrypt/live/example.com/privkey.pem",
                ssl_certfile="/etc/letsencrypt/live/example.com/fullchain.pem")
                # Change certificate paths to match your ssl certificate paths.
