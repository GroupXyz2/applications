import threading
import threading
import customtkinter
import keyboard
import ctypes
from ctypes import cast, POINTER
from comtypes import CoInitialize, CoUninitialize, CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from colorama import Fore, Style
import time
import sys

#variables

config_path = 'config.txt'

#start ui

customtkinter.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

app = customtkinter.CTk()
app.geometry("1000x780")
app.title("Hotkey Control Application")
app.after_cancel(lambda: print("stop"))
app.protocol("WM_DELETE_WINDOW", app.destroy)

def print_box(text):
    text_1.configure(state="normal")
    text_1.insert("0.0", text)
    text_1.configure(state="disabled")

def print_logs(text):
    text_2.configure(state="normal")
    text_2.insert("0.0", text)
    text_2.configure(state="disabled")

def microphone_callback(value):
    microphone()       

def speaker_callback(value):
    speaker()

def microphone_muted():
    CoInitialize()
    devices = AudioUtilities.GetMicrophone()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None
    ).QueryInterface(IAudioEndpointVolume)
    is_muted = interface.GetMute()
    if is_muted == False:
        return False
    elif is_muted == True:
        return True
    CoUninitialize()

def speaker_muted():
    CoInitialize()
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None
    ).QueryInterface(IAudioEndpointVolume)
    is_muted = interface.GetMute()
    if is_muted == False:
        return False
    elif is_muted == True:
        return True
    CoUninitialize()

def update_config():
    change_config()

def change_appearance_mode_event(new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)      

frame_1 = customtkinter.CTkFrame(master=app)
frame_1.pack(pady=20, padx=60, fill="both", expand=True)

label_1 = customtkinter.CTkLabel(master=frame_1, justify=customtkinter.LEFT, font=customtkinter.CTkFont(family="bold", size=20), text="Hotkey Control Panel")
label_1.pack(pady=10, padx=10)

label_1 = customtkinter.CTkLabel(master=frame_1, justify=customtkinter.LEFT, font=customtkinter.CTkFont(family="bold", size=15), text="Microphone")
label_1.pack(pady=10, padx=10)

button_1 = customtkinter.CTkSegmentedButton(master=frame_1, command=microphone_callback)
button_1.pack(pady=10, padx=10)
button_1.configure(values=["Active", "Inactive"])
if microphone_muted() == False:
    button_1.set("Active")
else:
    button_1.set("Inactive")      

label_1 = customtkinter.CTkLabel(master=frame_1, justify=customtkinter.LEFT, font=customtkinter.CTkFont(family="bold", size=15), text="Speaker")
label_1.pack(pady=10, padx=10)

button_2 = customtkinter.CTkSegmentedButton(master=frame_1, command=speaker_callback)
button_2.pack(pady=10, padx=10)
button_2.configure(values=["Active", "Inactive"])
if speaker_muted() == False:
    button_2.set("Active")
else:
    button_2.set("Inactive")
    
label_1 = customtkinter.CTkLabel(master=frame_1, justify=customtkinter.LEFT, font=customtkinter.CTkFont(family="bold", size=15), text="Change hotkeys")
label_1.pack(pady=10, padx=10)    
    
optionmenu_1 = customtkinter.CTkOptionMenu(frame_1, values=["Mute microphone", "Mute speaker", "Exit programm"])
optionmenu_1.pack(pady=10, padx=10)
optionmenu_1.set("Select hotkey")
hotkey_option = optionmenu_1.get()    

entry_1 = customtkinter.CTkEntry(master=frame_1, placeholder_text="Enter keyboard-key")
entry_1.pack(pady=10, padx=10)
hotkey_key = entry_1.get()

button_3 = customtkinter.CTkButton(master=frame_1, command=update_config, text="Apply")
button_3.pack(pady=10, padx=10)

#switch_1 = customtkinter.CTkSwitch(master=frame_1)
#switch_1.pack(pady=10, padx=10)

label_2 = customtkinter.CTkLabel(master=frame_1, justify=customtkinter.LEFT, text_color="white", font=customtkinter.CTkFont(family="bold", size=15), text="Hotkeys")
label_2.pack(pady=10, padx=10)

text_1 = customtkinter.CTkTextbox(master=frame_1, width=400, height=120)
text_1.pack(pady=10, padx=10)
text_1.configure(state="disabled")
text_1._scrollbars_activated = False

label_2 = customtkinter.CTkLabel(master=frame_1, justify=customtkinter.LEFT, text_color="white", font=customtkinter.CTkFont(family="bold", size=15), text="Logs")
label_2.pack(pady=10, padx=10)

text_2 = customtkinter.CTkTextbox(master=frame_1, width=400, height=140)
text_2.pack(pady=10, padx=10)
text_2.configure(state="disabled")

appearance_mode_label = customtkinter.CTkLabel(master=frame_1, text="Appearance Mode:", anchor="w")
appearance_mode_label.pack(pady=10, padx=10)
appearance_mode_optionemenu = customtkinter.CTkOptionMenu(master=frame_1, values=["Light", "Dark", "System"], command=change_appearance_mode_event)
appearance_mode_optionemenu.pack(pady=10, padx=10)
appearance_mode_optionemenu.set("System")

#end ui

#config

