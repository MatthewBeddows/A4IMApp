import sys
import os
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt
from collections import OrderedDict
from mainmenu_widget import MainMenuWidget
from gitbuilding_widget import GitBuildingWindow
from systemview_widget import SystemView
from download_thread import DownloadThread
from gitbuilding_setup import GitBuildingSetup
from ArchitectSelector_widget import ArchitectSelector


# Auto detect devices on the network
# ethernet, usb connection

class GitFileReaderApp(QMainWindow):
    def __init__(self, architect_url,architect_folder):
        super().__init__()
        self.setWindowTitle("Git File Reader")
        self.setGeometry(100, 100, 800, 600)

        # Store the selected architect URL
        self.architect_url = architect_url
        self.architect_folder = architect_folder


        # Central widget setup
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        
        # Initialize UI components
        self.main_menu = MainMenuWidget(self)
        self.system_view = SystemView(self)
        self.git_building = GitBuildingWindow(self)
        
        # Add widgets to the stacked widget
        self.central_widget.addWidget(self.main_menu)
        self.central_widget.addWidget(self.system_view)
        self.central_widget.addWidget(self.git_building)
        
        # Set up GitBuilding
        self.git_building_runner = GitBuildingSetup()
        self.git_building_runner.log.connect(self.on_git_building_log)
        self.run_git_building()
    
        # Hide the main menu initially
        self.main_menu.hide()
        
        # Initialize modules data structure
        self.modules = {}  # Stores modules and submodules
        self.module_order = []  # Tracks the order of top-level modules
        self.progress_bar = None  # Initialize progress_bar to None
        
        # Track loading state
        self.loading_complete = False
        self.pending_downloads = 0  # Track number of active downloads

        # Keep track of active threads
        self.active_threads = []

        # Start downloading the project architect
        self.download_project_architect()

    def download_project_architect(self):
        download_dir = os.path.join(os.getcwd(), "Downloaded Repositories")
        architect_dir = os.path.join(download_dir, self.architect_folder)
        clone_folder = os.path.join(architect_dir, "ProjectArchitect")

        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        if not os.path.exists(architect_dir):
            os.makedirs(architect_dir)

        if os.path.exists(architect_dir):
            import shutil
            shutil.rmtree(architect_dir)
            os.makedirs(architect_dir)

        try:
            import pygit2
            # Clone with pygit2
            pygit2.clone_repository(
                self.architect_url,
                clone_folder
            )
            
            architect_path = os.path.join(clone_folder, "architect.txt")
            if os.path.exists(architect_path):
                with open(architect_path, 'r') as f:
                    content = f.read()
                
                self.parse_project_architect(architect_path)
            else:
                QMessageBox.critical(self, "File Error", "architect.txt not found in cloned repository.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")


    def run_git_building(self):
        self.git_building_runner.run()
    
    def on_git_building_log(self, message):
        print(message)
    
    def show_main_menu(self):
        if self.loading_complete:
            self.central_widget.setCurrentWidget(self.main_menu)
    
    def show_system_view(self):
        self.system_view.populate_modules(self.modules)
        self.central_widget.setCurrentWidget(self.system_view)
    
    def show_git_building(self, module, submodule, url):
        self.git_building.load_url(url)
        self.central_widget.setCurrentWidget(self.git_building)

    def download_modules(self, parent_module_path, module_addresses):
        self.pending_downloads += 1
        
        if self.progress_bar is None:
            self.progress_bar = QProgressBar(self)
            self.progress_bar.setGeometry(30, 40, 200, 25)
            self.progress_bar.setAlignment(Qt.AlignCenter)
            self.main_menu.layout().addWidget(self.progress_bar)
        else:
            self.progress_bar.setParent(None)
            self.progress_bar.deleteLater()
            self.progress_bar = QProgressBar(self)
            self.progress_bar.setGeometry(30, 40, 200, 25)
            self.progress_bar.setAlignment(Qt.AlignCenter)
            self.main_menu.layout().addWidget(self.progress_bar)
        
        download_thread = DownloadThread(module_addresses, self.architect_folder)
        download_thread.progress.connect(self.update_progress)
        download_thread.finished.connect(lambda: self.module_download_finished(parent_module_path, download_thread))
        download_thread.start()
        self.active_threads.append(download_thread)

    def module_download_finished(self, parent_module_path, thread):
        if thread in self.active_threads:
            self.active_threads.remove(thread)

        self.pending_downloads -= 1
        self.parse_module_info(parent_module_path)
        
        if self.pending_downloads == 0:
            if self.progress_bar:
                self.progress_bar.setParent(None)
                self.progress_bar.deleteLater()
                self.progress_bar = None
            
            self.loading_complete = True
            self.main_menu.show()
            self.show_main_menu()

    def parse_project_architect(self, architect_path):
        with open(architect_path, "r") as f:
            content = f.read()
            
        module_addresses = []
        for line in content.split("\n"):
            if line.lower().startswith("[module address]"):
                parts = line.split("]", 1)
                if len(parts) > 1:
                    address = parts[1].strip()
                    module_addresses.append(address)

        cleaned_addresses = []
        for address in module_addresses:
            if address.count("https://") > 1:
                address = address.replace("https://", "", address.count("https://") - 1)
            if address.count("github.com") > 1:
                address = address.replace("github.com/", "", address.count("github.com") - 1)
            cleaned_addresses.append(address)
        
        self.loading_complete = False
        self.pending_downloads = 0
        self.download_modules(parent_module_path=None, module_addresses=cleaned_addresses)

    def parse_module_info(self, parent_module_path):
        architect_dir = os.path.join("Downloaded Repositories", self.architect_folder)
        
        if parent_module_path is None:
            architect_file = os.path.join(architect_dir, "ProjectArchitect", "architect.txt")
            with open(architect_file, "r") as f:
                content = f.read()
            
            module_addresses = []
            for line in content.split("\n"):
                if line.lower().startswith("[module address]"):
                    parts = line.split("]", 1)
                    if len(parts) > 1:
                        address = parts[1].strip()
                        module_addresses.append(address)
        else:
            current_module = self.modules
            for name in parent_module_path:
                current_module = current_module[name]
            module_addresses = current_module.get('submodule_addresses', [])

        for module_address in module_addresses:
            repo_name = module_address.split('/')[-1]
            module_info_path = os.path.join(architect_dir, repo_name, "moduleInfo.txt")
            
            if os.path.exists(module_info_path):
                with open(module_info_path, 'r') as f:
                    content = f.read()

                    module_name = None
                    module_description = ""
                    submodule_addresses = []
                    lines = content.split('\n')
                    i = 0
                    in_requirements_section = False
                    while i < len(lines):
                        line = lines[i].strip()
                        if line.lower().startswith('[module name]'):
                            module_name = line.split(']', 1)[1].strip()
                            i += 1
                        elif line.lower().startswith('[module info]'):
                            module_description = line.split(']', 1)[1].strip()
                            i += 1
                            while i < len(lines) and not lines[i].startswith('['):
                                module_description += ' ' + lines[i].strip()
                                i += 1
                        elif line.lower().startswith('[requirements]'):
                            in_requirements_section = True
                            i += 1
                        # Check for module address with case insensitivity
                        elif line.lower().startswith('[module address]'):
                            parts = line.split(']', 1)
                            if len(parts) > 1:
                                address = parts[1].strip()
                                submodule_addresses.append(address)
                            i += 1
                        elif line.startswith('['):
                            in_requirements_section = False
                            i += 1
                        else:
                            i += 1

                    # Debug output for submodule addresses
                    print(f"Found {len(submodule_addresses)} submodule addresses for {repo_name}")
                    for addr in submodule_addresses:
                        print(f"  - {addr}")

                    if module_name is None:
                        print(f"Module name not found in {module_info_path}")
                        continue

                    docs_path = os.path.join(architect_dir, repo_name, "orshards", "index.html")
                    has_docs = os.path.exists(docs_path)

                    module_data = {
                        'description': module_description.strip(),
                        'submodules': OrderedDict(),
                        'submodule_addresses': submodule_addresses,
                        'repository': {
                            'name': repo_name,
                            'address': module_address,
                            'docs_path': docs_path if has_docs else None
                        }
                    }

                    if parent_module_path is None:
                        self.modules[module_name] = module_data
                        self.module_order.append(module_name)
                    else:
                        current_module = self.modules
                        for module_name_in_path in parent_module_path:
                            current_module = current_module[module_name_in_path]
                            if 'submodules' not in current_module:
                                current_module['submodules'] = OrderedDict()
                        current_module['submodules'][module_name] = module_data

                    if submodule_addresses:
                        current_module_path = parent_module_path.copy() if parent_module_path else []
                        current_module_path.append(module_name)
                        self.download_modules(current_module_path, submodule_addresses)
            else:
                print(f"moduleInfo.txt not found for repository: {repo_name}")
        
    def update_progress(self, value):
        if self.progress_bar is not None:
            self.progress_bar.setValue(value)
        else:
            print(f"Progress update: {value}%")

def main():
    app = QApplication(sys.argv + ['--disable-seccomp-filter-sandbox'])
    selector = ArchitectSelector()
    selector.show()
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())

