import os
import pygit2
import datetime
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, repo_urls, architect_folder):
        super().__init__()
        self.repo_urls = repo_urls
        self.architect_folder = architect_folder
        self._is_running = True

    def run(self):
        print(f"Starting to download repositories: {self.repo_urls}")
        for i, url in enumerate(self.repo_urls):
            if not self._is_running:
                break

            print(f"Processing repository URL: {url}")
            repo_name = url.split('/')[-1]
            local_path = os.path.join("Downloaded Repositories", self.architect_folder, repo_name)
            
            repo_updated = False
            if os.path.exists(local_path):
                try:
                    # Open existing repository
                    repo = pygit2.Repository(local_path)
                    # Get current remote
                    remote = repo.remotes["origin"]
                    # Fetch and merge changes
                    remote.fetch()
                    # Hard reset to latest
                    remote_master = repo.lookup_reference('refs/remotes/origin/master')
                    repo.reset(remote_master.target, pygit2.GIT_RESET_HARD)
                    repo_updated = True
                except Exception as e:
                    print(f"Failed to update {repo_name}: {e}")
            else:
                try:
                    print(f"Cloning {url} to {local_path}")
                    # Clone with pygit2
                    pygit2.clone_repository(url, local_path)
                    repo_updated = True
                except Exception as e:
                    print(f"Failed to clone {url}: {e}")
            
            # Add timestamp to ModuleInfo.txt if repo was updated or cloned
            if repo_updated:
                self.add_timestamp_to_module_info(local_path)
                
            self.progress.emit(int((i + 1) / len(self.repo_urls) * 100))
        
        self.finished.emit()

    def add_timestamp_to_module_info(self, repo_path):
        """Add a deployment timestamp to the ModuleInfo.txt file in lib folder"""
        module_info_path = None

        lib_path = os.path.join(repo_path, "lib")
        try:
            if os.path.exists(lib_path):
                for filename in os.listdir(lib_path):
                    if filename.lower() == "moduleinfo.txt":
                        module_info_path = os.path.join(lib_path, filename)
                        break
        except Exception as e:
            print(f"Error listing directory {lib_path}: {str(e)}")
            return

        if module_info_path:
            try:
                with open(module_info_path, 'r') as f:
                    content = f.read()

                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if "[Deployed]" in content:
                    import re
                    content = re.sub(r'\[Deployed\].*', f"[Deployed] {timestamp}", content)
                else:
                    content += f"\n[Deployed] {timestamp}"

                with open(module_info_path, 'w') as f:
                    f.write(content)

                print(f"Added deployment timestamp to {module_info_path}")
            except Exception as e:
                print(f"Failed to add timestamp to ModuleInfo.txt: {str(e)}")
