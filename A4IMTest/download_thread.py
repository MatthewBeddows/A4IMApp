# download_thread.py

import os
import git
from PyQt5.QtCore import QThread, pyqtSignal

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, repos):
        super().__init__()
        self.repos = repos

    def run(self):
        download_dir = "Downloaded Repositories"
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        for i, repo_url in enumerate(self.repos):
            repo_name = repo_url.split('/')[-1]
            repo_path = os.path.join(download_dir, repo_name)
            if not os.path.exists(repo_path):
                git.Repo.clone_from(f"https://github.com/{repo_url}.git", repo_path)
            self.progress.emit((i + 1) * 100 // len(self.repos))

        self.finished.emit()