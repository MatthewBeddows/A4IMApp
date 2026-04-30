from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QTextBrowser, QMessageBox, QListWidgetItem
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont
import markdown
from MarkdownViewer_widget import fix_root_relative_paths
import os
import re
import subprocess
import sys
import datetime


SCRIPT_EXTENSIONS = {'.py', '.sh', '.js', '.r', '.rb'}

RUNNERS = {
    '.py': [sys.executable],
    '.sh': ['bash'],
    '.js': ['node'],
    '.r':  ['Rscript'],
    '.rb': ['ruby'],
}

SCRIPT_ICONS = {
    '.py': '🐍',
    '.sh': '⚙',
    '.js': 'JS',
    '.r':  'R',
    '.rb': '💎',
}


def _extract_script_error(output):
    """Return a short, human-readable error summary from script output."""
    low = output.lower()
    if 'permission denied' in low:
        return ("Serial port permission denied.\n"
                "Run the 'Setup Flash Permissions' script from the Firmware doc, "
                "then unplug and replug the board.")
    if 'no boards detected' in low or 'no arduino' in low:
        return ("No Arduino board was detected.\n"
                "Check the USB connection. On WSL2, run 'usbipd attach' in PowerShell first.")
    if 'hex file not found' in low or 'firmware file not found' in low:
        return ("Firmware file (firmware.hex) not found.\n"
                "Export it from Arduino IDE via Sketch > Export Compiled Binary "
                "and place it in the scripts/ folder.")
    if 'board.json not found' in low:
        return "board.json is missing from the scripts/ folder."
    if 'timeout' in low or 'not in sync' in low:
        return ("The board did not respond.\n"
                "Check that the correct board type, programmer, and baud rate are set in board.json.")
    if 'no such file or directory' in low:
        return "A required file was not found. Check the log for details."
    if output.strip():
        # Return last non-empty line of output as a hint
        lines = [l.strip() for l in output.splitlines() if l.strip()]
        last = lines[-1] if lines else ''
        return f"The script reported an error.\nLast output: {last}\n\nSee the log file for full details."
    return "The script exited with an error. See the log file for details."


def find_script_links(md_file_path):
    """Parse a markdown file and return list of (label, abs_path) for script links."""
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return []

    base_dir = os.path.dirname(md_file_path)
    results = []
    for match in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', content):
        label = match.group(1)
        href = match.group(2)
        if not href.startswith('http'):
            ext = os.path.splitext(href)[1].lower()
            if ext in SCRIPT_EXTENSIONS:
                abs_path = os.path.normpath(os.path.join(base_dir, href))
                results.append((label, abs_path))
    return results


