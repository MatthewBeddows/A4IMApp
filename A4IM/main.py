import sys
import os
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QListWidget, QTextEdit, 
                             QLabel, QStackedWidget, QListWidgetItem, QCheckBox,
                             QProgressBar, QMessageBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QFont, QLinearGradient, QColor, QPalette, QIcon
from collections import OrderedDict

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
        
        # setup gitbuilding
        self.git_building_runner = GitBuildingSetup()
        self.git_building_runner.log.connect(self.on_git_building_log)

        self.run_git_building()

        self.show_main_menu()
        
        self.systems = {}
        self.system_order = []  # New attribute to track system order
        self.progress_bar = None  # Initialize progress_bar to None
        self.download_project_architect()

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

    def show_git_building(self, system, module, url):
        self.git_building.load_url(url)
        self.central_widget.setCurrentWidget(self.git_building)

    def download_project_architect(self):
        url = "https://github.com/MatthewBeddows/A4IM-ProjectArchitect/raw/main/architect.txt"
        response = requests.get(url)
        if response.status_code == 200:
            with open("architect.txt", "w") as f:
                f.write(response.text)
            self.parse_project_architect()
        else:
            QMessageBox.critical(self, "Download Error", "Failed to download Project Architect file.")

    def parse_project_architect(self):
        with open("architect.txt", "r") as f:
            content = f.read()
        
        system_addresses = [line.split("] ")[1].strip() for line in content.split("\n") if line.startswith("[system address]")]
        
        # Remove any duplicate "https://" or "github.com" occurrences
        cleaned_addresses = []
        for address in system_addresses:
            if address.count("https://") > 1:
                address = address.replace("https://", "", address.count("https://") - 1)
            if address.count("github.com") > 1:
                address = address.replace("github.com/", "", address.count("github.com") - 1)
            cleaned_addresses.append(address)
        
        self.download_systems(cleaned_addresses)

    def download_systems(self, system_addresses):
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setGeometry(30, 40, 200, 25)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.main_menu.layout().addWidget(self.progress_bar)
        
        self.download_thread = DownloadThread(system_addresses)
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.system_download_finished)
        self.download_thread.start()

    def system_download_finished(self):
        if self.progress_bar:
            self.progress_bar.setParent(None)
            self.progress_bar.deleteLater()
        self.progress_bar = None
        self.parse_system_info()

    def parse_system_info(self):
        self.systems = OrderedDict()
        with open("architect.txt", "r") as f:
            content = f.read()
        
        system_addresses = [line.split("] ")[1].strip() for line in content.split("\n") if line.startswith("[system address]")]
        
        for system_address in system_addresses:
            repo_name = system_address.split('/')[-1]
            system_info_path = os.path.join("Downloaded Repositories", repo_name, "systemInfo.txt")
            
            if os.path.exists(system_info_path):
                with open(system_info_path, 'r') as f:
                    system_content = f.read()
                    system_parts = system_content.split('[System]')[1:]
                    for system_part in system_parts:
                        lines = system_part.strip().split('\n')
                        system_name = lines[0].strip()
                        system_description = '\n'.join(lines[1:]).split('[Module Address]')[0].strip()
                        
                        self.systems[system_name] = {
                            'description': system_description,
                            'modules': OrderedDict(),
                            'module_addresses': []
                        }
                        
                        module_addresses = [line.split("] ")[1].strip() for line in lines if line.startswith("[Module Address]")]
                        self.systems[system_name]['module_addresses'] = module_addresses
                        
                        print(f"Found module addresses for system {system_name}: {module_addresses}")
                        
                        if module_addresses:
                            self.download_modules(system_name, module_addresses)
                        else:
                            print(f"No module addresses found for system: {system_name}")
            else:
                print(f"systemInfo.txt not found for repository: {repo_name}")

        self.process_downloaded_modules()

    def download_modules(self, system_name, module_addresses):
        print(f"Starting download of modules for system: {system_name}")
        print(f"Module addresses to download: {module_addresses}")
        
        if self.progress_bar is None:
            self.progress_bar = QProgressBar(self)
            self.progress_bar.setGeometry(30, 40, 200, 25)
            self.progress_bar.setAlignment(Qt.AlignCenter)
            self.main_menu.layout().addWidget(self.progress_bar)
        
        self.current_download_thread = DownloadThread(module_addresses)
        
        # Disconnect any existing connections first
        try:
            self.current_download_thread.progress.disconnect()
            self.current_download_thread.finished.disconnect()
        except TypeError:
            # Ignore if there were no existing connections
            pass
        
        # Connect new signals
        self.current_download_thread.progress.connect(self.update_progress)
        self.current_download_thread.finished.connect(lambda: self.module_download_finished(system_name))
        
        self.current_download_thread.start()
        print(f"Download thread started for modules of system: {system_name}")


    def module_download_finished(self, system_name):
        print(f"Module download finished for system: {system_name}")
        if self.progress_bar:
            self.progress_bar.setParent(None)
            self.progress_bar.deleteLater()
            self.progress_bar = None
        
        # Safely disconnect the progress signal if it exists
        if hasattr(self, 'current_download_thread'):
            try:
                self.current_download_thread.progress.disconnect(self.update_progress)
            except TypeError:
                # Signal was not connected, so we can ignore this error
                pass
        
        self.parse_module_info(system_name)
        #QMessageBox.information(self, "Download Complete", f"Modules for system '{system_name}' have been downloaded and parsed successfully.")

    def process_downloaded_modules(self):
        for system_name in self.system_order:
            self.parse_module_info(system_name)

    def parse_module_info(self, system_name):
        print(f"Parsing module info for system: {system_name}")
        download_dir = "Downloaded Repositories"
        
        module_addresses = self.systems[system_name]['module_addresses']
        
        for module_address in module_addresses:
            repo_name = module_address.split('/')[-1]
            module_info_path = os.path.join(download_dir, repo_name, "moduleInfo.txt")
            
            if os.path.exists(module_info_path):
                print(f"Found moduleInfo.txt in: {module_info_path}")
                with open(module_info_path, 'r') as f:
                    content = f.read()
                    module_parts = content.split('[Module]')[1:]
                    for module_part in module_parts:
                        module_lines = module_part.strip().split('\n')
                        module_name = module_lines[0].strip()
                        module_description = '\n'.join(module_lines[1:]).strip()
                        self.systems[system_name]['modules'][module_name] = module_description
                        print(f"Added module {module_name} to system {system_name}")
            else:
                print(f"moduleInfo.txt not found in: {module_info_path}")
        
        print(f"Finished parsing module info for system: {system_name}")

    def update_progress(self, value):
        if self.progress_bar is not None:
            self.progress_bar.setValue(value)
        else:
            print(f"Progress update: {value}%")


if __name__ == "__main__":
    app = QApplication(sys.argv + ['--disable-seccomp-filter-sandbox'])
    window = GitFileReaderApp()
    window.show()
    sys.exit(app.exec_())