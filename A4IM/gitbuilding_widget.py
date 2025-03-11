from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                           QCheckBox, QScrollArea, QLabel, QFrame, QTextEdit,
                           QDialog, QDialogButtonBox, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QCursor
from bs4 import BeautifulSoup
import os
import sys
import subprocess
import platform
import traceback

class TestOutputDialog(QDialog):
    def __init__(self, output, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test Output")
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        output_text = QTextEdit()
        output_text.setReadOnly(True)
        output_text.setPlainText(output)
        layout.addWidget(output_text)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

class TaskItem(QWidget):
    def __init__(self, text, href=None, is_test=False, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(5)
        
        self.checkbox = QCheckBox()
        self.text = text
        self.label = QLabel(text)
        
        layout.addWidget(self.checkbox)
        layout.addWidget(self.label, stretch=1)
        
        self.href = href
        self.is_test = is_test
        self.setCursor(Qt.PointingHandCursor)
        
        base_style = """
            QWidget {
                background-color: transparent;
            }
            QWidget:hover {
                background-color: #e0e0e0;
                border-radius: 5px;
            }
            QLabel {
                font-size: 13px;
                padding: 5px;
            }
            QCheckBox { spacing: 0px; }
            QCheckBox::indicator { width: 20px; height: 20px; }
        """
        
        if is_test:
            self.label.setStyleSheet("""
                QLabel {
                    color: #465775;
                    font-weight: bold;
                }
            """)
            
        self.setStyleSheet(base_style)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            parent = self
            while parent is not None:
                if isinstance(parent, GitBuildingWindow):
                    break
                parent = parent.parent()

            if parent is not None:
                if self.is_test:
                    parent.run_test()
                elif self.href:
                    parent.open_task(self.href)

class GitBuildingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.current_base_path = None
        self.test_script_path = None
        self.is_windows = platform.system() == "Windows"
        self.setup_ui()
        self.debug_mode = True  # Set to False in production

    def log(self, message):
        """Helper function for debug logging"""
        if self.debug_mode:
            print(f"DEBUG: {message}")

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 20, 10, 20)
        main_layout.setSpacing(10)

        # Tasks Header
        tasks_header = QLabel("Tasks")
        tasks_header.setFont(QFont('Arial', 14, QFont.Bold))
        tasks_header.setStyleSheet("color: #465775; padding-bottom: 10px;")
        main_layout.addWidget(tasks_header)

        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setStyleSheet("background-color: #ddd;")
        main_layout.addWidget(separator1)

        # Scrollable task area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        task_container = QWidget()
        self.task_container_layout = QVBoxLayout(task_container)
        self.task_container_layout.setSpacing(8)
        
        # Create a container for tasks
        self.tasks_container = QWidget()
        self.tasks_container_layout = QVBoxLayout(self.tasks_container)
        self.tasks_container_layout.setSpacing(8)
        self.task_container_layout.addWidget(self.tasks_container)
        
        # Tests Header
        self.tests_header = QLabel("Tests")
        self.tests_header.setFont(QFont('Arial', 14, QFont.Bold))
        self.tests_header.setStyleSheet("color: #465775; padding: 20px 0px 10px 0px;")
        self.tests_header.hide()
        self.task_container_layout.addWidget(self.tests_header)

        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setStyleSheet("background-color: #ddd;")
        separator2.hide()
        self.task_container_layout.addWidget(separator2)

        # Test item
        self.test_item = TaskItem("Run Tests", is_test=True, parent=self)
        self.test_item.hide()
        self.task_container_layout.addWidget(self.test_item)
        
        # Store the test separator reference
        self.test_separator = separator2
        
        self.task_container_layout.addStretch()
        scroll.setWidget(task_container)
        main_layout.addWidget(scroll)

        # Back button
        back_button = QPushButton("Back")
        back_button.setFixedHeight(40)
        back_button.setStyleSheet("""
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
        """)
        back_button.clicked.connect(self.go_back)
        main_layout.addWidget(back_button)

    def find_all_files(self, directory, pattern):
        """Find all files in a directory and subdirectories matching a pattern"""
        matches = []
        for root, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                if pattern in filename:
                    matches.append(os.path.join(root, filename))
        return matches

    def normalize_path(self, path):
        """Normalize path separators based on platform"""
        if self.is_windows:
            return path.replace('/', '\\')
        else:
            return path.replace('\\', '/')

    def clean_url_to_path(self, url):
        """Convert a file URL to a clean path string"""
        if not url.startswith('file:///'):
            return None
            
        # Remove file:/// prefix
        path = url.replace('file:///', '')
        
        # Handle Windows paths with drive letters
        if self.is_windows:
            # If path starts with / followed by drive letter (e.g. /C:/path)
            if path.startswith('/') and len(path) > 2 and path[1].isalpha() and path[2] == ':':
                path = path[1:]  # Remove leading slash
        else:
            # Ensure Unix paths start with /
            if not path.startswith('/'):
                path = '/' + path
        
        return path

    def find_repository_root(self, path):
        """Find the repository root directory from a path"""
        try:
            if 'Downloaded Repositories' in path:
                parts = path.replace('\\', '/').split('/')
                repos_index = parts.index('Downloaded Repositories')
                
                # Path up to and including "Downloaded Repositories"
                repos_path = '/'.join(parts[:repos_index+1])
                if self.is_windows and ':' in parts[0]:
                    # Add drive letter for Windows
                    repos_path = parts[0] + '/' + repos_path
                elif not repos_path.startswith('/'):
                    # Ensure absolute path for Unix
                    repos_path = '/' + repos_path
                
                return self.normalize_path(repos_path)
            return None
        except Exception as e:
            self.log(f"Error finding repository root: {e}")
            return None

    def find_gitbuilding_paths(self, base_path):
        """Find all potential GitBuilding paths based on the given base path"""
        gitbuilding_paths = []
        try:
            # Path to split for all methods
            clean_path = self.normalize_path(base_path).replace('\\', '/')
            path_parts = clean_path.split('/')
            
            # Method 1: Direct approach using the orshards directory
            if 'orshards' in path_parts:
                orshards_index = path_parts.index('orshards')
                
                # Reconstruct path up to orshards
                if self.is_windows and ':' in path_parts[0]:
                    # Windows path with drive letter
                    orshards_path = path_parts[0] + ':\\'
                    for part in path_parts[1:orshards_index+1]:
                        if part:
                            orshards_path = os.path.join(orshards_path, part)
                else:
                    # Unix path or Windows without drive letter
                    orshards_path_parts = path_parts[:orshards_index+1]
                    if not orshards_path_parts[0].startswith('/') and not (':' in orshards_path_parts[0]):
                        orshards_path_parts[0] = '/' + orshards_path_parts[0]
                    orshards_path = '/'.join(orshards_path_parts)
                
                orshards_path = self.normalize_path(orshards_path)
                gitbuilding_path = os.path.join(orshards_path, 'GitBuilding', 'index.html')
                gitbuilding_paths.append(gitbuilding_path)
            
            # Method 2: Using the repository structure logic
            if 'Downloaded Repositories' in path_parts:
                repos_index = path_parts.index('Downloaded Repositories')
                if repos_index + 2 < len(path_parts):
                    architect_folder = path_parts[repos_index + 1]
                    repo_name = path_parts[repos_index + 2]
                    
                    repos_base = ''
                    if self.is_windows and ':' in path_parts[0]:
                        repos_base = path_parts[0] + ':/'
                    
                    alt_path = os.path.join(repos_base, 
                                          'Downloaded Repositories',
                                          architect_folder, 
                                          repo_name,
                                          'orshards', 
                                          'GitBuilding', 
                                          'index.html')
                    alt_path = self.normalize_path(alt_path)
                    if alt_path not in gitbuilding_paths:
                        gitbuilding_paths.append(alt_path)
            
            # Method 3: Try to find the file using a search in nearby directories
            try:
                search_dir = os.path.dirname(os.path.dirname(base_path))
                potential_files = self.find_all_files(search_dir, 'GitBuilding/index.html')
                
                for found_path in potential_files:
                    found_path = self.normalize_path(found_path)
                    if found_path not in gitbuilding_paths:
                        gitbuilding_paths.append(found_path)
            except Exception as e:
                self.log(f"Search method failed: {e}")

            # Verify that each path actually exists
            valid_paths = []
            for path in gitbuilding_paths:
                try:
                    if os.path.exists(path):
                        valid_paths.append(path)
                        self.log(f"Found valid GitBuilding path: {path}")
                except Exception as e:
                    self.log(f"Error checking path {path}: {e}")
            
            return valid_paths
        except Exception as e:
            self.log(f"Error finding GitBuilding paths: {e}")
            traceback.print_exc()
            return []



    def process_tests(self, base_path):
        """Process test information from the repository"""
        try:
            # Path for tests
            orshards_dir = os.path.dirname(self.normalize_path(base_path))
            repo_dir = os.path.dirname(orshards_dir)
            tests_dir = os.path.join(repo_dir, 'tests')
            tests_info_path = os.path.join(tests_dir, 'TestsInfo.txt')
            
            self.log(f"Tests dir: {tests_dir}")
            self.log(f"Tests info path: {tests_info_path}")
            
            tests_exist = False
            try:
                tests_exist = os.path.exists(tests_dir) and os.path.exists(tests_info_path)
                self.log(f"Tests dir exists: {os.path.exists(tests_dir)}")
                self.log(f"Tests info path exists: {os.path.exists(tests_info_path)}")
            except Exception as e:
                self.log(f"Error checking tests: {e}")
            
            if tests_exist:
                try:
                    with open(tests_info_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    test_name = None
                    for line in content.split('\n'):
                        if line.startswith('[TestName]'):
                            test_name = line[len('[TestName]'):].strip()
                    
                    if test_name:
                        self.test_item.label.setText(test_name)
                    
                    python_files = [f for f in os.listdir(tests_dir) if f.endswith('.py')]
                    if python_files:
                        self.test_script_path = os.path.join(tests_dir, python_files[0])
                    
                    self.tests_header.show()
                    self.test_separator.show()
                    self.test_item.show()
                except Exception as e:
                    self.log(f"Error processing tests: {e}")
                    self.tests_header.hide()
                    self.test_separator.hide()
                    self.test_item.hide()
            else:
                self.tests_header.hide()
                self.test_separator.hide()
                self.test_item.hide()
        except Exception as e:
            self.log(f"Error in process_tests: {e}")
            self.tests_header.hide()
            self.test_separator.hide()
            self.test_item.hide()

    def load_gitbuilding_content(self, base_path):
        """Load content from GitBuilding directory"""
        try:
            # Find all possible GitBuilding paths
            gitbuilding_paths = self.find_gitbuilding_paths(base_path)
            
            # If no paths were found, show error
            if not gitbuilding_paths:
                self.log("No GitBuilding paths found")
                return
            
            # Try each path until one works
            for gitbuilding_path in gitbuilding_paths:
                try:
                    self.log(f"Trying GitBuilding path: {gitbuilding_path}")
                    
                    if not os.path.exists(gitbuilding_path):
                        self.log(f"Path does not exist: {gitbuilding_path}")
                        continue
                    
                    with open(gitbuilding_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    self.log(f"Read HTML content, length: {len(html_content)}")
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    active_section = soup.find('li', class_='active')
                    self.log(f"Found active section: {active_section is not None}")
                    
                    sub_nav = active_section.find('ul', class_='sub-nav-list') if active_section else None
                    self.log(f"Found sub-nav: {sub_nav is not None}")
                    
                    if active_section and sub_nav:
                        # Clear existing task items
                        self.clear_tasks()
                        
                        # Add new task items
                        task_count = 0
                        for item in sub_nav.find_all('li'):
                            if link := item.find('a'):
                                text = link.text.strip()
                                href = link.get('href')
                                self.log(f"Adding task: {text}, href: {href}")
                                task_item = TaskItem(text, href, is_test=False, parent=self)
                                self.tasks_container_layout.addWidget(task_item)
                                task_count += 1
                        
                        self.log(f"Added {task_count} tasks")
                        return  # Success, exit the function
                    else:
                        self.log("No active section or sub-nav found in HTML")
                        
                except Exception as e:
                    self.log(f"Error loading content from {gitbuilding_path}: {str(e)}")
                    continue  # Try next path
            
            # If we get here, none of the paths worked
            self.log("Failed to load content from any GitBuilding path")
                
        except Exception as e:
            self.log(f"Error loading GitBuilding content: {str(e)}")
            traceback.print_exc()

    def clear_tasks(self):
        """Remove all tasks from the task container"""
        try:
            for i in reversed(range(self.tasks_container_layout.count())):
                widget = self.tasks_container_layout.itemAt(i).widget()
                if isinstance(widget, TaskItem):
                    widget.deleteLater()
        except Exception as e:
            self.log(f"Error clearing tasks: {e}")

    def load_url(self, url):
        """Load content directly from the URL path and extract both navigation and content links"""
        try:
            self.log(f"Loading URL: {url}")
            
            # Convert URL to path
            if not url.startswith('file:///'):
                self.log("Invalid URL format, must start with file:///")
                return
                
            # Remove file:/// prefix
            base_path = url.replace('file:///', '')
            
            # Handle Windows paths with drive letters
            if self.is_windows:
                # If path starts with / followed by drive letter (e.g. /C:/path)
                if base_path.startswith('/') and len(base_path) > 2 and base_path[1].isalpha() and base_path[2] == ':':
                    base_path = base_path[1:]  # Remove leading slash
            else:
                # Ensure Unix paths start with /
                if not base_path.startswith('/'):
                    base_path = '/' + base_path
                    
            self.log(f"Base path: {base_path}")
            self.current_base_path = base_path
            
            # Process test information
            self.process_tests(base_path)
            
            # Load content directly from the index.html file
            try:
                if os.path.exists(base_path):
                    self.log(f"Loading HTML directly from: {base_path}")
                    
                    with open(base_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    self.log(f"Read HTML content, length: {len(html_content)}")
                    
                    # Parse content
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Clear existing task items
                    self.clear_tasks()
                    
                    task_count = 0
                    
                    # Find any page title or header to use as a section title
                    page_title = None
                    if title_tag := soup.find('title'):
                        page_title = title_tag.text.strip()
                    elif h1_tag := soup.find('h1'):
                        page_title = h1_tag.text.strip()
                    
                    self.log(f"Page title: {page_title}")
                    
                    # Step 1: Check for navigation sidebar
                    nav_links = []
                    active_section = soup.find('li', class_='active')
                    if active_section:
                        section_title = None
                        if link := active_section.find('a'):
                            section_title = link.text.strip()
                        
                        self.log(f"Active section: {section_title}")
                        
                        # Find the sub-navigation list
                        sub_nav = active_section.find('ul', class_='sub-nav-list')
                        if sub_nav:
                            for item in sub_nav.find_all('li'):
                                if link := item.find('a'):
                                    text = link.text.strip()
                                    href = link.get('href')
                                    self.log(f"Adding navigation item: {text}, href: {href}")
                                    nav_links.append((text, href))
                    
                    # Step 2: Find content area links - look for lists in the main content
                    content_links = []
                    
                    # First try to find the main content area
                    content_area = None
                    if wrapper := soup.find('div', class_='wrapper'):
                        if not wrapper.find('nav'):  # Exclude nav wrapper
                            content_area = wrapper
                    
                    if not content_area:
                        # Try other common content area selectors
                        for selector in ['.page-content', 'main', 'article', '#content']:
                            if content := soup.select_one(selector):
                                content_area = content
                                break
                    
                    # If no specific content area found, search the whole document
                    if not content_area:
                        content_area = soup
                    
                    # Find all lists in the content area
                    for ul in content_area.find_all('ul'):
                        # Skip navigation lists
                        if 'nav-list' in ul.get('class', []) or 'sub-nav-list' in ul.get('class', []):
                            continue
                            
                        # Get links from this list
                        for li in ul.find_all('li'):
                            if link := li.find('a'):
                                text = link.text.strip()
                                href = link.get('href')
                                if text and href and not href.startswith('http'):
                                    self.log(f"Adding content link: {text}, href: {href}")
                                    content_links.append((text, href))
                    
                    # Step 3: Find direct paragraph links that might be relevant
                    for p in content_area.find_all('p'):
                        for link in p.find_all('a'):
                            text = link.text.strip()
                            href = link.get('href')
                            if (text and href and not href.startswith('http') and 
                                not href.startswith('#') and 
                                not 'mailto:' in href):
                                # Skip generic navigation links like "Next page"
                                skip_terms = ['next', 'previous', 'back', 'home']
                                if not any(term in text.lower() for term in skip_terms):
                                    self.log(f"Adding paragraph link: {text}, href: {href}")
                                    content_links.append((text, href))
                    
                    # Now add all the items to the task list
                    
                    # First add the navigation items
                    if nav_links:
                        # Add a header for the navigation section if we have a title
                        if active_section and (link := active_section.find('a')):
                            section_title = link.text.strip()
                            nav_header = QLabel(section_title)
                            nav_header.setFont(QFont('Arial', 12, QFont.Bold))
                            nav_header.setStyleSheet("color: #465775; padding: 10px 0px 5px 0px;")
                            self.tasks_container_layout.addWidget(nav_header)
                        
                        # Add navigation items
                        for text, href in nav_links:
                            task_item = TaskItem(text, href, is_test=False, parent=self)
                            self.tasks_container_layout.addWidget(task_item)
                            task_count += 1
                    
                    # Then add content links if we have any
                    if content_links:
                        # Add a separator
                        if nav_links:
                            separator = QFrame()
                            separator.setFrameShape(QFrame.HLine)
                            separator.setStyleSheet("background-color: #ddd;")
                            self.tasks_container_layout.addWidget(separator)
                        
                        # Add a header for the content links
                        content_header = QLabel("Page Links")
                        content_header.setFont(QFont('Arial', 12, QFont.Bold))
                        content_header.setStyleSheet("color: #465775; padding: 10px 0px 5px 0px;")
                        self.tasks_container_layout.addWidget(content_header)
                        
                        # Add content links
                        for text, href in content_links:
                            task_item = TaskItem(text, href, is_test=False, parent=self)
                            self.tasks_container_layout.addWidget(task_item)
                            task_count += 1
                    
                    # Step 4: Find index.html files in orshards subdirectories
                    orshards_dir = os.path.dirname(base_path)
                    subdir_indexes = self.find_subdirectory_indexes(orshards_dir)
                    
                    if subdir_indexes:
                        # Add a separator if we have other content
                        if task_count > 0:
                            separator = QFrame()
                            separator.setFrameShape(QFrame.HLine)
                            separator.setStyleSheet("background-color: #ddd;")
                            self.tasks_container_layout.addWidget(separator)
                        
                        # Add a header for the subdirectory indexes
                        subdir_header = QLabel("Subdirectory Indexes")
                        subdir_header.setFont(QFont('Arial', 12, QFont.Bold))
                        subdir_header.setStyleSheet("color: #465775; padding: 10px 0px 5px 0px;")
                        self.tasks_container_layout.addWidget(subdir_header)
                        
                        # Add each subdirectory index as a task
                        for dir_name, index_path in subdir_indexes:
                            # Make the path relative to current file
                            if os.path.isabs(index_path):
                                try:
                                    # Convert to path relative to the current directory
                                    rel_path = os.path.relpath(index_path, os.path.dirname(base_path))
                                    # Convert backslashes to forward slashes for href
                                    rel_path = rel_path.replace('\\', '/')
                                except Exception:
                                    # If relpath fails, use the absolute path
                                    rel_path = index_path
                            else:
                                rel_path = index_path
                                
                            self.log(f"Adding subdirectory index: {dir_name}, href: {rel_path}")
                            task_item = TaskItem(dir_name, rel_path, is_test=False, parent=self)
                            self.tasks_container_layout.addWidget(task_item)
                            task_count += 1
                    
                    self.log(f"Added {task_count} total tasks")
                    
                    # If no tasks were found at all, show a message
                    if task_count == 0:
                        no_tasks_label = QLabel("No tasks found in this page")
                        no_tasks_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
                        self.tasks_container_layout.addWidget(no_tasks_label)
                else:
                    self.log(f"Index file doesn't exist: {base_path}")
            except Exception as e:
                self.log(f"Error loading HTML content: {str(e)}")
                traceback.print_exc()
                    
        except Exception as e:
            self.log(f"Exception in load_url: {str(e)}")
            traceback.print_exc()


    def open_task(self, href):
        """Open a task file in the browser"""
        if not href or not self.current_base_path:
            return
            
        try:
            # Get the directory containing the base HTML
            base_dir = os.path.dirname(self.current_base_path)
            
            # Resolve the target file path
            if href.startswith('../'):
                # If relative path goes up, join with parent of base dir
                parent_dir = os.path.dirname(base_dir)
                file_path = os.path.normpath(os.path.join(parent_dir, href[3:]))
            else:
                # Otherwise join directly with base dir
                file_path = os.path.normpath(os.path.join(base_dir, href))
            
            self.log(f"Task file path: {file_path}")
            
            if not os.path.exists(file_path):
                self.log(f"File doesn't exist: {file_path}")
                
                # Try looking for the file in nearby directories
                base_parent = os.path.dirname(base_dir)
                
                # Try typical locations
                alternative_paths = [
                    # Try in GitBuilding subdirectory
                    os.path.join(base_parent, 'GitBuilding', os.path.basename(href)),
                    # # Try in docs subdirectory
                    # os.path.join(base_parent, 'docs', os.path.basename(href)),
                    # # Try in orshards subdirectory
                    # os.path.join(base_parent, 'orshards', os.path.basename(href)),
                    # # Try direct in parent
                    # os.path.join(base_parent, os.path.basename(href))
                ]
                
                for alt_path in alternative_paths:
                    self.log(f"Trying alternative path: {alt_path}")
                    if os.path.exists(alt_path):
                        file_path = alt_path
                        self.log(f"Using alternative path: {file_path}")
                        break
                else:
                    self.show_error_message("File Not Found", f"The file does not exist at path: {file_path}")
                    return
                    
            # Open the file based on platform
            self.open_file_in_browser(file_path)
                
        except Exception as e:
            self.log(f"Error opening task: {str(e)}")
            traceback.print_exc()
            self.show_error_message("Open Task", 
                                f"Unable to open browser automatically: {str(e)}\nPlease copy this path:",
                                file_path if 'file_path' in locals() else href)
    def open_documentation(self):
        """Open the GitBuilding documentation in the browser"""
        if not self.current_base_path:
            return
            
        try:
            # Find the GitBuilding index.html path
            gitbuilding_paths = self.find_gitbuilding_paths(self.current_base_path)
            
            if not gitbuilding_paths:
                self.log("No GitBuilding paths found")
                self.show_error_message("Documentation Error", "Cannot find GitBuilding documentation.")
                return
                
            # Use the first valid path
            gitbuilding_path = gitbuilding_paths[0]
            
            if not os.path.exists(gitbuilding_path):
                self.log(f"Documentation doesn't exist: {gitbuilding_path}")
                self.show_error_message("File Not Found", f"Documentation not found at path: {gitbuilding_path}")
                return
                
            # Open the documentation based on platform
            self.open_file_in_browser(gitbuilding_path)
                
        except Exception as e:
            self.log(f"Error opening documentation: {str(e)}")
            traceback.print_exc()
            self.show_error_message("Open Documentation", 
                                f"Unable to open browser automatically: {str(e)}\nPlease copy this path:",
                                gitbuilding_paths[0] if 'gitbuilding_paths' in locals() and gitbuilding_paths else "Documentation path")


    def find_subdirectory_indexes(self, directory):
        """Find all index.html files in subdirectories of the given directory"""
        index_files = []
        try:
            if not os.path.exists(directory) or not os.path.isdir(directory):
                self.log(f"Directory does not exist or is not a directory: {directory}")
                return index_files
                
            # List all subdirectories in the given directory
            subdirs = []
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path):
                    subdirs.append(item_path)
                    
            self.log(f"Found {len(subdirs)} subdirectories in {directory}")
            
            # Check for index.html in each subdirectory
            for subdir in subdirs:
                index_path = os.path.join(subdir, 'index.html')
                if os.path.exists(index_path):
                    # Get the directory name as the task name
                    dir_name = os.path.basename(subdir)
                    index_files.append((dir_name, index_path))
                    self.log(f"Found index.html in {dir_name}")
                    
            return index_files
        except Exception as e:
            self.log(f"Error finding subdirectory indexes: {str(e)}")
            traceback.print_exc()
            return index_files

    def open_file_in_browser(self, file_path):
        """Open a file in the browser based on platform"""
        try:
            if self.is_windows:
                # Windows - use cmd to open browser
                windows_url = "file:///" + file_path.replace('\\', '/')
                subprocess.run(['cmd', '/c', f'start "" "{windows_url}"'], shell=True)
            else:
                # WSL - convert path and use powershell
                try:
                    # First try wslpath
                    process = subprocess.Popen(['wslpath', '-w', file_path],
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            text=True)
                    windows_path, stderr = process.communicate()
                    
                    if process.returncode == 0 and windows_path:
                        windows_url = "file:///" + windows_path.strip().replace('\\', '/')
                        subprocess.run(['powershell.exe', '-Command', f'Start-Process "{windows_url}"'])
                    else:
                        # If wslpath fails, try direct browser launch
                        self.log(f"wslpath failed: {stderr}")
                        subprocess.run(['xdg-open', file_path])
                except Exception as e:
                    self.log(f"Error opening browser: {e}")
                    # Try fallback method
                    subprocess.run(['xdg-open', file_path])
        except Exception as e:
            self.log(f"Error opening file in browser: {e}")
            raise  # Re-raise the exception to be caught by the calling function

    def show_error_message(self, title, message, informative_text=None):
        """Show an error message dialog"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(title)
        msg.setText(message)
        if informative_text:
            msg.setInformativeText(informative_text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def run_test(self):
        """Run test script and show output"""
        if not self.test_script_path or not os.path.exists(self.test_script_path):
            dialog = TestOutputDialog("Test script not found.", self)
            dialog.exec_()
            return
            
        try:
            process = subprocess.Popen([sys.executable, self.test_script_path],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True)
            stdout, stderr = process.communicate()
            output = stdout + stderr
            dialog = TestOutputDialog(output, self)
            dialog.exec_()
        except Exception as e:
            self.log(f"Error running test: {e}")
            dialog = TestOutputDialog(f"Error running test: {str(e)}", self)
            dialog.exec_()

    def go_back(self):
        """Return to the previous view"""
        if self.parent and hasattr(self.parent, 'central_widget'):
            self.parent.central_widget.setCurrentIndex(1)