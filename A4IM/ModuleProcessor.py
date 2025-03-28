import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt
from collections import OrderedDict

class ModuleProcessor:
    """A helper class to handle module processing"""
    def __init__(self, repo_folder):
        self.repo_folder = repo_folder
        self.modules = OrderedDict()
        self.module_downloads_pending = {}  # Track which modules have pending downloads
        
    def add_root_module(self, name, description, repo_name, repo_url, submodule_addresses):
        """Add the root module to the hierarchy"""
        self.modules[name] = {
            'description': description,
            'submodules': OrderedDict(),
            'submodule_addresses': submodule_addresses,
            'repository': {
                'name': repo_name,
                'address': repo_url,
                'docs_path': None  # This can be updated later if needed
            }
        }
        
        # Mark the root as having pending downloads if it has submodules
        if submodule_addresses:
            self.module_downloads_pending[name] = len(submodule_addresses)
        
        return self.modules[name]
    
    def add_module(self, parent_path, name, description, repo_name, repo_url, submodule_addresses, docs_path=None):
        """Add a module to a specific parent path"""
        # Find the parent module
        current = self.modules
        path_str = ""
        
        for i, parent_name in enumerate(parent_path):
            path_str += parent_name + " > "
            if parent_name not in current:
                print(f"Error: Cannot find parent '{parent_name}' in path {parent_path}")
                return None
            
            if i == len(parent_path) - 1:  # We're at the immediate parent
                if 'submodules' not in current[parent_name]:
                    current[parent_name]['submodules'] = OrderedDict()
                
                # Add the new module
                current[parent_name]['submodules'][name] = {
                    'description': description,
                    'submodules': OrderedDict(),
                    'submodule_addresses': submodule_addresses,
                    'repository': {
                        'name': repo_name,
                        'address': repo_url,
                        'docs_path': docs_path
                    }
                }
                
                # Mark this module as having pending downloads if it has submodules
                if submodule_addresses:
                    full_path = parent_path + [name]
                    path_key = "->".join(full_path)
                    self.module_downloads_pending[path_key] = len(submodule_addresses)
                
                return current[parent_name]['submodules'][name]
            
            current = current[parent_name]['submodules']
        
        return None
    
    def process_module_info_file(self, file_path, repo_name, repo_url):
        """Process a ModuleInfo.txt file and extract all relevant information"""
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'r') as f:
            content = f.read()

        module_name = None
        module_description = ""
        submodule_addresses = []
        lines = content.split('\n')
        i = 0
        
        # Parse the ModuleInfo.txt file
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
            module_name = repo_name
        
        # Clean up submodule addresses
        cleaned_addresses = []
        for address in submodule_addresses:
            if address.count("https://") > 1:
                address = address.replace("https://", "", address.count("https://") - 1)
            if address.count("github.com") > 1:
                address = address.replace("github.com/", "", address.count("github.com") - 1)
            cleaned_addresses.append(address)
        
        return {
            'name': module_name,
            'description': module_description.strip(),
            'submodule_addresses': cleaned_addresses
        }
    
    def process_downloaded_modules(self):
        """Process all downloaded modules and build the full hierarchy"""
        download_dir = os.path.join(os.getcwd(), "Downloaded Repositories", self.repo_folder)
        
        # Skip RootModule - it's already processed
        processed_repos = set()
        
        # Find all repo folders
        for repo_name in os.listdir(download_dir):
            if repo_name == "RootModule" or not os.path.isdir(os.path.join(download_dir, repo_name)):
                continue
                
            repo_path = os.path.join(download_dir, repo_name)
            
            # Find ModuleInfo.txt
            module_info_path = None
            for filename in os.listdir(repo_path):
                if filename.lower() == "moduleinfo.txt":
                    module_info_path = os.path.join(repo_path, filename)
                    break
            
            if not module_info_path:
                continue
                
            # Find which module this belongs to by scanning all address lists
            parent_path = self.find_parent_for_repo(repo_name)
            if not parent_path:
                print(f"Warning: Could not find parent for repository {repo_name}")
                continue
                
            # Process the module info
            repo_url = f"https://github.com/MatthewBeddows/{repo_name}"  # Reconstruct URL
            module_info = self.process_module_info_file(module_info_path, repo_name, repo_url)
            
            if not module_info:
                continue
                
            # Check for documentation
            docs_path = os.path.join(repo_path, "orshards", "index.html")
            has_docs = os.path.exists(docs_path)
                
            # Add to parent module
            self.add_module(
                parent_path,
                module_info['name'],
                module_info['description'],
                repo_name,
                repo_url,
                module_info['submodule_addresses'],
                docs_path if has_docs else None
            )
            
            processed_repos.add(repo_name)
            
            # Mark parent as processed
            parent_key = "->".join(parent_path)
            if parent_key in self.module_downloads_pending:
                self.module_downloads_pending[parent_key] -= 1
                if self.module_downloads_pending[parent_key] <= 0:
                    del self.module_downloads_pending[parent_key]
        
        # Return the full hierarchy
        return self.modules
    
    def find_parent_for_repo(self, repo_name):
        """Find which module has this repo in its submodule_addresses"""
        def search_modules(modules, path=None):
            if path is None:
                path = []
                
            for name, data in modules.items():
                current_path = path + [name]
                
                # Check if this module has the repo as a submodule
                if 'submodule_addresses' in data:
                    for addr in data['submodule_addresses']:
                        if addr.endswith(f"/{repo_name}"):
                            return current_path
                
                # Check submodules recursively
                if 'submodules' in data and data['submodules']:
                    result = search_modules(data['submodules'], current_path)
                    if result:
                        return result
            
            return None
            
        return search_modules(self.modules)
    
    def print_module_structure(self):
        """Print the complete module structure"""
        print("\n==== COMPLETE MODULE STRUCTURE ====")
        self._print_modules(self.modules)
        print("==================================\n")
        
    def _print_modules(self, modules, indent=0):
        """Helper to print modules recursively"""
        for name, data in modules.items():
            indent_str = "  " * indent
            print(f"{indent_str}MODULE: {name}")
            
            if 'repository' in data:
                repo = data['repository']
                print(f"{indent_str}  Repository: {repo.get('name')} - {repo.get('address')}")
            
            if 'submodules' in data and data['submodules']:
                print(f"{indent_str}  Submodules:")
                self._print_modules(data['submodules'], indent + 1)
            else:
                print(f"{indent_str}  No submodules")