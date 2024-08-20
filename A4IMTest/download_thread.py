import os
import git
from PyQt5.QtCore import QThread, pyqtSignal

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    #finished = pyqtSignal()

    def __init__(self, repo_urls):
        super().__init__()
        self.repo_urls = repo_urls
    
    def run(self):
        print(f"Starting to download repositories: {self.repo_urls}")
        for i, url in enumerate(self.repo_urls):
            print(f"Processing repository URL: {url}")
            repo_name = url.split('/')[-1]
            local_path = os.path.join("Downloaded Repositories", repo_name)
            
            if os.path.exists(local_path):
                print(f"Repository {repo_name} already exists. Updating...")
                repo = git.Repo(local_path)
                origin = repo.remotes.origin
                origin.pull()
            else:
                print(f"Attempting to clone {url} to {local_path}")
                git.Repo.clone_from(url, local_path)
                print(f"Successfully cloned {url}")
            
            self.progress.emit(int((i + 1) / len(self.repo_urls) * 100))
        
        print("Download thread finished")