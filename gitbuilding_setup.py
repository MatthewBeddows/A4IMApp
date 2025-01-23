import subprocess
import requests
from PyQt5.QtCore import QObject, pyqtSignal

class GitBuildingSetup(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def is_server_running(self, url="http://localhost:6178"):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                self.log.emit(f"Server is already running at {url}")
                return True
        except requests.ConnectionError:
            return False

    def run_command(self, command):
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in process.stdout:
                self.log.emit(line.strip())
            for line in process.stderr:
                self.log.emit(line.strip())
            process.wait()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, command)
        except subprocess.CalledProcessError as e:
            if "ServerAlreadyRunningError" in str(e):
                self.error.emit("A server is already running on the specified port. Please stop the existing server or use a different port.")
            else:
                self.error.emit(f"Error executing command: {command}\nError message: {str(e)}")
            return False
        return True

    def run(self):
        self.log.emit("Installing gitbuilding...")
        if self.run_command("pip install gitbuilding"):
            self.log.emit("\nChecking if gitbuilding webapp is already running...")
            if not self.is_server_running():
                self.log.emit("\nRunning gitbuilding webapp...")

                # if self.run_command("gitbuilding webapp"):
                #     self.finished.emit()
                # else:
                #     self.error.emit("Failed to run gitbuilding webapp")
            else:
                self.finished.emit()  # Considered finished if the server is already running
        else:
            self.error.emit("Failed to install gitbuilding")
