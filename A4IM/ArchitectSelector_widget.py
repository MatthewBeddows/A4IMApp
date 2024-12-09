import sys
import os
import git
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QListWidget, QPushButton, QLabel)

class ArchitectSelector(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Architect Repository Selector")
        self.setGeometry(100, 100, 600, 400)

        # Define my architect repos and their folder names
        self.architects = {
            "A4IM Project Architect": {
                "url": "https://github.com/MatthewBeddows/A4IM-ProjectArchitect.git",
                "folder": "A4IM Project Architect"  # This folder will replace ArchitectRepository
            },
            "COSI Architect": {
                "url": "https://github.com/MatthewBeddows/COSI-Architect",
                "folder": "COSI Architect"  # This folder will replace ArchitectRepository
            }
        }

        # Setup the window
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Add a nice header
        header = QLabel("Select an Architect Repository:")
        layout.addWidget(header)

        # List where I can select my architect
        self.architect_list = QListWidget()
        self.architect_list.addItems(self.architects.keys())
        layout.addWidget(self.architect_list)

        # Button to load it up
        load_button = QPushButton("Load Selected Architect")
        load_button.clicked.connect(self.load_architect)
        layout.addWidget(load_button)

    def load_architect(self):
        # Get what I selected
        selected_item = self.architect_list.currentItem()
        if selected_item:
            # Grab the URL and folder name for the selected architect
            selected = self.architects[selected_item.text()]
            # Hide this window
            self.hide()
            # Fire up the main app with my chosen architect
            from main import GitFileReaderApp
            self.main_window = GitFileReaderApp(selected["url"], selected["folder"])
            self.main_window.show()