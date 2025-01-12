from PyQt5.QtWidgets import QApplication, QLabel, QFileDialog, QLineEdit
from PyQt5.QtGui import QMovie, QPixmap, QCursor
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtCore import QObject, QEvent
import json
import sys
import os

class Overlay(QLabel):
    def __init__(self, file_path=None, custom_text=None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        
        self.movie = None
        self.dragging = False
        self.resizing = False
        self.offset = QPoint()
        self.resize_offset = QPoint()
        self.editing = False

        if file_path:
            if file_path.lower().endswith(".gif"):
                self.load_gif(file_path)
            elif file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                self.load_image(file_path)
            elif file_path.lower().endswith(".txt"):
                self.load_text(file_path)   
            else:
                print("Unsupported file type, trying to load as image.")
                self.load_image(file_path)
        elif custom_text:
            self.display_text(custom_text)
        else:
            print("No content found, exiting.")
            sys.exit()

    def load_gif(self, file_path):
        self.movie = QMovie(file_path)
        if self.movie.isValid():
            self.setMovie(self.movie)
            self.movie.start()
            self.movie.frameChanged.connect(self.adjust_size)
        else:
            print("Invalid or corrupted GIF, exiting.")
            sys.exit()

    def load_image(self, file_path):
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            self.setPixmap(pixmap)
            self.adjust_size()
        else:
            print("Can't load as image, trying to load as text file.")
            self.load_text(file_path)

    def load_text(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                text = file.read()
                self.display_text(text)
        except Exception as e:
            print(f"Error loading text file: {e}")
            sys.exit()

    def display_text(self, text):
        self.setText(text)
        self.setStyleSheet("color: white; background-color: black; font-size: 16px; padding: 10px;")
        self.setAlignment(Qt.AlignCenter)
        self.adjust_size()

    def adjust_size(self):
        if self.movie:
            self.resize(self.movie.currentPixmap().size())
        elif self.pixmap():
            self.resize(self.pixmap().size())
        elif self.text():
            self.adjustSize()

    def mouseDoubleClickEvent(self, event):
        if self.text() and not self.editing:
            self.start_editing()

    def mousePressEvent(self, event):
        #TODO: buggy
        if event.button() == Qt.LeftButton and not self.editing:
            rect = self.rect()
            bottom_right = rect.bottomRight()
            
            delta_x = bottom_right.x() - event.pos().x()
            delta_y = bottom_right.y() - event.pos().y()
            
            if delta_x < 10 and delta_y < 10:
                self.resizing = True
                self.resize_start_pos = event.pos()
                event.accept()
            else:
                self.dragging = True
                self.offset = event.globalPos() - self.pos()
                event.accept()


    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.offset)
            event.accept()

        if self.resizing:
            diff = event.pos() - self.resize_offset
            new_width = self.width() + diff.x()
            new_height = self.height() + diff.y()
            if new_width > 50 and new_height > 50:
                self.resize(new_width, new_height)
                self.resize_offset = event.pos()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.resizing = False
            event.accept()

    def start_editing(self):
        if not self.editing:
            self.editing = True
            self.edit_box = QLineEdit(self.text(), self)
            self.edit_box.setStyleSheet(self.styleSheet())
            self.edit_box.setGeometry(self.rect())
            self.edit_box.setAlignment(Qt.AlignCenter)
            self.edit_box.setFocus()
            self.edit_box.returnPressed.connect(self.finish_editing)
            self.edit_box.show()

    def finish_editing(self):
        if self.editing:
            self.setText(self.edit_box.text())
            self.edit_box.deleteLater()
            self.editing = False
            self.adjust_size()

    def cancel_editing(self):
        if self.editing:
            self.finish_editing()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.editing:
            self.cancel_editing()
            event.accept()
        elif event.key() == Qt.Key_Escape:
            #print("Cursor Position:", QCursor.pos())
            #print("Overlay Global Position:", self.pos())
            
            overlay_rect = self.rect() 
            overlay_rect.moveTopLeft(self.pos()) 
            
            if overlay_rect.contains(QCursor.pos()):
                print("ESC pressed while cursor on overlay, exiting...")
                self.close()
                event.accept()
                sys.exit()    
            else:
                #print("ESC pressed, but mouse not above overlay.")
                super().keyPressEvent(event)
 

class GlobalEventFilter(QObject):
    def __init__(self, overlay):
        super().__init__()
        self.overlay = overlay

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if not self.overlay.geometry().contains(event.globalPos()):
                self.overlay.cancel_editing()
        return False

def get_config_path():
    appdata_path = os.getenv('APPDATA')
    config_dir = os.path.join(appdata_path, "OverlayApp")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "config.json")

def load_config():
    config_path = get_config_path()
    if os.path.exists(config_path):
        with open(config_path, "r") as file:
            return json.load(file)
    return {}

def save_config(data):
    config_path = get_config_path()
    with open(config_path, "w") as file:
        json.dump(data, file)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    config = load_config()

    select = True
    if len(sys.argv) > 1:
        select = sys.argv[1].lower() == 'true'
        
    custom_text = "Standart text! \n Doubleclick to edit. \n ESC to stop editing. \n (File not found?)"
    file_paths = []

    if select:
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(
            None, "Choose files", "", 
            "All supported files (*.gif *.png *.jpg *.jpeg *.bmp *.txt);;All files (*)"
        )
        if file_paths:
            config["file_paths"] = file_paths
            save_config(config)
        else:
            sys.exit("No files selected.")
    else:
        file_paths = config.get("file_paths", [])

    overlays = []
    for file_path in file_paths:
        if os.path.exists(file_path):
            overlays.append(Overlay(file_path=file_path))
        else:
            overlays.append(Overlay(custom_text=custom_text))

    for overlay in overlays:
        event_filter = GlobalEventFilter(overlay)
        app.installEventFilter(event_filter)
        overlay.show()

    sys.exit(app.exec_())
