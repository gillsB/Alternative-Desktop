from PySide6.QtCore import Qt, Property, QPropertyAnimation, QEasingCurve, QPointF
from PySide6.QtWidgets import (QGraphicsWidget, QGraphicsProxyWidget, QPushButton, QGraphicsRectItem,
                              QVBoxLayout, QWidget)
from PySide6.QtGui import QIcon
import logging

logger = logging.getLogger(__name__)
IS_HOVERED = False

# Parent passed is Desktop.py NOT desktop_grid where it is created.
class Shelf(QGraphicsWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.is_open = False
        self._content_width = 250
        self.parent = parent
        self.hide_after_close = False
        
        # Create the toggle button
        button_widget = QWidget()
        self.toggle_button = QPushButton()
        self.toggle_button.setIcon(QIcon.fromTheme("go-previous"))
        self.toggle_button.setFixedSize(30, 80)
        button_layout = QVBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(self.toggle_button)
        
        # Create a proxy for the button
        self.button_proxy = QGraphicsProxyWidget(self)
        self.button_proxy.setWidget(button_widget)

        # Create content widget
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        
        settings_button = QPushButton("Settings Menu")
        content_layout.addWidget(settings_button)
        content_layout.addStretch()
        settings_button.clicked.connect(self.settings_button_clicked)
        
        # Create a proxy for the content
        self.content_proxy = QGraphicsProxyWidget(self)
        self.content_proxy.setWidget(self.content_widget)
        self.content_proxy.setMinimumWidth(0)
        self.content_proxy.setMaximumWidth(0)
        
        # Position content to the right of button at the same height
        button_width = self.button_proxy.size().width()
        self.content_proxy.setPos(button_width, 0)  # Same vertical position as button

        # Connect the button to toggle action
        self.toggle_button.clicked.connect(self.toggle_shelf)

        # Set up animation for content
        self.content_animation = QPropertyAnimation(self, b"content_width")
        self.content_animation.setDuration(300)
        self.content_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.content_animation.finished.connect(self.update_content_position)
        
        # Set up animation for shelf position
        self.shelf_animation = QPropertyAnimation(self, b"pos")
        self.shelf_animation.setDuration(300)
        self.shelf_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.shelf_animation.finished.connect(self.animation_finished)

        self.setAcceptHoverEvents(True)
        self.center_y = 0
        self.setZValue(2)

    def get_content_width(self):
        return self.content_proxy.size().width()

    def set_content_width(self, width):
        self.content_proxy.setMinimumWidth(width)
        self.content_proxy.setMaximumWidth(width)
        self.update_content_position()

    content_width = Property(int, get_content_width, set_content_width)
    
    def update_content_position(self):
        # Position content to the right of button at the same vertical position
        button_width = self.button_proxy.size().width()
        self.content_proxy.setPos(button_width, 0)
    
    def position_at_right(self, view_width, view_height):
        button_width = self.button_proxy.size().width()
        content_width = self.content_proxy.size().width()
        
        self.center_y = (view_height - self.button_proxy.size().height()) / 2

        if not self.is_open:
            self.setPos(view_width - button_width, self.center_y)
        else:
            self.setPos(view_width - button_width - content_width, self.center_y)

        self.update_content_position()

    def show_button(self, show):
        if show or self.is_open:
            self.show()
        else:
            self.hide()

    def close_shelf(self, hide = None):
        print(f"called with hide = {hide}")
        if self.is_open:
            scene = self.scene()
            view = scene.views()[0]
            view_width = view.viewport().width()
            current_pos_x = self.pos().x()
            button_width = self.button_proxy.size().width()
            target_pos_x = view_width - button_width

            self.shelf_animation.setStartValue(QPointF(current_pos_x, self.center_y))
            self.shelf_animation.setEndValue(QPointF(target_pos_x, self.center_y))

            self.content_animation.setStartValue(self.content_proxy.size().width())
            self.content_animation.setEndValue(0)

            self.toggle_button.setIcon(QIcon.fromTheme("go-previous"))

            self.is_open = False
            self.hide_after_close = hide
            # Start both animations
            self.shelf_animation.start()
            self.content_animation.start()
            logger.info("Closed shelf")
            
        else:
            logger.error("Attempted to close shelf when shelf is closed")

    def open_shelf(self):
        if not self.is_open:
            self.parent().grid_widget.pause_video()
            scene = self.scene()
            view = scene.views()[0]
            view_width = view.viewport().width()
            current_pos_x = self.pos().x()
            target_pos_x = view_width - self._content_width - self.button_proxy.size().width()

            self.shelf_animation.setStartValue(QPointF(current_pos_x, self.center_y))
            self.shelf_animation.setEndValue(QPointF(target_pos_x, self.center_y))

            self.content_animation.setStartValue(0)
            self.content_animation.setEndValue(self._content_width)

            self.toggle_button.setIcon(QIcon.fromTheme("go-next"))

            self.is_open = True

            # Start both animations
            self.shelf_animation.start()
            self.content_animation.start()
            logger.info("Opened shelf")
        else:
            logger.error("Attempted to open shelf that is open")

    def toggle_shelf(self):
        # Get the view width from parent scene and view
        scene = self.scene()
        if scene and len(scene.views()) > 0:
            if not self.is_open:
                self.open_shelf()
            else:
                self.close_shelf()
        else:
            logger.error(f"Critical error: scene not found or no view: {scene}, {len(scene.views())}. Aborting shelf toggle.")

    def animation_finished(self):
        # When the shelf is closed
        if not self.is_open:
            # Call to hide button if NOT hovering over ShelfHoverItem. Otherwise leave it showing.
            if not IS_HOVERED:
                self.show_button(False)
            self.parent().grid_widget.play_video()
            

    def settings_button_clicked(self):
        self.close_shelf(hide=True)
        self.parent().show_settings()



class ShelfHoverItem(QGraphicsRectItem):
    def __init__(self, width, height, shelf: Shelf, parent=None):
        super().__init__(0, 0, width, height)
        self.shelf = shelf 
        self.setBrush(Qt.transparent)  # Make the inside invisible/transparent
        #self.setPen(QPen(Qt.transparent))  # Eventually this will be transparent.
        self.setAcceptHoverEvents(True)
        self.width = width
        self.height = height
        self.setZValue(1)

    def hoverMoveEvent(self, event):
        global IS_HOVERED
        if not IS_HOVERED:
            IS_HOVERED = True
        super().hoverMoveEvent(event)

    def hoverEnterEvent(self, event):
        global IS_HOVERED
        IS_HOVERED = True
        self.shelf.show_button(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        global IS_HOVERED
        item_area = self.boundingRect()
        event_pos = event.pos()

        # Add a small margin to the item bounding rect to avoid small overlaps triggering .contains()
        margin = 5
        adjusted_item_area = item_area.adjusted(margin, margin, -margin, -margin)
        
        if not adjusted_item_area.contains(event_pos):
            IS_HOVERED = False
            self.shelf.show_button(False)
        else:
            # Only case where this should occur is when hovering over the shelf button/shelf item.
            pass
            
        super().hoverLeaveEvent(event)

    def updatePosition(self, view_width, view_height):
        width = (self.width * view_width) / 100
        height = (self.height * view_height) / 100

        self.setRect(0, 0, width, height)
        vertical_offset = (view_height - height) / 2
        self.setPos(view_width - width, vertical_offset)

    def is_mouse_in_hover_area(self, event):
        event_pos = self.mapFromScene(event.pos())  # Convert event position to local coordinates

        item_area = self.boundingRect()
        button_area = self.shelf.button_proxy.boundingRect()
        return item_area.contains(event_pos) or button_area.contains(event_pos)