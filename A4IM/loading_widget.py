from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap
import os

class LoadingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(50, 50, 50, 50)

        # Set flat white background
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor('white'))
        self.setPalette(palette)

        # Add logo
        logo_label = QLabel()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "images", "A4IM Logo_pink.png")
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(300, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label)

        # Add vertical spacing
        layout.addSpacing(100)

        # Loading message
        self.message_label = QLabel("Loading project information...")
        self.message_label.setFont(QFont('Arial', 14))
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("color: #465775;")
        layout.addWidget(self.message_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #e0e0e0;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background-color: #465775;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Status label for detailed messages
        self.status_label = QLabel("")
        self.status_label.setFont(QFont('Arial', 10))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)

    def update_message(self, message):
        """Update the main loading message"""
        self.message_label.setText(message)

    def update_status(self, status):
        """Update the detailed status message"""
        self.status_label.setText(status)

    def set_progress(self, current, total):
        """Set determinate progress"""
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
        else:
            self.progress_bar.setRange(0, 0)  # Indeterminate