import requests
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QTimer, QUrl

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
        
        self.web_view = QWebEngineView()
        
        back_button = QPushButton("Back")
        back_button.clicked.connect(self.go_back)
        
        layout.addWidget(self.web_view)
        layout.addWidget(back_button)
        
        self.setLayout(layout)

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
