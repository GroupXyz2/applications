import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import yt_dlp

def download_video(url, download_path, update_progress):
    try:
        def hook(data):
            if data['status'] == 'downloading':
                downloaded = data.get('downloaded_bytes', 0)
                total = data.get('total_bytes', 1)
                percentage = (downloaded / total) * 100
                update_progress(percentage, "Downloading...")

        ydl_opts = {
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
            'progress_hooks': [hook]
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def start_download():
    url = url_entry.get()
    if not url:
        messagebox.showwarning("Warning", "Please enter a YouTube URL.")
        return

    download_path = filedialog.askdirectory(title="Select Download Folder")
    if not download_path:
        return

    progress_label.config(text="Starting download...")
    progress_bar['value'] = 0

    def run():
        download_video(url, download_path, update_progress)
        progress_label.config(text="Download completed.")

    threading.Thread(target=run, daemon=True).start()

def update_progress(percentage, message):
    progress_bar['value'] = percentage
    progress_label.config(text=f"{message} {percentage:.2f}%")

def setup_dark_mode(root):
    root.configure(bg="#2e2e2e")
    style = ttk.Style()
    style.theme_use("default")
    style.configure("TLabel", background="#2e2e2e", foreground="white")
    style.configure("TButton", background="#444444", foreground="white")
    style.configure("TEntry", fieldbackground="#444444", foreground="white", insertcolor="white")
    style.configure("TProgressbar", troughcolor="#444444", background="#0080ff")

root = tk.Tk()
root.title("YouTube Downloader")
root.geometry("400x250")
root.resizable(False, False)

setup_dark_mode(root)

url_label = ttk.Label(root, text="YouTube URL:")
url_label.pack(pady=5)
url_entry = ttk.Entry(root, width=50)
url_entry.pack(pady=5)

download_button = ttk.Button(root, text="Download", command=start_download)
download_button.pack(pady=10)

progress_bar = ttk.Progressbar(root, orient="horizontal", mode="determinate", length=300)
progress_bar.pack(pady=10)
progress_label = ttk.Label(root, text="")
progress_label.pack()

root.mainloop()
