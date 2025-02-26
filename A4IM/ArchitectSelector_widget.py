import sys
import os
import pygit2
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QListWidget, QPushButton, QLabel, QMessageBox)
import requests

class ArchitectSelector(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Architect Repository Selector")
        self.setGeometry(100, 100, 600, 400)
        
        # Initialize architects dictionary
        self.architects = {}
        
        # Always fetch the latest architect list
        self.fetch_architect_list()

        # Setup the window
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Add a nice header
        header = QLabel("Select an Architect Repository:")
        layout.addWidget(header)

        # List where I can select my architect
        self.architect_list = QListWidget()
        self.update_list_widget()
        layout.addWidget(self.architect_list)

        # Button to load it up
        load_button = QPushButton("Load Selected Architect")
        load_button.clicked.connect(self.load_architect)
        layout.addWidget(load_button)

        # Add refresh button
        refresh_button = QPushButton("Refresh Architect List")
        refresh_button.clicked.connect(self.refresh_list)
        layout.addWidget(refresh_button)

    def update_list_widget(self):
        """Update the QListWidget with current architects"""
        self.architect_list.clear()
        print("Current architects:", list(self.architects.keys()))
        self.architect_list.addItems(self.architects.keys())

    def fetch_architect_list(self):
        try:
            # Clear existing architects
            self.architects.clear()
            print("Cleared architects dictionary")
            
            # Force fetch the latest version
            url = "https://raw.githubusercontent.com/MatthewBeddows/ArchitectList/main/architectList.txt"
            headers = {'Cache-Control': 'no-cache', 'Pragma': 'no-cache'}
            response = requests.get(url, headers=headers, verify=True)
            response.raise_for_status()
            
            print("Raw content from GitHub:", response.text)
            
            # Parse the content with stricter rules
            lines = [line.strip() for line in response.text.split('\n') if line.strip()]
            
            i = 0
            while i < len(lines):
                line = lines[i]
                print(f"Processing line: {line}")
                
                # Check for architect name
                if line.startswith('[architectName]'):
                    architect_name = line.replace('[architectName]', '').strip()
                    
                    # Look ahead for URL on next line
                    if i + 1 < len(lines) and lines[i + 1].startswith('[url]'):
                        url = lines[i + 1].replace('[url]', '').strip()
                        self.architects[architect_name] = {
                            "url": url,
                            "folder": architect_name
                        }
                        print(f"Added architect: {architect_name} with URL: {url}")
                        i += 2  # Skip the next line since we've processed it
                    else:
                        print(f"Skipping invalid entry - no URL found for {architect_name}")
                        i += 1
                else:
                    print(f"Skipping invalid line: {line}")
                    i += 1
            
            print("Final architects dictionary:", self.architects)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading Architect List",
                f"Failed to load architect list: {str(e)}\nPlease check your internet connection and try again."
            )
            self.close()

    def refresh_list(self):
        """Manually refresh the architect list"""
        print("Refreshing list...")
        self.fetch_architect_list()
        self.update_list_widget()

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