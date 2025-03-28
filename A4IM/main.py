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
from RepositorySelector_widget import RepositorySelector

class GitFileReaderApp(QMainWindow):
    def __init__(self, initial_repo_url, repo_folder):
        super().__init__()
        self.setWindowTitle("Git File Reader")
        self.setGeometry(100, 100, 800, 600)

        # Store the initial repository URL
        self.initial_repo_url = initial_repo_url
        self.repo_folder = repo_folder

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

        # Start downloading the initial repository
        self.download_initial_repository()

    def download_initial_repository(self):
        download_dir = os.path.join(os.getcwd(), "Downloaded Repositories")
        repo_dir = os.path.join(download_dir, self.repo_folder)
        clone_folder = os.path.join(repo_dir, "RootModule")

        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        if not os.path.exists(repo_dir):
            os.makedirs(repo_dir)

        # Clear existing directory if it exists
        if os.path.exists(repo_dir):
            import shutil
            shutil.rmtree(repo_dir)
            os.makedirs(repo_dir)

        try:
            import pygit2
            print(f"Cloning initial repository: {self.initial_repo_url}")
            pygit2.clone_repository(
                self.initial_repo_url,
                clone_folder
            )
            
            # Look for ModuleInfo.txt file with case-insensitive comparison
            module_info_path = None
            for filename in os.listdir(clone_folder):
                if filename.lower() == "moduleinfo.txt":
                    module_info_path = os.path.join(clone_folder, filename)
                    break
                    
            if module_info_path and os.path.exists(module_info_path):
                self.parse_initial_module(module_info_path)
            else:
                QMessageBox.critical(self, "File Error", "ModuleInfo.txt not found in the repository.")
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
        """Load a specific repository URL in the git building view"""
        print(f"Showing Git Building for module: {module}, submodule: {submodule}, URL: {url}")
        self.git_building.load_url(url)
        self.central_widget.setCurrentWidget(self.git_building)

    def download_modules(self, parent_module_path, module_addresses):
        self.pending_downloads += len(module_addresses)
        
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
        
        download_thread = DownloadThread(module_addresses, self.repo_folder)
        download_thread.progress.connect(self.update_progress)
        download_thread.finished.connect(lambda: self.module_download_finished(parent_module_path, download_thread))
        download_thread.start()
        self.active_threads.append(download_thread)

    def module_download_finished(self, parent_module_path, thread):
        """Handle completion of module downloads"""
        if thread in self.active_threads:
            self.active_threads.remove(thread)

        self.pending_downloads -= 1
        print(f"Download finished. Remaining downloads: {self.pending_downloads}")
        
        # Process the downloaded modules
        if parent_module_path:
            self.parse_module_info(parent_module_path)
        
        # Add a timeout check to ensure we eventually complete
        if self.pending_downloads <= 0 or not self.active_threads:
            print("All downloads complete or no active threads remaining!")
            if self.progress_bar:
                self.progress_bar.setParent(None)
                self.progress_bar.deleteLater()
                self.progress_bar = None
            
            self.loading_complete = True
            self.main_menu.show()
            self.show_main_menu()

    def parse_initial_module(self, module_info_path):
        """Parse the initial ModuleInfo.txt file and start the download process"""
        with open(module_info_path, 'r') as f:
            content = f.read()
        
        module_name = None
        module_description = ""
        submodule_addresses = []
        
        lines = content.split('\n')
        i = 0
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
            elif line.lower().startswith('[module address]'):
                parts = line.split(']', 1)
                if len(parts) > 1:
                    address = parts[1].strip()
                    submodule_addresses.append(address)
                i += 1
            else:
                i += 1
        
        if not module_name:
            module_name = "Root Module"  # Default name if not found
        
        # Clean up addresses if needed
        cleaned_addresses = []
        for address in submodule_addresses:
            if address.count("https://") > 1:
                address = address.replace("https://", "", address.count("https://") - 1)
            if address.count("github.com") > 1:
                address = address.replace("github.com/", "", address.count("github.com") - 1)
            cleaned_addresses.append(address)  # Fixed: using 'address' instead of 'addr'
        
        # Create the root module entry
        repo_name = self.initial_repo_url.split('/')[-1]
        docs_path = os.path.join("Downloaded Repositories", self.repo_folder, "RootModule", "orshards", "index.html")
        has_docs = os.path.exists(docs_path)
        
        # Initialize modules dictionary with the root module
        self.modules = OrderedDict()
        self.modules[module_name] = {
            'description': module_description.strip(),
            'submodules': OrderedDict(),
            'submodule_addresses': cleaned_addresses,
            'repository': {
                'name': repo_name,
                'address': self.initial_repo_url,
                'docs_path': docs_path if has_docs else None
            }
        }
        self.module_order.append(module_name)
        
        print(f"Initial module '{module_name}' created with {len(cleaned_addresses)} submodule addresses")
        
        # Start downloading submodules if any
        if cleaned_addresses:
            print(f"Root module has submodules: {cleaned_addresses}")
            self.loading_complete = False
            self.pending_downloads = 0
            self.download_modules(parent_module_path=[module_name], module_addresses=cleaned_addresses)
        else:
            print("No submodules found for root module. Loading main menu...")
            self.loading_complete = True
            self.main_menu.show()
            self.show_main_menu()

    def parse_module_info(self, parent_module_path):
        """Parse ModuleInfo.txt files from downloaded submodules"""
        if not parent_module_path:
            return
        
        # Navigate to the parent module
        current = self.modules
        for name in parent_module_path[:-1]:  # All but the last element
            if name in current:
                if 'submodules' in current[name]:
                    current = current[name]['submodules']
                else:
                    current[name]['submodules'] = OrderedDict()
                    current = current[name]['submodules']
            else:
                print(f"Error: Parent path not found: {name}")
                return
        
        # Get the parent module
        parent_name = parent_module_path[-1]
        if parent_name not in current:
            print(f"Error: Parent module not found: {parent_name}")
            return
        
        parent_module = current[parent_name]
        
        # Get the submodule addresses
        addresses = parent_module.get('submodule_addresses', [])
        repo_dir = os.path.join("Downloaded Repositories", self.repo_folder)
        
        # Make sure parent has submodules container
        if 'submodules' not in parent_module:
            parent_module['submodules'] = OrderedDict()
        
        for address in addresses:
            repo_name = address.split('/')[-1]
            repo_path = os.path.join(repo_dir, repo_name)
            
            # Find ModuleInfo.txt
            module_info_path = None
            if os.path.exists(repo_path):
                for filename in os.listdir(repo_path):
                    if filename.lower() == "moduleinfo.txt":
                        module_info_path = os.path.join(repo_path, filename)
                        break
            
            if module_info_path and os.path.exists(module_info_path):
                # Parse the module info
                with open(module_info_path, 'r') as f:
                    content = f.read()
                
                module_name = None
                module_description = ""
                module_addresses = []
                
                lines = content.split('\n')
                i = 0
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
                    elif line.lower().startswith('[module address]'):
                        parts = line.split(']', 1)
                        if len(parts) > 1:
                            addr = parts[1].strip()
                            module_addresses.append(addr)
                        i += 1
                    else:
                        i += 1
                
                if not module_name:
                    module_name = repo_name
                
                # Clean up addresses
                cleaned_addresses = []
                for addr in module_addresses:
                    if addr.count("https://") > 1:
                        addr = addr.replace("https://", "", addr.count("https://") - 1)
                    if addr.count("github.com") > 1:
                        addr = addr.replace("github.com/", "", addr.count("github.com") - 1)
                    cleaned_addresses.append(addr)
                
                # Check for documentation
                docs_path = os.path.join(repo_path, "orshards", "index.html")
                has_docs = os.path.exists(docs_path)
                
                # Add the module
                parent_module['submodules'][module_name] = {
                    'description': module_description.strip(),
                    'submodules': OrderedDict(),
                    'submodule_addresses': cleaned_addresses,
                    'repository': {
                        'name': repo_name,
                        'address': address,
                        'docs_path': docs_path if has_docs else None
                    }
                }
                
                print(f"Added module {module_name} to {parent_name}")
                
                # Download submodules if any
                if cleaned_addresses:
                    new_path = parent_module_path.copy()
                    new_path.append(module_name)
                    self.download_modules(new_path, cleaned_addresses)

    def update_progress(self, value):
        """Update the progress bar with the current value"""
        if self.progress_bar:
            self.progress_bar.setValue(value)
        else:
            print(f"Progress: {value}%")

def main():
    app = QApplication(sys.argv + ['--disable-seccomp-filter-sandbox'])
    # Import here to avoid circular imports
    from RepositorySelector_widget import RepositorySelector
    selector = RepositorySelector()
    selector.show()
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())