import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QListWidget, QTextEdit, 
                             QLabel, QStackedWidget, QListWidgetItem, QCheckBox,
                             QProgressBar, QMessageBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QFont, QLinearGradient, QColor, QPalette, QIcon

from mainmenu_widget import MainMenuWidget
from gitbuilding_widget import GitBuildingWindow
from systemview_widget import SystemView
from moduleview_widget import ModuleView
from gitbuilding_widget import GitBuildingWindow
from download_thread import DownloadThread
from gitbuilding_setup import GitBuildingSetup

class GitFileReaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Git File Reader")
        self.setGeometry(100, 100, 800, 600)
        
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_menu = MainMenuWidget(self)
        self.system_view = SystemView(self)
        self.module_view = ModuleView(self)
        self.git_building = GitBuildingWindow(self)
        
        self.central_widget.addWidget(self.main_menu)
        self.central_widget.addWidget(self.system_view)
        self.central_widget.addWidget(self.module_view)
        self.central_widget.addWidget(self.git_building)
        
        #setup gitbuilding
        self.git_building_runner = GitBuildingSetup()
        self.git_building_runner.log.connect(self.on_git_building_log)

        self.run_git_building()

        self.show_main_menu()
        
        self.systems = {}
        self.download_repositories()

    def run_git_building(self):
        # You might want to disable UI elements here
        self.git_building_runner.run()


    def on_git_building_log(self, message):
        # You can update a QTextEdit or similar widget to show the log
        print(message)  # For now, just print to console

    def show_main_menu(self):
        self.central_widget.setCurrentWidget(self.main_menu)

    def show_system_view(self):
        self.system_view.populate_systems(self.systems)
        self.central_widget.setCurrentWidget(self.system_view)

    def show_module_view(self, system):
        self.module_view.load_modules(system)
        self.central_widget.setCurrentWidget(self.module_view)

    def show_git_building(self, system, module):
        self.git_building.load_module(system, module)
        self.central_widget.setCurrentWidget(self.git_building)

    def download_repositories(self):
        repos = [
            "MatthewBeddows/ModuleDemo1",
            "MatthewBeddows/ModuleDemo2",
            "MatthewBeddows/ModuleDemo3"
        ]
        
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setGeometry(30, 40, 200, 25)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.main_menu.layout().addWidget(self.progress_bar)
        
        self.download_thread = DownloadThread(repos)
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def download_finished(self):
        self.progress_bar.setParent(None)
        self.progress_bar.deleteLater()
        self.progress_bar = None
        self.parse_module_info()
        QMessageBox.information(self, "Download Complete", "Repositories have been downloaded and parsed successfully.")

    def parse_module_info(self):
        download_dir = "Downloaded Repositories"
        for repo in os.listdir(download_dir):
            module_info_path = os.path.join(download_dir, repo, "moduleInfo.txt")
            if os.path.exists(module_info_path):
                with open(module_info_path, 'r') as f:
                    content = f.read()
                    systems = content.split('[System]')[1:]
                    for system in systems:
                        system_parts = system.split('[Module]')
                        system_name = system_parts[0].split('\n')[0].strip()
                        system_description = system_parts[0].split('\n', 1)[1].strip()
                        
                        if system_name not in self.systems:
                            self.systems[system_name] = {'description': system_description, 'modules': {}}
                        
                        for module_part in system_parts[1:]:
                            module_lines = module_part.strip().split('\n')
                            module_name = module_lines[0].strip()
                            module_description = '\n'.join(module_lines[1:]).strip()
                            self.systems[system_name]['modules'][module_name] = module_description

if __name__ == "__main__":
    app = QApplication(sys.argv + ['--disable-seccomp-filter-sandbox'])
    window = GitFileReaderApp()
    window.show()
    sys.exit(app.exec_())
