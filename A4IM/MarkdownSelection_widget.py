from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QTextEdit, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import os


class MarkdownSelectionWidget(QWidget):
    """Widget for selecting and viewing markdown files"""

    def __init__(self, parent, md_files, doc_folder):
        super().__init__()
        self.parent = parent
        self.md_files = md_files
        self.doc_folder = doc_folder
        self.open_viewers = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 30, 20, 30)
        main_layout.setSpacing(20)

        # Title header
        title_header = QLabel("Documentation Viewer")
        title_header.setFont(QFont('Arial', 18, QFont.Bold))
        title_header.setStyleSheet("color: #465775; margin-bottom: 10px;")
        main_layout.addWidget(title_header)

        # Description
        description = QLabel("Select a documentation file to view it.")
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
        self.list_widget.addItems(sorted(self.md_files))
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        content_layout.addWidget(self.list_widget, 1)

        # Right side: Content area and buttons
        right_layout = QVBoxLayout()

        # Content area - show instructions
        content_area = QTextEdit()
        content_area.setReadOnly(True)
        content_area.setStyleSheet("""
            QTextEdit {
                background-color: #f8f8f8;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 10px;
                color: #333;
                font-size: 14px;
            }
        """)
        content_area.setHtml("""
            <div style="text-align: center;">
                <h2>Documentation Files</h2>
                <p>Select a documentation file from the list to view it.</p>
                <p>You can:</p>
                <ul style="text-align: left;">
                    <li>Double-click a file to open it in a new window</li>
                    <li>Select a file and click "Open" button</li>
                    <li>Open multiple files at once</li>
                    <li>Click "Back" to return to System View</li>
                </ul>
            </div>
        """)
        right_layout.addWidget(content_area, 1)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Open button
        open_button = QPushButton("Open")
        open_button.setFixedHeight(40)
        open_button.setStyleSheet("""
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
        open_button.clicked.connect(self.on_open_clicked)
        button_layout.addWidget(open_button)

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
        button_layout.addWidget(back_button)

        right_layout.addLayout(button_layout)
        content_layout.addLayout(right_layout, 2)
        main_layout.addLayout(content_layout)

        self.setLayout(main_layout)

    def on_item_double_clicked(self, item):
        file_path = os.path.join(self.doc_folder, item.text())
        self.open_markdown_file(file_path)

    def on_open_clicked(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            file_path = os.path.join(self.doc_folder, selected_items[0].text())
            self.open_markdown_file(file_path)
        else:
            QMessageBox.warning(self, "No Selection", "Please select a markdown file.")

    def open_markdown_file(self, file_path):
        try:
            from MarkdownViewer_widget import MarkdownViewerWidget

            md_viewer = MarkdownViewerWidget(None, file_path)
            md_viewer.setWindowTitle(f"Documentation - {os.path.basename(file_path)}")
            md_viewer.resize(1000, 700)
            md_viewer.show()

            self.open_viewers.append(md_viewer)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open markdown viewer: {str(e)}")

    def go_back(self):
        if hasattr(self.parent, 'central_widget'):
            for i in range(self.parent.central_widget.count()):
                widget = self.parent.central_widget.widget(i)
                if widget.__class__.__name__ == 'SystemView':
                    self.parent.central_widget.setCurrentWidget(widget)
                    self.parent.central_widget.removeWidget(self)
                    self.deleteLater()
                    break
