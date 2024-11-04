from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                           QCheckBox, QScrollArea, QLabel, QFrame, QTextEdit,
                           QDialog, QDialogButtonBox, QStackedWidget)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt, QProcess
from PyQt5.QtGui import QFont, QCursor
from bs4 import BeautifulSoup
import os
import sys

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

class TestView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        self.name_label = QLabel()
        self.name_label.setFont(QFont('Arial', 16, QFont.Bold))
        self.name_label.setStyleSheet("color: #465775;")
        layout.addWidget(self.name_label)
        
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
            QPushButton:hover { background-color: #566985; }
            QPushButton:pressed { background-color: #364765; }
        """)
        layout.addWidget(self.run_button)
        layout.addStretch()

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
            # Find the GitBuildingWindow instance
            parent = self
            while parent is not None:
                if isinstance(parent, GitBuildingWindow):
                    break
                parent = parent.parent()

            if parent is not None:
                if self.is_test:
                    parent.set_current_view('test')
                else:
                    parent.set_current_view('web', self.href)

class GitBuildingWindow(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.current_gitbuilding_url = None
        self.test_script_path = None
        self.setup_ui()


    def setup_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Left panel for tasks
        task_panel = QWidget()
        task_panel.setFixedWidth(250)
        task_panel.setStyleSheet("QWidget { background-color: #f5f5f5; border-right: 1px solid #ddd; }")
        
        task_layout = QVBoxLayout(task_panel)
        task_layout.setContentsMargins(10, 20, 10, 20)
        task_layout.setSpacing(10)

        # Header
        header = QLabel("Tasks")
        header.setFont(QFont('Arial', 14, QFont.Bold))
        header.setStyleSheet("color: #465775; padding-bottom: 10px;")
        task_layout.addWidget(header)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #ddd;")
        task_layout.addWidget(separator)

        # Scrollable task area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        self.task_container = QWidget()
        self.task_container_layout = QVBoxLayout(self.task_container)
        self.task_container_layout.setSpacing(8)
        
        # Test item with direct parent reference
        self.test_item = TaskItem("Run Tests", is_test=True, parent=self)
        self.test_item.hide()
        self.task_container_layout.addWidget(self.test_item)
        
        # Test separator
        self.test_separator = QFrame()
        self.test_separator.setFrameShape(QFrame.HLine)
        self.test_separator.setStyleSheet("background-color: #ddd;")
        self.test_separator.hide()
        self.task_container_layout.addWidget(self.test_separator)
        
        self.task_container_layout.addStretch()
        scroll.setWidget(self.task_container)
        task_layout.addWidget(scroll)

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
        task_layout.addWidget(back_button)

        # Right panel setup
        self.right_panel = QStackedWidget()
        self.web_view = QWebEngineView()
        self.test_view = TestView()
        self.test_view.run_button.clicked.connect(self.run_test)
        
        self.right_panel.addWidget(self.web_view)
        self.right_panel.addWidget(self.test_view)

        main_layout.addWidget(task_panel)
        main_layout.addWidget(self.right_panel, stretch=1)
        self.setLayout(main_layout)
        print("UI setup completed")

    def load_url(self, url):
        print(f"Loading URL: {url}")
        self.current_gitbuilding_url = url
        if not url.startswith('file:///'):
            self.web_view.setUrl(QUrl(url))
            return

        base_path = url.replace('file:///', '')
        if not base_path.startswith('/'):
            base_path = '/' + base_path

        # Check for tests
        docs_dir = os.path.dirname(base_path)
        repo_dir = os.path.dirname(docs_dir)
        tests_dir = os.path.join(repo_dir, 'tests')
        tests_info_path = os.path.join(tests_dir, 'TestsInfo.txt')
        
        # Handle test information
        if os.path.exists(tests_dir) and os.path.exists(tests_info_path):
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
                self.test_item.label.setText(test_name)
                self.test_view.name_label.setText(test_name)
                self.test_view.description.setPlainText(test_description)
            
            python_files = [f for f in os.listdir(tests_dir) if f.endswith('.py')]
            if python_files:
                self.test_script_path = os.path.join(tests_dir, python_files[0])
            
            self.test_item.show()
            self.test_separator.show()
            print("Test item shown")
        else:
            self.test_item.hide()
            self.test_separator.hide()
            print("No test found")

        # Load GitBuilding content
        path_parts = base_path.split('/')
        if 'docs' in path_parts:
            docs_index = path_parts.index('docs')
            docs_path = '/' + '/'.join(path_parts[:docs_index + 1])
            gitbuilding_path = os.path.join(docs_path, 'GitBuilding', 'index.html')
            
            if os.path.exists(gitbuilding_path):
                with open(gitbuilding_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Clear existing tasks
                for i in reversed(range(self.task_container_layout.count())):
                    widget = self.task_container_layout.itemAt(i).widget()
                    if isinstance(widget, TaskItem) and widget != self.test_item:
                        widget.deleteLater()

                # Create new tasks
                active_section = soup.find('li', class_='active')
                if active_section and (sub_nav := active_section.find('ul', class_='sub-nav-list')):
                    for item in sub_nav.find_all('li'):
                        if link := item.find('a'):
                            if 'BOM' not in link.text:
                                task_item = TaskItem(link.text.strip(), link.get('href'), is_test=False, parent=self)
                                self.task_container_layout.insertWidget(
                                    self.task_container_layout.count() - 1, task_item)
                                print(f"Added task: {link.text.strip()}")

                gitbuilding_url = 'file://' + gitbuilding_path
                if not gitbuilding_url.startswith('file:///'):
                    gitbuilding_url = gitbuilding_url.replace('file://', 'file:///')
                self.current_gitbuilding_url = gitbuilding_url
                self.web_view.setUrl(QUrl(gitbuilding_url))
            else:
                self.web_view.setUrl(QUrl(url))
        else:
            self.web_view.setUrl(QUrl(url))

    def set_current_view(self, view_type, href=None):
        """Switch between views and handle navigation"""
        print(f"Switching to {view_type} view")
        
        if view_type == 'test':
            self.right_panel.setCurrentWidget(self.test_view)
        elif view_type == 'web':
            self.right_panel.setCurrentWidget(self.web_view)
            if href:
                self.navigate_to_page(href)

    def navigate_to_page(self, href):
        """Navigate to a specific page in the web view"""
        print(f"Navigating to: {href}")
        if href and self.current_gitbuilding_url:
            base_url = os.path.dirname(self.current_gitbuilding_url)
            new_url = os.path.join(base_url, href)
            if not new_url.startswith('file:///'):
                new_url = new_url.replace('file://', 'file:///')
            print(f"Full URL: {new_url}")
            self.web_view.setUrl(QUrl(new_url))

    def run_test(self):
        print("Running test")
        if self.test_script_path and os.path.exists(self.test_script_path):
            process = QProcess()
            process.setProcessChannelMode(QProcess.MergedChannels)
            output = []
            
            def handle_output():
                output.append(str(process.readAll(), 'utf-8'))
            
            def process_finished():
                dialog = TestOutputDialog(''.join(output), self)
                dialog.exec_()
            
            process.readyReadStandardOutput.connect(handle_output)
            process.finished.connect(process_finished)
            print(f"Starting test script: {self.test_script_path}")
            process.start(sys.executable, [self.test_script_path])
        else:
            print("Test script not found")
            dialog = TestOutputDialog("Test script not found.", self)
            dialog.exec_()
            
    def go_back(self):
        print("Going back")
        if self.parent and self.parent.central_widget:
            self.parent.central_widget.setCurrentWidget(self.parent.system_view)

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    class DummyParent:
        def __init__(self):
            self.central_widget = None
            self.system_view = None
    
    window = GitBuildingWindow(DummyParent())
    window.show()
    sys.exit(app.exec_())