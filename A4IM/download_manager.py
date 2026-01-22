"""
Download Manager Module
Handles all Git repository downloading functionality for the System View
"""

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QColor
import pygit2
import os


class DownloadWorker(QThread):
    """Background thread for downloading repositories"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, repo_url, local_path, branch=None):
        super().__init__()
        self.repo_url = repo_url
        self.local_path = local_path
        self.branch = branch
        self._is_running = True

    def stop(self):
        """Stop the download thread"""
        self._is_running = False

    def run(self):
        try:
            if not self._is_running:
                self.finished.emit(False, "Download cancelled")
                return

            if self.branch:
                self.progress.emit(f"Cloning repository (branch: {self.branch})...")
                pygit2.clone_repository(self.repo_url, self.local_path, checkout_branch=self.branch)
            else:
                self.progress.emit(f"Cloning repository...")
                pygit2.clone_repository(self.repo_url, self.local_path)

            if self._is_running:
                self.finished.emit(True, "Download complete")
            else:
                self.finished.emit(False, "Download cancelled")
        except Exception as e:
            self.finished.emit(False, str(e))


class DownloadManager:
    """
    Manages downloading Git repositories for modules
    Handles single module downloads and batch downloads of module trees
    """
    
    def __init__(self, system_view):
        """
        Initialize the download manager
        
        Args:
            system_view: Reference to the SystemView widget that owns this manager
        """
        self.system_view = system_view
        self.download_worker = None
        self.download_queue = []
        self.current_download_index = 0
    
    def cleanup_download_worker(self):
        """Properly cleanup the download worker thread"""
        if self.download_worker:
            # Stop the worker
            self.download_worker.stop()
            
            # Disconnect signals to prevent issues
            try:
                self.download_worker.progress.disconnect()
                self.download_worker.finished.disconnect()
            except:
                pass
            
            # Wait for thread to finish (with timeout)
            if self.download_worker.isRunning():
                self.download_worker.wait(2000)  # Wait up to 2 seconds
                
                # Force quit if still running
                if self.download_worker.isRunning():
                    self.download_worker.terminate()
                    self.download_worker.wait()
            
            # Delete the worker
            self.download_worker.deleteLater()
            self.download_worker = None
    
    def download_single_module(self, node):
        """
        Clone the repository for a single module

        Args:
            node: NodeItem representing the module to download
        """
        repo_info = node.data.get('repository', {})
        if not repo_info or not repo_info.get('address'):
            print(f"No repo_info or address for node: {node.data}")
            return

        repo_url = repo_info['address'].rstrip('/')
        branch = repo_info.get('branch')
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        repo_dir = os.path.join("Downloaded Repositories", self.system_view.parent.repo_folder)
        local_path = os.path.join(repo_dir, repo_name)

        print(f"=== Download Single Module Debug ===")
        print(f"  repo_info: {repo_info}")
        print(f"  repo_url: {repo_url}")
        print(f"  branch: {branch}")
        print(f"  repo_name: {repo_name}")
        print(f"  repo_dir: {repo_dir}")
        print(f"  local_path: {local_path}")
        print(f"====================================")

        # Clean up any existing worker
        if self.download_worker:
            self.cleanup_download_worker()

        # Create and start download worker
        self.download_worker = DownloadWorker(repo_url, local_path, branch)
        self.download_worker.progress.connect(lambda msg: print(msg))
        self.download_worker.finished.connect(
            lambda success, msg: self.on_download_finished(node, repo_name, success, msg)
        )
        
        # Disable button during download
        self.system_view.download_module_button.setEnabled(False)
        self.system_view.download_module_button.setText("Downloading...")
        
        self.download_worker.start()
    
    def on_download_finished(self, node, repo_name, success, message):
        """
        Handle download completion for a single module
        
        Args:
            node: The module node that was downloaded
            repo_name: Name of the repository
            success: Whether download succeeded
            message: Success or error message
        """
        # Re-enable button
        self.system_view.download_module_button.setEnabled(True)
        self.system_view.download_module_button.setText("Download Module")
        
        if success:
            # Update node state
            node.is_downloaded = True
            node.download_indicator.setPlainText("✓")
            node.download_indicator.setDefaultTextColor(QColor("#32CD32"))
            
            # Hide download button
            self.system_view.download_module_button.hide()
            
            QMessageBox.information(
                self.system_view, 
                "Success", 
                f"Downloaded {repo_name}"
            )
        else:
            QMessageBox.critical(
                self.system_view, 
                "Error", 
                f"Failed to download: {message}"
            )
        
        # Clean up the worker
        self.cleanup_download_worker()
    
    def download_node_tree(self, node):
        """
        Recursively download node and all its children
        
        Args:
            node: Root NodeItem to start downloading from
        """
        # Create list of all nodes to download
        nodes_to_download = []
        
        def collect_nodes(n):
            # Only add if not already downloaded
            if not n.is_downloaded:
                nodes_to_download.append(n)
            for child in n.child_nodes:
                collect_nodes(child)
        
        collect_nodes(node)
        
        if not nodes_to_download:
            QMessageBox.information(
                self.system_view, 
                "Complete", 
                "All modules already downloaded!"
            )
            return
        
        # Start downloading
        self.download_queue = nodes_to_download
        self.current_download_index = 0
        self.download_next_in_queue()
    
    def download_next_in_queue(self):
        """Download the next module in the queue"""
        if self.current_download_index >= len(self.download_queue):
            # All downloads complete
            self.system_view.download_module_button.setEnabled(True)
            self.system_view.download_module_button.setText("Download Module")
            self.system_view.download_module_button.hide()  # Hide since all are downloaded
            
            QMessageBox.information(
                self.system_view, 
                "Complete", 
                "All modules downloaded successfully!"
            )
            
            # Clean up
            self.download_queue = []
            self.cleanup_download_worker()
            return
        
        current_node = self.download_queue[self.current_download_index]
        
        repo_info = current_node.data.get('repository', {})
        if not repo_info or not repo_info.get('address'):
            self.current_download_index += 1
            self.download_next_in_queue()
            return
        
        repo_url = repo_info['address'].rstrip('/')
        branch = repo_info.get('branch')
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        repo_dir = os.path.join("Downloaded Repositories", self.system_view.parent.repo_folder)
        local_path = os.path.join(repo_dir, repo_name)

        print(f"=== Download Queue Debug ===")
        print(f"  repo_info: {repo_info}")
        print(f"  repo_url: {repo_url}")
        print(f"  branch: {branch}")
        print(f"  repo_name: {repo_name}")
        print(f"  repo_dir: {repo_dir}")
        print(f"  local_path: {local_path}")
        print(f"============================")

        # Clean up any existing worker
        if self.download_worker:
            self.cleanup_download_worker()

        # Create and start download worker
        self.download_worker = DownloadWorker(repo_url, local_path, branch)
        self.download_worker.progress.connect(lambda msg: print(msg))
        self.download_worker.finished.connect(
            lambda success, msg: self.on_queue_download_finished(current_node, repo_name, success, msg)
        )
        
        # Update button to show progress
        self.system_view.download_module_button.setEnabled(False)
        self.system_view.download_module_button.setText(
            f"Downloading {self.current_download_index + 1}/{len(self.download_queue)}..."
        )
        
        self.download_worker.start()
    
    def on_queue_download_finished(self, node, repo_name, success, message):
        """
        Handle completion of a queued download
        
        Args:
            node: The module node that was downloaded
            repo_name: Name of the repository
            success: Whether download succeeded
            message: Success or error message
        """
        if success:
            # Update node state
            node.is_downloaded = True
            node.download_indicator.setPlainText("✓")
            node.download_indicator.setDefaultTextColor(QColor("#32CD32"))
            print(f"Downloaded {repo_name}")
        else:
            print(f"Failed to download {repo_name}: {message}")
            # Show error but continue with remaining downloads
            QMessageBox.warning(
                self.system_view, 
                "Download Error", 
                f"Failed to download {repo_name}: {message}\n\nContinuing with remaining downloads..."
            )
        
        # Clean up the current worker
        self.cleanup_download_worker()
        
        # Move to next download
        self.current_download_index += 1
        self.download_next_in_queue()
    
    def shutdown(self):
        """Clean up when the system view is closed"""
        if self.download_worker:
            self.cleanup_download_worker()