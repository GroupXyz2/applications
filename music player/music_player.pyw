import os
import tkinter as tk
from tkinter import filedialog
import pygame
from mutagen.mp3 import MP3
from tkinter import ttk
import keyboard
import threading
import time
from pypresence import Presence
import pypresence
import sys
import urllib.parse
import webbrowser
#import winreg as reg #BROKEN
import platform

script_directory = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_directory, 'config.txt')
azure_theme_path = os.path.join(script_directory, 'Azure_Theme', 'azure.tcl')
forest_theme_light_path = os.path.join(script_directory, 'Forest_Theme', 'forest-light.tcl')
forest_theme_dark_path = os.path.join(script_directory, 'Forest_Theme', 'forest-dark.tcl')
icon_path = os.path.join(script_directory, 'icon.ico')
discord_application_id = "1266010137139744952"
standart_theme = "Azure"
standart_mode = "Dark"
version = "V1.6"

class MusicPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("Music Player " + version)
        self.root.geometry("750x500")

        self.style = ttk.Style(root)

        if os.path.isfile(icon_path) and platform.system() == "windows": #Broken on Linux
            root.iconbitmap(icon_path)    

        self.playlist = []
        self.current_track = tk.StringVar()
        self.track_length = tk.IntVar()
        self.current_time = tk.IntVar()
        self.volume = tk.DoubleVar()
        self.last_index = tk.IntVar()
        self.spacepause_enabled = tk.BooleanVar()

        self.skip_pressed = False
        self.keyboard_thread_started = False
        self.is_paused = False
        self.listener_active = False
        self.azure_theme_initialized = False
        self.forest_theme_light_initialized = False
        self.forest_theme_dark_initialized = False
        self.valorant_theme_light_initialized = False
        self.valorant_theme_dark_initialized = False
        self.is_closing = False

        self.create_ui()
        self.load_config()
        pygame.mixer.init()
        self.print_to_console("Info: Currently only accepts mp3 Files, Programmed by GroupXyz")

        if len(sys.argv) > 1:
            self.handle_custom_url(sys.argv[1])               

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

        # Themes and Modes

        appearance_frame = tk.Frame(self.root)
        appearance_frame.pack(pady=10)

        self.selected_theme = tk.StringVar()
        theme_label = tk.Label(appearance_frame, text="Theme:")
        theme_label.grid(row=0, column=0, padx=10)
        self.theme_box = ttk.Combobox(appearance_frame, textvariable=self.selected_theme, values=["Azure", "Forest"])
        self.theme_box.set(standart_theme)
        self.theme_box.grid(row=0, column=1, padx=10)

        self.selected_mode = tk.StringVar()
        mode_label = tk.Label(appearance_frame, text="Mode:")
        mode_label.grid(row=0, column=2, padx=10)
        self.mode_box = ttk.Combobox(appearance_frame, textvariable=self.selected_mode, values=["Dark", "Light"])
        self.mode_box.set(standart_mode)
        self.mode_box.grid(row=0, column=3, padx=10)

        self.pause_checkbutton = ttk.Checkbutton(appearance_frame, text="Pause with Spacebar", variable=self.spacepause_enabled)
        self.pause_checkbutton.grid(row=0, column=5, padx=10)

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

        self.theme_box.bind("<<ComboboxSelected>>", lambda event: self.change_mode())
        self.mode_box.bind("<<ComboboxSelected>>", lambda event: self.change_mode())

        self.change_mode()

        self.root.after(1000, self.update_ui)

        try:
            self.rpc = Presence(discord_application_id)
            self.rpc.connect()
        except Exception as e:
            self.print_to_console(f'Error connecting Discord rich presence: {e}')       

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
            self.discord_rich_presence(track)  
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
                    if self.spacepause_enabled.get():
                        self.pause_checkbutton.configure(state="disabled")
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

    def change_mode(self):
        try:
            theme = self.selected_theme.get()
            mode = self.selected_mode.get()
            if theme == "Forest":
                if mode == "Dark":
                    self.forest_dark_mode()
                elif mode == "Light":
                    self.forest_light_mode()
            elif theme == "Azure":
                if mode == "Dark":
                    self.azure_dark_mode()
                elif mode == "Light":
                    self.azure_light_mode()                      
        except Exception as e:
            self.print_to_console(f'Error changing Mode/Theme: {e}')                      


    def azure_dark_mode(self):
        try:
            if self.azure_theme_initialized == False:
                self.azure_theme_initialized = True
                self.root.tk.call("source", os.path.join(azure_theme_path))
            self.root.tk.call("set_theme", "dark")
            self.playlist_listbox.configure(bg="gray", selectbackground="#6b6c6d", selectforeground="black")
            self.mode_box.configure(state="enabled")
        except Exception as e:
            self.print_to_console(f'Error loading azure Theme: {e}')    

    def azure_light_mode(self):
        try:
            if self.azure_theme_initialized == False:
                self.azure_theme_initialized = True
                self.root.tk.call("source", os.path.join(azure_theme_path))
            self.root.tk.call("set_theme", "light")
            self.playlist_listbox.configure(bg="lightgray", selectbackground="gray")
            self.mode_box.configure(state="enabled")
        except Exception as e:
            self.print_to_console(f'Error loading azure Theme: {e}')

    def forest_dark_mode(self):
        try:
            if self.forest_theme_dark_initialized == False:
                self.forest_theme_dark_initialized = True
                self.root.tk.call("source", os.path.join(forest_theme_dark_path))#
            self.style.theme_use("forest-dark")
            self.playlist_listbox.configure(bg="gray", selectbackground="#6b6c6d", selectforeground="black")
            self.mode_box.configure(state="disabled")
        except Exception as e:
            self.print_to_console(f'Error loading forest Theme: {e}')

    def forest_light_mode(self):
        try:
            if self.forest_theme_light_initialized == False:
                self.forest_theme_light_initialized = True
                self.root.tk.call("source", os.path.join(forest_theme_light_path))
            self.style.theme_use("forest-light")
            self.playlist_listbox.configure(bg="lightgray", selectbackground="gray")
            self.mode_box.configure(state="disabled")
        except Exception as e:
            self.print_to_console(f'Error loading forest Theme: {e}')

    def discord_rich_presence(self, track):
        try:
            self.song_files = []
            self.current_song_length = pygame.mixer.music.get_pos()
            song_name = os.path.basename(track)
            self.rpc.connect()
            self.rpc.update(
                    details=f"Listening to PyPlayer",
                    state=f"Playing: {song_name}",
                    large_image=icon_path,
                    large_text="PyPlayerByGroupXyz",
                    #start = int(self.current_time),
                    #end = int(self.current_song_length),
                    buttons=[
                        {"label": "PyPlayer", "url": "https://github.com/GroupXyz2/applications/tree/main/music%20player"}
                    ]
                )
        except Exception as e:
            self.print_to_console(f'Error loading Discord rich presence: {e}')

    def handle_custom_url(self, url):
        try:
            parsed_url = urllib.parse.urlparse(url)
            
            if parsed_url.scheme == "play":
                song_name = parsed_url.netloc
                
                if song_name:
                    self.play_track_by_name(song_name)
                else:
                    self.print_to_console("Error: Song name is empty or invalid.")
            else:
                self.print_to_console(f"Error: URL scheme is not 'play'. Found scheme: '{parsed_url.scheme}'")
        except Exception as e:
            self.print_to_console(f"Error handling custom URL: {e}")



    def play_track_by_name(self, song_name):
        try:
            song_name = os.path.basename(song_name).strip().lower()
            song_name = song_name.replace(' ', '_')
            song_name = song_name.replace('%20', '_')
            self.print_to_console(f"Searching for song: '{song_name}'")
            
            found = False
            if (song_name != ""):
                for index, track in enumerate(self.playlist):
                    track_name = os.path.basename(track).strip().lower()
                    track_name = track_name.replace(' ', '_')
                    track_name = track_name.replace('%20', '_')
                    #self.print_to_console(f"Checking track {index}: '{track_name}'")
                    
                    if song_name in track_name:
                        self.play_track(track)
                        self.playlist_listbox.selection_set(index)
                        found = True
                        break
                    
            if not found:
                self.print_to_console(f"Song '{song_name}' not found in playlist.")
        except Exception as e:
            self.print_to_console(f"Error playing track: {e}")                    

                                                                


if __name__ == "__main__":

    def protocol_exists(protocol_name):
        try:
            key = reg.OpenKey(reg.HKEY_CLASSES_ROOT, protocol_name, 0, reg.KEY_READ)
            reg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False

    def register_protocol():

            protocol_name = "play"
            if not protocol_exists(protocol_name):
                executable_path = os.path.abspath(sys.argv[0])

                key = reg.HKEY_CLASSES_ROOT
                key_value = protocol_name

                key = reg.CreateKey(key, key_value)
                reg.SetValue(key, '', reg.REG_SZ, 'URL:Play Protocol')
                reg.SetValueEx(key, 'URL Protocol', 0, reg.REG_SZ, '')

                key = reg.CreateKey(key, r'shell\open\command')
                reg.SetValue(key, '', reg.REG_SZ, f'"{executable_path}" "%1"')            
   
    #if (platform.system() == "Windows"):
        #register_protocol()         

    root = tk.Tk()
    app = MusicPlayer(root)

    root.mainloop()

    

    
