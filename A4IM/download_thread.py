import os
import git
import subprocess
from PyQt5.QtCore import QThread, pyqtSignal

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, repo_urls, architect_folder):
        super().__init__()
        self.repo_urls = repo_urls
        self.architect_folder = architect_folder
        self._is_running = True
        self._configure_git()

    def _configure_git(self):
        """Configure git settings."""
        try:
            # Only set GnuTLS priority
            os.environ['GIT_SSL_GNUTLS_PRIORITY'] = 'NORMAL:-VERS-TLS1.3'
        except Exception as e:
            print(f"Warning: Could not configure Git: {e}")

    def _clone_repository(self, url, local_path):
        """Clone repository with fallback methods."""
        try:
            print(f"Attempting to clone {url} to {local_path}")
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            cmd = ['git', 'clone', url, local_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return git.Repo(local_path)
            else:
                raise Exception(f"Git command failed: {result.stderr}")
        except Exception as e:
            print(f"Clone failed: {e}")
            raise

    def run(self):
        print(f"Starting to download repositories: {self.repo_urls}")
        
        for i, url in enumerate(self.repo_urls):
            if not self._is_running:
                break

            print(f"Processing repository URL: {url}")
            repo_name = url.split('/')[-1].replace(" ", "_")
            local_path = os.path.join(
                "Downloaded Repositories", 
                self.architect_folder.replace(" ", "_"), 
                repo_name
            )
            
            if os.path.exists(local_path):
                try:
                    repo = git.Repo(local_path)
                    origin = repo.remotes.origin
                    origin.pull()
                except Exception as e:
                    print(f"Failed to update {repo_name}: {e}")
                    try:
                        # If pull fails, attempt to clone fresh
                        import shutil
                        shutil.rmtree(local_path)
                        self._clone_repository(url, local_path)
                    except Exception as e2:
                        print(f"Failed to re-clone {repo_name}: {e2}")
            else:
                try:
                    print(f"Cloning {url} to {local_path}")
                    self._clone_repository(url, local_path)
                except Exception as e:
                    print(f"Failed to clone {url}: {e}")
            
            self.progress.emit(int((i + 1) / len(self.repo_urls) * 100))
        
        self.finished.emit()

    def stop(self):
        self._is_running = False