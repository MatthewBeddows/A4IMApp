from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                            QMessageBox, QTextEdit, QFrame, QHBoxLayout)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont
import os
import subprocess
import platform
import webbrowser

class GitBuildingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.current_base_path = None
        self.is_windows = platform.system() == "Windows"
        self.setup_ui()
        self.debug_mode = True

    def log(self, message):
        """Helper function for debug logging"""
        if self.debug_mode:
            print(f"DEBUG: {message}")

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 20, 10, 20)
        main_layout.setSpacing(10)

        # Title header
        title_header = QLabel("Documentation Viewer")
        title_header.setFont(QFont('Arial', 14, QFont.Bold))
        title_header.setStyleSheet("color: #465775; padding-bottom: 10px;")
        main_layout.addWidget(title_header)

        # Content area - we'll show instructions here
        self.content_area = QTextEdit()
        self.content_area.setReadOnly(True)
        self.content_area.setStyleSheet("""
            QTextEdit {
                background-color: #f8f8f8;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 10px;
                color: #333;
            }
        """)
        
        # Set initial message
        self.content_area.setHtml("""
            <div style="text-align: center;">
                <h2>Documentation Viewer</h2>
                <p>When documentation is loaded, it will automatically open in your default browser.</p>
                <p>You can use the buttons below to:</p>
                <ul style="text-align: left;">
                    <li>Re-open the documentation in your browser</li>
                    <li>Open the containing folder</li>
                    <li>Return to the previous view</li>
                </ul>
            </div>
        """)
        
        main_layout.addWidget(self.content_area, 1)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Open in Browser button
        self.browser_button = QPushButton("Open in Browser")
        self.browser_button.setFixedHeight(40)
        self.browser_button.setStyleSheet(self.get_button_style())
        self.browser_button.clicked.connect(self.open_in_browser)
        button_layout.addWidget(self.browser_button)

        # Open Folder button
        open_folder_button = QPushButton("Open Folder")
        open_folder_button.setFixedHeight(40)
        open_folder_button.setStyleSheet(self.get_button_style())
        open_folder_button.clicked.connect(self.open_orshards_folder)
        button_layout.addWidget(open_folder_button)

        # Back button
        back_button = QPushButton("Back")
        back_button.setFixedHeight(40)
        back_button.setStyleSheet(self.get_button_style())
        back_button.clicked.connect(self.go_back)
        button_layout.addWidget(back_button)

        main_layout.addLayout(button_layout)

    def get_button_style(self):
        return """
            QPushButton {
                background-color: #465775;
                border: none;
                border-radius: 20px;
                color: white;
                font-size: 12px;
                padding: 10px;
            }
            QPushButton:hover { background-color: #566985; }
            QPushButton:pressed { background-color: #364765; }
        """

    def load_url(self, url):
        """Process URL and open it in browser"""
        try:
            self.log(f"Loading URL: {url}")
            
            if url.startswith('file:///'):
                self.current_base_path = url.replace('file:///', '')
                
                # Handle Windows paths with drive letters
                if self.is_windows:
                    # If path starts with / followed by drive letter (e.g. /C:/path)
                    if self.current_base_path.startswith('/') and len(self.current_base_path) > 2 and self.current_base_path[1].isalpha() and self.current_base_path[2] == ':':
                        self.current_base_path = self.current_base_path[1:]  # Remove leading slash
                
                # Update the content area with file info
                filename = os.path.basename(self.current_base_path)
                self.content_area.setHtml(f"""
                    <div style="text-align: center;">
                        <h2>Documentation Ready</h2>
                        <p>File: <b>{filename}</b></p>
                        <p>The documentation should automatically open in your browser.</p>
                        <p>If it doesn't open automatically, click "Open in Browser" below.</p>
                    </div>
                """)
                
                # Try to open in browser immediately
                self.open_in_browser()
            else:
                # Non-file URL
                self.current_base_path = url
                self.content_area.setHtml(f"""
                    <div style="text-align: center;">
                        <h2>External URL</h2>
                        <p>URL: <b>{url}</b></p>
                        <p>Click "Open in Browser" to view this URL.</p>
                    </div>
                """)
                
        except Exception as e:
            self.log(f"Error loading URL: {e}")
            self.content_area.setHtml(f"""
                <div style="text-align: center;">
                    <h2>Error Loading Documentation</h2>
                    <p>Could not load: <b>{url}</b></p>
                    <p>Error: {str(e)}</p>
                </div>
            """)

    def is_wsl(self):
        """Check if running in Windows Subsystem for Linux"""
        try:
            with open('/proc/version', 'r') as f:
                return 'microsoft' in f.read().lower()
        except:
            return False

    def open_in_browser(self):
        """Open the HTML file in the default browser"""
        if not self.current_base_path:
            QMessageBox.warning(self, "Error", "No documentation URL available.")
            return
            
        try:
            # Check for WSL
            is_wsl = self.is_wsl()
                
            if is_wsl:
                # Create the correct WSL URL format with proper slash
                # Make sure there's a slash between Ubuntu and the path
                if self.current_base_path.startswith('/'):
                    wsl_url = f"file://wsl.localhost/Ubuntu{self.current_base_path}"
                else:
                    wsl_url = f"file://wsl.localhost/Ubuntu/{self.current_base_path}"
                
                # Log the URL we're trying
                self.log(f"Opening browser with correct WSL URL: {wsl_url}")
                
                # Try multiple methods to open the file
                try:
                    # Method 1: PowerShell Start-Process
                    subprocess.run(['powershell.exe', '-Command', f'Start-Process "{wsl_url}"'])
                except Exception as e:
                    self.log(f"PowerShell error: {e}")
                    
                    try:
                        # Method 2: Use the explorer.exe approach
                        subprocess.run(['explorer.exe', wsl_url])
                    except Exception as e2:
                        self.log(f"Explorer error: {e2}")
                        
                        # Method 3: Show the URL for manual copying
                        QMessageBox.information(self, "Browser URL", 
                                         f"Please copy and paste this URL into your browser:\n\n{wsl_url}")
            else:
                # For non-WSL environments, use standard browser opening
                file_url = 'file://' + os.path.abspath(self.current_base_path)
                webbrowser.open(file_url)
                    
        except Exception as e:
            self.log(f"Error opening HTML file: {e}")
            QMessageBox.warning(self, "Error", f"Could not open HTML file: {str(e)}")

    def open_orshards_folder(self):
        """Open the orshards folder in file explorer"""
        if not self.current_base_path:
            QMessageBox.warning(self, "Error", "No content loaded.")
            return
            
        try:
            # Get the orshards directory path
            orshards_dir = None
            path_parts = self.current_base_path.replace('\\', '/').split('/')
            
            if 'orshards' in path_parts:
                # Find the orshards directory
                orshards_index = path_parts.index('orshards')
                orshards_dir = '/'.join(path_parts[:orshards_index+1])
                
                # Fix Windows paths
                if self.is_windows and ':' in path_parts[0]:
                    orshards_dir = path_parts[0] + ':/' + '/'.join(path_parts[1:orshards_index+1])
            
            if not orshards_dir or not os.path.exists(orshards_dir):
                QMessageBox.warning(self, "Error", "Could not locate orshards directory.")
                return
                
            # Check for WSL
            is_wsl = self.is_wsl()
                
            if is_wsl:
                # For WSL, use wslpath and explorer.exe
                try:
                    # Convert path to Windows format
                    process = subprocess.run(['wslpath', '-w', orshards_dir], 
                                           capture_output=True, text=True, check=True)
                    windows_path = process.stdout.strip()
                    
                    # Open folder in explorer
                    subprocess.run(['explorer.exe', windows_path])
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Could not open folder: {str(e)}")
            else:
                # Native OS handling
                if self.is_windows:
                    subprocess.run(['explorer', orshards_dir])
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(['open', orshards_dir])
                else:  # Linux
                    try:
                        subprocess.run(['xdg-open', orshards_dir])
                    except FileNotFoundError:
                        QMessageBox.information(self, "Folder Path", f"The orshards folder is located at:\n{orshards_dir}")
        except Exception as e:
            self.log(f"Error opening orshards folder: {e}")
            QMessageBox.warning(self, "Error", f"Could not open folder: {str(e)}")

    def go_back(self):
        """Return to the previous view"""
        if self.parent and hasattr(self.parent, 'central_widget'):
            self.parent.central_widget.setCurrentIndex(1)