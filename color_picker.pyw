import tkinter as tk
from PIL import ImageGrab
import webcolors
from pynput import mouse
import pyperclip

class ColorPickerApp:
    def __init__(self, master):
        self.master = master
        master.title("Color Picker")
        self.pick_button = tk.Button(master, text="Choose Pixel", command=self.hide_app, font=("Helvetica", 12), bg="#4CAF50", fg="white")
        self.pick_button.pack(pady=5)

        self.previewtext_label = tk.Label(master, text="Preview", font=("Helvetica", 14, "bold"))
        self.previewtext_label.pack(pady=10)
        self.previewtext_label.bind("<Button-1>", self.copy_to_clipboard)

        self.preview_label = tk.Label(master, text="", font=("Helvetica", 14))
        self.preview_label.pack(pady=10)
        self.preview_label.bind("<Button-1>", self.copy_to_clipboard)

        self.preview_canvas = tk.Canvas(master, width=100, height=100, bg="white")
        self.preview_canvas.pack()
        self.preview_canvas.bind("<Button-1>", self.copy_to_clipboard)

        self.color_preview = None

        self.previewcopy_label = tk.Label(master, text="", font=("Helvetica", 14))
        self.previewcopy_label.pack(pady=10)
        self.previewcopy_label.bind("<Button-1>", self.copy_to_clipboard)

    def hide_app(self):
        self.master.withdraw()
        self.listener = mouse.Listener(on_click=self.get_color_preview)
        self.listener.start()

    def get_color_preview(self, x, y, button, pressed):
        if pressed:
            screenshot = ImageGrab.grab()
            pixel = screenshot.getpixel((x, y))
            color = webcolors.rgb_to_hex(pixel[:3])
            self.update_color_preview(color)
            self.master.deiconify()
            self.listener.stop()

    def update_color_preview(self, color):
        self.preview_canvas.delete("all")
        self.color_preview = color
        self.preview_canvas.create_rectangle(0, 0, 100, 100, fill=color, outline="")
        self.preview_label.config(text=f"{color}", font=("Helvetica", 14, "bold"))
        self.previewcopy_label.config(text=f"Click to copy", font=("Helvetica", 14, "bold"))

    def copy_to_clipboard(self, event):
        pyperclip.copy(self.color_preview)

def main():
    root = tk.Tk()
    app = ColorPickerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()





