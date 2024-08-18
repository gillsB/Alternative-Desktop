import sys
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QGridLayout, QVBoxLayout,  
                               QGraphicsView, QGraphicsScene, QDialog, QSizePolicy, QMessageBox, QMenu, QToolTip)
from PySide6.QtGui import QPixmap, QAction, QPainter, QBrush, QColor, QCursor, QMovie, QDrag
from PySide6.QtCore import Qt, QTimer, QEvent, QUrl, QMimeData, QMetaObject
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
import os

import subprocess
import shlex
from desktop_grid_menu import Menu
from run_menu_dialog import RunMenuDialog
from settings import get_setting
from config import (get_item_data, create_config_path, load_desktop_config, entry_exists, check_for_new_config, get_entry,
                    set_entry_to_default, is_default, swap_items_by_position, change_launch)





MAX_LABELS = None
MAX_ROWS = 20 #only used for now to get max_labels
MAX_COLS = 40
DATA_DIRECTORY = None
LABEL_SIZE = 64
LABEL_VERT_PAD = 64
DEFAULT_BORDER = "border 0px"
CONTEXT_OPEN = False
LABEL_TEXT_STYLESHEET = "QLabel { color : white }"
DRAG_ROW = None
DRAG_COL = None
AUTOGEN_ICON_SIZE = 128






