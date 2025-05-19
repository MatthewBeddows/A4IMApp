from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton, 
    QFileDialog, QLabel, QMessageBox, QDialog, QCheckBox,
    QComboBox, QFormLayout, QLineEdit, QHeaderView, QSizePolicy
)
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, QUrl
from PyQt5.QtGui import QFont, QColor, QCursor
import os
import csv
import pandas as pd
import platform
import subprocess
import webbrowser

class PandasModel(QAbstractTableModel):
    """Model for displaying pandas DataFrame in QTableView with editable checkboxes"""
    
    def __init__(self, data):
        super().__init__()
        self._data = data
        
        # If the DataFrame doesn't have an 'Acquired' column, add it
        if 'Acquired' not in self._data.columns:
            self._data['Acquired'] = 0  # Default to unchecked (0)
        else:
            # Ensure values are numeric for checkbox state
            self._data['Acquired'] = self._data['Acquired'].fillna(0).astype(int)
            
    def rowCount(self, parent=QModelIndex()):
        return len(self._data)
        
    def columnCount(self, parent=QModelIndex()):
        return len(self._data.columns)
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        
        col_name = self._data.columns[index.column()]
            
        # Special handling for Acquired column as checkbox
        if col_name == 'Acquired':
            if role == Qt.CheckStateRole:
                return Qt.Checked if self._data.iloc[index.row(), index.column()] else Qt.Unchecked
            # Don't show text for checkbox column
            if role == Qt.DisplayRole:
                return None
        elif role == Qt.DisplayRole or role == Qt.EditRole:
            value = self._data.iloc[index.row(), index.column()]
            # Handle different data types appropriately
            if pd.isna(value):
                return ""
            else:
                return str(value)
                
        if role == Qt.TextAlignmentRole:
            value = self._data.iloc[index.row(), index.column()]
            # Right-align numeric data (except checkbox column)
            if col_name != 'Acquired' and isinstance(value, (int, float)):
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter
                
        if role == Qt.BackgroundRole:
            # Add alternate row coloring
            if index.row() % 2 == 0:
                return QColor(240, 240, 240)
        
        if role == Qt.ForegroundRole:
            # Color URLs in blue
            if col_name != 'Acquired':  # Don't color checkbox column
                value = self._data.iloc[index.row(), index.column()]
                if self.is_url(index.row(), index.column()):
                    return QColor('blue')
        
        if role == Qt.FontRole:
            # Underline URLs
            if col_name != 'Acquired':  # Don't style checkbox column
                value = self._data.iloc[index.row(), index.column()]
                if self.is_url(index.row(), index.column()):
                    font = QFont()
                    font.setUnderline(True)
                    return font
        
        if role == Qt.ToolTipRole:
            if col_name != 'Acquired':  # Don't tooltip checkbox column
                value = self._data.iloc[index.row(), index.column()]
                # Check if this cell contains an URL
                if self.is_url(index.row(), index.column()):
                    return f"Click to open: {value}"
            else:
                # Tooltip for checkbox
                return "Check if you have acquired this part"
            return None
                
        return QVariant()
    
    def setData(self, index, value, role=Qt.EditRole):
        """Set data for editable cells (checkboxes)"""
        if not index.isValid():
            return False
            
        if role == Qt.CheckStateRole and self._data.columns[index.column()] == 'Acquired':
            # Convert from Qt CheckState to 0/1
            self._data.iloc[index.row(), index.column()] = 1 if value == Qt.Checked else 0
            self.dataChanged.emit(index, index)
            return True
            
        return False
        
    def flags(self, index):
        """Set flags for cells - make Acquired column checkable"""
        if not index.isValid():
            return Qt.NoItemFlags
            
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        
        # Make the Acquired column checkable
        if self._data.columns[index.column()] == 'Acquired':
            flags |= Qt.ItemIsUserCheckable
            
        return flags
        
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])
            else:
                return str(section + 1)  # Row numbers starting from 1
        return QVariant()
        
    def is_url(self, row, column):
        """Check if the cell contains a URL"""
        value = self._data.iloc[row, column]
        if not isinstance(value, str):
            return False
            
        # Check for common URL patterns
        value_lower = value.lower().strip()
        # Direct checks for common URL prefixes
        if any(value_lower.startswith(prefix) for prefix in ['http://', 'https://', 'www.']):
            return True
            
        # Check for domain patterns like example.com, example.org, etc.
        if ' ' not in value_lower and '.' in value_lower:
            parts = value_lower.split('.')
            if len(parts) >= 2:
                # Check if it ends with a common TLD
                common_tlds = ['.com', '.org', '.net', '.io', '.edu', '.gov', '.co', '.us', '.uk', '.de', '.au']
                if any(value_lower.endswith(tld) for tld in common_tlds):
                    return True
                    
        return False
        
    def get_url(self, row, column):
        """Get the URL from a cell"""
        value = str(self._data.iloc[row, column]).strip()
        # If it's an URL but doesn't have a protocol, add https://
        if not value.lower().startswith(('http://', 'https://')):
            return 'https://' + value
        return value
        
    def get_dataframe(self):
        """Get the current DataFrame with all modifications"""
        return self._data.copy()

