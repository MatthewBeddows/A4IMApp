from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap
import os
import re
import subprocess
import webbrowser

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
        # Build absolute path to logo file (it's in A4IM/images/)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "images", "A4IM Logo_pink.png")
        pixmap = QPixmap(logo_path)
        if pixmap.isNull():
            print(f"Warning: Could not load logo from {logo_path}")
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
        buttons = []
        
        # Only add Project Overview button if architect module has documentation
        if self.check_architect_documentation():
            buttons.append(("Project Overview", self.show_project_overview))
        
        buttons.extend([
            ("System View", self.parent.show_system_view),
            ("Exit", self.parent.close)
        ])

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

    def check_architect_documentation(self):
        """Check if the architect module has documentation"""
        try:
            # Get the architect folder path
            if not hasattr(self.parent, 'repo_folder') or not self.parent.repo_folder:
                return False
                
            repo_dir = os.path.join("Downloaded Repositories", self.parent.repo_folder)
            
            if not os.path.exists(repo_dir):
                return False
            
            # Use the initial_repo_url directly from parent to get the root module name
            if not hasattr(self.parent, 'initial_repo_url') or not self.parent.initial_repo_url:
                return False
                
            # Extract repository name from the initial URL
            repo_name = self.parent.initial_repo_url.split('/')[-1]
            module_dir = os.path.join(repo_dir, repo_name)
            
            # Check for documentation using the new recursive logic
            return self.check_module_documentation_path(module_dir)
                
        except Exception as e:
            print(f"Error checking architect documentation: {e}")
            return False

    def check_module_documentation_path(self, module_dir):
        """Check if a module has documentation file using recursive search"""
        if not os.path.exists(module_dir):
            return False
        
        # Recursively search for index.html files
        def find_index_html(directory):
            """Recursively search for index.html files"""
            found_files = []
            try:
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if file.lower() == 'index.html':
                            full_path = os.path.join(root, file)
                            found_files.append(full_path)
            except Exception as e:
                pass
            return found_files
        
        # Search for all index.html files
        found_files = find_index_html(module_dir)
        
        # Return True if any index.html files are found
        return len(found_files) > 0

    def get_architect_documentation_path(self):
        """Get the documentation path for the architect module"""
        try:
            # Get the architect folder path
            if not hasattr(self.parent, 'repo_folder') or not self.parent.repo_folder:
                return None
                
            repo_dir = os.path.join("Downloaded Repositories", self.parent.repo_folder)
            
            if not os.path.exists(repo_dir):
                return None
            
            # Use the initial_repo_url directly from parent to get the root module name
            if not hasattr(self.parent, 'initial_repo_url') or not self.parent.initial_repo_url:
                return None
                
            # Extract repository name from the initial URL
            repo_name = self.parent.initial_repo_url.split('/')[-1]
            module_dir = os.path.join(repo_dir, repo_name)
            
            # Get the documentation path using recursive search
            return self.get_module_documentation_path(module_dir)
                
        except Exception as e:
            print(f"Error getting architect documentation path: {e}")
            return None

    def get_module_documentation_path(self, module_dir):
        """Get the documentation file path using recursive search"""
        if not os.path.exists(module_dir):
            return None
        
        # Recursively search for index.html files
        def find_index_html(directory):
            """Recursively search for index.html files"""
            found_files = []
            try:
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if file.lower() == 'index.html':
                            full_path = os.path.join(root, file)
                            found_files.append(full_path)
            except Exception as e:
                pass
            return found_files
        
        # Search for all index.html files
        found_files = find_index_html(module_dir)
        
        # If we found files, return the first one
        if found_files:
            return found_files[0]
        
        return None

    def find_module_info_file(self, module_dir):
        """Find the module info file in lib folder with case-insensitive search"""
        if not os.path.exists(module_dir):
            return None

        possible_filenames = [
            "ModuleInfo.txt",
            "moduleInfo.txt",
            "moduleinfo.txt",
            "MODULEINFO.txt",
            "ModuleInfor.txt",
            "moduleInfor.txt",
            "moduleinfor.txt",
            "Module_Info.txt",
            "module_info.txt"
        ]

        lib_dir = os.path.join(module_dir, "lib")

        # Check for exact filename matches in lib folder
        for filename in possible_filenames:
            file_path = os.path.join(lib_dir, filename)
            if os.path.exists(file_path):
                return file_path

        # Case-insensitive search in lib folder
        if os.path.exists(lib_dir):
            try:
                existing_files = os.listdir(lib_dir)
                for existing_file in existing_files:
                    lower_file = existing_file.lower()
                    if "moduleinfo" in lower_file or "moduleinfor" in lower_file:
                        return os.path.join(lib_dir, existing_file)
            except:
                pass

        return None  # No matching file found

    def is_wsl(self):
        """Check if running in Windows Subsystem for Linux"""
        try:
            with open('/proc/version', 'r') as f:
                return 'microsoft' in f.read().lower()
        except:
            return False

    def show_project_overview(self):
        """Open the first documentation page directly in browser"""
        doc_path = self.get_architect_documentation_path()
        
        if not doc_path:
            print("No documentation found for architect module")
            return
        
        try:
            # Extract the first documentation link from the HTML file (like GitBuildingWindow does)
            first_doc_path = self.get_first_documentation_link(doc_path)
            
            if first_doc_path:
                print(f"Opening first documentation page: {first_doc_path}")
                # Open the first actual documentation page using the working browser method
                self.open_documentation_in_browser(first_doc_path)
            else:
                print("No documentation links found, opening main page")
                # Fallback to opening the main page if no links found
                self.open_documentation_in_browser(doc_path)
                
        except Exception as e:
            print(f"Error opening project overview: {e}")

    def get_first_documentation_link(self, html_file_path):
        """Extract the first documentation link from HTML file (exact same logic as GitBuildingWindow)"""
        try:
            if not os.path.exists(html_file_path):
                return None
                
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Get base directory for building absolute paths
            base_dir = os.path.dirname(html_file_path)
            
            # Use the exact same extraction logic as GitBuildingWindow
            # Method 1: Multi-line regex with very flexible pattern
            pattern1 = r'<li[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>((?:(?!</a>).)*)</a>'
            matches1 = re.findall(pattern1, html_content, re.DOTALL)
            
            # Method 2: Find all <a> tags in the whole document
            pattern2 = r'<a[^>]*href="([^"]*)"[^>]*>((?:(?!</a>).)*)</a>'
            matches2 = re.findall(pattern2, html_content, re.DOTALL)
            
            # Method 3: Split by lines and look for specific sequences
            matches3 = []
            lines = html_content.split('\n')
            for i in range(len(lines)):
                if '<li class=' in lines[i] and i+1 < len(lines) and '<a ' in lines[i+1]:
                    href_match = re.search(r'href="([^"]*)"', lines[i+1])
                    title_match = re.search(r'>([^<]*)</a>', lines[i+1])
                    if href_match and title_match:
                        matches3.append((href_match.group(1), title_match.group(1)))
            
            # Choose the method that found the most valid-looking links (same as GitBuildingWindow)
            all_matches = []
            if len(matches1) > 0 and any(m[0].endswith('.html') for m in matches1):
                all_matches = matches1
            elif len(matches3) > 0:
                all_matches = matches3
            else:
                # Filter method 2 results to only include .html links
                filtered_matches2 = [m for m in matches2 if m[0].endswith('.html')]
                if filtered_matches2:
                    all_matches = filtered_matches2
                else:
                    all_matches = matches2
            
            # Process matches and find the first valid documentation link (same as GitBuildingWindow)
            for href, title in all_matches:
                # Clean up title (remove HTML tags and extra whitespace)
                clean_title = re.sub(r'<[^>]*>', '', title).strip()
                
                # Skip empty or placeholder titles
                if not clean_title or clean_title.startswith('##'):
                    continue
                
                # If href starts with ./, remove it
                if href.startswith('./'):
                    href = href[2:]
                
                # Create full path
                full_path = os.path.normpath(os.path.join(base_dir, href))
                
                # Make sure we have the absolute path (like GitBuildingWindow does)
                full_path = os.path.abspath(full_path)
                
                # Filter out non-HTML links like CSS, JS, images
                if not full_path.endswith('.html'):
                    continue
                
                # Return the first valid documentation link
                print(f"Found first doc link: '{clean_title}' -> {full_path}")
                return full_path
            
            return None
            
        except Exception as e:
            print(f"Error extracting first documentation link: {e}")
            return None

    def open_documentation_in_browser(self, doc_path):
        """Open the HTML file in the default browser"""
        if not doc_path:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", "No documentation URL available.")
            return
            
        try:
            # Check for WSL
            is_wsl = self.is_wsl()
                
            if is_wsl:
                # Create the correct WSL URL format with proper slash
                # Make sure there's a slash between Ubuntu and the path
                if doc_path.startswith('/'):
                    wsl_url = f"file://wsl.localhost/Ubuntu{doc_path}"
                else:
                    wsl_url = f"file://wsl.localhost/Ubuntu/{doc_path}"
                
                # Log the URL we're trying
                print(f"Opening browser with correct WSL URL: {wsl_url}")
                
                # Try multiple methods to open the file
                try:
                    # Method 1: PowerShell Start-Process (exact same as GitBuildingWindow)
                    powershell_command = f'Start-Process "{wsl_url}"'
                    subprocess.run(['powershell.exe', '-Command', powershell_command])
                except Exception as e:
                    print(f"PowerShell error: {e}")
                    
                    try:
                        # Method 2: Use the explorer.exe approach (exact same as GitBuildingWindow)
                        subprocess.run(['explorer.exe', wsl_url])
                    except Exception as e2:
                        print(f"Explorer error: {e2}")
                        
                        # Method 3: Show the URL for manual copying
                        from PyQt5.QtWidgets import QMessageBox
                        QMessageBox.information(self, "Browser URL", 
                                         f"Please copy and paste this URL into your browser:\n\n{wsl_url}")
            else:
                # For non-WSL environments, use standard browser opening
                file_url = 'file://' + os.path.abspath(doc_path)
                webbrowser.open(file_url)
                    
        except Exception as e:
            print(f"Error opening HTML file: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Could not open HTML file: {str(e)}")

    def show_intro(self):
        print("Intro button clicked")

    def show_about(self):
        print("About button clicked")