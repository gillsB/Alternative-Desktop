from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QMessageBox, QVBoxLayout, QLabel, QCheckBox, QDialog, QFormLayout, QLineEdit, QKeySequenceEdit, QDialogButtonBox, QSlider, QComboBox
from PySide6.QtCore import Qt, QEvent, QKeyCombination
from PySide6.QtGui import QIcon, QKeySequence
import sys
from pynput import keyboard
from settings import get_setting, set_setting, load_settings, save_settings, add_angle_brackets
from settingsMenu import SettingsDialog
from qt_material import apply_stylesheet
from desktop_grid import Grid
from hotkey_handler import HotkeyHandler



class OverlayWidget(QWidget):
    def __init__(self):
        super().__init__()
        #self.setAttribute(Qt.WA_TranslucentBackground)
        window_opacity = get_setting("window_opacity", -1)
        window_opacity = float(window_opacity/100)
        self.setWindowOpacity(window_opacity)
        self.setWindowTitle("Overlay Desktop")
        self.setGeometry(300, 300, 400, 200)

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.grid_widget = Grid()
        layout.addWidget(self.grid_widget)

        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(self.show_settings)
        

        self.closeButton = QPushButton("Close", self)
        self.closeButton.clicked.connect(self.close)
        

        layout.addWidget(settings_button)
        layout.addWidget(self.closeButton)

        self.theme_selector = QComboBox()
        self.theme_selector.addItems(['dark_amber.xml',
            'dark_blue.xml',
            'dark_cyan.xml',
            'dark_lightgreen.xml',
            'dark_pink.xml',
            'dark_purple.xml',
            'dark_red.xml',
            'dark_teal.xml',
            'dark_yellow.xml',
            'light_amber.xml',
            'light_blue.xml',
            'light_cyan.xml',
            'light_cyan_500.xml',
            'light_lightgreen.xml',
            'light_pink.xml',
            'light_purple.xml',
            'light_red.xml',
            'light_teal.xml',
            'light_yellow.xml'])
        self.theme_selector.currentIndexChanged.connect(self.on_theme_change)
        layout.addWidget(self.theme_selector)

        self.hotkey_handler = HotkeyHandler(self)
        self.hotkey_handler.toggle_signal.connect(self.toggle_window_state)

    def change_theme(self, theme_name):
        self.grid_widget.pause_video()
        QApplication.processEvents()
        if theme_name.startswith("dark"):
            apply_stylesheet(QApplication.instance(), theme=theme_name, invert_secondary=True, extra={'primaryTextColor': '#FFFFFF'})
        else:
            apply_stylesheet(QApplication.instance(), theme=theme_name, invert_secondary=True, extra={'primaryTextColor': '#000000'})
        self.grid_widget.play_video()

    def on_theme_change(self, index):
        theme_name = self.theme_selector.itemText(index)
        self.change_theme(theme_name)

    def show_settings(self):
        dialog = SettingsDialog(parent=self)
        dialog.exec()
    
    def change_opacity(self ,i):
        print("change_opacity = ")
        print(float(i/100))
        self.setWindowOpacity(float(i/100))

    def toggle_window_state(self):
        if self.isMinimized():
            # Restore to the last visible state
            if self.last_visible_state == Qt.WindowFullScreen:
                self.showFullScreen()
            elif self.last_visible_state == Qt.WindowMaximized:
                self.showMaximized()
            else:
                self.showNormal()
            self.grid_widget.play_video()
        else:
            # Save the current state before minimizing
            if self.isFullScreen():
                self.last_visible_state = Qt.WindowFullScreen
            elif self.isMaximized():
                self.last_visible_state = Qt.WindowMaximized
            else:
                self.last_visible_state = Qt.WindowNoState
            self.showMinimized()
            self.grid_widget.pause_video()
    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if not self.isMinimized():
                # Update last_visible_state when window state changes (except for minimization)
                if self.isFullScreen():
                    self.last_visible_state = Qt.WindowFullScreen
                elif self.isMaximized():
                    self.last_visible_state = Qt.WindowMaximized
                else:
                    self.last_visible_state = Qt.WindowNoState
        super().changeEvent(event)
    def set_hotkey(self):
        self.hotkey_handler.set_hotkey()
        
    

def main():
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_teal.xml', invert_secondary=True, extra={'primaryTextColor': '#FFFFFF'})
    overlay = OverlayWidget()
    overlay.setMinimumSize(100, 100)  
    overlay.resize(1760, 990)
    overlay.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()