class CSVViewerWidget(QWidget):
    def __init__(self, parent=None, csv_path=None):
        super().__init__(parent)
        self.parent = parent
        self.csv_path = csv_path
        self.df = None
        self.setup_ui()
        
        # Load CSV if path provided
        if csv_path and os.path.exists(csv_path):
            self.load_csv(csv_path)
    def setup_ui(self):
        self.setWindowTitle("CSV Viewer")
        self.resize(800, 600)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Set background color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor('white'))
        self.setPalette(palette)
        
        # Header with file info
        self.header_label = QLabel("No file loaded")
        self.header_label.setFont(QFont('Arial', 12, QFont.Bold))
        self.header_label.setStyleSheet("color: #465775; margin-bottom: 10px;")
        main_layout.addWidget(self.header_label)
        
        # Table view for displaying CSV data
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table_view.setStyleSheet("""
            QTableView {
                border: 1px solid #d9d9d9;
                border-radius: 5px;
                selection-background-color: #465775;
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #465775;
                color: white;
                padding: 5px;
                border: 1px solid #364765;
            }
        """)
        # Connect the cell clicked event
        self.table_view.clicked.connect(self.handle_cell_click)
        main_layout.addWidget(self.table_view, 1)  # Add stretch factor of 1
        
        # Info area for displaying the selected URL
        self.url_info_layout = QHBoxLayout()
        
        self.url_label = QLabel("Selected URL:")
        self.url_label.setFont(QFont('Arial', 10, QFont.Bold))
        self.url_label.setFixedWidth(100)
        self.url_info_layout.addWidget(self.url_label)
        
        self.url_value = QLabel("")
        self.url_value.setFont(QFont('Arial', 10))
        self.url_value.setStyleSheet("color: blue; text-decoration: underline;")
        self.url_info_layout.addWidget(self.url_value, 1)  # Give it stretch
        
        self.open_url_button = QPushButton("Open URL")
        self.open_url_button.setStyleSheet("""
            QPushButton {
                background-color: #465775;
                border: none;
                border-radius: 12px;
                color: white;
                padding: 5px 10px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #566985; }
            QPushButton:pressed { background-color: #364765; }
        """)
        self.open_url_button.setFixedHeight(30)
        self.open_url_button.clicked.connect(self.open_selected_url)
        self.open_url_button.setEnabled(False)
        self.url_info_layout.addWidget(self.open_url_button)
        
        # Hide the URL info layout initially
        self.url_widget = QWidget()
        self.url_widget.setLayout(self.url_info_layout)
        self.url_widget.setVisible(False)
        main_layout.addWidget(self.url_widget)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Filter button
        self.filter_button = self.create_button("Filter Data")
        self.filter_button.clicked.connect(self.show_filter_dialog)
        button_layout.addWidget(self.filter_button)
        
        # Save Changes button
        self.save_button = self.create_button("Save Changes")
        self.save_button.clicked.connect(self.save_changes)
        button_layout.addWidget(self.save_button)
        
        # Add spacer to push back button to the right
        button_layout.addStretch()
        
        # Back button
        self.back_button = self.create_button("Back")
        self.back_button.clicked.connect(self.close_viewer)
        button_layout.addWidget(self.back_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        
        # Store the current selected URL
        self.current_url = None
        
        # Flag to track if data has been modified
        self.data_modified = False
        
    def create_button(self, text):
        button = QPushButton(text)
        button.setFixedHeight(40)
        button.setFont(QFont('Arial', 12))
        button.setStyleSheet("""
            QPushButton {
                background-color: #465775;
                border: none;
                border-radius: 20px;
                color: white;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #566985;
            }
            QPushButton:pressed {
                background-color: #364765;
            }
            QPushButton:disabled {
                background-color: #a0a0a0;
            }
        """)
        return button
    
    def open_csv_file(self):
        """Open file dialog to select a CSV file"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV File", "", "CSV Files (*.csv);;All Files (*)", 
            options=options
        )
        
        if file_path:
            self.load_csv(file_path)
    
    def load_csv(self, file_path):
        """Load CSV file using pandas"""
        try:
            # First, try to detect the delimiter
            with open(file_path, 'r', newline='') as f:
                sample = f.read(4096)  # Read a sample to detect delimiter
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample)
                delimiter = dialect.delimiter
            
            # Read the CSV file with the detected delimiter
            self.df = pd.read_csv(file_path, delimiter=delimiter)
            
            # Update the model
            model = PandasModel(self.df)
            # Connect to dataChanged signal to track modifications
            model.dataChanged.connect(self.on_data_changed)
            self.table_view.setModel(model)
            
            # Auto-resize columns to content initially
            self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            
            # After initial resize, set interactive mode to allow user resizing
            self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            
            # Update header information
            filename = os.path.basename(file_path)
            self.header_label.setText(f"File: {filename} - {len(self.df)} rows, {len(self.df.columns)} columns")
            
            # Update window title
            self.setWindowTitle(f"CSV Viewer - {filename}")
            
            # Store the path
            self.csv_path = file_path
            
            # Reset modification flag
            self.data_modified = False
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CSV file: {str(e)}")
    
    def on_data_changed(self, topLeft, bottomRight, roles=None):
        """Track when data is modified"""
        self.data_modified = True
    
    def show_filter_dialog(self):
        """Show dialog to filter data"""
        if self.df is None:
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Filter Data")
        dialog.resize(400, 200)
        
        layout = QFormLayout()
        
        # Column selection
        column_combo = QComboBox()
        column_combo.addItems(self.df.columns)
        layout.addRow("Column:", column_combo)
        
        # Filter value
        filter_input = QLineEdit()
        layout.addRow("Value:", filter_input)
        
        # Filter type
        filter_type = QComboBox()
        filter_type.addItems(["Contains", "Equals", "Starts with", "Ends with", "Greater than", "Less than"])
        layout.addRow("Filter type:", filter_type)
        
        # Case sensitive option
        case_sensitive = QCheckBox("Case sensitive")
        layout.addRow("", case_sensitive)
        
        # Buttons
        button_layout = QHBoxLayout()
        apply_button = QPushButton("Apply Filter")
        apply_button.clicked.connect(dialog.accept)
        
        reset_button = QPushButton("Reset Filters")
        reset_button.clicked.connect(lambda: self.reset_filters(dialog))
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        
        button_layout.addWidget(apply_button)
        button_layout.addWidget(reset_button)
        button_layout.addWidget(cancel_button)
        
        layout.addRow("", button_layout)
        dialog.setLayout(layout)
        
        # Execute dialog
        if dialog.exec_() == QDialog.Accepted:
            self.apply_filter(
                column_combo.currentText(),
                filter_input.text(),
                filter_type.currentText(),
                case_sensitive.isChecked()
            )
    
    def apply_filter(self, column, value, filter_type, case_sensitive):
        """Apply filter to DataFrame"""
        try:
            # Store original DataFrame if this is first filter
            if not hasattr(self, 'original_df'):
                self.original_df = self.df.copy()
            else:
                # Start from original for new filter
                self.df = self.original_df.copy()
            
            # Apply filter based on type
            if filter_type == "Contains":
                if case_sensitive:
                    mask = self.df[column].astype(str).str.contains(value, regex=False)
                else:
                    mask = self.df[column].astype(str).str.contains(value, case=False, regex=False)
            
            elif filter_type == "Equals":
                if case_sensitive:
                    mask = self.df[column].astype(str) == value
                else:
                    mask = self.df[column].astype(str).str.lower() == value.lower()
            
            elif filter_type == "Starts with":
                if case_sensitive:
                    mask = self.df[column].astype(str).str.startswith(value)
                else:
                    mask = self.df[column].astype(str).str.lower().str.startswith(value.lower())
            
            elif filter_type == "Ends with":
                if case_sensitive:
                    mask = self.df[column].astype(str).str.endswith(value)
                else:
                    mask = self.df[column].astype(str).str.lower().str.endswith(value.lower())
            
            elif filter_type == "Greater than":
                # Try to convert to numeric for comparison
                try:
                    mask = pd.to_numeric(self.df[column]) > float(value)
                except:
                    QMessageBox.warning(self, "Warning", 
                                       "Could not apply numeric filter. Column may contain non-numeric values.")
                    return
            
            elif filter_type == "Less than":
                # Try to convert to numeric for comparison
                try:
                    mask = pd.to_numeric(self.df[column]) < float(value)
                except:
                    QMessageBox.warning(self, "Warning", 
                                       "Could not apply numeric filter. Column may contain non-numeric values.")
                    return
            
            # Apply filter
            self.df = self.df[mask]
            
            # Update the model
            model = PandasModel(self.df)
            self.table_view.setModel(model)
            
            # Update header with filter info
            filename = os.path.basename(self.csv_path)
            self.header_label.setText(
                f"File: {filename} - Filtered: {len(self.df)} of {len(self.original_df)} rows"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply filter: {str(e)}")
    
    def reset_filters(self, dialog=None):
        """Reset all filters and restore original data"""
        if hasattr(self, 'original_df'):
            self.df = self.original_df.copy()
            
            # Update the model
            model = PandasModel(self.df)
            self.table_view.setModel(model)
            
            # Update header
            filename = os.path.basename(self.csv_path)
            self.header_label.setText(f"File: {filename} - {len(self.df)} rows, {len(self.df.columns)} columns")
            
            if dialog:
                dialog.reject()
    
    def handle_cell_click(self, index):
        """Handle cell click to detect URLs and show the URL open option"""
        if not self.df is None and index.isValid():
            # Get the model and check if the cell has a URL
            model = self.table_view.model()
            
            # First hide the URL widget (we'll show it again if this is a URL)
            self.url_widget.setVisible(False)
            self.current_url = None
            
            if isinstance(model, PandasModel) and model.is_url(index.row(), index.column()):
                url = model.get_url(index.row(), index.column())
                self.current_url = url
                
                # Update the URL label and show the widget
                self.url_value.setText(url)
                self.open_url_button.setEnabled(True)
                self.url_widget.setVisible(True)
    
    def open_selected_url(self):
        """Open the currently selected URL"""
        if self.current_url:
            self.open_url(self.current_url)
    
    def is_wsl(self):
        """Check if running in Windows Subsystem for Linux"""
        try:
            with open('/proc/version', 'r') as f:
                return 'microsoft' in f.read().lower()
        except:
            return False
    
    def open_url(self, url):
        """Open a URL in the browser using similar approach to GitBuildingWindow"""
        try:
            # Ensure URL has a http/https prefix
            if not url.startswith(('http://', 'https://')):
                if url.startswith('www.'):
                    url = 'https://' + url
                else:
                    # If it's not clearly a web URL, show a confirmation dialog
                    reply = QMessageBox.question(
                        self, 'Open URL', 
                        f"Open this as a URL?\n\n{url}",
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return
                    # Assume https if user confirms
                    url = 'https://' + url
            
            # Check for WSL
            is_wsl = self.is_wsl()
                
            if is_wsl:
                # For WSL, try PowerShell's Start-Process first
                try:
                    powershell_command = f'Start-Process "{url}"'
                    subprocess.run(['powershell.exe', '-Command', powershell_command])
                except Exception as e:
                    # If PowerShell fails, try explorer
                    try:
                        subprocess.run(['explorer.exe', url])
                    except Exception as e2:
                        # As a last resort, show URL for manual copy
                        QMessageBox.information(
                            self, "Browser URL", 
                            f"Please copy and paste this URL into your browser:\n\n{url}"
                        )
            else:
                # For other systems, use standard webbrowser module
                webbrowser.open(url)
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open URL: {str(e)}")

    def save_changes(self):
        """Save changes to CSV file"""
        if not self.csv_path or not hasattr(self, 'df') or self.df is None:
            QMessageBox.warning(self, "Error", "No data loaded to save.")
            return
            
        try:
            # Get the model with updated data
            model = self.table_view.model()
            if not isinstance(model, PandasModel):
                QMessageBox.warning(self, "Error", "Invalid data model.")
                return
                
            # Get the updated DataFrame from the model
            updated_df = model.get_dataframe()
            
            # Confirm overwrite of original file
            reply = QMessageBox.question(
                self, 'Save Changes', 
                f"Save changes to the original file?\n\n{self.csv_path}",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Save to the original file path
                updated_df.to_csv(self.csv_path, index=False)
                QMessageBox.information(self, "Success", "Changes saved successfully.")
                self.data_modified = False
            else:
                # Save to a new file
                options = QFileDialog.Options()
                # Suggest a filename with _updated suffix
                base_name, ext = os.path.splitext(self.csv_path)
                suggested_path = f"{base_name}_updated{ext}"
                
                new_path, _ = QFileDialog.getSaveFileName(
                    self, "Save As", suggested_path, 
                    "CSV Files (*.csv);;All Files (*)", options=options
                )
                
                if new_path:
                    # Ensure .csv extension
                    if not new_path.lower().endswith('.csv'):
                        new_path += '.csv'
                    
                    # Save to the new file
                    updated_df.to_csv(new_path, index=False)
                    
                    # Update the current path and reload
                    self.csv_path = new_path
                    self.load_csv(new_path)
                    
                    QMessageBox.information(self, "Success", f"Changes saved to new file:\n{new_path}")
                    self.data_modified = False
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save changes: {str(e)}")
    
    def close_viewer(self):
        """Close the CSV viewer and return to system view"""
        # Check if there are unsaved changes
        if self.data_modified:
            reply = QMessageBox.question(
                self, 'Unsaved Changes', 
                "You have unsaved changes. Would you like to save before closing?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # Save changes
                self.save_changes()
                # If still modified (user canceled save dialog), don't close
                if self.data_modified:
                    return
            elif reply == QMessageBox.Cancel:
                # Cancel closing
                return
        
        self.close()
        
        # Return to system view
        if self.parent:
            self.parent.central_widget.setCurrentWidget(self.parent.system_view)
            self.parent.system_view.show()