import sys
import os
import pygit2
import re
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QListWidget, QPushButton, QLabel, QMessageBox, 
                            QLineEdit, QGroupBox, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import requests

class RepositorySelector(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Repository Selector")
        self.setGeometry(100, 100, 700, 500)
        
        # Initialize projects dictionary
        self.projects = {}
        self.custom_repos_file = "custom_repositories.txt"
        
        # Load custom repositories first
        self.load_custom_repositories()
        
        # Then fetch the latest project list from GitHub
        self.fetch_project_list()

        # Setup the window
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Add a nice header
        header = QLabel("Select a Project Repository:")
        header.setFont(QFont('Arial', 14, QFont.Bold))
        layout.addWidget(header)

        # Group box for repository list
        list_group = QGroupBox("Available Repositories")
        list_layout = QVBoxLayout(list_group)
        
        # List where users can select their project
        self.project_list = QListWidget()
        self.project_list.setMinimumHeight(200)
        self.update_list_widget()
        list_layout.addWidget(self.project_list)
        
        # Buttons for list operations
        list_buttons_layout = QHBoxLayout()
        
        load_button = QPushButton("Load Selected Project")
        load_button.clicked.connect(self.load_project)
        list_buttons_layout.addWidget(load_button)
        
        refresh_button = QPushButton("Refresh Project List")
        refresh_button.clicked.connect(self.refresh_list)
        list_buttons_layout.addWidget(refresh_button)
        
        remove_button = QPushButton("Remove Custom Repository")
        remove_button.clicked.connect(self.remove_custom_repository)
        list_buttons_layout.addWidget(remove_button)
        
        list_layout.addLayout(list_buttons_layout)
        layout.addWidget(list_group)

        # Add separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Group box for adding custom repository
        custom_group = QGroupBox("Add Custom Repository")
        custom_layout = QVBoxLayout(custom_group)
        
        # Input field for custom repository URL
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Repository URL:"))
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://github.com/username/repo or https://gitlab.com/username/repo")
        self.url_input.returnPressed.connect(self.add_custom_repository)
        url_layout.addWidget(self.url_input)
        
        custom_layout.addLayout(url_layout)
        
        # Input field for custom name (optional)
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Display Name (optional):"))
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Leave empty to use repository name")
        self.name_input.returnPressed.connect(self.add_custom_repository)
        name_layout.addWidget(self.name_input)
        
        custom_layout.addLayout(name_layout)
        
        # Button to add custom repository
        add_button = QPushButton("Add Custom Repository")
        add_button.clicked.connect(self.add_custom_repository)
        custom_layout.addWidget(add_button)
        
        layout.addWidget(custom_group)

    def update_list_widget(self):
        """Update the QListWidget with current projects"""
        self.project_list.clear()
        print("Current projects:", list(self.projects.keys()))
        
        # Sort projects to show custom ones with a prefix
        sorted_projects = []
        for name, data in self.projects.items():
            if data.get('is_custom', False):
                sorted_projects.append(f"[Custom] {name}")
            else:
                sorted_projects.append(name)
        
        self.project_list.addItems(sorted_projects)

    def load_custom_repositories(self):
        """Load custom repositories from local file"""
        if not os.path.exists(self.custom_repos_file):
            return
            
        try:
            with open(self.custom_repos_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            if not content:
                return
                
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                if line.startswith('[customName]'):
                    project_name = line.replace('[customName]', '').strip()
                    
                    # Look for URL on next line
                    if i + 1 < len(lines) and lines[i + 1].startswith('[url]'):
                        url = lines[i + 1].replace('[url]', '').strip()
                        
                        # Look for folder name on next line (optional)
                        folder_name = project_name
                        if i + 2 < len(lines) and lines[i + 2].startswith('[folder]'):
                            folder_name = lines[i + 2].replace('[folder]', '').strip()
                            i += 3
                        else:
                            i += 2
                            
                        self.projects[project_name] = {
                            "url": url,
                            "folder": folder_name,
                            "is_custom": True
                        }
                        print(f"Loaded custom repository: {project_name} with URL: {url}")
                    else:
                        i += 1
                else:
                    i += 1
                    
        except Exception as e:
            print(f"Error loading custom repositories: {e}")

    def save_custom_repositories(self):
        """Save custom repositories to local file"""
        try:
            custom_repos = {name: data for name, data in self.projects.items() 
                          if data.get('is_custom', False)}
            
            with open(self.custom_repos_file, 'w', encoding='utf-8') as f:
                for name, data in custom_repos.items():
                    f.write(f"[customName]{name}\n")
                    f.write(f"[url]{data['url']}\n")
                    f.write(f"[folder]{data['folder']}\n")
                    f.write("\n")
                    
            print(f"Saved {len(custom_repos)} custom repositories")
            
        except Exception as e:
            print(f"Error saving custom repositories: {e}")
            QMessageBox.warning(self, "Save Error", f"Failed to save custom repositories: {str(e)}")

    def validate_git_url(self, url):
        """Validate that the URL is a valid Git repository URL (GitHub or GitLab)"""
        # Support both GitHub and GitLab URLs
        github_pattern = r'^https://github\.com/[^/]+/[^/]+/?$'
        gitlab_pattern = r'^https://gitlab\.com/[^/]+/[^/]+/?$'
        
        url_clean = url.rstrip('/')
        return (re.match(github_pattern, url_clean) is not None or 
                re.match(gitlab_pattern, url_clean) is not None)

    def extract_repo_name(self, url):
        """Extract repository name from GitHub or GitLab URL"""
        try:
            # Remove trailing slash and split
            parts = url.rstrip('/').split('/')
            return parts[-1]  # Last part is the repo name
        except:
            return None

    def add_custom_repository(self):
        """Add a custom repository from user input"""
        url = self.url_input.text().strip()
        custom_name = self.name_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Input Error", "Please enter a repository URL.")
            return
            
        # Validate URL
        if not self.validate_git_url(url):
            QMessageBox.warning(self, "Invalid URL", 
                              "Please enter a valid GitHub or GitLab repository URL.\n"
                              "Examples:\n"
                              "https://github.com/username/repository\n"
                              "https://gitlab.com/username/repository")
            return
        
        # Extract repository name for folder and default display name
        repo_name = self.extract_repo_name(url)
        if not repo_name:
            QMessageBox.warning(self, "URL Error", "Could not extract repository name from URL.")
            return
            
        # Use custom name if provided, otherwise use repo name
        display_name = custom_name if custom_name else repo_name
        
        # Check if this repository already exists
        if display_name in self.projects:
            reply = QMessageBox.question(self, "Repository Exists", 
                                       f"Repository '{display_name}' already exists. "
                                       "Do you want to update it?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        
        # Verify the repository exists by making a simple request
        try:
            # Check if the repository is accessible
            if 'github.com' in url:
                # GitHub API check
                api_url = url.replace('github.com', 'api.github.com/repos')
                response = requests.get(api_url, timeout=10)
            elif 'gitlab.com' in url:
                # GitLab API check - extract project path and use GitLab API
                # Format: https://gitlab.com/username/project -> username%2Fproject
                path_parts = url.replace('https://gitlab.com/', '').rstrip('/').split('/')
                if len(path_parts) >= 2:
                    project_path = '%2F'.join(path_parts)  # URL encode the forward slashes
                    api_url = f"https://gitlab.com/api/v4/projects/{project_path}"
                    response = requests.get(api_url, timeout=10)
                else:
                    raise requests.RequestException("Invalid GitLab URL format")
            else:
                raise requests.RequestException("Unsupported repository host")
            
            if response.status_code == 404:
                QMessageBox.warning(self, "Repository Not Found", 
                                  "The repository does not exist or is not publicly accessible.")
                return
            elif response.status_code != 200:
                # Ask user if they want to continue anyway
                reply = QMessageBox.question(self, "Repository Access", 
                                           f"Could not verify repository access (HTTP {response.status_code}). "
                                           "Do you want to add it anyway?",
                                           QMessageBox.Yes | QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return
                    
        except requests.RequestException as e:
            # Ask user if they want to continue without verification
            reply = QMessageBox.question(self, "Network Error", 
                                       f"Could not verify repository due to network error: {str(e)}\n"
                                       "Do you want to add it anyway?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        
        # Add the repository
        self.projects[display_name] = {
            "url": url,
            "folder": repo_name,  # Use actual repo name for folder
            "is_custom": True
        }
        
        # Save to file
        self.save_custom_repositories()
        
        # Update the list
        self.update_list_widget()
        
        # Clear input fields
        self.url_input.clear()
        self.name_input.clear()
        
        # Select the newly added repository
        items = self.project_list.findItems(f"[Custom] {display_name}", Qt.MatchExactly)
        if items:
            self.project_list.setCurrentItem(items[0])
        
        QMessageBox.information(self, "Success", f"Repository '{display_name}' added successfully!")

    def remove_custom_repository(self):
        """Remove selected custom repository"""
        selected_item = self.project_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Selection Error", "Please select a repository to remove.")
            return
            
        selected_text = selected_item.text()
        
        # Extract the actual project name
        if selected_text.startswith("[Custom] "):
            project_name = selected_text.replace("[Custom] ", "")
        else:
            QMessageBox.warning(self, "Remove Error", "You can only remove custom repositories.")
            return
            
        # Confirm removal
        reply = QMessageBox.question(self, "Confirm Removal", 
                                   f"Are you sure you want to remove '{project_name}' from your custom repositories?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Remove from projects
            if project_name in self.projects:
                del self.projects[project_name]
                
                # Save updated list
                self.save_custom_repositories()
                
                # Update UI
                self.update_list_widget()
                
                QMessageBox.information(self, "Success", f"Repository '{project_name}' removed successfully!")

    def fetch_project_list(self):
        try:
            # Force fetch the latest version from GitHub
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
                        
                        # Only add if not already a custom repository
                        if project_name not in self.projects:
                            self.projects[project_name] = {
                                "url": url,
                                "folder": project_name,
                                "is_custom": False
                            }
                            print(f"Added project: {project_name} with URL: {url}")
                        else:
                            print(f"Skipping {project_name} - already exists as custom repository")
                            
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

    def refresh_list(self):
        """Manually refresh the project list"""
        print("Refreshing list...")
        # Preserve custom repositories
        custom_repos = {name: data for name, data in self.projects.items() 
                       if data.get('is_custom', False)}
        
        # Clear and reload
        self.projects.clear()
        self.projects.update(custom_repos)
        
        # Fetch updated list from GitHub
        self.fetch_project_list()
        self.update_list_widget()

    def load_project(self):
        """Load the selected project"""
        selected_item = self.project_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Selection Error", "Please select a repository to load.")
            return
            
        selected_text = selected_item.text()
        
        # Extract the actual project name
        if selected_text.startswith("[Custom] "):
            project_name = selected_text.replace("[Custom] ", "")
        else:
            project_name = selected_text
            
        if project_name not in self.projects:
            QMessageBox.warning(self, "Load Error", "Selected repository not found.")
            return
            
        # Get the project data
        selected = self.projects[project_name]
        
        # Hide this window
        self.hide()
        
        # Import here to avoid circular imports
        from main import GitFileReaderApp
        
        # Fire up the main app with chosen project
        self.main_window = GitFileReaderApp(selected["url"], selected["folder"])
        self.main_window.show()