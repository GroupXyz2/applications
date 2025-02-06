import os
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
from collections import deque
import threading
import re
import subprocess

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"], # Change to your urls, which are allowed to connect to the backend
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
                print(f"Error deleting {file_path}: {e}")

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

def is_valid_spotify_url(url):
    spotify_regex = r'(https?://)?(open\.spotify\.com|spotify:)/.+'
    return re.match(spotify_regex, url) is not None

@app.post("/download/")
async def download_video(request: VideoRequest):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Download-request received: URL={request.url}, Format={request.format}")

    if not is_valid_youtube_url(request.url) and not is_valid_spotify_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid URL. Only YouTube and Spotify URL's supported.")
    check_rate_limit()

    if is_valid_youtube_url(request.url):
        if request.format == "mp3":
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                "outtmpl": os.path.join(DOWNLOAD_FOLDER, "%(title)s.%(ext)s").replace(",", ""),
                'socket_timeout': 30,
            }
        else:
            ydl_opts = {
                'format': 'best',
                "outtmpl": os.path.join(DOWNLOAD_FOLDER, "%(title)s.%(ext)s").replace(",", ""),
                'socket_timeout': 30,
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
    
    elif is_valid_spotify_url(request.url):
        if request.format != "mp3":
            request.format = "mp3"

        try:
            result = subprocess.run(
                ["spotdl", "download", request.url, "--output", DOWNLOAD_FOLDER],
                capture_output=True,
                text=True,
                timeout=30
            )
            print(f"spotdl stdout: {result.stdout}")
            print(f"spotdl stderr: {result.stderr}")
            if result.returncode != 0:
                raise HTTPException(status_code=500, detail=f"Download-Error: {result.stderr}")
            
            match = re.search(r'Downloaded "([^"]+)"', result.stdout)
            if not match:
                match = re.search(r'Skipping ([^ ]+) \(file already exists\)', result.stdout)
                if not match:
                    raise HTTPException(status_code=500, detail="Error while extracting filename.")
            file_name = match.group(1).replace(" ", "%20") + ".mp3"
            file_path = os.path.join(DOWNLOAD_FOLDER, file_name)
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Download-Timeout: Timeout of 30sec exceeded.")
        except Exception as e:
            print(f"Exception during spotdl execution: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unknown Error: {str(e)}")

    return {"message": f"{request.format.upper()} downloaded: {request.url}", "file_path": file_path}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081, # Replace paths to your certificates, port can be changed but needs to be adjusted in the frontend too
                ssl_keyfile="/etc/letsencrypt/live/example.com/privkey.pem",
                ssl_certfile="/etc/letsencrypt/live/example.com/fullchain.pem")