def load_config():
    try:
        with open(config_path, 'r') as file:
            lines = file.readlines()
        config = {}
        for line in lines:
            key, value = line.strip().split('=')
            config[key] = value
        return config
    except FileNotFoundError:
        print_logs('Created new config file: ' + config_path)
        config = {
            'mute_microphone_key': '<',
            'mute_speaker_key': '>',
            'exit_programm': 'esc'
        }
        with open(config_path, 'w') as file:
            for key, value in config.items():
                file.write(f"{key}={value}\n")
        return config

config = load_config()
if not config:
    config = {
        'mute_microphone_key': '<',
        'mute_speaker_key': '>',
        'exit_programm': 'esc'
    }

mute_microphone_key = config.get('mute_microphone_key', '<')
mute_speaker_key = config.get('mute_speaker_key', '>')
exit_programm_key = config.get('exit_programm', 'esc')

#change config

def change_config():
    global hotkey_option, hotkey_key, mute_microphone_key, mute_speaker_key, exit_programm_key

    # Get the selected hotkey option and entered hotkey key
    hotkey_option = optionmenu_1.get()
    hotkey_key = entry_1.get()

    # Update the corresponding configuration key
    if hotkey_option.lower() == 'mute microphone':
        hotkey_option = "mute_microphone_key"
        mute_microphone_key = hotkey_key
    elif hotkey_option.lower() == 'mute speaker':
        hotkey_option = "mute_speaker_key"
        mute_speaker_key = hotkey_key
    elif hotkey_option.lower() == 'exit programm':
        print_logs("Exit programm Hotkey is still in development, sorry!" + "\n")
        return
    elif hotkey_option.lower() == 'select hotkey':
        print_logs("Invalid, please choose a option!" + "\n")
        return
        hotkey_option = "exit_programm"
        exit_programm_key = hotkey_key

    # Update the configuration dictionary
    config[hotkey_option.lower()] = hotkey_key

    # Save the updated configuration to the file
    with open(config_path, 'w') as file:
        for key, value in config.items():
            file.write(f"{key}={value}\n")

    print_logs(f"Config updated: {hotkey_option} set to {hotkey_key}\n")

    text_1.delete("0.0")
    dump_instruction()

                           
#microphone

def microphone():
    CoInitialize()
    devices = AudioUtilities.GetMicrophone()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None
    ).QueryInterface(IAudioEndpointVolume)
    is_muted = interface.GetMute()

    if is_muted == False:
        mute_microphone(interface)
    else:
        unmute_microphone(interface)    

def mute_microphone(interface):
    interface.SetMute(1, None)
    print_status_microphone("Microphone: ", "deactivated" + "\n")
    if microphone_muted() == False:
        button_1.set("Active")
    else:
        button_1.set("Inactive")  

def unmute_microphone(interface):
    interface.SetMute(0, None)
    print_status_microphone("Microphone: ", "activated  " + "\n")
    if microphone_muted() == False:
        button_1.set("Active")
    else:
        button_1.set("Inactive")

def print_status_microphone(prefix, status):
    print_logs(prefix + status)    

    CoUninitialize()   

#speaker    

def speaker():
    CoInitialize()
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None
    ).QueryInterface(IAudioEndpointVolume)
    is_muted = interface.GetMute()

    if is_muted == False:
        mute_speaker(interface)
    else:
        unmute_speaker(interface)        

def mute_speaker(interface):
    interface.SetMute(1, None)
    print_status_speaker("Speaker   : ", "deactivated" + "\n")
    if speaker_muted() == False:
        button_2.set("Active")
    else:
        button_2.set("Inactive")

def unmute_speaker(interface):
    interface.SetMute(0, None)
    print_status_speaker("Speaker   : ", "activated  " + "\n")
    if speaker_muted() == False:
        button_2.set("Active")
    else:
        button_2.set("Inactive")

def print_status_speaker(prefix, status):
    print_logs(prefix + status)                 

    CoUninitialize()  

def on_key_event(e):
    if e.event_type == keyboard.KEY_DOWN and e.name == mute_microphone_key:
        microphone()
    if e.event_type == keyboard.KEY_DOWN and e.name == mute_speaker_key:
        speaker()       

def keyboard_listener():
    while not app.protocol("WM_DELETE_WINDOW", app.destroy):
        keyboard.hook(on_key_event)
        #if button_1.get() == "Active":
        print_logs("Hotkey hook started" + "\n")
        keyboard.wait(exit_programm_key)
        #else:
            #return   

def dump_instruction():
    print_box('' + '\n')
    print_box('____________________________' + '\n')
    print_box('Mute microphone with "' + mute_microphone_key + '"' + '\n')
    print_box('Mute speakers with "' + mute_speaker_key + '"' + '\n')
    print_box('End programm with "' + exit_programm_key + '"' + " (Currently in development!)" + '\n')
    print_box('____________________________' + '\n')
    print_box('' + '\n')                

#main       

def main():

    print_logs('Hotkey script started!' + '\n')

    #dump instruction

    dump_instruction()

    #loop

    keyboard_thread = threading.Thread(target=keyboard_listener)
    keyboard_thread.start()
    app.mainloop()
    keyboard_thread.join()

if __name__ == "__main__":
    main()