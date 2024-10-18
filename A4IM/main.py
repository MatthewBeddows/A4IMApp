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

class GitFileReaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Git File Reader")
        self.setGeometry(100, 100, 800, 600)
        
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
    
        # Show the main menu
        self.show_main_menu()
        
        # Initialize modules data structure
        self.modules = {}  # Stores modules and submodules
        self.module_order = []  # Tracks the order of top-level modules
        self.progress_bar = None  # Initialize progress_bar to None

        # Keep track of active threads
        self.active_threads = []

        # Start downloading the project architect
        self.download_project_architect()
    
    def run_git_building(self):
        # Run GitBuilding setup (you might want to disable UI elements here)
        self.git_building_runner.run()
    
    def on_git_building_log(self, message):
        # Update a QTextEdit or similar widget to show the log
        print(message)  # For now, just print to console
    
    def show_main_menu(self):
        self.central_widget.setCurrentWidget(self.main_menu)
    
    def show_system_view(self):
        # Pass the modules data structure to the system view
        self.system_view.populate_modules(self.modules)
        self.central_widget.setCurrentWidget(self.system_view)
    
    def show_git_building(self, module, submodule, url):
        # Load the URL in the GitBuilding widget
        self.git_building.load_url(url)
        self.central_widget.setCurrentWidget(self.git_building)
    
    def download_project_architect(self):
        # Define the target folder where the repositories will be downloaded
        download_dir = os.path.join(os.getcwd(), "Downloaded Repositories")
        clone_folder = os.path.join(download_dir, "ArchitectRepository")
    
        # Ensure the "Downloaded Repositories" directory exists
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
    
        # Ensure the Architect repository folder exists
        if not os.path.exists(clone_folder):
            os.makedirs(clone_folder)
    
        # Download the architect.txt file from the repository
        url = "https://github.com/MatthewBeddows/A4IM-ProjectArchitect/raw/main/architect.txt"
        response = requests.get(url)
        if response.status_code == 200:
            with open("architect.txt", "w") as f:
                f.write(response.text)
            self.parse_project_architect()
        else:
            QMessageBox.critical(self, "Download Error", "Failed to download Project Architect file.")
    
    def parse_project_architect(self):
        # Read the architect.txt file and extract module addresses
        with open("architect.txt", "r") as f:
            content = f.read()
        
        # Parse '[module address]' lines
        module_addresses = [line.split("] ")[1].strip() for line in content.split("\n") if line.startswith("[module address]")]

        # Clean up addresses
        cleaned_addresses = []
        for address in module_addresses:
            if address.count("https://") > 1:
                address = address.replace("https://", "", address.count("https://") - 1)
            if address.count("github.com") > 1:
                address = address.replace("github.com/", "", address.count("github.com") - 1)
            cleaned_addresses.append(address)
        
        # Start downloading top-level modules
        self.download_modules(parent_module_path=None, module_addresses=cleaned_addresses)
    
    def download_modules(self, parent_module_path, module_addresses):
        # Initialize or reset the progress bar
        if self.progress_bar is None:
            self.progress_bar = QProgressBar(self)
            self.progress_bar.setGeometry(30, 40, 200, 25)
            self.progress_bar.setAlignment(Qt.AlignCenter)
            self.main_menu.layout().addWidget(self.progress_bar)
        else:
            # Remove existing progress bar and create a new one
            self.progress_bar.setParent(None)
            self.progress_bar.deleteLater()
            self.progress_bar = QProgressBar(self)
            self.progress_bar.setGeometry(30, 40, 200, 25)
            self.progress_bar.setAlignment(Qt.AlignCenter)
            self.main_menu.layout().addWidget(self.progress_bar)
        
        # Start the download thread for the modules
        download_thread = DownloadThread(module_addresses)
        download_thread.progress.connect(self.update_progress)
        download_thread.finished.connect(lambda: self.module_download_finished(parent_module_path, download_thread))
        download_thread.start()
        self.active_threads.append(download_thread)  # Keep a strong reference

    def module_download_finished(self, parent_module_path, thread):
        # Remove the thread from active threads
        if thread in self.active_threads:
            self.active_threads.remove(thread)

        # Remove the progress bar after download completes
        if self.progress_bar:
            self.progress_bar.setParent(None)
            self.progress_bar.deleteLater()
            self.progress_bar = None
        # Parse the moduleInfo.txt files
        self.parse_module_info(parent_module_path)
    
    def parse_module_info(self, parent_module_path):
        """
        Parses moduleInfo.txt files and updates the modules data structure.
        If parent_module_path is None, it parses top-level modules from architect.txt.
        """
        download_dir = "Downloaded Repositories"
        if parent_module_path is None:
            # Parsing top-level modules from architect.txt
            with open("architect.txt", "r") as f:
                content = f.read()
            module_addresses = [line.split("] ")[1].strip() for line in content.split("\n") if line.startswith("[module address]")]
        else:
            # Parsing submodules from parent module
            # Navigate to the parent module in self.modules
            current_module = self.modules
            for module_name_in_path in parent_module_path:
                # Access the module by name
                current_module = current_module[module_name_in_path]
            module_addresses = current_module.get('submodule_addresses', [])

        for module_address in module_addresses:
            # Extract the repository name from the address
            repo_name = module_address.split('/')[-1]
            module_info_path = os.path.join(download_dir, repo_name, "moduleInfo.txt")
            
            if os.path.exists(module_info_path):
                with open(module_info_path, 'r') as f:
                    content = f.read()

                    # Parse the moduleInfo.txt file
                    module_name = None
                    module_description = ""
                    submodule_addresses = []
                    lines = content.split('\n')
                    i = 0
                    in_submodules_section = False
                    while i < len(lines):
                        line = lines[i].strip()
                        if line.startswith('[Module Name]'):
                            # The module name is on the same line
                            module_name = line[len('[Module Name]'):].strip()
                            i += 1
                        elif line.startswith('[Module Info]'):
                            # The module description is on the same line
                            module_description = line[len('[Module Info]'):].strip()
                            i += 1
                            # Collect additional lines until the next section
                            while i < len(lines) and not lines[i].startswith('['):
                                module_description += ' ' + lines[i].strip()
                                i += 1
                        elif line.startswith('[Submodules]'):
                            # Start collecting submodule addresses
                            in_submodules_section = True
                            i += 1
                        elif in_submodules_section and line.startswith('[Module Address]'):
                            # Collect submodule addresses
                            address = line.split('] ')[1].strip()
                            submodule_addresses.append(address)
                            i += 1
                        elif line.startswith('['):
                            # Exit the current section
                            in_submodules_section = False
                            i += 1
                        else:
                            i += 1

                    if module_name is None:
                        print(f"Module name not found in {module_info_path}")
                        continue

                    if parent_module_path is None:
                        # Top-level module
                        self.modules[module_name] = {
                            'description': module_description.strip(),
                            'submodules': OrderedDict(),
                            'submodule_addresses': submodule_addresses
                        }
                        self.module_order.append(module_name)
                    else:
                        # Submodule
                        # Navigate to the parent module in self.modules
                        current_module = self.modules
                        for module_name_in_path in parent_module_path:
                            # Access the module by name
                            current_module = current_module[module_name_in_path]
                            # Ensure 'submodules' key exists
                            if 'submodules' not in current_module:
                                current_module['submodules'] = OrderedDict()
                        # Add the submodule to the parent module's 'submodules'
                        current_module['submodules'][module_name] = {
                            'description': module_description.strip(),
                            'submodules': OrderedDict(),
                            'submodule_addresses': submodule_addresses
                        }
                    # Recursively download submodules if any
                    if submodule_addresses:
                        # Keep the path to the current module
                        current_module_path = parent_module_path.copy() if parent_module_path else []
                        current_module_path.append(module_name)
                        # Download submodules
                        self.download_modules(current_module_path, submodule_addresses)
            else:
                print(f"moduleInfo.txt not found for repository: {repo_name}")


        # If parent_module_path is None, and all threads are done, show the system view
        if parent_module_path is None and not self.active_threads:
            # After all modules and submodules are downloaded and parsed, show the system view
            self.show_system_view()
    
    def update_progress(self, value):
        # Update the progress bar value
        if self.progress_bar is not None:
            self.progress_bar.setValue(value)
        else:
            print(f"Progress update: {value}%")
    
if __name__ == "__main__":
    app = QApplication(sys.argv + ['--disable-seccomp-filter-sandbox'])
    window = GitFileReaderApp()
    window.show()
    sys.exit(app.exec_())
