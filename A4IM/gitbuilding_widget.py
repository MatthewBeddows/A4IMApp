from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                            QMessageBox, QTextEdit)
from PyQt5.QtCore import Qt
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

        # Info text area
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setPlaceholderText("Documentation will open in your browser")
        self.info_text.setFixedHeight(100)
        main_layout.addWidget(self.info_text)

        # Open in Browser button
        browser_button = QPushButton("Open in Browser")
        browser_button.setFixedHeight(40)
        browser_button.setStyleSheet(self.get_button_style())
        browser_button.clicked.connect(self.open_in_browser)
        main_layout.addWidget(browser_button)

        # Open Folder button
        open_folder_button = QPushButton("Open Folder")
        open_folder_button.setFixedHeight(40)
        open_folder_button.setStyleSheet(self.get_button_style())
        open_folder_button.clicked.connect(self.open_orshards_folder)
        main_layout.addWidget(open_folder_button)

        # Back button
        back_button = QPushButton("Back")
        back_button.setFixedHeight(40)
        back_button.setStyleSheet(self.get_button_style())
        back_button.clicked.connect(self.go_back)
        main_layout.addWidget(back_button)

        # Add some space
        main_layout.addStretch()

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
                
                # Update info text
                self.info_text.setText(f"Documentation is ready to view:\n{os.path.basename(self.current_base_path)}\n\nClick 'Open in Browser' to view the documentation.")
                
                # Automatically open in browser
                self.open_in_browser()
            else:
                self.info_text.setText(f"Non-file URL received: {url}\n\nClick 'Open in Browser' to view.")
                self.current_base_path = url
        except Exception as e:
            self.log(f"Error loading URL: {e}")
            self.info_text.setText(f"Error loading URL: {str(e)}")

    def open_in_browser(self):
        """Open the HTML file in the default browser"""
        if not self.current_base_path:
            QMessageBox.warning(self, "Error", "No documentation URL available.")
            return
            
        try:
            # Check for WSL
            is_wsl = False
            try:
                with open('/proc/version', 'r') as f:
                    if 'microsoft' in f.read().lower():
                        is_wsl = True
            except:
                pass
                
            if is_wsl:
                # For WSL, use a different approach
                try:
                    # Convert path to Windows format
                    process = subprocess.run(['wslpath', '-w', self.current_base_path], 
                                        capture_output=True, text=True, check=True)
                    windows_path = process.stdout.strip()
                    
                    # Use cmd.exe with start command - this works better with HTML files
                    subprocess.run(['cmd.exe', '/c', f'start "" "{windows_path}"'])
                except Exception as e:
                    self.log(f"Error opening file via WSL: {e}")
                    # Try alternative approach with rundll32
                    try:
                        subprocess.run(['rundll32.exe', 'url.dll,FileProtocolHandler', windows_path])
                    except Exception as e:
                        self.log(f"Error with rundll32: {e}")
                        # Last resort fallback
                        QMessageBox.information(self, "HTML File Path", 
                                            f"Your HTML file is located at:\n{self.current_base_path}")
            else:
                # Use standard methods for non-WSL
                if self.is_windows:
                    # Windows
                    os.startfile(self.current_base_path)
                elif platform.system() == "Darwin":
                    # macOS
                    subprocess.run(['open', self.current_base_path])
                else:
                    # Linux
                    subprocess.run(['xdg-open', self.current_base_path])
                    
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
            is_wsl = False
            try:
                with open('/proc/version', 'r') as f:
                    if 'microsoft' in f.read().lower():
                        is_wsl = True
            except:
                pass
                
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