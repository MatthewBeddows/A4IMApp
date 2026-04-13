from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QMessageBox, QScrollArea
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap
import os
import re
import subprocess
import webbrowser


class BrowserOpenerThread(QThread):
    """Thread for opening browsers/URLs without blocking the UI"""
    error_signal = pyqtSignal(str)

    def __init__(self, url, is_wsl=False, is_file=True):
        super().__init__()
        self.url = url
        self.is_wsl = is_wsl
        self.is_file = is_file

    def run(self):
        try:
            if self.is_wsl:
                # WSL handling
                try:
                    powershell_command = f'Start-Process "{self.url}"'
                    subprocess.run(['powershell.exe', '-Command', powershell_command])
                except Exception as e:
                    try:
                        subprocess.run(['explorer.exe', self.url])
                    except Exception as e2:
                        self.error_signal.emit(self.url)
            else:
                # Standard handling
                if self.is_file:
                    file_url = 'file://' + os.path.abspath(self.url)
                    webbrowser.open(file_url)
                else:
                    webbrowser.open(self.url)
        except Exception as e:
            self.error_signal.emit(f"Failed to open browser: {str(e)}")

class MainMenuWidget(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.browser_thread = None  # Keep reference to browser thread
        self.setup_ui()

    def setup_ui(self):
        root_layout = QVBoxLayout()
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Set flat white background
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor('white'))
        self.setPalette(palette)

        # ── Top bar: logo ──────────────────────────────────────────────────
        top_bar = QWidget()
        top_bar.setStyleSheet("background-color: white;")
        top_bar_layout = QVBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(40, 30, 40, 20)

        title_image = QLabel()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "images", "A4IM Logo_pink.png")
        pixmap = QPixmap(logo_path)
        scaled_pixmap = pixmap.scaled(300, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        title_image.setPixmap(scaled_pixmap)
        title_image.setAlignment(Qt.AlignCenter)
        top_bar_layout.addWidget(title_image)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet("background-color: #d9d9d9; border: none;")
        line.setFixedHeight(1)
        top_bar_layout.addWidget(line)

        root_layout.addWidget(top_bar)

        # ── Body: info panel (left) + buttons (right) ──────────────────────
        body = QWidget()
        body_layout_h = QHBoxLayout(body)
        body_layout_h.setContentsMargins(40, 30, 40, 30)
        body_layout_h.setSpacing(40)

        # Left: project info
        info_widget = QWidget()
        info_widget.setStyleSheet("""
            QWidget {
                background-color: #f8f8f8;
                border-radius: 8px;
            }
        """)
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(20, 20, 20, 20)
        info_layout.setSpacing(12)

        self.proj_name_label = QLabel("Loading...")
        self.proj_name_label.setFont(QFont('Arial', 18, QFont.Bold))
        self.proj_name_label.setStyleSheet("color: #465775; background: transparent;")
        self.proj_name_label.setWordWrap(True)
        info_layout.addWidget(self.proj_name_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #d9d9d9; border: none;")
        sep.setFixedHeight(1)
        info_layout.addWidget(sep)

        self.proj_desc_label = QLabel("")
        self.proj_desc_label.setFont(QFont('Arial', 12))
        self.proj_desc_label.setStyleSheet("color: #555; background: transparent;")
        self.proj_desc_label.setWordWrap(True)
        self.proj_desc_label.setAlignment(Qt.AlignTop)
        info_layout.addWidget(self.proj_desc_label)

        info_layout.addStretch()
        body_layout_h.addWidget(info_widget, 2)

        # Right: buttons
        btn_widget = QWidget()
        btn_layout = QVBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(15)
        btn_layout.setAlignment(Qt.AlignCenter)

        buttons = []
        if self.check_architect_documentation():
            buttons.append(("Project Overview", self.show_project_overview))
        buttons.extend([
            ("System View", self.parent.show_system_view),
            ("Refresh Hierarchy", self.parent.refresh_hierarchy),
            ("Exit", self.parent.close)
        ])

        # About button — shown only if root repo has a README
        self.about_button = self.create_menu_button("About")
        self.about_button.clicked.connect(self.open_about)
        self.about_button.hide()
        btn_layout.addWidget(self.about_button)

        for text, callback in buttons:
            btn = self.create_menu_button(text)
            btn.clicked.connect(callback)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        body_layout_h.addWidget(btn_widget, 1)

        root_layout.addWidget(body, 1)
        self.setLayout(root_layout)

    def refresh_project_info(self):
        """Update the project name and description once modules are loaded."""
        name, desc = self._get_project_info()
        self.proj_name_label.setText(name)
        self.proj_desc_label.setText(desc if desc else "No description available.")
        self.about_button.setVisible(self.find_root_readme() is not None)

    def find_root_readme(self):
        """Return path to README.md at the root repo, or None."""
        try:
            repo_dir = os.path.join("Downloaded Repositories", self.parent.repo_folder)
            repo_name = self.parent.initial_repo_url.rstrip('/').split('/')[-1].replace('.git', '')
            module_dir = os.path.join(repo_dir, repo_name)
            if not os.path.exists(module_dir):
                return None
            for fname in os.listdir(module_dir):
                if fname.lower() == 'readme.md':
                    return os.path.join(module_dir, fname)
        except Exception:
            pass
        return None

    def open_about(self):
        """Open the root repo README in the markdown viewer."""
        readme = self.find_root_readme()
        if not readme:
            QMessageBox.information(self, "About", "No README found for this project.")
            return
        try:
            from MarkdownViewer_widget import MarkdownViewerWidget
            viewer = MarkdownViewerWidget(None, readme)
            viewer.setWindowTitle("About")
            viewer.resize(900, 700)
            viewer.setAttribute(Qt.WA_DeleteOnClose, True)
            viewer.show()
            viewer.raise_()
            if not hasattr(self, '_about_viewers'):
                self._about_viewers = []
            self._about_viewers.append(viewer)
            viewer.destroyed.connect(
                lambda: self._about_viewers.remove(viewer) if viewer in self._about_viewers else None
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open README:\n{e}")

    def _get_project_info(self):
        """Return (name, description) for the root module."""
        try:
            modules = getattr(self.parent, 'modules', {})
            if not modules:
                return "Project", ""
            first_key = next(iter(modules))
            data = modules[first_key]
            name = re.sub(r'\[.*?\]', '', first_key).strip()
            description = re.sub(r'\[.*?\]', '', data.get('description', '')).strip()
            return name, description
        except Exception:
            return "Project", ""

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
        """Check if a module has markdown files in src/doc folder"""
        if not os.path.exists(module_dir):
            return False

        doc_folder = os.path.join(module_dir, "src", "doc")

        if not os.path.exists(doc_folder):
            return False

        try:
            for filename in os.listdir(doc_folder):
                if filename.lower().endswith('.md'):
                    return True
        except:
            pass

        return False

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
        """Open the first markdown file from src/doc folder"""
        try:
            repo_dir = os.path.join("Downloaded Repositories", self.parent.repo_folder)
            repo_name = self.parent.initial_repo_url.split('/')[-1]
            module_dir = os.path.join(repo_dir, repo_name)
            doc_folder = os.path.join(module_dir, "src", "doc")

            if not os.path.exists(doc_folder):
                QMessageBox.information(self, "Documentation Not Found",
                                    "No src/doc folder found for this project.")
                return

            # Find all markdown files
            md_files = []
            for filename in os.listdir(doc_folder):
                if filename.lower().endswith('.md'):
                    md_files.append(filename)

            if not md_files:
                QMessageBox.information(self, "No Markdown Files",
                                    "No markdown files found in src/doc folder.")
                return

            # Open the first markdown file
            first_md = sorted(md_files)[0]
            file_path = os.path.join(doc_folder, first_md)

            from MarkdownViewer_widget import MarkdownViewerWidget

            md_viewer = MarkdownViewerWidget(None, file_path)
            md_viewer.setWindowTitle(f"Project Overview - {first_md}")
            md_viewer.resize(1000, 700)
            md_viewer.show()

            # Store reference to prevent garbage collection
            if not hasattr(self, 'overview_viewers'):
                self.overview_viewers = []
            self.overview_viewers.append(md_viewer)

        except Exception as e:
            print(f"Error opening project overview: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open project overview: {str(e)}")

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
        """Open the HTML file in the default browser (threaded)"""
        if not doc_path:
            QMessageBox.warning(self, "Error", "No documentation URL available.")
            return

        # Wait for existing thread to finish if still running
        if self.browser_thread and self.browser_thread.isRunning():
            print("Browser thread already running, waiting for it to finish...")
            self.browser_thread.wait(1000)  # Wait up to 1 second
            if self.browser_thread.isRunning():
                print("Thread still running, ignoring click")
                return

        try:
            is_wsl = self.is_wsl()

            if is_wsl:
                # Create the correct WSL URL format
                if doc_path.startswith('/'):
                    wsl_url = f"file://wsl.localhost/Ubuntu{doc_path}"
                else:
                    wsl_url = f"file://wsl.localhost/Ubuntu/{doc_path}"

                print(f"Opening browser with WSL URL: {wsl_url}")

                # Use threaded browser opener
                self.browser_thread = BrowserOpenerThread(wsl_url, is_wsl=True, is_file=True)
                self.browser_thread.error_signal.connect(lambda msg: QMessageBox.information(
                    self, "Browser URL", f"Please copy and paste this URL into your browser:\n\n{wsl_url}"
                ))
                self.browser_thread.start()
            else:
                # For non-WSL environments, use threaded browser opener
                self.browser_thread = BrowserOpenerThread(doc_path, is_wsl=False, is_file=True)
                self.browser_thread.error_signal.connect(lambda msg: QMessageBox.warning(
                    self, "Error", f"Could not open HTML file: {msg}"
                ))
                self.browser_thread.start()

        except Exception as e:
            print(f"Error opening HTML file: {e}")
            QMessageBox.warning(self, "Error", f"Could not open HTML file: {str(e)}")

    def show_intro(self):
        print("Intro button clicked")

    def show_about(self):
        print("About button clicked")