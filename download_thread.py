import os
import git
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
            
            if os.path.exists(local_path):
                try:
                    repo = git.Repo(local_path)
                    origin = repo.remotes.origin
                    origin.pull()
                except Exception as e:
                    print(f"Failed to update {repo_name}: {e}")
            else:
                try:
                    print(f"Cloning {url} to {local_path}")
                    git.Repo.clone_from(url, local_path)
                except Exception as e:
                    print(f"Failed to clone {url}: {e}")
            
            self.progress.emit(int((i + 1) / len(self.repo_urls) * 100))
        
        self.finished.emit()