import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os

class FFmpegConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("FFmpeg Converter")

        self.file_paths = []

        self.input_files_label = tk.Label(root, text="Input files:")
        self.input_files_label.pack(pady=5)
        
        self.input_files_button = tk.Button(root, text="Add files", command=self.select_input_files)
        self.input_files_button.pack(pady=5)
        
        self.input_files_listbox = tk.Listbox(root, width=50, height=10, selectmode=tk.MULTIPLE)
        self.input_files_listbox.pack(pady=5)

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
        
    def select_input_files(self):
        file_paths = filedialog.askopenfilenames(title="Choose the input files")
        if file_paths:
            for file_path in file_paths:
                if file_path not in self.file_paths:
                    self.file_paths.append(file_path)
                    self.input_files_listbox.insert(tk.END, file_path)
                    
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
