import requests
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QTimer, QUrl, Qt
from PyQt5.QtGui import QFont, QColor, QPalette

class GitBuildingWindow(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.current_system = None
        self.current_module = None
        self.setup_ui()
        
        self.retry_timer = QTimer()
        self.retry_timer.timeout.connect(self.load_web_content)

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Set flat white background
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor('white'))
        self.setPalette(palette)

        # # Title
        # title_label = QLabel("Git Building")
        # title_label.setFont(QFont('Arial', 16, QFont.Bold))
        # title_label.setStyleSheet("color: #465775;")
        # layout.addWidget(title_label)

        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
        
        back_button = self.create_button("Back")
        back_button.clicked.connect(self.go_back)
        
        layout.addWidget(back_button)
        
        self.setLayout(layout)

    def create_button(self, text):
        button = QPushButton(text)
        button.setFixedHeight(40)
        button.setFont(QFont('Arial', 12))
        button.setStyleSheet("""
            QPushButton {
                background-color: #465775;
                border: none;
                border-radius: 20px;
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

    def go_back(self):
        if self.parent and self.current_system:
            self.parent.show_module_view(self.current_system)

    def load_module(self, system, module):
        self.current_system = system
        self.current_module = module
        self.load_web_content()

    def load_web_content(self):
        url = "http://localhost:6178/live/editor1/"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                self.web_view.setUrl(QUrl(url))
                self.retry_timer.stop()
            else:
                self.retry_timer.start(5000)  # Retry every 5 seconds
        except requests.RequestException:
            self.retry_timer.start(5000)  # Retry every 5 seconds