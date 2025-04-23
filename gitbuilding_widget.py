from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                            QMessageBox, QTextEdit, QFrame, QHBoxLayout,
                            QScrollArea, QCheckBox, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QIcon
import os
import subprocess
import platform
import webbrowser
import re

class GitBuildingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.current_base_path = None
        self.is_windows = platform.system() == "Windows"
        self.doc_links = []  # Store the documentation links
        self.completed_docs = set()  # Store completed documentation pages
        self.setup_ui()
        self.debug_mode = True

    def log(self, message):
        """Helper function for debug logging"""
        if self.debug_mode:
            print(f"DEBUG: {message}")

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 30, 20, 30)
        main_layout.setSpacing(20)

        # Title header
        title_header = QLabel("Documentation Viewer")
        title_header.setFont(QFont('Arial', 18, QFont.Bold))
        title_header.setStyleSheet("color: #465775; margin-bottom: 10px;")
        main_layout.addWidget(title_header)

        # Description
        description = QLabel("Check off each section as you complete it.")
        description.setFont(QFont('Arial', 12))
        description.setStyleSheet("color: #666; margin-bottom: 10px;")
        main_layout.addWidget(description)

        # Horizontal layout for content
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Left side: Documentation list
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #f8f8f8;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
            QListWidget::item {
                border-bottom: 1px solid #eee;
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: #465775;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e0e0e0;
            }
        """)
        self.list_widget.itemClicked.connect(self.doc_item_clicked)
        content_layout.addWidget(self.list_widget, 1)

        # Right side: Content area and buttons
        right_layout = QVBoxLayout()

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
                font-size: 14px;
            }
        """)
        
        # Set initial message
        self.content_area.setHtml("""
            <div style="text-align: center;">
                <h2>Documentation Viewer</h2>
                <p>Select a documentation page from the list to view it.</p>
                <p>You can use the buttons below to:</p>
                <ul style="text-align: left;">
                    <li>Open the selected documentation in your browser</li>
                    <li>Mark the documentation as completed</li>
                    <li>Open the containing folder</li>
                    <li>Return to the previous view</li>
                </ul>
            </div>
        """)
        
        right_layout.addWidget(self.content_area, 1)

        # Add completion checkbox
        self.completion_checkbox = QCheckBox("Mark as Completed")
        self.completion_checkbox.setFont(QFont('Arial', 12))
        self.completion_checkbox.stateChanged.connect(self.completion_status_changed)
        self.completion_checkbox.setEnabled(False)  # Initially disabled until a doc is selected
        right_layout.addWidget(self.completion_checkbox)

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

        right_layout.addLayout(button_layout)
        content_layout.addLayout(right_layout, 2)
        main_layout.addLayout(content_layout)

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
                else:
                    # For Linux/WSL paths, ensure there's a leading slash
                    if not self.current_base_path.startswith('/'):
                        self.current_base_path = '/' + self.current_base_path
                
                self.log(f"Processing file path: {self.current_base_path}")
                
                # Parse the HTML to extract documentation links
                self.extract_doc_links()
                
                # Update the list widget with the extracted links
                self.populate_doc_list()
                
                # Update the content area with file info
                filename = os.path.basename(self.current_base_path)
                self.content_area.setHtml(f"""
                    <div style="text-align: center;">
                        <h2>Documentation Ready</h2>
                        <p>File: <b>{filename}</b></p>
                        <p>Select a documentation page from the list to view it.</p>
                        <p>Click "Open in Browser" to view the selected document.</p>
                    </div>
                """)
                
                # Do NOT automatically open the browser
                # self.open_in_browser() - removed this line
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
            import traceback
            self.log(traceback.format_exc())
            self.content_area.setHtml(f"""
                <div style="text-align: center;">
                    <h2>Error Loading Documentation</h2>
                    <p>Could not load: <b>{url}</b></p>
                    <p>Error: {str(e)}</p>
                </div>
            """)

    def extract_doc_links(self):
        """Extract documentation links from the HTML file - using multiple methods"""
        try:
            # Reset the links list
            self.doc_links = []
            
            # Read the HTML file
            if not os.path.exists(self.current_base_path):
                self.log(f"File not found: {self.current_base_path}")
                return
                
            with open(self.current_base_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Get base directory for building absolute paths
            base_dir = os.path.dirname(self.current_base_path)
            
            # Try multiple parsing methods:
            
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
            
            self.log(f"Method 1 found {len(matches1)} links")
            self.log(f"Method 2 found {len(matches2)} links")
            self.log(f"Method 3 found {len(matches3)} links")
            
            # Choose the method that found the most valid-looking links
            all_matches = []
            if len(matches1) > 0 and any(m[0].endswith('.html') for m in matches1):
                all_matches = matches1
                self.log("Using method 1 results")
            elif len(matches3) > 0:
                all_matches = matches3
                self.log("Using method 3 results")
            else:
                # Filter method 2 results to only include .html links
                filtered_matches2 = [m for m in matches2 if m[0].endswith('.html')]
                if filtered_matches2:
                    all_matches = filtered_matches2
                    self.log("Using filtered method 2 results")
                else:
                    all_matches = matches2
                    self.log("Using method 2 results")
            
            # Process matches and add to doc_links
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
                
                # Filter out non-HTML links like CSS, JS, images
                if not full_path.endswith('.html'):
                    continue
                
                self.log(f"Adding doc link: '{clean_title}' -> {full_path}")
                
                self.doc_links.append({
                    'href': full_path,
                    'title': clean_title
                })
            
            # Log results
            self.log(f"Extracted {len(self.doc_links)} documentation links")
            
            # If no links found with any method, add a message to the UI
            if not self.doc_links:
                self.content_area.setHtml(f"""
                    <div style="text-align: center;">
                        <h2>No Documentation Links Found</h2>
                        <p>Could not extract any documentation links from the HTML file.</p>
                        <p>Click "Open in Browser" to view the main documentation page.</p>
                    </div>
                """)
            
        except Exception as e:
            self.log(f"Error extracting documentation links: {e}")
            import traceback
            self.log(traceback.format_exc())
            self.doc_links = []

    def populate_doc_list(self):
        """Populate the list widget with documentation links"""
        try:
            # Clear the list
            self.list_widget.clear()
            
            self.log(f"Populating list with {len(self.doc_links)} documents")
            
            # Add each doc link as an item
            for doc in self.doc_links:
                self.log(f"Adding list item: {doc['title']}")
                item = QListWidgetItem(doc['title'])
                item.setData(Qt.UserRole, doc['href'])  # Store the href as user data
                
                # Check if this doc is marked as completed
                if doc['href'] in self.completed_docs:
                    # Since we might not have an icon resource, just use color
                    # item.setIcon(QIcon(":/checkmark.png"))
                    item.setForeground(Qt.gray)
                
                self.list_widget.addItem(item)
                
        except Exception as e:
            self.log(f"Error populating doc list: {e}")
            import traceback
            self.log(traceback.format_exc())

    def doc_item_clicked(self, item):
        """Handle click on a documentation item"""
        try:
            # Get the href from the item
            href = item.data(Qt.UserRole)
            
            # The href should already be the full path from our extraction
            doc_path = href
            
            # Log for debugging
            self.log(f"Selected document: {item.text()} -> {doc_path}")
            
            # Update the current path to the selected document
            self.current_base_path = doc_path
            
            # Update the content area
            self.content_area.setHtml(f"""
                <div style="text-align: center;">
                    <h2>{item.text()}</h2>
                    <p>Click "Open in Browser" to view this document.</p>
                </div>
            """)
            
            # Enable the completion checkbox
            self.completion_checkbox.setEnabled(True)
            
            # Update the checkbox state based on completion status
            self.completion_checkbox.blockSignals(True)
            self.completion_checkbox.setChecked(href in self.completed_docs)
            self.completion_checkbox.blockSignals(False)
            
        except Exception as e:
            self.log(f"Error handling doc item click: {e}")
            import traceback
            self.log(traceback.format_exc())
            self.content_area.setHtml(f"""
                <div style="text-align: center;">
                    <h2>Error</h2>
                    <p>Could not load the selected document.</p>
                    <p>Error: {str(e)}</p>
                </div>
            """)

    def completion_status_changed(self, state):
        """Handle checkbox state change for documentation completion"""
        try:
            # Get the current selected item
            selected_items = self.list_widget.selectedItems()
            if not selected_items:
                return
                
            item = selected_items[0]
            href = item.data(Qt.UserRole)
            
            if state == Qt.Checked:
                # Mark as completed
                self.completed_docs.add(href)
                item.setForeground(Qt.gray)
                # Add checkmark icon if available
                # item.setIcon(QIcon(":/checkmark.png"))
            else:
                # Mark as not completed
                if href in self.completed_docs:
                    self.completed_docs.remove(href)
                item.setForeground(Qt.black)
                # item.setIcon(QIcon())  # Remove icon
                
            # TODO: Save completion status to a file for persistence
            
        except Exception as e:
            self.log(f"Error updating completion status: {e}")

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
                    powershell_command = f'Start-Process "{wsl_url}"'
                    subprocess.run(['powershell.exe', '-Command', powershell_command])
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
                # If orshards not found, open the parent directory of the current file
                orshards_dir = os.path.dirname(self.current_base_path)
                
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
                        QMessageBox.information(self, "Folder Path", f"The folder is located at:\n{orshards_dir}")
        except Exception as e:
            self.log(f"Error opening folder: {e}")
            QMessageBox.warning(self, "Error", f"Could not open folder: {str(e)}")

    def go_back(self):
        """Return to the previous view"""
        if self.parent and hasattr(self.parent, 'central_widget'):
            self.parent.central_widget.setCurrentIndex(1)