class MarkdownSelectionWidget(QWidget):
    """Widget for selecting and viewing markdown files"""

    def __init__(self, parent, md_files, doc_folder):
        super().__init__()
        self.parent = parent
        self.md_files = md_files
        self.doc_folder = doc_folder
        self.open_viewers = []
        self.current_scripts = []  # list of (label, abs_path) for selected file
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 30, 20, 30)
        main_layout.setSpacing(20)

        title_header = QLabel("Documentation Viewer")
        title_header.setFont(QFont('Arial', 18, QFont.Bold))
        title_header.setStyleSheet("color: #465775; margin-bottom: 10px;")
        main_layout.addWidget(title_header)

        description = QLabel("Select a documentation file to view it.")
        description.setFont(QFont('Arial', 12))
        description.setStyleSheet("color: #666; margin-bottom: 10px;")
        main_layout.addWidget(description)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Left side: file list
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
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        content_layout.addWidget(self.list_widget, 1)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

        # Right side
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)

        # Markdown preview area
        self.content_area = QTextBrowser()
        self.content_area.setOpenLinks(False)
        self.content_area.setStyleSheet("""
            QTextBrowser {
                background-color: #f8f8f8;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 10px;
                color: #333;
                font-size: 13px;
            }
        """)
        right_layout.addWidget(self.content_area, 1)

        # Linked Scripts section (hidden until a file with scripts is selected)
        self.scripts_label = QLabel("Linked Scripts")
        self.scripts_label.setFont(QFont('Arial', 11, QFont.Bold))
        self.scripts_label.setStyleSheet("color: #465775; margin-top: 5px;")
        self.scripts_label.hide()
        right_layout.addWidget(self.scripts_label)

        self.scripts_list = QListWidget()
        self.scripts_list.setMaximumHeight(120)
        self.scripts_list.setStyleSheet("""
            QListWidget {
                background-color: #f0f4f8;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #ddd;
            }
            QListWidget::item:selected {
                background-color: #465775;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #dce8f5;
            }
        """)
        self.scripts_list.hide()
        right_layout.addWidget(self.scripts_list)

        self.run_script_button = QPushButton("Run Script")
        self.run_script_button.setFixedHeight(36)
        self.run_script_button.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                border: none;
                border-radius: 18px;
                color: white;
                font-size: 12px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #388e3c; }
            QPushButton:pressed { background-color: #1b5e20; }
            QPushButton:disabled { background-color: #aaa; }
        """)
        self.run_script_button.clicked.connect(self.on_run_script_clicked)
        self.run_script_button.hide()
        right_layout.addWidget(self.run_script_button)

        # Open / Back buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

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

        back_button = QPushButton("Close")
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

        # Preview and populate scripts for the initially selected item
        if self.list_widget.count() > 0:
            first_file = os.path.join(self.doc_folder, self.list_widget.item(0).text())
            self.preview_markdown(first_file)
            self.current_scripts = find_script_links(first_file)
            self.update_scripts_panel()

    def on_item_clicked(self, item):
        file_path = os.path.join(self.doc_folder, item.text())
        self.preview_markdown(file_path)
        self.current_scripts = find_script_links(file_path)
        self.update_scripts_panel()

    def preview_markdown(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()

            md_content = re.sub(r'\{[^}]*\}', '', md_content)
            html_body = markdown.markdown(md_content, extensions=['extra', 'nl2br'])
            html_body = re.sub(r'<img ', '<img style="max-width:100%;height:auto;" ', html_body)
            html_body = fix_root_relative_paths(html_body, file_path)

            styled = f"""<html><head><style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                h1,h2,h3 {{ color: #465775; }}
                code {{ background:#f0f0f0; padding:2px 4px; border-radius:3px; }}
                pre {{ background:#f0f0f0; padding:10px; border-radius:5px; }}
            </style></head><body>{html_body}</body></html>"""

            base_url = QUrl.fromLocalFile(os.path.dirname(file_path) + os.sep)
            self.content_area.document().setBaseUrl(base_url)
            self.content_area.setHtml(styled)
        except Exception as e:
            self.content_area.setPlainText(f"Could not preview file:\n{e}")

    def update_scripts_panel(self):
        self.scripts_list.clear()
        if self.current_scripts:
            for label, abs_path in self.current_scripts:
                ext = os.path.splitext(abs_path)[1].lower()
                icon = SCRIPT_ICONS.get(ext, '')
                display = f"{icon}  {label}  ({os.path.basename(abs_path)})"
                self.scripts_list.addItem(display)
            self.scripts_label.show()
            self.scripts_list.show()
            self.run_script_button.show()
        else:
            self.scripts_label.hide()
            self.scripts_list.hide()
            self.run_script_button.hide()

    def on_run_script_clicked(self):
        idx = self.scripts_list.currentRow()
        if idx < 0:
            if self.current_scripts:
                idx = 0  # default to first script if none selected
            else:
                return
        _, file_path = self.current_scripts[idx]
        self.run_script(file_path)

    def run_script(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        cmd = RUNNERS.get(ext)
        if not cmd:
            QMessageBox.warning(self, "Unsupported", f"No runner configured for {ext} files.")
            return
        try:
            abs_file_path = os.path.abspath(file_path)
            script_dir = os.path.dirname(abs_file_path)
            var_dir = os.path.join(script_dir, 'var')
            os.makedirs(var_dir, exist_ok=True)

            stem = os.path.splitext(os.path.basename(abs_file_path))[0]
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(var_dir, f"{stem}_{timestamp}.txt")

            env = os.environ.copy()
            tools_base = os.path.dirname(os.path.abspath(__file__))
            if getattr(sys, 'frozen', False):
                avrdude_dir = sys._MEIPASS
                avrdude_name = 'avrdude.exe' if sys.platform.startswith('win') else 'avrdude'
                env['A4IM_AVRDUDE'] = os.path.join(avrdude_dir, avrdude_name)
                env['A4IM_AVRDUDE_CONF'] = os.path.join(avrdude_dir, 'avrdude.conf')
            else:
                if sys.platform.startswith('win'):
                    env['A4IM_AVRDUDE'] = os.path.join(tools_base, 'tools', 'avrdude', 'windows', 'avrdude.exe')
                    env['A4IM_AVRDUDE_CONF'] = os.path.join(tools_base, 'tools', 'avrdude', 'windows', 'avrdude.conf')
                else:
                    env['A4IM_AVRDUDE'] = os.path.join(tools_base, 'tools', 'avrdude', 'linux', 'avrdude_Linux_64bit', 'bin', 'avrdude')
                    env['A4IM_AVRDUDE_CONF'] = os.path.join(tools_base, 'tools', 'avrdude', 'linux', 'avrdude_Linux_64bit', 'etc', 'avrdude.conf')

            result = subprocess.run(
                cmd + [abs_file_path],
                capture_output=True,
                text=True,
                cwd=script_dir,
                env=env
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

            combined_output = (result.stdout or '') + (result.stderr or '')

            if result.returncode == 0:
                QMessageBox.information(
                    self, "Script Completed",
                    f"{os.path.basename(abs_file_path)} completed successfully.\n\n"
                    f"Full log saved to:\n{output_path}"
                )
            else:
                # Extract a user-friendly reason from the output
                reason = _extract_script_error(combined_output)
                QMessageBox.warning(
                    self, "Script Failed",
                    f"{os.path.basename(abs_file_path)} did not complete successfully.\n\n"
                    f"{reason}\n\n"
                    f"Full log saved to:\n{output_path}"
                )
        except Exception as e:
            QMessageBox.critical(
                self, "Script Error",
                f"Could not run script:\n{str(e)}\n\n"
                "Check that the script file exists and is a valid Python file."
            )

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
            md_viewer.setAttribute(Qt.WA_DeleteOnClose, True)
            md_viewer.setWindowTitle(f"Documentation - {os.path.basename(file_path)}")
            md_viewer.resize(1000, 700)
            md_viewer.show()

            self.open_viewers.append(md_viewer)

            # Also keep a reference in SystemView so the window survives
            # after this selection widget is closed
            if hasattr(self.parent, 'system_view'):
                sv = self.parent.system_view
                if not hasattr(sv, '_open_viewers'):
                    sv._open_viewers = []
                sv._open_viewers.append(md_viewer)
                md_viewer.destroyed.connect(
                    lambda: sv._open_viewers.remove(md_viewer) if md_viewer in sv._open_viewers else None
                )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open markdown viewer: {str(e)}")

    def go_back(self):
        self.close()
