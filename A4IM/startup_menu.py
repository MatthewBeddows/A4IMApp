from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class StartupMenu(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.repo_selector = None  # Will hold the repository selector window

    def setup_ui(self):
        self.setWindowTitle("Project Repository Selector")
        self.setGeometry(100, 100, 600, 400)
        
        # Setup the window
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Add a nice header
        header = QLabel("Welcome to Orshards Repository Tool")
        header.setFont(QFont('Arial', 16, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("margin: 20px;")
        layout.addWidget(header)

        # Main menu buttons with repository selector styling
        buttons = [
            ("Select Project", self.open_project_selector),
            ("Create Project", self.create_project),
            ("About", self.show_about),
            ("Exit", self.exit_application)
        ]
        
        for text, callback in buttons:
            button = QPushButton(text)
            button.clicked.connect(callback)
            layout.addWidget(button)

    def create_menu_button(self, text):
        # This method is no longer used as we're using default QPushButton styling
        button = QPushButton(text)
        return button

    def open_project_selector(self):
        """Open the repository selector window"""
        print("Opening project selector...")
        self.hide()  # Hide the startup menu
        
        # Import here to avoid circular imports
        from RepositorySelector_widget import RepositorySelector
        self.repo_selector = RepositorySelector()
        self.repo_selector.show()

    def create_project(self):
        """Placeholder for create project functionality"""
        QMessageBox.information(
            self,
            "Create Project",
            "Create Project functionality will be implemented in a future version."
        )

    def show_about(self):
        """Show information about the application"""
        about_text = """Orshards Repository Tool

A tool for managing and exploring project repositories.

Features:
• Browse and select from available projects
• View project system architecture  
• Access project documentation
• Git repository management

Version 1.0"""
        
        QMessageBox.about(self, "About Orshards Repository Tool", about_text)

    def exit_application(self):
        """Close the application"""
        reply = QMessageBox.question(
            self,
            "Exit Application",
            "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.close()

    def closeEvent(self, event):
        """Handle window close event"""
        reply = QMessageBox.question(
            self,
            "Exit Application", 
            "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Make sure to close any open child windows
            if self.repo_selector:
                self.repo_selector.close()
            event.accept()
        else:
            event.ignore()