class Grid(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(1.0)
        create_config_path()
        create_data_path()

        #main layout
        self.main_layout = QGridLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.load_video, self.load_image = self.background_setting()

        #QGraphicsView and QGraphicsScene
        self.view = QGraphicsView(self)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setStyleSheet("background: transparent;")
        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)

        self.video_item = QGraphicsVideoItem()
        self.scene.addItem(self.video_item)
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_item)
        self.media_player.mediaStatusChanged.connect(self.handle_media_status_changed)

        self.main_layout.addWidget(self.view, 0, 0)

        # grid_layout
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(0)
        self.main_layout.addLayout(self.grid_layout, 0, 0)

        self.labels = []

        # Set MAX_LABELS to the maximum amount of items you would need based on rows/cols
        MAX_LABELS = MAX_ROWS * MAX_COLS

        check_for_new_config()
        # Use MAX_COLS to differentiate when to add a new row.
        for i in range(MAX_LABELS):
            row = i // MAX_COLS
            col = i % MAX_COLS
            data = get_item_data(row, col)
            if data['icon_path'] == "":
                data['icon_path'] = "assets/images/blank.png"
            desktop_icon = DesktopIcon(
                row, 
                col, 
                data['name'], 
                data['icon_path'], 
                data['executable_path'], 
                data['command_args'], 
                data['website_link'], 
                data['launch_option']
            )
            label = ClickableLabel(desktop_icon, data['name'])
            self.labels.append(label)
            self.grid_layout.addWidget(label, row, col)

        self.render_bg()
        self.setAcceptDrops(True)

    def background_setting(self):
        bg_setting = get_setting("background_source")
        exists_video = os.path.exists("background.mp4")
        exists_image = os.path.exists("background.png")
        if bg_setting == "first_found":
            if exists_video:
                return True, False
            elif exists_image:
                return False, True
            return False, False
        elif bg_setting == "both":
            return exists_video, exists_image
        elif bg_setting == "video_only":
            return exists_video, False
        elif bg_setting == "image_only":
            return False, exists_image

        return False, False
    
    def render_bg(self):
        self.load_video, self.load_image = self.background_setting()
        if self.load_video:
            self.set_video_source("background.mp4")
        else:
            self.media_player.stop()  # Stop the playback
            self.media_player.setSource(QUrl())  # Clear the media source

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        position = self.mapFromParent(event.position().toPoint())
        new_widget = event.source()

        print(f"Drop position: {position}")
        print(f"Widget size: {self.size()}")

        new_row, new_col = self.findCellAtPosition(position)
        if new_row == None or new_col == None:
            QMessageBox.warning(self, "Drop Error",
                                    f"Error dropping item at position {position}.",
                                    QMessageBox.Ok)
            return
        print(f"Dropped at cell: ({new_row}, {new_col})")

        if isinstance(new_widget, ClickableLabel) and new_row is not None and new_col is not None:
            existing_widget = self.grid_layout.itemAtPosition(new_row, new_col).widget()
            if existing_widget:
                swap_items_by_position(DRAG_ROW, DRAG_COL, new_row, new_col)
                new_widget.render_icon()
                existing_widget.render_icon()
                event.acceptProposedAction()
        elif event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if new_row is not None and new_col is not None:
                label_widget = self.grid_layout.itemAtPosition(new_row, new_col).widget()
                if label_widget:
                    label_widget.drop_file_to_edit(urls)

        self.updateGeometries()
                
        

    #get row, col at position
    def findCellAtPosition(self, pos):
        visible_labels = [label for label in self.labels if not label.isHidden()]
        if not visible_labels:
            return None, None

        widget_rect = self.rect()
        visible_rows = max(label.desktop_icon.row for label in visible_labels) + 1
        visible_cols = max(label.desktop_icon.col for label in visible_labels) + 1

        cell_width = widget_rect.width() / visible_cols
        cell_height = widget_rect.height() / visible_rows

        row = int(pos.y() / cell_height)
        col = int(pos.x() / cell_width)

        for label in visible_labels:
            if label.desktop_icon.row == row and label.desktop_icon.col == col:
                return row, col

        return None, None
    
    def paintEvent(self, event):

        painter = QPainter(self)
        if self.load_image:
            self.background_pixmap = QPixmap("background.png")
            painter.drawPixmap(self.rect(), self.background_pixmap)
        else:
            # whole program is affected by setWindowOpacity() thus color does not need to be anything specific to be transparent.
            color = QColor(32, 32, 32) 
            painter.fillRect(self.rect(), color)
        
    def set_video_source(self, video_path):
        self.media_player.setSource(QUrl.fromLocalFile(video_path))
        self.media_player.play()
    
    def handle_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.media_player.setPosition(0)
            self.media_player.play()
    
    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.view.setGeometry(self.rect())
        self.scene.setSceneRect(self.rect())
        self.video_item.setSize(self.size())
        self.draw_labels()

    def draw_labels(self):
        window_width = self.frameGeometry().width()
        window_height = self.frameGeometry().height()

        self.num_columns = max(1, window_width // LABEL_SIZE)
        self.num_rows = max(1, window_height // (LABEL_SIZE + LABEL_VERT_PAD)) 

        print(f"window dimensions : {window_width}x{window_height}")
        print(f"window num_rows : {self.num_rows}")
        print(f"window num_cols : {self.num_columns}")

        for label in self.labels:
            row = label.desktop_icon.row
            col = label.desktop_icon.col

            if col < self.num_columns and row < self.num_rows:
                label.show()
            else:
                label.hide()
    
    def showEvent(self, event):
        super().showEvent(event)
        self.updateGeometries()

    def updateGeometries(self):
        self.grid_layout.update()
        self.updateGeometry()
        self.draw_labels()

    def pause_video(self):
        QMetaObject.invokeMethod(self.media_player, "pause", Qt.QueuedConnection)
    def play_video(self):
        QMetaObject.invokeMethod(self.media_player, "play", Qt.QueuedConnection)

class ClickableLabel(QLabel):
    def __init__(self, desktop_icon, text, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        
        #timer for right click on an icon (to not trigger launch programs on next left click)
        self.timer_right_click = QTimer()
        #timer for delaying a QToolTip on hovering over a desktop icon's name label
        self.timer_hover = QTimer()
        self.timer_hover.setSingleShot(True)
        self.timer_hover.timeout.connect(self.show_tooltip)
        
        self.desktop_icon = desktop_icon
        self.setFixedSize(LABEL_SIZE, LABEL_SIZE*1.75)
        self.setAlignment(Qt.AlignCenter)
        
        
        self.icon_label = QLabel(self)
        self.icon_label.setStyleSheet(DEFAULT_BORDER)
        self.icon_label.setFixedSize(LABEL_SIZE -2, LABEL_SIZE -2)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.set_icon(self.desktop_icon.icon_path)
        
        self.text_label = QLabel(text)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.text_label.setStyleSheet(LABEL_TEXT_STYLESHEET)

        # give it an EventFilter to detect mouseover
        self.text_label.installEventFilter(self)
        

        layout = QVBoxLayout(self)
        layout.addWidget(self.icon_label)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.addWidget(self.text_label)
        self.setLayout(layout)
        self.render_icon()
        self.movie = None

    def set_icon(self, icon_path):
        if isinstance(self.movie, QMovie):
            self.movie.stop()
            self.movie.deleteLater()
            self.movie = None

        if not os.path.isfile(icon_path):
            if entry_exists(self.desktop_icon.row, self.desktop_icon.col) and is_default(self.desktop_icon.row, self.desktop_icon.col) == False:
                icon_path = "assets/images/unknown.png"
            

        if icon_path.lower().endswith('.gif'):
            self.movie = QMovie(icon_path)
            self.movie.setScaledSize(self.icon_label.size())
            self.icon_label.setMovie(self.movie)
            self.movie.start()
        else:
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(LABEL_SIZE - 2, LABEL_SIZE - 2, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.icon_label.setPixmap(pixmap)
            else:
                # Pixmap invalid set icon to blank
                self.icon_label.setPixmap(QPixmap("assets/images/blank.png").scaled(LABEL_SIZE - 2, LABEL_SIZE - 2, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self.desktop_icon.icon_path == "assets/images/add.png":
            self.parent().media_player.pause()
            menu = Menu(None, parent=self)
            main_window_size = self.parent().size()
            dialog_width = main_window_size.width() / 2
            dialog_height = main_window_size.height() / 2
            menu.resize(dialog_width, dialog_height)
            
            menu.exec()
            self.parent().media_player.play()
        #if icon has an executable_path already (icon exists with path)
        elif event.button() == Qt.LeftButton:
            self.run_program()
            
    def mousePressEvent(self, event):
        global CONTEXT_OPEN,DRAG_ROW,DRAG_COL
        if event.button() == Qt.LeftButton:
            CONTEXT_OPEN = False
            DRAG_ROW = self.desktop_icon.row
            DRAG_COL = self.desktop_icon.col
            self.drag_start_position = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            #only drag if icon is not default
            if not (is_default(self.desktop_icon.row, self.desktop_icon.col)):
                drag = QDrag(self)
                mime_data = QMimeData()
                mime_data.setText(self.text_label.text())
                drag.setMimeData(mime_data)
                drag.setHotSpot(event.position().toPoint() - self.rect().topLeft())

                drop_action = drag.exec(Qt.MoveAction)

    def showContextMenu(self, pos):
            global CONTEXT_OPEN
            CONTEXT_OPEN = True
            context_menu = QMenu(self)

            self.edit_mode_icon()

            # Edit Icon section
            
            print(f"Row: {self.desktop_icon.row}, Column: {self.desktop_icon.col}, Name: {self.desktop_icon.name}, Icon_path: {self.desktop_icon.icon_path}, Exec Path: {self.desktop_icon.executable_path}, Command args: {self.desktop_icon.command_args}, Website Link: {self.desktop_icon.website_link}, Launch option: {self.desktop_icon.launch_option}")
            
            edit_action = QAction('Edit Icon', self)
            edit_action.triggered.connect(self.edit_triggered)
            context_menu.addAction(edit_action)

            context_menu.addSeparator()

            #Launch Options submenu section
            launch_options_sm = QMenu("Launch Options", self)
        
            action_names = [
                "Launch first found",
                "Prioritize Website links",
                "Ask upon launching",
                "Executable only",
                "Website Link only"
            ]
        
            for i, name in enumerate(action_names, start=0):
                action = QAction(name, self)
                action.triggered.connect(lambda checked, pos=i: self.update_launch(pos, self.desktop_icon.row, self.desktop_icon.col))
                action.setCheckable(True)
                action.setChecked(i ==  self.desktop_icon.launch_option)
                launch_options_sm.addAction(action)

            context_menu.addMenu(launch_options_sm)

            context_menu.addSeparator()

            # Launch executable or website section
            executable_action = QAction('Run Executable', self)
            executable_action.triggered.connect(self.run_executable)
            context_menu.addAction(executable_action)
            
            website_link_action = QAction('Open Website in browser', self)
            website_link_action.triggered.connect(self.run_website_link)
            context_menu.addAction(website_link_action)

            context_menu.addSeparator()

            #Open Icon and Executable section
            icon_path_action = QAction('Open Icon location', self)
            icon_path_action.triggered.connect(lambda: self.path_triggered(self.desktop_icon.icon_path))
            context_menu.addAction(icon_path_action)

            exec_path_action = QAction('Open Executable location', self)
            exec_path_action.triggered.connect(lambda: self.path_triggered(self.desktop_icon.executable_path))
            context_menu.addAction(exec_path_action)


            
            context_menu.addSeparator()

            delte_action = QAction('Delete Icon', self)
            delte_action.triggered.connect(self.delete_triggered)
            context_menu.addAction(delte_action)
            
            context_menu.aboutToHide.connect(self.context_menu_closed)
            context_menu.exec(self.mapToGlobal(pos))

    
    def context_menu_closed(self):
        print("Context menu closed without selecting any action")
        self.normal_mode_icon()
        self.timer_right_click.timeout.connect(self.context_close)
        self.timer_right_click.start(100) 


    def context_close(self):
        global CONTEXT_OPEN
        CONTEXT_OPEN = False
        self.timer_right_click.stop()
        self.timer_right_click.timeout.disconnect(self.context_close)

    def update_launch(self, launch_val, row, col):
        change_launch(launch_val, row, col)
        self.render_icon()

    def edit_triggered(self):
        self.parent().media_player.pause()
        menu = Menu(None, parent=self)
        main_window_size = self.parent().size()
        dialog_width = main_window_size.width() / 2
        dialog_height = main_window_size.height() / 2
        menu.resize(dialog_width, dialog_height)
        menu.exec()
        self.parent().media_player.play()
    def drop_file_to_edit(self, urls):
        self.parent().media_player.pause()
        menu = Menu(urls, parent=self)
        main_window_size = self.parent().size()
        dialog_width = main_window_size.width() / 2
        dialog_height = main_window_size.height() / 2
        menu.resize(dialog_width, dialog_height)
        menu.exec()
        self.parent().media_player.play()
    def path_triggered(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, "Path does not exist",
                                    f"File at location: {path}\n does not exist, please check the location.",
                                    QMessageBox.Ok)
            return
        # Open the folder and select the file in Explorer
        subprocess.run(['explorer', '/select,', os.path.normpath(path)])
    
    def delete_triggered(self):
        ret = QMessageBox.warning(self, "Delete Icon",
                                    f"Are you sure you wish to delete \"{self.desktop_icon.name}\" at: [{self.desktop_icon.row},{self.desktop_icon.col}]?",
                                    QMessageBox.Ok| QMessageBox.Cancel)
        if ret == QMessageBox.Ok:   
            set_entry_to_default(self.desktop_icon.row, self.desktop_icon.col)
            self.render_icon()

    

    #mouseover icon
    def enterEvent(self, event):
        if self.desktop_icon.icon_path == "assets/images/blank.png" or self.desktop_icon.icon_path == "" and is_default(self.desktop_icon.row, self.desktop_icon.col):
            self.set_icon_path("assets/images/add.png")

    #mouseover leaves the icon
    def leaveEvent(self, event):
        if self.desktop_icon.icon_path == "assets/images/add.png":
            self.set_icon_path("assets/images/blank.png")
    
    #mouseover the desktop_icon name
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            self.timer_hover.start(1000)
        elif event.type() == QEvent.Leave:
            self.timer_hover.stop()
            QToolTip.hideText()
        return super().eventFilter(obj, event)
    def show_tooltip(self):
        QToolTip.showText(QCursor.pos(), self.desktop_icon.name, self)
        
    def selected_border(self, percent):
        self.icon_label.setStyleSheet(f"border: {LABEL_SIZE * (percent/100)}px solid red;")

    def default_border(self):
        self.icon_label.setStyleSheet(DEFAULT_BORDER)

    def get_row(self):
        return self.desktop_icon.row
    def get_col(self):
        return self.desktop_icon.col
    def get_coord(self):
        return f"Row: {self.desktop_icon.row}, Column: {self.desktop_icon.col}"
    
    def set_name(self, new_name):
        self.desktop_icon.name = new_name
        self.text_label.setText(new_name)
        self.update()
    def set_icon_path(self, new_icon_path):
        self.desktop_icon.icon_path = new_icon_path
        self.set_icon(new_icon_path)
        self.icon_label.setStyleSheet(DEFAULT_BORDER)
    def set_executable_path(self, new_executable_path):
        self.desktop_icon.executable_path = new_executable_path
    def set_command_args(self, command_args):
        self.desktop_icon.command_args = command_args
    def set_website_link(self, website_link):
        self.desktop_icon.website_link = website_link
    def set_launch_option(self, launch_option):
        self.desktop_icon.launch_option = launch_option


    # returns base DATA_DIRECTORY/[row, col]
    def get_data_icon_dir(self):
        data_path = os.path.join(DATA_DIRECTORY, f'[{self.desktop_icon.row}, {self.desktop_icon.col}]')
        #make file if no file (new)
        if not os.path.exists(data_path):
            print("makedir")
            os.makedirs(data_path)
        print(f"get_data_icon_path: {data_path}")
        return data_path
    
    def get_autogen_icon_size(self):
        return AUTOGEN_ICON_SIZE
        


    #
    #
    # This is required to run in order for any client sided (non restart) edit to appear/work as normal
    #
    #
    def render_icon(self):
        entry = get_entry(self.desktop_icon.row, self.desktop_icon.col)
        if entry:
            self.set_name(entry['name'])
            self.set_icon_path(entry['icon_path'])
            self.set_executable_path(entry['executable_path'])
            self.set_command_args(entry['command_args'])
            self.set_website_link(entry['website_link'])
            self.set_launch_option(entry['launch_option'])
        else:
            self.set_name("")
            self.set_icon_path("")
            self.set_executable_path("")
            self.set_command_args("")
            self.set_website_link("")
            self.set_launch_option(0)
            

    
    #set icon into edit mode: red selected border, if icon is originally blank, set it to "add2.png"
    def edit_mode_icon(self):
        if self.desktop_icon.icon_path == "" or entry_exists(self.desktop_icon.row, self.desktop_icon.col) == False:
            self.set_icon_path("assets/images/add2.png")
        self.selected_border(10)
    
    #return icon into normal mode: (remove red select border) revert back to blank if icon was "add2.png"
    def normal_mode_icon(self):
        self.default_border()
        #revert add
        if self.get_icon_path() == "assets/images/add2.png":
            self.set_icon_path("assets/images/blank.png")

        self.render_icon()
    
    def get_icon_path(self):
        return self.desktop_icon.icon_path
    
    def run_program(self):
        launch_option_methods = {
            0: self.launch_first_found,
            1: self.launch_prio_web_link,
            2: self.launch_ask_upon_launching,
            3: self.launch_exec_only,
            4: self.launch_web_link_only,
        }

        launch_option = self.desktop_icon.launch_option
        method = launch_option_methods.get(launch_option, 0)
        success = method()
        
        if not success:
            QMessageBox.warning(self, "No Successful launch",
                                    f"No Successful launch detected, please check the icon's Executable path or Website Link",
                                    QMessageBox.Ok)
    
    def launch_first_found(self):
        print("launch option = 0")
        return self.run_executable() or self.run_website_link()
    def launch_prio_web_link(self):
        print("launch option = 1")
        return self.run_website_link() or self.run_executable()
    def launch_ask_upon_launching(self):
        print("launch option = 2")
        return self.choose_launch()
    def launch_exec_only(self):
        print("launch option = 3")
        return self.run_executable()
    def launch_web_link_only(self):
        print("launch option = 4")
        return self.run_website_link()

    def run_executable(self):
        #returns running = true if runs program, false otherwise
        running = False

        file_path = self.desktop_icon.executable_path
        args = shlex.split(self.desktop_icon.command_args)
        command = [file_path] + args

        

        #only bother trying to run file_path if it is not empty
        if file_path == "":
            return running
        
        #ensure path is an actual file that exists, display message if not
        try:
            if os.path.exists(file_path) == False:
                raise FileNotFoundError
        except FileNotFoundError:
            QMessageBox.warning(self, "Error Opening File",
                                    f"The file could not be opened.\nFile path:{self.desktop_icon.executable_path}\nPlease check that the file exists at the specified location.",
                                    QMessageBox.Ok)
            return running


        #file path exists and is not ""
        try:
            #if it is a .lnk file it is expected that the .lnk contains the command line arguments
            #upon which running os.startfile(file_path) runs the .lnk the same as just clicking it from a shortcut
            if file_path.lower().endswith('.lnk'):
                running = True
                os.startfile(file_path)
            else:
                try:

                    #when shell=True exceptions like FileNotFoundError are no longer raised but put into stderr
                    process = subprocess.Popen(command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                    running = True
                    stdout, stderr = process.communicate(timeout=0.5)
                    

                    text = stderr.decode('utf-8')
                    if "is not recognized as an internal or external command" in text:
                        running = False
                        
                        QMessageBox.warning(self, "Error Opening File",
                                    f"The file could not be opened.\nFile path:{self.desktop_icon.executable_path}\nPlease ensure there is a default application set to open this file type.",
                                    QMessageBox.Ok)
                    
                #kill the connection between this process and the subprocess we just launched.
                #this will not kill the subprocess but just set it free from the connection
                except Exception as e:
                    print("killing connection to new subprocess")
                    process.kill()

        except Exception as e:
            print(f"An error occurred: {e}")
        return running
        
    def run_website_link(self):
        print("run_web_link attempted")
        running = True
        url = self.desktop_icon.website_link

        if(url == ""): 
            running = False
            return running
        #append http:// to website to get it to open as a web link
        #for example google.com will not open as a link, but www.google.com, http://google.com, www.google.com all will, even http://google will open in the web browser (it just won't put you at google.com)
        elif not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        
        os.startfile(url)
        print(running)
        return running

    
    def choose_launch(self):
        
        print("Choose_launch called")
        self.run_menu_dialog = RunMenuDialog()
        if self.run_menu_dialog.exec() == QDialog.Accepted:
            result = self.run_menu_dialog.get_result()
            if result == 'run_executable':
                print("Run Executable button was clicked")
                return self.run_executable()

            elif result == 'open_website_link':
                print("Open Website Link button was clicked")
                return self.run_website_link()
        return True
        

class DesktopIcon:
    def __init__(self, row, col, name, icon_path, executable_path, command_args, website_link, launch_option):
        self.row = row
        self.col = col
        self.name = name
        self.icon_path = icon_path
        self.executable_path = executable_path
        self.command_args = command_args
        self.website_link = website_link
        self.launch_option = launch_option


#this would be passed by AlternativeDesktop.py or one of the main program files (settings.py etc.)
def create_data_path():

    global DATA_DIRECTORY
    app_data_path = os.path.join(os.getenv('APPDATA'), 'AlternativeDesktop')

    # Create app_data directory if it doesn't exist
    if not os.path.exists(app_data_path):
        os.makedirs(app_data_path)

    # Append /config/data.json to the AppData path
    data_path = os.path.join(app_data_path, 'data')
    if not os.path.exists(data_path):
        print("makedir")
        os.makedirs(data_path)
    
    DATA_DIRECTORY = data_path
