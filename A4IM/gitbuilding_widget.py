from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                           QCheckBox, QScrollArea, QLabel, QFrame, QTextEdit,
                           QDialog, QDialogButtonBox, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QCursor
from bs4 import BeautifulSoup
import os
import sys
import subprocess

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
        self.setup_ui()

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

    def load_url(self, url):
        if not url.startswith('file:///'):
            return

        base_path = url.replace('file:///', '')
        if not base_path.startswith('/'):
            base_path = '/' + base_path
            
        self.current_base_path = base_path

        # Process test information
        orshards_dir = os.path.dirname(base_path)
        repo_dir = os.path.dirname(orshards_dir)
        tests_dir = os.path.join(repo_dir, 'tests')
        tests_info_path = os.path.join(tests_dir, 'TestsInfo.txt')
        
        if os.path.exists(tests_dir) and os.path.exists(tests_info_path):
            with open(tests_info_path, 'r') as f:
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
        else:
            self.tests_header.hide()
            self.test_separator.hide()
            self.test_item.hide()

        # Load GitBuilding content
        path_parts = base_path.split('/')
        if 'orshards' in path_parts:
            orshards_index = path_parts.index('orshards')
            orshards_path = '/' + '/'.join(path_parts[:orshards_index + 1])
            gitbuilding_path = os.path.join(orshards_path, 'GitBuilding', 'index.html')
            
            if os.path.exists(gitbuilding_path):
                try:
                    with open(gitbuilding_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    active_section = soup.find('li', class_='active')
                    sub_nav = active_section.find('ul', class_='sub-nav-list') if active_section else None
                    
                    if active_section and sub_nav:
                        for i in reversed(range(self.tasks_container_layout.count())):
                            widget = self.tasks_container_layout.itemAt(i).widget()
                            if isinstance(widget, TaskItem):
                                widget.deleteLater()
                        
                        for item in sub_nav.find_all('li'):
                            if link := item.find('a'):
                                if 'BOM' not in link.text:
                                    task_item = TaskItem(link.text.strip(), link.get('href'), is_test=False, parent=self)
                                    self.tasks_container_layout.addWidget(task_item)
                
                except Exception as e:
                    print(f"Error loading content: {str(e)}")


    def open_task(self, href):
        if href and self.current_base_path:
            path_parts = self.current_base_path.split('/')
            if 'orshards' in path_parts:
                orshards_index = path_parts.index('orshards')
                orshards_path = '/' + '/'.join(path_parts[:orshards_index + 1])
                file_path = os.path.join(orshards_path, 'GitBuilding', href)
                
                if os.path.exists(file_path):
                    try:
                        # Convert WSL path to Windows path
                        process = subprocess.Popen(['wslpath', '-w', file_path],
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE,
                                                text=True)
                        windows_path, stderr = process.communicate()
                        windows_path = windows_path.strip()
                        
                        if process.returncode == 0 and windows_path:
                            windows_url = "file:///" + windows_path.replace('\\', '/')
                            subprocess.run(['powershell.exe', '-Command', f'Start-Process "{windows_url}"'])
                        else:
                            raise Exception(f"Failed to convert path: {stderr}")
                    except Exception as e:
                        msg = QMessageBox(self)
                        msg.setIcon(QMessageBox.Information)
                        msg.setWindowTitle("Open Task")
                        msg.setText("Unable to open browser automatically.\nPlease copy this path:")
                        msg.setInformativeText(file_path)
                        msg.setStandardButtons(QMessageBox.Ok)
                        msg.exec_()

    def open_documentation(self):
        if self.current_base_path:
            path_parts = self.current_base_path.split('/')
            if 'orshards' in path_parts:
                orshards_index = path_parts.index('orshards')
                orshards_path = '/' + '/'.join(path_parts[:orshards_index + 1])
                gitbuilding_path = os.path.join(orshards_path, 'GitBuilding', 'index.html')
                
                if os.path.exists(gitbuilding_path):
                    try:
                        # Convert WSL path to Windows path
                        process = subprocess.Popen(['wslpath', '-w', gitbuilding_path],
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE,
                                                text=True)
                        windows_path, stderr = process.communicate()
                        windows_path = windows_path.strip()
                        
                        if process.returncode == 0 and windows_path:
                            windows_url = "file:///" + windows_path.replace('\\', '/')
                            subprocess.run(['powershell.exe', '-Command', f'Start-Process "{windows_url}"'])
                        else:
                            raise Exception(f"Failed to convert path: {stderr}")
                    except Exception as e:
                        msg = QMessageBox(self)
                        msg.setIcon(QMessageBox.Information)
                        msg.setWindowTitle("Open Documentation")
                        msg.setText("Unable to open browser automatically.\nPlease copy this path:")
                        msg.setInformativeText(gitbuilding_path)
                        msg.setStandardButtons(QMessageBox.Ok)
                        msg.exec_()
    def run_test(self):
        if self.test_script_path and os.path.exists(self.test_script_path):
            process = subprocess.Popen([sys.executable, self.test_script_path],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True)
            stdout, stderr = process.communicate()
            output = stdout + stderr
            dialog = TestOutputDialog(output, self)
            dialog.exec_()
        else:
            dialog = TestOutputDialog("Test script not found.", self)
            dialog.exec_()

    def go_back(self):
        if self.parent and hasattr(self.parent, 'central_widget'):
            self.parent.central_widget.setCurrentIndex(1)