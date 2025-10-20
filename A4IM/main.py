import sys
import os
import requests

# Set high DPI scaling policy
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PyQt5.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt, QCoreApplication
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
        self.setWindowTitle("Orshards Repository Tool")
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


    def fetch_module_info_only(self, repo_url):
        """Fetch only ModuleInfo.txt from a Git repository (GitHub or GitLab)"""
        try:
            repo_url = repo_url.strip()
            if not repo_url.startswith('http'):
                repo_url = 'https://' + repo_url
            
            # Determine if it's GitHub or GitLab
            is_github = 'github.com' in repo_url
            is_gitlab = 'gitlab.com' in repo_url
            
            if is_github:
                parts = repo_url.replace('https://github.com/', '').replace('.git', '').split('/')
                if len(parts) >= 2:
                    owner, repo = parts[0], parts[1]
                    branches = ['main', 'master']
                    filenames = ['ModuleInfo.txt', 'moduleInfo.txt', 'moduleinfo.txt', 'ModuleInfor.txt']
                    
                    for branch in branches:
                        for filename in filenames:
                            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filename}"
                            print(f"Trying GitHub: {raw_url}")
                            response = requests.get(raw_url, timeout=10)
                            if response.status_code == 200:
                                print(f"✓ Found {filename} on {branch}")
                                return response.text
            
            elif is_gitlab:
                parts = repo_url.replace('https://gitlab.com/', '').replace('.git', '').split('/')
                if len(parts) >= 2:
                    owner, repo = parts[0], parts[1]
                    branches = ['main', 'master']
                    filenames = ['ModuleInfo.txt', 'moduleInfo.txt', 'moduleinfo.txt', 'ModuleInfor.txt']
                    
                    for branch in branches:
                        for filename in filenames:
                            raw_url = f"https://gitlab.com/{owner}/{repo}/-/raw/{branch}/{filename}"
                            print(f"Trying GitLab: {raw_url}")
                            response = requests.get(raw_url, timeout=10)
                            if response.status_code == 200:
                                print(f"✓ Found {filename} on {branch}")
                                return response.text
            
            print(f"Could not find ModuleInfo.txt in repository")
            return None
            
        except Exception as e:
            print(f"Failed to fetch ModuleInfo.txt: {e}")
            import traceback
            traceback.print_exc()
            return None
        

    def download_initial_repository(self):
        """Only fetch ModuleInfo.txt - no full clone"""
        import datetime
        
        repo_name = self.initial_repo_url.split('/')[-1].replace('.git', '')
        download_dir = os.path.join(os.getcwd(), "Downloaded Repositories")
        repo_dir = os.path.join(download_dir, self.repo_folder)
        metadata_dir = os.path.join(repo_dir, ".metadata")
        
        os.makedirs(metadata_dir, exist_ok=True)
        
        print(f"Fetching ModuleInfo.txt from: {self.initial_repo_url}")
        
        # Fetch just the ModuleInfo.txt content
        module_info_content = self.fetch_module_info_only(self.initial_repo_url)
        
        if module_info_content:
            # Save to metadata folder
            module_info_path = os.path.join(metadata_dir, f"{repo_name}_ModuleInfo.txt")
            with open(module_info_path, 'w') as f:
                f.write(module_info_content)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n[Deployed] {timestamp}")
            
            print(f"✓ Saved ModuleInfo.txt to {module_info_path}")
            self.parse_initial_module(module_info_path, repo_name)
        else:
            QMessageBox.critical(self, "Error", 
                            f"Could not fetch ModuleInfo.txt from:\n{self.initial_repo_url}\n\n"
                            "Please check the repository URL and ensure ModuleInfo.txt exists.")

    def fetch_submodule_infos(self, module_addresses):
        """Fetch ModuleInfo.txt for multiple submodules"""
        metadata_dir = os.path.join("Downloaded Repositories", self.repo_folder, ".metadata")
        
        for address in module_addresses:
            repo_name = address.split('/')[-1].replace('.git', '')
            
            print(f"Fetching {repo_name}...")
            content = self.fetch_module_info_only(address)
            
            if content:
                # Save to metadata folder
                module_info_path = os.path.join(metadata_dir, f"{repo_name}_ModuleInfo.txt")
                with open(module_info_path, 'w') as f:
                    f.write(content)
                print(f"✓ Saved {repo_name}")
            else:
                print(f"✗ Could not fetch {repo_name}")


    def check_if_all_complete(self):
        """Check if all downloads are complete"""
        if self.pending_downloads <= 0:
            print("All downloads complete! Loading main menu...")
            if self.progress_bar:
                self.progress_bar.setParent(None)
                self.progress_bar.deleteLater()
                self.progress_bar = None
            
            self.loading_complete = True
            self.main_menu.show()
            self.show_main_menu()

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


    def add_timestamp_to_module_info(self, repo_path):
        """Add a deployment timestamp to the ModuleInfo.txt file"""
        module_info_path = None
        
        # Find ModuleInfo.txt with case-insensitive search
        try:
            for filename in os.listdir(repo_path):
                if filename.lower() == "moduleinfo.txt":
                    module_info_path = os.path.join(repo_path, filename)
                    break
        except Exception as e:
            print(f"Error listing directory {repo_path}: {str(e)}")
            return
            
        if module_info_path:
            try:
                # Read current content
                with open(module_info_path, 'r') as f:
                    content = f.read()
                
                # Get current timestamp
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Check if there's already a deployment timestamp
                if "[Deployed]" in content:
                    # Replace existing timestamp
                    import re
                    content = re.sub(r'\[Deployed\].*', f"[Deployed] {timestamp}", content)
                else:
                    # Add timestamp at the end
                    content += f"\n[Deployed] {timestamp}"
                
                # Write back to file
                with open(module_info_path, 'w') as f:
                    f.write(content)
                    
                print(f"Added deployment timestamp to {module_info_path}")
            except Exception as e:
                print(f"Failed to add timestamp to ModuleInfo.txt: {str(e)}")

    def module_download_finished(self, parent_module_path, thread):
        """Handle completion of module downloads"""
        if thread in self.active_threads:
            self.active_threads.remove(thread)

        self.pending_downloads -= 1
        print(f"Download finished. Remaining downloads: {self.pending_downloads}")
        
        # Process the downloaded modules
        if parent_module_path:
            self.parse_module_info(parent_module_path)
        
        # Check if we're done
        self.check_if_all_complete()

    def parse_initial_module(self, module_info_path, repo_name):
        """Parse initial ModuleInfo.txt without downloading repos"""
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
            module_name = "Root Module"
        
        # Clean up addresses
        cleaned_addresses = []
        for address in submodule_addresses:
            if address.count("https://") > 1:
                address = address.replace("https://", "", address.count("https://") - 1)
            if address.count("github.com") > 1:
                address = address.replace("github.com/", "", address.count("github.com") - 1)
            if address.count("gitlab.com") > 1:
                address = address.replace("gitlab.com/", "", address.count("gitlab.com") - 1)
            cleaned_addresses.append(address)
        
        # Initialize modules dictionary
        self.modules = OrderedDict()
        self.modules[module_name] = {
            'description': module_description.strip(),
            'submodules': OrderedDict(),
            'submodule_addresses': cleaned_addresses,
            'repository': {
                'name': repo_name,
                'address': self.initial_repo_url,
                'docs_path': None
            },
            'is_downloaded': False  # Track download state
        }
        self.module_order.append(module_name)
        
        print(f"Initial module '{module_name}' created with {len(cleaned_addresses)} submodule addresses")
        
        # Fetch submodule ModuleInfo.txt files (not full repos)
        if cleaned_addresses:
            print(f"Fetching info for {len(cleaned_addresses)} submodules...")
            self.fetch_submodule_infos(cleaned_addresses)
            self.parse_submodule_infos([module_name], cleaned_addresses)
        
        # Load complete - show main menu
        print("All module info loaded! Loading main menu...")
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

    def parse_submodule_infos(self, parent_module_path, addresses):
        """Parse fetched ModuleInfo.txt files without downloading full repos"""
        metadata_dir = os.path.join("Downloaded Repositories", self.repo_folder, ".metadata")
        
        # Navigate to parent module
        current = self.modules
        for name in parent_module_path[:-1]:
            if name in current and 'submodules' in current[name]:
                current = current[name]['submodules']
        
        parent_name = parent_module_path[-1]
        if parent_name not in current:
            return
        
        parent_module = current[parent_name]
        if 'submodules' not in parent_module:
            parent_module['submodules'] = OrderedDict()
        
        for address in addresses:
            repo_name = address.split('/')[-1].replace('.git', '')
            module_info_path = os.path.join(metadata_dir, f"{repo_name}_ModuleInfo.txt")
            
            if os.path.exists(module_info_path):
                with open(module_info_path, 'r') as f:
                    content = f.read()
                
                # Parse module info
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
                
                # Clean addresses
                cleaned_addresses = []
                for addr in module_addresses:
                    if addr.count("https://") > 1:
                        addr = addr.replace("https://", "", addr.count("https://") - 1)
                    if addr.count("github.com") > 1:
                        addr = addr.replace("github.com/", "", addr.count("github.com") - 1)
                    if addr.count("gitlab.com") > 1:
                        addr = addr.replace("gitlab.com/", "", addr.count("gitlab.com") - 1)
                    cleaned_addresses.append(addr)
                
                # Add module without downloading
                parent_module['submodules'][module_name] = {
                    'description': module_description.strip(),
                    'submodules': OrderedDict(),
                    'submodule_addresses': cleaned_addresses,
                    'repository': {
                        'name': repo_name,
                        'address': address,
                        'docs_path': None
                    },
                    'is_downloaded': False
                }
                
                print(f"Added module info: {module_name}")
                
                # Recursively fetch child module infos
                if cleaned_addresses:
                    self.fetch_submodule_infos(cleaned_addresses)
                    new_path = parent_module_path.copy()
                    new_path.append(module_name)
                    self.parse_submodule_infos(new_path, cleaned_addresses)

    def update_progress(self, value):
        """Update the progress bar with the current value"""
        if self.progress_bar:
            self.progress_bar.setValue(value)
        else:
            print(f"Progress: {value}%")

def main():

    # Enable High DPI scaling BEFORE creating QApplication
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv + ['--disable-seccomp-filter-sandbox'])

    # Configure QtWebEngine for software rendering
    QCoreApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

    # Import and show the Startup Menu (FIRST WINDOW)
    from startup_menu import StartupMenu
    startup = StartupMenu()
    startup.show()
    return app.exec_()

def closeEvent(self, event):
    """Called when the application is closing"""
    # Clean up temporary CSV files
    if hasattr(self, 'system_view'):
        self.system_view.cleanup_temp_files()
    
    # Accept the close event
    event.accept()

if __name__ == "__main__":
    sys.exit(main())