from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTextBrowser, QMessageBox
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont
import os
import markdown


class MarkdownViewerWidget(QWidget):
    """Widget for viewing markdown files with HTML rendering"""

    def __init__(self, parent, file_path):
        super().__init__()
        self.parent = parent
        self.file_path = file_path
        self.init_ui()
        self.load_markdown()

    def init_ui(self):
        layout = QVBoxLayout()

        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setFont(QFont("Arial", 10))
        layout.addWidget(self.text_browser)

        self.setLayout(layout)

    def load_markdown(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()

            # Convert markdown to HTML
            html_content = markdown.markdown(
                md_content,
                extensions=['extra', 'codehilite', 'toc', 'nl2br']
            )

            styled_html = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        padding: 20px;
                        color: #333;
                    }}
                    h1, h2, h3, h4, h5, h6 {{
                        color: #2c3e50;
                        margin-top: 24px;
                        margin-bottom: 16px;
                    }}
                    h1 {{
                        border-bottom: 2px solid #eee;
                        padding-bottom: 10px;
                    }}
                    h2 {{
                        border-bottom: 1px solid #eee;
                        padding-bottom: 8px;
                    }}
                    code {{
                        background-color: #f4f4f4;
                        padding: 2px 4px;
                        border-radius: 3px;
                        font-family: 'Courier New', monospace;
                    }}
                    pre {{
                        background-color: #f4f4f4;
                        padding: 10px;
                        border-radius: 5px;
                        overflow-x: auto;
                    }}
                    pre code {{
                        background-color: transparent;
                        padding: 0;
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 16px 0;
                    }}
                    th, td {{
                        border: 1px solid #ddd;
                        padding: 8px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #f2f2f2;
                        font-weight: bold;
                    }}
                    tr:nth-child(even) {{
                        background-color: #f9f9f9;
                    }}
                    blockquote {{
                        border-left: 4px solid #ddd;
                        padding-left: 16px;
                        margin-left: 0;
                        color: #666;
                    }}
                    a {{
                        color: #3498db;
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                    img {{
                        max-width: 100%;
                        height: auto;
                    }}
                    ul, ol {{
                        padding-left: 30px;
                    }}
                    li {{
                        margin: 8px 0;
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """

            self.text_browser.setHtml(styled_html)

        except Exception as e:
            error_msg = f"Error loading markdown file: {str(e)}"
            self.text_browser.setHtml(f"<p style='color: red;'>{error_msg}</p>")
            QMessageBox.critical(self, "Error", error_msg)
