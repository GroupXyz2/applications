import os
import tkinter as tk
from tkinter import filedialog
import pygame
from mutagen.mp3 import MP3
from tkinter import ttk
import keyboard
import threading
import time
import sys

script_directory = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_directory, 'config.txt')
theme_path = os.path.join(script_directory, 'Azure_Theme', 'azure.tcl')
icon_path = os.path.join(script_directory, 'icon.ico')
standard_theme = "azure"
standard_mode = "dark"
version = "V1.5"

class MusicPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("Music Player " + version)
        self.root.geometry("750x500")

        if os.path.isfile(icon_path):
            root.iconbitmap(icon_path)    

        self.playlist = []
        self.current_track = tk.StringVar()
        self.track_length = tk.IntVar()
        self.current_time = tk.IntVar()
        self.volume = tk.DoubleVar()
        self.last_index = tk.IntVar()

        self.skip_pressed = False
        self.keyboard_thread_started = False
        self.is_paused = False
        self.listener_active = False
        self.azure_theme_initialized = False

        self.create_ui()
        self.load_config()
        pygame.mixer.init()
        self.print_to_console("Info: Currently only accepts mp3 Files, Programmed by GroupXyz")

        # Apply Theme
        if standard_theme == "azure":
            self.root.option_add('*Listbox.Foreground', '#FFFFFF')
            if standard_mode == "light":
                self.azure_light_mode()
            elif standard_mode == "dark":
                self.azure_dark_mode()    

    def create_ui(self):
         # Track Info
        track_info_frame = tk.Frame(self.root)
        track_info_frame.pack(pady=10)

        ttk.Label(track_info_frame, textvariable=self.current_track, font=("Helvetica", 12)).pack()

        # Playlist Listbox
        self.playlist_listbox = tk.Listbox(self.root, selectmode=tk.SINGLE, bg="lightgray", selectbackground="gray")
        self.playlist_listbox.pack(pady=10, fill=tk.BOTH, expand=True)
        self.load_button = ttk.Button(self.root, text="Load Playlist (Folder with mp3 Files)", command=self.load_playlist)
        self.load_button.pack()

        # Controls Frame
        controls_frame = tk.Frame(self.root)
        controls_frame.pack(pady=10)

        ttk.Button(controls_frame, text="Start", command=self.start).grid(row=0, column=0, padx=10)
        ttk.Button(controls_frame, text="Pause", command=self.pause).grid(row=0, column=1, padx=10)    
        ttk.Button(controls_frame, text="Continue", command=self.play).grid(row=0, column=2, padx=10)
        ttk.Button(controls_frame, text="Skip", command=self.next_track).grid(row=0, column=3, padx=10)

        # Time Entry (dev)

        self.time_entry = ttk.Entry(controls_frame)
        ttk.Button(controls_frame, text="Skip to time ->", command=self.set_time_from_entry).grid(row=0, column=4, padx=10)
        self.time_entry.grid(row=0, column=5, padx=10)

        # Light/Dark Mode
        ttk.Button(controls_frame, text="Dark Mode", command=self.azure_dark_mode).grid(row=0, column=6, padx=10)
        ttk.Button(controls_frame, text="Light Mode", command=self.azure_light_mode).grid(row=0, column=7, padx=10)

        # Volume Slider
        volume_frame = tk.Frame(self.root)
        volume_frame.pack(pady=10)

        ttk.Label(volume_frame, text="Volume:").grid(row=0, column=0, padx=10)
        volume_slider = ttk.Scale(volume_frame, from_=0, to=1, orient=tk.HORIZONTAL, variable=self.volume, command=self.set_volume)
        volume_slider.set(0.1)
        volume_slider.grid(row=0, column=1, padx=10)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, length=500, mode="determinate")
        self.progress_bar.pack(pady=10)

        # Console

        console_frame = tk.Frame(self.root)
        console_frame.pack(pady=10)

        console_label = ttk.Label(console_frame, text="Console:")
        console_label.pack()

        self.console_text = tk.Text(console_frame, wrap=tk.WORD, height=2, width=80)
        self.console_text.pack()

        self.console_text.configure(state="disabled")  

        # Time Slider

        # time_slider_frame = tk.Frame(self.root)
        # time_slider_frame.pack(pady=10)

        # ttk.Label(time_slider_frame, text="Quick switch:").grid(row=0, column=0, padx=10)
        # self.time_slider = ttk.Scale(time_slider_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.current_time, command=self.set_time)
        # self.time_slider.set(0)
        # self.time_slider.grid(row=0, column=1, padx=10)

        self.playlist_listbox.bind("<Double-1>", self.play_selected_track)

        self.root.after(1000, self.update_ui)

    def load_config(self):
        try:
            with open(config_path, 'r') as file:
                lines = file.readlines()
            config = {}
            for line in lines:
                key, value = line.strip().split('=')
                config[key] = value
            self.load_standart_playlist(config['standart_path']) 
            return config
        except FileNotFoundError:
            self.print_to_console('Created new config file: ' + config_path)
            config = {
                'standart_path': script_directory + '\\songs' 
            }
            with open(config_path,'w') as file:
                for key, value in config.items():
                    file.write(f"{key}={value}\n")
            self.load_standart_playlist(config['standart_path'])        
            return config
        except ValueError as e:
            self.print_to_console(f'Exception while trying to load config: {e}')  

    def load_standart_playlist(self, standart_path):
        directory = standart_path
        try:
            if directory:
                    self.playlist = [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith(".mp3")]
                    self.playlist_listbox.delete(0, tk.END)
                    for track in self.playlist:
                        self.playlist_listbox.insert(tk.END, os.path.basename(track))
        except Exception:
            try:
               os.makedirs(directory) 
               self.print_to_console(f'Folder for standart playlist created: ' + directory)
            except: return                

    def load_playlist(self):
        directory = filedialog.askdirectory()
        try:
            if directory:
                self.playlist = [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith(".mp3")]
                self.playlist_listbox.delete(0, tk.END)
                for track in self.playlist:
                    self.playlist_listbox.insert(tk.END, os.path.basename(track))
        except Exception as e:
            self.print_to_console(f'Error loading playlist: {e}')            

    def play_selected_track(self, event):
        selected_index = self.playlist_listbox.curselection()
        if selected_index:
            selected_track = self.playlist[selected_index[0]]
            self.play_track(selected_track)
            self.check_music_end()

    def play_track(self, track):
        try:
            pygame.mixer.music.load(track)
            pygame.mixer.music.set_volume(self.volume.get())
            pygame.mixer.music.play()
            self.current_track.set("Now Playing: " + os.path.basename(track))
            self.track_length.set(int(MP3(track).info.length))
            self.current_time.set(0)
            self.progress_bar["maximum"] = self.track_length.get()
            self.last_index = self.playlist_listbox.curselection()
            self.is_paused = False
            self.start_keyboard_thread() 
        except Exception as e:
            self.print_to_console(f'Error while opening file: {e}')   

    def start(self):
        if self.playlist:
            first_track = self.playlist[0]
            self.print_to_console("player started: " + first_track)
            self.play_track(first_track)
            self.playlist_listbox.selection_set(0)
            self.check_music_end()
        else:
            self.print_to_console("Playlist is empty.")

    def print_to_console(self, message):
        self.console_text.configure(state="normal")
        self.console_text.insert(0.0, message + "\n")
        self.console_text.see(0.0)
        self.console_text.configure(state="disabled")

    def start_keyboard_thread(self):
        if not self.keyboard_thread_started:
            self.keyboard_thread = threading.Thread(target=self.keyboard_listener)
            self.keyboard_thread.start()
            self.keyboard_thread_started = True

    def on_key_event(self, e):
        try:
            if self.root.winfo_ismapped():
                if e.event_type == keyboard.KEY_DOWN and e.name == "space":
                    if pygame.mixer.music.get_busy and not self.is_paused:
                        self.root.focus_set()
                        self.pause()
                    elif pygame.mixer.music.get_busy and self.is_paused:
                        self.root.focus_set()
                        self.play()
                        self.is_paused = False  
        except Exception as e:
            self.print_to_console(f'Space key listener error: {e}')    

    def keyboard_listener(self):
        try:
            while self.root.winfo_exists():
                print("debug")
                if not self.listener_active:
                    keyboard.hook(self.on_key_event)
                    keyboard.wait()
                    self.listener_active = True
                    #TODO Stop Thread     
        except Exception as e: self.print_to_console(f'Space key thread error: {e}')                              

    # Time Entry Function (dev)

    def set_time_from_entry(self):
        try:
            input_time = int(self.time_entry.get())

            if 0 <= input_time <= self.track_length.get():
                self.progress_bar["value"] = input_time

                self.skip_pressed = True
                self.is_paused = False
                pygame.mixer.music.set_pos(input_time)

                self.skip_pressed = False
                    
        except ValueError as e:
                self.print_to_console(f'Invalid entry: {e}')                    

    def play(self):
        pygame.mixer.music.unpause()
        self.skip_pressed = False  

    def pause(self):
        self.skip_pressed = True
        pygame.mixer.music.pause()
        self.is_paused = True   

    def stop(self):
        pygame.mixer.music.stop()

    def set_volume(self, *args):
        try:
            pygame.mixer.music.set_volume(self.volume.get())
        except: return     

    def set_time(self, value):
        target_time = int(float(value) * self.track_length.get())
        pygame.mixer.music.set_pos(target_time)        

    def update_ui(self):
        current_time = pygame.mixer.music.get_pos() // 1000
        self.current_time.set(current_time)
        self.progress_bar["value"] = current_time

        if current_time < self.track_length.get():
            self.root.after(1000, self.update_ui)
        else:
            self.next_track()

    def check_music_end(self):
        if not pygame.mixer.music.get_busy() and not self.skip_pressed:
            self.next_track()
        else:
            self.root.after(100, self.check_music_end)             

    def next_track(self):

        current_index = self.playlist_listbox.curselection()

        if not current_index:
            self.print_to_console("Marker not found, using last index")
            current_index = (self.last_index)

        if current_index:
            next_index = (current_index[0] + 1) % len(self.playlist)
            next_track = self.playlist[next_index]
            self.play_track(next_track)
            self.playlist_listbox.selection_clear(0, tk.END)
            self.playlist_listbox.selection_set(next_index)
            self.playlist_listbox.see(next_index)
            self.root.after(100, lambda: self.set_selection(next_index))
            self.check_music_end()
        self.skip_pressed = False
        self.is_paused = False

    def set_selection(self, index):
       self.playlist_listbox.selection_clear(0, tk.END)
       self.playlist_listbox.selection_set(index)
       self.playlist_listbox.see(index)

    def azure_dark_mode(self):
        try:
            if self.azure_theme_initialized == False:
                self.azure_theme_initialized = True
                self.root.tk.call("source", os.path.join(theme_path))
            self.root.tk.call("set_theme", "dark")
            self.playlist_listbox.configure(bg="gray", selectbackground="#6b6c6d", selectforeground="black")
            self.root.option_add('*Listbox.Foreground', '#FFFFFF')
        except Exception as e:
            self.print_to_console(f'Error loading azure Theme: {e}')    

    def azure_light_mode(self):
        try:
            if self.azure_theme_initialized == False:
                self.azure_theme_initialized = True
                self.root.tk.call("source", os.path.join(theme_path))
            self.root.tk.call("set_theme", "light")
            self.playlist_listbox.configure(bg="lightgray", selectbackground="gray")
        except Exception as e:
            self.print_to_console(f'Error loading azure Theme: {e}')  


if __name__ == "__main__":
    root = tk.Tk()
    app = MusicPlayer(root)
    root.mainloop()
    
