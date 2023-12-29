import customtkinter
from datetime import datetime

customtkinter.set_appearance_mode("system")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

app = customtkinter.CTk()
app.geometry("600x390")
app.title("time converter")

def print_output(text):
    text_1.configure(state="normal")
    text_1.insert("0.0", text + "\n")
    text_1.configure(state="disabled")

def button_callback():
    time = entry_1.get()
    selection = combobox_1.get()
    convert_discordtime(selection, time)

def convert_discordtime(selection, time):
    if selection == "time->discord-timestamp":
        try:
            if len(time) == len("01.01.2000 12:30"):
                stripped_date = datetime.strptime(time, "%d.%m.%Y %H:%M")
            elif len(time) == len("01.01.2000"):
                stripped_date = datetime.strptime(time + " 00:00", "%d.%m.%Y %H:%M")
            else:
                raise ValueError("invalid format!")    
            unix_date= int(stripped_date.timestamp())
            discord_timestamp = f"<t:{unix_date}>"
            print_output(discord_timestamp)
        except:
            print_output("error while converting, please check your input!")
    else:
        print_output("invalid selection!")    

frame_1 = customtkinter.CTkFrame(master=app)
frame_1.pack(pady=20, padx=60, fill="both", expand=True)

label_1 = customtkinter.CTkLabel(master=frame_1, justify=customtkinter.LEFT, text="time converter")
label_1.pack(pady=10, padx=10)

combobox_1 = customtkinter.CTkComboBox(frame_1, values=["time->discord-timestamp", "Option 2"])
combobox_1.pack(pady=10, padx=10)
combobox_1.set("time->discord-timestamp")

label_2 = customtkinter.CTkLabel(master=frame_1, justify=customtkinter.LEFT, text="example input:     01.01.2000 12:34")
label_2.pack(pady=5, padx=10)

entry_1 = customtkinter.CTkEntry(master=frame_1, placeholder_text="enter time")
entry_1.pack(pady=10, padx=10)

button_1 = customtkinter.CTkButton(master=frame_1, command=button_callback, text="convert")
button_1.pack(pady=10, padx=10)

label_3 = customtkinter.CTkLabel(master=frame_1, justify=customtkinter.LEFT, text="output")
label_3.pack(pady=10, padx=10)

text_1 = customtkinter.CTkTextbox(master=frame_1, width=200, height=70)
text_1.pack(pady=10, padx=10)
text_1._scrollbars_activated = False
text_1.insert("0.0", "\n")
text_1.configure(state="disabled")

app.mainloop()