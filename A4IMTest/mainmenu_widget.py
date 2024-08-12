# main_menu_widget.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap

class MainMenuWidget(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(50, 50, 50, 50)

        # Set flat white background
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor('white'))
        self.setPalette(palette)

        # Title Image
        title_image = QLabel()
        pixmap = QPixmap("images/A4IM Logo_pink.png")  # Replace with your image file name
        scaled_pixmap = pixmap.scaled(300, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        title_image.setPixmap(scaled_pixmap)
        title_image.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_image)

        # Slim grey line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet("""
            QFrame {
                border: none;
                background-color: #d9d9d9;
            }
        """)
        line.setFixedHeight(1)
        layout.addWidget(line)

        layout.addSpacing(50)  # Adjust this value to move buttons further down or up

        # Buttons
        buttons = [
            ("Construct", self.parent.show_system_view),
            ("User Docs", self.show_docs),
            ("About", self.show_about),
            ("Exit", self.parent.close)
        ]

        button_layout = QVBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)
        for text, callback in buttons:
            button = self.create_menu_button(text)
            button.clicked.connect(callback)
            button_layout.addWidget(button)

        layout.addLayout(button_layout)
        layout.addStretch()
        self.setLayout(layout)

    def create_menu_button(self, text):
        button = QPushButton(text)
        button.setFixedSize(250, 60)
        button.setFont(QFont('Arial', 14))
        button.setStyleSheet("""
            QPushButton {
                background-color: #465775;
                border: none;
                border-radius: 30px;
                color: white;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #566985;
            }
            QPushButton:pressed {
                background-color: #364765;
            }
        """)
        return button

    def show_docs(self):
        print("User Docs button clicked")

    def show_about(self):
        print("About button clicked")