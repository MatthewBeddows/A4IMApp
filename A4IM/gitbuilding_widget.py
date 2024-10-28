from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QCheckBox, QScrollArea, QLabel, QFrame)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QFont, QColor, QPalette
import os
from bs4 import BeautifulSoup

class GitBuildingWindow(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.tasks = {}  # Store task checkboxes
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

        # Scrollable area for tasks
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        self.task_container = QWidget()
        self.task_container_layout = QVBoxLayout(self.task_container)
        self.task_container_layout.setSpacing(8)
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

        # Right panel for web view
        web_panel = QVBoxLayout()
        web_panel.setContentsMargins(0, 0, 0, 0)
        web_panel.setSpacing(0)
        
        self.web_view = QWebEngineView()
        web_panel.addWidget(self.web_view)

        # Add panels to main layout
        main_layout.addWidget(task_panel)
        main_layout.addLayout(web_panel, stretch=1)
        
        self.setLayout(main_layout)

    def load_url(self, url):
        original_url = url  # Keep original URL for web view
        
        if url.startswith('file:///'):
            # Get the base path and ensure it starts with /
            base_path = url.replace('file:///', '')
            if not base_path.startswith('/'):
                base_path = '/' + base_path
                
            # Split the path and look for docs/index.html
            path_parts = base_path.split('/')
            docs_index = path_parts.index('docs') if 'docs' in path_parts else -1
            
            if docs_index != -1:
                # Reconstruct the path up to the docs folder
                docs_path = '/' + '/'.join(path_parts[:docs_index + 1])
                gitbuilding_dir = os.path.join(docs_path, 'GitBuilding')
                gitbuilding_path = os.path.join(gitbuilding_dir, 'index.html')
                
                if os.path.exists(gitbuilding_path):
                    # Load and parse the HTML to find active menu items
                    with open(gitbuilding_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                        
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Clear existing tasks
                    for i in reversed(range(self.task_container_layout.count())):
                        widget = self.task_container_layout.itemAt(i).widget()
                        if widget is not None:
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
                                    self.tasks[task_name] = checkbox
                                    self.task_container_layout.insertWidget(
                                        self.task_container_layout.count() - 1, checkbox)

                # Load the original file in the web view
                gitbuilding_url = os.path.join(os.path.dirname(original_url), 'GitBuilding', 'index.html')
                self.web_view.setUrl(QUrl(gitbuilding_url))
            else:
                self.web_view.setUrl(QUrl(original_url))
        else:
            self.web_view.setUrl(QUrl(original_url))

    def go_back(self):
        if self.parent and self.parent.central_widget:
            self.parent.central_widget.setCurrentWidget(self.parent.system_view)