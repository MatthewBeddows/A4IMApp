import sys
import os
import pygit2
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                            QListWidget, QPushButton, QLabel, QMessageBox)
import requests

class RepositorySelector(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Repository Selector")
        self.setGeometry(100, 100, 600, 400)
        
        # Initialize projects dictionary
        self.projects = {}
        
        # Always fetch the latest project list
        self.fetch_project_list()

        # Setup the window
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Add a nice header
        header = QLabel("Select a Project Repository:")
        layout.addWidget(header)

        # List where I can select my project
        self.project_list = QListWidget()
        self.update_list_widget()
        layout.addWidget(self.project_list)

        # Button to load it up
        load_button = QPushButton("Load Selected Project")
        load_button.clicked.connect(self.load_project)
        layout.addWidget(load_button)

        # Add refresh button
        refresh_button = QPushButton("Refresh Project List")
        refresh_button.clicked.connect(self.refresh_list)
        layout.addWidget(refresh_button)

    def update_list_widget(self):
        """Update the QListWidget with current projects"""
        self.project_list.clear()
        print("Current projects:", list(self.projects.keys()))
        self.project_list.addItems(self.projects.keys())

    def fetch_project_list(self):
        try:
            # Clear existing projects
            self.projects.clear()
            print("Cleared projects dictionary")
            
            # Force fetch the latest version
            # Note: Still using the same GitHub repo as before
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
                
                # Check for project name (using same format as before)
                if line.startswith('[architectName]'):
                    project_name = line.replace('[architectName]', '').strip()
                    
                    # Look ahead for URL on next line
                    if i + 1 < len(lines) and lines[i + 1].startswith('[url]'):
                        url = lines[i + 1].replace('[url]', '').strip()
                        self.projects[project_name] = {
                            "url": url,
                            "folder": project_name
                        }
                        print(f"Added project: {project_name} with URL: {url}")
                        i += 2  # Skip the next line since we've processed it
                    else:
                        print(f"Skipping invalid entry - no URL found for {project_name}")
                        i += 1
                else:
                    print(f"Skipping invalid line: {line}")
                    i += 1
            
            print("Final projects dictionary:", self.projects)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading Project List",
                f"Failed to load project list: {str(e)}\nPlease check your internet connection and try again."
            )
            self.close()

    def refresh_list(self):
        """Manually refresh the project list"""
        print("Refreshing list...")
        self.fetch_project_list()
        self.update_list_widget()

    def load_project(self):
        # Get what I selected
        selected_item = self.project_list.currentItem()
        if selected_item:
            # Grab the URL and folder name for the selected project
            selected = self.projects[selected_item.text()]
            # Hide this window
            self.hide()
            
            # Import here to avoid circular imports
            from main import GitFileReaderApp
            
            # Fire up the main app with my chosen project
            self.main_window = GitFileReaderApp(selected["url"], selected["folder"])
            self.main_window.show()