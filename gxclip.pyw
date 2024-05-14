import tkinter as tk
from tkinter import ttk, simpledialog
import cv2
import threading
from datetime import datetime
import os
import pyaudio
import wave
import numpy as np
import pyautogui
from PIL import Image, ImageTk
from moviepy.editor import VideoFileClip, AudioFileClip
import keyboard
import time
import queue
import json
import sys
import sounddevice as sd



class ScreenRecorderApp:
    def __init__(self, master):
        self.master = master
        master.title("gxclip")
        master.geometry("800x600")

        self.recording = False
        self.record_start_time = None
        self.recorded_clips = []
        self.version = "Development Version 0.1"

        self.style = ttk.Style()
        self.style.configure('TButton', font=('Helvetica', 14), padding=10)
        self.style.map('TButton', foreground=[('pressed', 'white'), ('active', 'white')],
                       background=[('pressed', '!disabled', '#4CAF50'), ('active', '#4CAF50')])
        self.style.configure('TFrame', background='#f0f0f0')

        self.record_button = ttk.Button(master, text="Start Recording (F1)", command=self.toggle_recording)
        self.record_button.pack(pady=20)

        self.clip_frame = ttk.Frame(master)
        self.clip_frame.pack(pady=20)

        self.version_label = ttk.Label(self.clip_frame, text=self.version, font=('Helvetica', 16, 'bold'), foreground="red")
        self.version_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        self.clip_label = ttk.Label(self.clip_frame, text="Recorded Clips:", font=('Helvetica', 16, 'bold'))
        self.clip_label.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

        self.clip_canvas = tk.Canvas(self.clip_frame, width=780, height=400, bg='#ffffff')
        self.clip_canvas.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

        self.hotkey_thread = threading.Thread(target=self.listen_hotkey)
        self.hotkey_thread.daemon = True
        self.hotkey_thread.start()

        self.folder_label = ttk.Label(self.clip_frame, text="Click to open records Folder", font=('Helvetica', 16, 'bold'))
        self.folder_label.grid(row=1, column=0, columnspan=2, padx=10, pady=10)
        self.folder_label.bind("<Button-1>", self.open_records_folder)

        self.temp_folder = os.path.join(os.path.dirname(__file__), 'temp')
        self.records_folder = os.path.join(os.path.dirname(__file__), 'records')

        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)

        if not os.path.exists(self.records_folder):
            os.makedirs(self.records_folder)

        self.load_data_on_startup()

        self.master.protocol("WM_DELETE_WINDOW", self.save_data_on_close)
        time.sleep(1)
        self.master.protocol("WM_DELETE_WINDOW", self.exit)

    def open_records_folder(self, event):
        records_folder_path = os.path.join(os.path.dirname(__file__), 'records')
        os.startfile(records_folder_path)            

    def load_recorded_clips(self):
        self.recorded_clips.clear()
        for root, dirs, files in os.walk(self.records_folder):
            for file in files:
                if file.endswith(".mp4"):
                    mp4_filepath = os.path.join(root, file)
                    thumbnail_filename = f"{os.path.splitext(file)[0]}.png"
                    thumbnail_filepath = os.path.join(os.path.dirname(__file__), 'temp', thumbnail_filename)
                    if os.path.exists(thumbnail_filepath):
                        self.recorded_clips.append((mp4_filepath, thumbnail_filepath))
        self.update_clip_list()

    def toggle_recording(self):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.recording = True
        self.record_start_time = datetime.now()
        self.record_button.configure(text="Stop Recording (F1)", style='TButton')
        self.record_clip_callback = queue.Queue()
        self.record_clip_thread = threading.Thread(target=self.record_clip, args=(self.record_clip_callback,))
        self.record_clip_thread.start()

    def stop_recording(self):
        self.recording = False
        self.record_button.configure(text="Start Recording (F1)", style='TButton')

    def record_clip(self, callback=None):
        try:
            temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)

            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            filename = f"clip_{self.record_start_time.strftime('%Y-%m-%d_%H-%M-%S')}.avi"
            filepath = os.path.join(temp_dir, filename)
            out = cv2.VideoWriter(filepath, fourcc, 20.0, (1920, 1080))

            audio_filename = f"audio_{self.record_start_time.strftime('%Y-%m-%d_%H-%M-%S')}.wav"
            audio_filepath = os.path.join(temp_dir, audio_filename)
            audio_thread = threading.Thread(target=self.record_audio, args=(audio_filepath,))
            audio_thread.start()

            while self.recording:
                screenshot = pyautogui.screenshot()
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                out.write(frame)
                time.sleep(0.05)

            out.release()

            audio_thread.join()

            if callback:
                callback.put("AVI file is ready for conversion")

            self.merge_audio_video(filepath, audio_filepath, temp_dir)
            mp4_filepath = self.convert_to_mp4(filepath, self.records_folder)
            if mp4_filepath:
                thumbnail_filepath = self.create_thumbnail(mp4_filepath)
                if thumbnail_filepath:
                    self.recorded_clips.append((mp4_filepath, thumbnail_filepath))
                    self.update_clip_list()
        except Exception as e:
            print(f"Error during recording: {e}")


    def record_audio(self, filepath):
        try:
            print("Starting audio recording...")
            RATE = 44100
            CHUNK = 1024
            CHANNELS = 1
            FORMAT = pyaudio.paInt16

            p = pyaudio.PyAudio()
            stream = p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK)

            frames = []
            while self.recording:
                data = stream.read(CHUNK)
                frames.append(data)

            stream.stop_stream()
            stream.close()
            p.terminate()
            print("Audio recording stopped")

            wf = wave.open(filepath, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            print("Audio file saved:", filepath)

        except Exception as e:
            print(f"Error during audio recording: {e}")

    def merge_audio_video(self, video_filepath, audio_filepath, temp_dir):
        try:
            print("Merging audio and video...")
            video_clip = VideoFileClip(video_filepath)
            audio_clip = AudioFileClip(audio_filepath)
            final_clip = video_clip.set_audio(audio_clip)
            final_clip.write_videofile(os.path.join(temp_dir, "temp.mp4"), codec="libx264", audio_codec="aac")
            print("Audio and video merged successfully")
        except Exception as e:
            print(f"Error merging audio and video: {e}")

    def convert_to_mp4(self, avi_filepath, output_dir):
        try:
            if not self.record_clip_callback.empty():
                self.record_clip_callback.get()
            mp4_filepath = os.path.join(output_dir, os.path.splitext(os.path.basename(avi_filepath))[0] + '.mp4')
            video = VideoFileClip(avi_filepath)
            video.write_videofile(mp4_filepath)
            return mp4_filepath
        except Exception as e:
            print(f"Error converting to MP4: {e}")
            return None

    def create_thumbnail(self, video_filepath):
        try:
            thumbnail_filename = f"{os.path.splitext(os.path.basename(video_filepath))[0]}.png"
            thumbnail_filepath = os.path.join(self.temp_folder, thumbnail_filename)
            clip = VideoFileClip(video_filepath)
            frame = clip.get_frame(0)
            Image.fromarray(frame).save(thumbnail_filepath)
            return thumbnail_filepath
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            return None

    def update_clip_list(self):
        self.clip_canvas.delete("all")
        x, y = 10, 10
        thumbnail_width = 150
        thumbnail_height = 100
        row_height = thumbnail_height + 30
        for clip, thumbnail in self.recorded_clips:
            if os.path.exists(thumbnail):
                image = Image.open(thumbnail)
                image.thumbnail((thumbnail_width, thumbnail_height))
                photo = ImageTk.PhotoImage(image)
                self.clip_canvas.create_image(x, y, anchor='nw', image=photo)
                self.clip_canvas.image = photo
                text_id = self.clip_canvas.create_text(x + thumbnail_width / 2, y + thumbnail_height + 10, text=os.path.basename(clip), font=('Helvetica', 12), fill='black')
                self.clip_canvas.tag_bind(text_id, "<Double-1>", lambda event, clip=clip: self.rename_clip(event, clip))
                y += row_height
                if y > self.clip_canvas.winfo_reqheight():
                    y = 10 
                    x += thumbnail_width + 10

    def save_data_on_close(self):
        with open('clips_data.json', 'w') as f:
            json.dump(self.recorded_clips, f)   

    def load_data_on_startup(self):
        if os.path.isfile('clips_data.json'):
            with open('clips_data.json', 'r') as f:
                self.recorded_clips = json.load(f)
            self.update_clip_list()                     

    def rename_clip(self, event, clip):
        name = simpledialog.askstring("Clip Name", "Enter a new name for the clip:")
        if name:
            new_clip = os.path.join(os.path.dirname(clip), f"{name}.mp4")
            os.rename(clip, new_clip)
            self.update_clip_list()

    def listen_hotkey(self):
        while True:
            if keyboard.is_pressed('F1'):
                self.toggle_recording()
            time.sleep(0.1)

    def exit(self):
        sys.exit()        

def main():
    root = tk.Tk()
    app = ScreenRecorderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
    











