from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                           QCheckBox, QScrollArea, QLabel, QFrame, QTextEdit,
                           QDialog, QDialogButtonBox, QStackedWidget)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt, QProcess
from PyQt5.QtGui import QFont
from bs4 import BeautifulSoup
import os
import sys

class TestOutputDialog(QDialog):
    def __init__(self, output, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test Output")
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Output display
        output_text = QTextEdit()
        output_text.setReadOnly(True)
        output_text.setPlainText(output)
        layout.addWidget(output_text)
        
        # OK button
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

class TestView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Test name
        self.name_label = QLabel()
        self.name_label.setFont(QFont('Arial', 16, QFont.Bold))
        self.name_label.setStyleSheet("color: #465775;")
        layout.addWidget(self.name_label)
        
        # Test description
        self.description = QTextEdit()
        self.description.setReadOnly(True)
        self.description.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                background-color: white;
                color: #465775;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.description)
        
        # Run test button
        self.run_button = QPushButton("Run Test")
        self.run_button.setFixedHeight(40)
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: #465775;
                border: none;
                border-radius: 20px;
                color: white;
                font-size: 14px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #566985;
            }
            QPushButton:pressed {
                background-color: #364765;
            }
        """)
        layout.addWidget(self.run_button)
        layout.addStretch()

class GitBuildingWindow(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.tasks = {}  # Store task checkboxes
        self.test_checkbox = None  # Store test checkbox separately
        self.current_gitbuilding_url = None  # Store current GitBuilding URL
        self.test_script_path = None  # Store path to test script
        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Left panel for tasks
        task_panel = QWidget()
        task_panel.setFixedWidth(250)  # Fixed width for task panel
        task_panel.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border-right: 1px solid #ddd;
            }
        """)
        
        task_layout = QVBoxLayout(task_panel)
        task_layout.setContentsMargins(10, 20, 10, 20)
        task_layout.setSpacing(10)

        # Task list header
        header = QLabel("Tasks")
        header.setFont(QFont('Arial', 14, QFont.Bold))
        header.setStyleSheet("color: #465775; padding-bottom: 10px;")
        task_layout.addWidget(header)

        # Add separator between header and tasks
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #ddd;")
        task_layout.addWidget(separator)

        # Scrollable area for tasks
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        self.task_container = QWidget()
        self.task_container_layout = QVBoxLayout(self.task_container)
        self.task_container_layout.setSpacing(8)
        
        # Test checkbox will be added here when needed
        self.test_checkbox = QCheckBox("Run Tests")
        self.test_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                padding: 5px;
                color: #465775;
                font-weight: bold;
            }
            QCheckBox:hover {
                background-color: #e0e0e0;
                border-radius: 5px;
            }
        """)
        self.test_checkbox.hide()  # Hidden by default
        self.task_container_layout.addWidget(self.test_checkbox)
        
        # Add separator after test checkbox
        self.test_separator = QFrame()
        self.test_separator.setFrameShape(QFrame.HLine)
        self.test_separator.setStyleSheet("background-color: #ddd;")
        self.test_separator.hide()  # Hidden by default
        self.task_container_layout.addWidget(self.test_separator)

        self.task_container_layout.addStretch()
        scroll.setWidget(self.task_container)
        task_layout.addWidget(scroll)

        # Back button in task panel
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
            QPushButton:hover {
                background-color: #566985;
            }
            QPushButton:pressed {
                background-color: #364765;
            }
        """)
        back_button.clicked.connect(self.go_back)
        task_layout.addWidget(back_button)

        # Right panel stack
        self.right_panel = QStackedWidget()
        
        # Web view widget
        self.web_view = QWebEngineView()
        self.right_panel.addWidget(self.web_view)
        
        # Test view widget
        self.test_view = TestView()
        self.test_view.run_button.clicked.connect(self.run_test)
        self.right_panel.addWidget(self.test_view)

        # Add panels to main layout
        main_layout.addWidget(task_panel)
        main_layout.addWidget(self.right_panel, stretch=1)
        
        self.setLayout(main_layout)

    def load_url(self, url):
        original_url = url  # Store the original URL
        self.current_gitbuilding_url = url
        
        if url.startswith('file:///'):
            # Get the base path and ensure it starts with /
            base_path = url.replace('file:///', '')
            if not base_path.startswith('/'):
                base_path = '/' + base_path

            # Check for tests folder and TestsInfo.txt
            docs_dir = os.path.dirname(base_path)
            repo_dir = os.path.dirname(docs_dir)
            tests_dir = os.path.join(repo_dir, 'tests')
            tests_info_path = os.path.join(tests_dir, 'TestsInfo.txt')
            
            print(f"Checking for tests at: {tests_info_path}")  # Debug print
            
            if os.path.exists(tests_dir) and os.path.exists(tests_info_path):
                # Parse TestsInfo.txt
                with open(tests_info_path, 'r') as f:
                    content = f.read()
                    
                test_name = None
                test_description = None
                
                for line in content.split('\n'):
                    if line.startswith('[TestName]'):
                        test_name = line[len('[TestName]'):].strip()
                    elif line.startswith('[TestDescription]'):
                        test_description = line[len('[TestDescription]'):].strip()
                
                if test_name and test_description:
                    self.test_checkbox.setText(test_name)
                    self.test_view.name_label.setText(test_name)
                    self.test_view.description.setPlainText(test_description)
                    
                # Look for Python files in tests directory
                python_files = [f for f in os.listdir(tests_dir) if f.endswith('.py')]
                print(f"Found Python files: {python_files}")  # Debug print
                
                if python_files:
                    # Use the first Python file found
                    self.test_script_path = os.path.join(tests_dir, python_files[0])
                    print(f"Using test script: {self.test_script_path}")  # Debug print
                
                self.test_checkbox.show()
                self.test_separator.show()
                self.test_checkbox.stateChanged.connect(self.handle_test_checkbox)
            else:
                self.test_checkbox.hide()
                self.test_separator.hide()
            
                
            # Split the path and look for docs/index.html
            path_parts = base_path.split('/')
            docs_index = path_parts.index('docs') if 'docs' in path_parts else -1
            
            if docs_index != -1:
                # Reconstruct the path up to the docs folder
                docs_path = '/' + '/'.join(path_parts[:docs_index + 1])
                gitbuilding_dir = os.path.join(docs_path, 'GitBuilding')
                gitbuilding_path = os.path.join(gitbuilding_dir, 'index.html')
                
                print(f"Looking for GitBuilding at: {gitbuilding_path}")  # Debug print
                
                if os.path.exists(gitbuilding_path):
                    # Load and parse the HTML to find active menu items
                    with open(gitbuilding_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                        
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Clear existing tasks
                    for i in reversed(range(self.task_container_layout.count())):
                        widget = self.task_container_layout.itemAt(i).widget()
                        if widget is not None and widget not in [self.test_checkbox, self.test_separator]:
                            widget.deleteLater()
                    self.tasks.clear()

                    # Find the active section
                    active_section = soup.find('li', class_='active')
                    
                    if active_section:
                        sub_nav = active_section.find('ul', class_='sub-nav-list')
                        
                        if sub_nav:
                            for item in sub_nav.find_all('li'):
                                link = item.find('a')
                                if link and 'BOM' not in link.text:
                                    task_name = link.text.strip()
                                    checkbox = QCheckBox(task_name)
                                    checkbox.setStyleSheet("""
                                        QCheckBox {
                                            font-size: 13px;
                                            padding: 5px;
                                        }
                                        QCheckBox:hover {
                                            background-color: #e0e0e0;
                                            border-radius: 5px;
                                        }
                                    """)
                                    checkbox.stateChanged.connect(self.handle_task_checkbox)
                                    self.tasks[task_name] = checkbox
                                    # Insert checkboxes after test separator
                                    self.task_container_layout.insertWidget(
                                        self.task_container_layout.count() - 1, checkbox)

                    # Create GitBuilding URL
                    gitbuilding_url = 'file://' + gitbuilding_path
                    if not gitbuilding_url.startswith('file:///'):
                        gitbuilding_url = gitbuilding_url.replace('file://', 'file:///')
                        
                    print(f"Loading URL: {gitbuilding_url}")  # Debug print
                    
                    self.current_gitbuilding_url = gitbuilding_url
                    self.web_view.setUrl(QUrl(gitbuilding_url))
                else:
                    print(f"GitBuilding not found, loading original: {original_url}")  # Debug print
                    self.web_view.setUrl(QUrl(original_url))
            else:
                print(f"No docs folder found, loading original: {original_url}")  # Debug print
                self.web_view.setUrl(QUrl(original_url))
        else:
            print(f"Not a file URL, loading as is: {original_url}")  # Debug print
            self.web_view.setUrl(QUrl(original_url))
    




    def handle_test_checkbox(self, state):
        if state == Qt.Checked:
            self.right_panel.setCurrentWidget(self.test_view)
            # Uncheck other checkboxes
            for checkbox in self.tasks.values():
                checkbox.setChecked(False)
        else:
            self.right_panel.setCurrentWidget(self.web_view)
            if self.current_gitbuilding_url:
                self.web_view.setUrl(QUrl(self.current_gitbuilding_url))

    def handle_task_checkbox(self, state):
        checkbox = self.sender()
        if state == Qt.Checked:
            # Uncheck test checkbox and show web view
            self.test_checkbox.setChecked(False)
            self.right_panel.setCurrentWidget(self.web_view)
            # Uncheck other task checkboxes
            for other_checkbox in self.tasks.values():
                if other_checkbox != checkbox:
                    other_checkbox.setChecked(False)

    def run_test(self):
        if self.test_script_path and os.path.exists(self.test_script_path):
            process = QProcess()
            process.setProcessChannelMode(QProcess.MergedChannels)
            
            output = []
            
            def handle_output():
                output.append(str(process.readAll(), 'utf-8'))
            
            def process_finished():
                full_output = ''.join(output)
                dialog = TestOutputDialog(full_output, self)
                dialog.exec_()
            
            process.readyReadStandardOutput.connect(handle_output)
            process.finished.connect(process_finished)
            
            # Run the test script
            python_executable = sys.executable
            process.start(python_executable, [self.test_script_path])
        else:
            dialog = TestOutputDialog("Test script not found.", self)
            dialog.exec_()
            
    def go_back(self):
        if self.parent and self.parent.central_widget:
            self.parent.central_widget.setCurrentWidget(self.parent.system_view)