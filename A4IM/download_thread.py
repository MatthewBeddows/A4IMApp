import os
import git
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, repo_urls):
        super().__init__()
        self.repo_urls = repo_urls
        self._is_running = True
    
    # The stop method sets _is_running to False. This allows the thread to be gracefully stopped if needed.
    def stop(self):
        self._is_running = False

    @pyqtSlot()
    def run(self):
        print(f"Starting to download repositories: {self.repo_urls}")
        for i, url in enumerate(self.repo_urls):
            if not self._is_running:
                print("Download thread stopped")
                break

            print(f"Processing repository URL: {url}")
            repo_name = url.split('/')[-1]
            local_path = os.path.join("Downloaded Repositories", repo_name)
            


            # Try-except to prevent the thread from crashing in case of errors during cloning or updating repositories.
            if os.path.exists(local_path):
                print(f"Repository {repo_name} already exists. Updating...")
                try:
                    repo = git.Repo(local_path)
                    origin = repo.remotes.origin
                    origin.pull()
                    print(f"Successfully updated {repo_name}")
                except Exception as e:
                    print(f"Failed to update {repo_name}: {e}")
            else:
                try:
                    print(f"Attempting to clone {url} to {local_path}")
                    git.Repo.clone_from(url, local_path)
                    print(f"Successfully cloned {url}")
                except Exception as e:
                    print(f"Failed to clone {url}: {e}")
            
            self.progress.emit(int((i + 1) / len(self.repo_urls) * 100))
        
        print("Download thread finished")
        self.finished.emit()