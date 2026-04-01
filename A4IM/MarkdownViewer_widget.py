from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTextBrowser, QMessageBox
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont
import os
import re
import markdown
import subprocess
import sys
import datetime
import webbrowser


SCRIPT_EXTENSIONS = {'.py', '.sh', '.js', '.r', '.rb'}

RUNNERS = {
    '.py': [sys.executable],
    '.sh': ['bash'],
    '.js': ['node'],
    '.r':  ['Rscript'],
    '.rb': ['ruby'],
}


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
        self.text_browser.setOpenLinks(False)
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.anchorClicked.connect(self.handle_link_clicked)
        self.text_browser.setFont(QFont("Arial", 10))
        layout.addWidget(self.text_browser)

        self.setLayout(layout)

    def handle_link_clicked(self, url):
        href = url.toString()

        # Resolve relative paths
        if url.isLocalFile():
            resolved = url.toLocalFile()
        elif not href.startswith('http'):
            base_dir = os.path.dirname(self.file_path)
            resolved = os.path.normpath(os.path.join(base_dir, href))
        else:
            webbrowser.open(href)
            return

        ext = os.path.splitext(resolved)[1].lower()
        if ext in SCRIPT_EXTENSIONS:
            self.run_script(resolved)
        else:
            webbrowser.open(resolved)

    def run_script(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        cmd = RUNNERS.get(ext)
        if not cmd:
            QMessageBox.warning(self, "Unsupported", f"No runner configured for {ext} files.")
            return
        try:
            script_dir = os.path.dirname(file_path)
            var_dir = os.path.join(script_dir, 'var')
            os.makedirs(var_dir, exist_ok=True)

            stem = os.path.splitext(os.path.basename(file_path))[0]
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(var_dir, f"{stem}_{timestamp}.txt")

            result = subprocess.run(
                cmd + [file_path],
                capture_output=True,
                text=True,
                cwd=script_dir
            )

            with open(output_path, 'w') as f:
                f.write(f"Script: {file_path}\n")
                f.write(f"Run at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Return code: {result.returncode}\n")
                f.write("=" * 60 + "\n")
                if result.stdout:
                    f.write("STDOUT:\n")
                    f.write(result.stdout)
                if result.stderr:
                    f.write("STDERR:\n")
                    f.write(result.stderr)

            status = "Completed" if result.returncode == 0 else "FAILED"
            QMessageBox.information(
                self, f"Script {status}",
                f"{os.path.basename(file_path)} finished (code {result.returncode}).\n\nOutput saved to:\n{output_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run script:\n{str(e)}")

    def load_markdown(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()

            # Strip {width=...} / {height=...} attribute syntax before parsing
            md_content = re.sub(r'\{[^}]*\}', '', md_content)

            html_content = markdown.markdown(
                md_content,
                extensions=['extra', 'codehilite', 'toc', 'nl2br']
            )

            # Set max-width on all images via inline style injection
            html_content = re.sub(
                r'<img ',
                '<img style="max-width:100%;height:auto;" ',
                html_content
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

            base_url = QUrl.fromLocalFile(os.path.dirname(os.path.abspath(self.file_path)) + os.sep)
            self.text_browser.document().setBaseUrl(base_url)
            self.text_browser.setHtml(styled_html)

        except Exception as e:
            error_msg = f"Error loading markdown file: {str(e)}"
            self.text_browser.setHtml(f"<p style='color: red;'>{error_msg}</p>")
            QMessageBox.critical(self, "Error", error_msg)
