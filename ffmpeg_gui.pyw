import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os
import webbrowser

class FFmpegConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("FFmpeg Converter")

        if not self.check_ffmpeg_installed():
            self.install_ffmpeg()

        self.file_paths = []

        self.input_files_label = tk.Label(root, text="Input files:")
        self.input_files_label.pack(pady=5)
        
        self.input_files_button = tk.Button(root, text="Add files", command=self.select_input_files)
        self.input_files_button.pack(pady=5)
        
        self.input_files_frame = tk.Frame(root)
        self.input_files_frame.pack(pady=5)

        self.output_format_label = tk.Label(root, text="Output format:")
        self.output_format_label.pack(pady=5)
        
        self.output_format = tk.StringVar(value='mp4')
        self.format_menu = tk.OptionMenu(root, self.output_format, 'mp4', 'avi', 'mov', 'mkv', 'Custom')
        self.format_menu.pack(pady=5)

        self.custom_format_label = tk.Label(root, text="Custom format:")
        self.custom_format_label.pack(pady=5)
        
        self.custom_format_entry = tk.Entry(root, width=20)
        self.custom_format_entry.pack(pady=5)
    
        self.convert_button = tk.Button(root, text="Convert", command=self.convert_videos)
        self.convert_button.pack(pady=20)

    def check_ffmpeg_installed(self):
        try:
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            return False

    def install_ffmpeg(self):
        try:
            messagebox.showinfo("Info", "FFmpeg not found, trying to install, please wait!")
            subprocess.run(['winget', 'install', 'ffmpeg'], check=True)
            messagebox.showinfo("Info", "FFmpeg was successfully installed, if it doesn't work yet, please restart once.")
        except subprocess.CalledProcessError:
            result = messagebox.askyesno("FFmpeg not found", "FFmpeg could not be installed automatically. "
                                                            "Would you like to visit the download page?")
            if result:
                webbrowser.open("https://ffmpeg.org/download.html")
            self.root.quit()    
        
    def select_input_files(self):
        file_paths = filedialog.askopenfilenames(title="Choose the input files")
        if file_paths:
            for file_path in file_paths:
                if file_path not in self.file_paths:
                    self.file_paths.append(file_path)
                    self.add_file_entry(file_path)

    def add_file_entry(self, file_path):
        file_frame = tk.Frame(self.input_files_frame)
        file_frame.pack(fill='x', pady=2)

        file_label = tk.Label(file_frame, text=file_path, anchor='w')
        file_label.pack(side='left', fill='x', expand=True)

        remove_button = tk.Button(file_frame, text="X", command=lambda: self.remove_file(file_frame, file_path))
        remove_button.pack(side='right')

    def remove_file(self, file_frame, file_path):
        self.file_paths.remove(file_path)
        file_frame.destroy()

    def convert_videos(self):
        if not self.file_paths:
            messagebox.showerror("Error", "Please choose at least one input file.")
            return
        
        selected_format = self.output_format.get()
        
        if selected_format == 'Custom':
            custom_format = self.custom_format_entry.get().strip()
            if not custom_format:
                messagebox.showerror("Error", "Please enter a file format.")
                return
            output_extension = custom_format
        else:
            output_extension = selected_format
        
        for input_file in self.file_paths:
            if not os.path.isfile(input_file):
                messagebox.showerror("Error", f"The input file {input_file} doesn't exist.")
                continue
            
            output_file = f"{os.path.splitext(input_file)[0]}.{output_extension}"
            
            command = [
                'ffmpeg',
                '-i', input_file,
                '-c:v', 'libx264',
                '-b:v', '1000k',
                output_file
            ]

            try:
                subprocess.run(command, check=True)
                messagebox.showinfo("Success", f"The file was converted successfully: {output_file}")
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"Error while converting {input_file}: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FFmpegConverter(root)
    root.mainloop()
