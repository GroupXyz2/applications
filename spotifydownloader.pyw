import os
import subprocess
import customtkinter as ctk
from tkinter import messagebox
import sys

def run_as_admin(command):
    try:
        if os.name == "nt":
            subprocess.run(["powershell", "-Command", f"Start-Process cmd -ArgumentList '/c {command}' -Verb RunAs"], check=True)
        else:
            subprocess.run(["sudo"] + command.split(), check=True)
    except subprocess.CalledProcessError:
        raise Exception("Administratorrechte benötigt, Installation fehlgeschlagen.")

def check_and_install_spotdl():
    try:
        subprocess.run(["spotdl", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        try:
            command = "pip install spotdl"
            messagebox.showinfo("Info", "spotdl wird installiert, bitte erlaubte erhöhte Rechte!")
            run_as_admin(command)
            #subprocess.run(command.split(), check=True)
            messagebox.showinfo("Info", "spotdl wurde erfolgreich installiert.")
        except subprocess.CalledProcessError:
            messagebox.showerror("Fehler", "Fehler beim Installieren von spotdl. Bitte manuell installieren.")
            return False
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Installieren von spotdl: {e}")
            return False
    return True

def download_song():
    if not check_and_install_spotdl():
        return

    song_url = entry.get()
    if not song_url.strip():
        messagebox.showerror("Fehler", "Bitte gib eine gültige Spotify-URL ein.")
        return

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "downloads")
        os.makedirs(output_dir, exist_ok=True)
        os.chdir(output_dir)

        command = ["spotdl", song_url]
        subprocess.run(command, check=True)
        messagebox.showinfo("Erfolg", f"Song wurde erfolgreich heruntergeladen in: {output_dir}")
    except subprocess.CalledProcessError:
        messagebox.showerror("Fehler", "Fehler beim Herunterladen des Songs. Bitte überprüfe die URL und versuche es erneut.")
    except Exception as e:
        #messagebox.showerror("Fehler", f"Ein unerwarteter Fehler ist aufgetreten: {e}")
        ""

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

app = ctk.CTk()
app.title("Spotify Song Downloader")
app.geometry("600x300")

label = ctk.CTkLabel(app, text="Spotify Song Downloader", font=("Arial", 24, "bold"))
label.pack(pady=20)

entry = ctk.CTkEntry(app, placeholder_text="Spotify-Song-URL hier eingeben", width=500, font=("Arial", 14))
entry.pack(pady=20)

download_button = ctk.CTkButton(app, text="Download starten", command=download_song, width=200, height=50, font=("Arial", 14))
download_button.pack(pady=30)

app.mainloop()