import sys
import urllib.request
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextBrowser, 
                           QVBoxLayout, QWidget, QLineEdit, QPushButton, 
                           QHBoxLayout, QProgressBar, QStatusBar)
from PyQt5.QtCore import Qt, QUrl

class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Simple Browser')
        self.setGeometry(100, 100, 1024, 768)
        
        # Create central widget and main layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Create navigation bar
        nav_bar = QWidget()
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(5, 5, 5, 5)
        
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate)
        nav_layout.addWidget(self.url_bar)
        
        self.go_button = QPushButton('Go')
        self.go_button.clicked.connect(self.navigate)
        nav_layout.addWidget(self.go_button)
        
        layout.addWidget(nav_bar)
        
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        layout.addWidget(self.browser)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(100)
        self.progress.hide()
        self.status_bar.addPermanentWidget(self.progress)
        
        self.apply_styles()
        
        # Load Google by default
        self.url_bar.setText('https://www.google.com')
        self.navigate()

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: white;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
                font-size: 14px;
                min-height: 25px;
            }
            QPushButton {
                padding: 5px 15px;
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 14px;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QTextBrowser {
                border: none;
                background-color: white;
                font-family: Arial, sans-serif;
            }
        """)

    def navigate(self):
        url = self.url_bar.text()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            self.url_bar.setText(url)
        
        self.status_bar.showMessage('Loading...')
        self.progress.setVisible(True)
        self.progress.setValue(20)
        
        try:
            # Create a request with browser-like headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            req = urllib.request.Request(url, headers=headers)
            response = urllib.request.urlopen(req)
            self.progress.setValue(60)
            
            html = response.read().decode('utf-8')
            self.progress.setValue(80)
            
            # Keep any existing CSS and add our own styles
            styled_html = html.replace('</head>',
                '''
                <style>
                    body { 
                        font-family: Arial, sans-serif;
                        margin: 20px;
                        line-height: 1.6;
                    }
                    input { 
                        padding: 8px;
                        margin: 5px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        font-size: 14px;
                    }
                    button { 
                        padding: 8px 15px;
                        margin: 5px;
                        background-color: #f8f9fa;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        cursor: pointer;
                    }
                    a {
                        color: #1a0dab;
                        text-decoration: none;
                    }
                    a:hover {
                        text-decoration: underline;
                    }
                </style>
                </head>''')
            
            self.browser.setHtml(styled_html)
            self.status_bar.showMessage('Done')
            
        except Exception as e:
            error_html = f"""
            <html>
                <body style='font-family: Arial, sans-serif; padding: 20px;'>
                    <h2 style='color: #d93025;'>Unable to load page</h2>
                    <p style='color: #5f6368;'>Error: {str(e)}</p>
                    <p style='color: #5f6368;'>URL: {url}</p>
                </body>
            </html>
            """
            self.browser.setHtml(error_html)
            self.status_bar.showMessage('Error loading page')
        
        finally:
            self.progress.setValue(100)
            self.progress.setVisible(False)

def main():
    app = QApplication(sys.argv)
    window = BrowserWindow()
    window.show()
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())