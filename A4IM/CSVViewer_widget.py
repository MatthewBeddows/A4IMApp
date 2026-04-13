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
    """Base model for displaying pandas DataFrame in QTableView"""

    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._data.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()

        col_name = self._data.columns[index.column()]

        if role == Qt.DisplayRole or role == Qt.EditRole:
            value = self._data.iloc[index.row(), index.column()]
            if pd.isna(value):
                return ""
            else:
                return str(value)

        if role == Qt.TextAlignmentRole:
            value = self._data.iloc[index.row(), index.column()]
            if isinstance(value, (int, float)):
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        if role == Qt.BackgroundRole:
            if index.row() % 2 == 0:
                return QColor(240, 240, 240)

        if role == Qt.ForegroundRole:
            if self.is_url(index.row(), index.column()):
                return QColor('blue')

        if role == Qt.FontRole:
            if self.is_url(index.row(), index.column()):
                font = QFont()
                font.setUnderline(True)
                return font

        if role == Qt.ToolTipRole:
            if self.is_url(index.row(), index.column()):
                value = self._data.iloc[index.row(), index.column()]
                return f"Click to open: {value}"
            return None

        return QVariant()

    def flags(self, index):
        """Set flags for cells"""
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])
            else:
                return str(section + 1)
        return QVariant()

    def is_url(self, row, column):
        """Check if the cell contains a URL"""
        value = self._data.iloc[row, column]
        if not isinstance(value, str):
            return False

        value_lower = value.lower().strip()
        if any(value_lower.startswith(prefix) for prefix in ['http://', 'https://', 'www.']):
            return True

        if ' ' not in value_lower and '.' in value_lower:
            parts = value_lower.split('.')
            if len(parts) >= 2:
                common_tlds = ['.com', '.org', '.net', '.io', '.edu', '.gov', '.co', '.us', '.uk', '.de', '.au']
                if any(value_lower.endswith(tld) for tld in common_tlds):
                    return True

        return False

    def get_url(self, row, column):
        """Get the URL from a cell"""
        value = str(self._data.iloc[row, column]).strip()
        if not value.lower().startswith(('http://', 'https://')):
            return 'https://' + value
        return value

    def get_dataframe(self):
        """Get the current DataFrame with all modifications"""
        return self._data.copy()


class BOMPandasModel(PandasModel):
    """Model for BOM display with editable 'Acquired' checkboxes"""

    def __init__(self, data):
        super().__init__(data)

        # Add 'Acquired' column if it doesn't exist
        if 'Acquired' not in self._data.columns:
            self._data['Acquired'] = 0
        else:
            self._data['Acquired'] = self._data['Acquired'].fillna(0).astype(int)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()

        col_name = self._data.columns[index.column()]

        # Special handling for Acquired column as checkbox
        if col_name == 'Acquired':
            if role == Qt.CheckStateRole:
                return Qt.Checked if self._data.iloc[index.row(), index.column()] else Qt.Unchecked
            if role == Qt.DisplayRole:
                return None
            if role == Qt.ToolTipRole:
                return "Check if you have acquired this part"
            if role == Qt.BackgroundRole:
                if index.row() % 2 == 0:
                    return QColor(240, 240, 240)
            return QVariant()

        # For non-Acquired columns, use base class behavior
        return super().data(index, role)

    def setData(self, index, value, role=Qt.EditRole):
        """Set data for editable cells (checkboxes)"""
        if not index.isValid():
            return False

        if role == Qt.CheckStateRole and self._data.columns[index.column()] == 'Acquired':
            self._data.iloc[index.row(), index.column()] = 1 if value == Qt.Checked else 0
            self.dataChanged.emit(index, index)
            return True

        return False

    def flags(self, index):
        """Set flags for cells - make Acquired column checkable"""
        if not index.isValid():
            return Qt.NoItemFlags

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable

        if self._data.columns[index.column()] == 'Acquired':
            flags |= Qt.ItemIsUserCheckable

        return flags


class CSVViewerWidget(QWidget):
    """Base CSV viewer widget with generic viewing functionality"""

    def __init__(self, parent=None, csv_path=None):
        super().__init__(None)  # No Qt parent — standalone window
        self.parent = parent
        self.csv_path = csv_path
        self.df = None
        self.setup_ui()

        if csv_path and os.path.exists(csv_path):
            self.load_csv(csv_path)

    def get_model_class(self):
        """Return the model class to use. Override in subclasses."""
        return PandasModel

    def setup_ui(self):
        self.setWindowTitle("CSV Viewer")
        self.resize(800, 600)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor('white'))
        self.setPalette(palette)

        # Header with file info
        self.header_label = QLabel("No file loaded")
        self.header_label.setFont(QFont('Arial', 12, QFont.Bold))
        self.header_label.setStyleSheet("color: #465775; margin-bottom: 10px;")
        main_layout.addWidget(self.header_label)

        # Table view
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
        self.table_view.clicked.connect(self.handle_cell_click)
        main_layout.addWidget(self.table_view, 1)

        # URL info area
        self.url_info_layout = QHBoxLayout()

        self.url_label = QLabel("Selected URL:")
        self.url_label.setFont(QFont('Arial', 10, QFont.Bold))
        self.url_label.setFixedWidth(100)
        self.url_info_layout.addWidget(self.url_label)

        self.url_value = QLabel("")
        self.url_value.setFont(QFont('Arial', 10))
        self.url_value.setStyleSheet("color: blue; text-decoration: underline;")
        self.url_info_layout.addWidget(self.url_value, 1)

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

        # Add custom buttons (for subclasses to override)
        self.add_custom_buttons(button_layout)

        button_layout.addStretch()

        # Close button
        self.back_button = self.create_button("Close")
        self.back_button.clicked.connect(self.close_viewer)
        button_layout.addWidget(self.back_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        self.current_url = None

    def add_custom_buttons(self, button_layout):
        """Override in subclasses to add custom buttons"""
        pass

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
            with open(file_path, 'r', newline='') as f:
                sample = f.read(4096)
            try:
                dialect = csv.Sniffer().sniff(sample)
                delimiter = dialect.delimiter
            except csv.Error:
                delimiter = ','

            self.df = pd.read_csv(file_path, delimiter=delimiter)

            # Use the model class from get_model_class()
            model_class = self.get_model_class()
            model = model_class(self.df)
            self.on_model_created(model)
            self.table_view.setModel(model)

            self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

            filename = os.path.basename(file_path)
            self.header_label.setText(f"File: {filename} - {len(self.df)} rows, {len(self.df.columns)} columns")
            self.setWindowTitle(f"CSV Viewer - {filename}")
            self.csv_path = file_path

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CSV file: {str(e)}")

    def on_model_created(self, model):
        """Hook for subclasses to connect to model signals"""
        pass

    def show_filter_dialog(self):
        """Show dialog to filter data"""
        if self.df is None:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Filter Data")
        dialog.resize(400, 200)

        layout = QFormLayout()

        column_combo = QComboBox()
        column_combo.addItems(self.df.columns)
        layout.addRow("Column:", column_combo)

        filter_input = QLineEdit()
        layout.addRow("Value:", filter_input)

        filter_type = QComboBox()
        filter_type.addItems(["Contains", "Equals", "Starts with", "Ends with", "Greater than", "Less than"])
        layout.addRow("Filter type:", filter_type)

        case_sensitive = QCheckBox("Case sensitive")
        layout.addRow("", case_sensitive)

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
            if not hasattr(self, 'original_df'):
                self.original_df = self.df.copy()
            else:
                self.df = self.original_df.copy()

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
                try:
                    mask = pd.to_numeric(self.df[column]) > float(value)
                except:
                    QMessageBox.warning(self, "Warning",
                                       "Could not apply numeric filter. Column may contain non-numeric values.")
                    return

            elif filter_type == "Less than":
                try:
                    mask = pd.to_numeric(self.df[column]) < float(value)
                except:
                    QMessageBox.warning(self, "Warning",
                                       "Could not apply numeric filter. Column may contain non-numeric values.")
                    return

            self.df = self.df[mask]

            model_class = self.get_model_class()
            model = model_class(self.df)
            self.on_model_created(model)
            self.table_view.setModel(model)

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

            model_class = self.get_model_class()
            model = model_class(self.df)
            self.on_model_created(model)
            self.table_view.setModel(model)

            filename = os.path.basename(self.csv_path)
            self.header_label.setText(f"File: {filename} - {len(self.df)} rows, {len(self.df.columns)} columns")

            if dialog:
                dialog.reject()

    def handle_cell_click(self, index):
        """Handle cell click to detect URLs"""
        if not self.df is None and index.isValid():
            model = self.table_view.model()

            self.url_widget.setVisible(False)
            self.current_url = None

            if isinstance(model, PandasModel) and model.is_url(index.row(), index.column()):
                url = model.get_url(index.row(), index.column())
                self.current_url = url

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
        """Open a URL in the browser"""
        try:
            if not url.startswith(('http://', 'https://')):
                if url.startswith('www.'):
                    url = 'https://' + url
                else:
                    reply = QMessageBox.question(
                        self, 'Open URL',
                        f"Open this as a URL?\n\n{url}",
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return
                    url = 'https://' + url

            is_wsl = self.is_wsl()

            if is_wsl:
                try:
                    powershell_command = f'Start-Process "{url}"'
                    subprocess.run(['powershell.exe', '-Command', powershell_command])
                except Exception as e:
                    try:
                        subprocess.run(['explorer.exe', url])
                    except Exception as e2:
                        QMessageBox.information(
                            self, "Browser URL",
                            f"Please copy and paste this URL into your browser:\n\n{url}"
                        )
            else:
                webbrowser.open(url)

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open URL: {str(e)}")

    def close_viewer(self):
        """Close the pop-out viewer window"""
        self.close()


class BOMViewerWidget(CSVViewerWidget):
    """BOM-specific CSV viewer with 'Acquired' checkbox functionality"""

    def __init__(self, parent=None, csv_path=None):
        super().__init__(parent, csv_path)

    def get_model_class(self):
        """Use BOM-specific model with checkboxes"""
        return BOMPandasModel

    def on_model_created(self, model):
        """Auto-save whenever a checkbox changes"""
        model.dataChanged.connect(self.on_data_changed)

    def on_data_changed(self, topLeft, bottomRight, roles=None):
        """Save to the original CSV immediately on any change"""
        if not self.csv_path:
            return
        try:
            model = self.table_view.model()
            if isinstance(model, BOMPandasModel):
                model.get_dataframe().to_csv(self.csv_path, index=False)
        except Exception as e:
            print(f"Auto-save failed: {e}")


class RiskAssessmentPandasModel(PandasModel):
    """Model for Risk Assessment display.
    Rows with _mitigated=True (set by merge_mitigation_rows) are highlighted green.
    The _mitigated column is hidden from the view.
    """

    def __init__(self, data):
        super().__init__(data)
        self._has_mitigated = '_mitigated' in data.columns
        # Visible columns exclude the internal _mitigated flag
        self._visible_cols = [c for c in data.columns if c != '_mitigated']
        # Pre-compute actual DataFrame column indices for visible columns
        self._visible_idx = [data.columns.get_loc(c) for c in self._visible_cols]

    def columnCount(self, parent=QModelIndex()):
        return len(self._visible_cols)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._visible_cols[section])
            else:
                return str(section + 1)
        return QVariant()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()

        # Map display column → actual DataFrame column index
        df_col = self._visible_idx[index.column()]

        if role == Qt.BackgroundRole:
            if self._has_mitigated and bool(self._data.iloc[index.row()]['_mitigated']):
                return QColor(200, 240, 200)
            if index.row() % 2 == 0:
                return QColor(240, 240, 240)
            return QVariant()

        if role == Qt.DisplayRole or role == Qt.EditRole:
            value = self._data.iloc[index.row(), df_col]
            return "" if pd.isna(value) else str(value)

        if role == Qt.TextAlignmentRole:
            value = self._data.iloc[index.row(), df_col]
            if isinstance(value, (int, float)):
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        if role == Qt.ForegroundRole:
            if self.is_url(index.row(), df_col):
                return QColor('blue')

        if role == Qt.FontRole:
            if self.is_url(index.row(), df_col):
                font = QFont()
                font.setUnderline(True)
                return font

        if role == Qt.ToolTipRole:
            if self.is_url(index.row(), df_col):
                value = self._data.iloc[index.row(), df_col]
                return f"Click to open: {value}"
            return None

        return QVariant()


class RiskAssessmentViewerWidget(CSVViewerWidget):
    """Risk Assessment CSV viewer with green highlighting and word wrap"""

    def __init__(self, parent=None, csv_path=None):
        super().__init__(parent, csv_path)

    def get_model_class(self):
        """Use Risk Assessment model with green highlighting"""
        return RiskAssessmentPandasModel

    def load_csv(self, file_path):
        """Load CSV, merge mitigation rows if needed, enable word wrap"""
        try:
            with open(file_path, 'r', newline='') as f:
                sample = f.read(4096)
            try:
                dialect = csv.Sniffer().sniff(sample)
                delimiter = dialect.delimiter
            except csv.Error:
                delimiter = ','

            df = pd.read_csv(file_path, delimiter=delimiter)

            # Merge mitigation rows into columns if applicable
            df = self.merge_mitigation_rows(df)

            self.df = df

            model_class = self.get_model_class()
            model = model_class(self.df)
            self.on_model_created(model)
            self.table_view.setModel(model)

            # Enable word wrap and auto-fit rows
            self.table_view.setWordWrap(True)
            self.table_view.setTextElideMode(Qt.ElideNone)
            self.table_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            self.table_view.verticalHeader().setMinimumSectionSize(30)

            # Auto-fit columns to content, then allow interactive resize
            self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

            filename = os.path.basename(file_path)
            self.header_label.setText(f"File: {filename} - {len(self.df)} rows, {len(self.df.columns)} columns")
            self.setWindowTitle(f"Risk Assessment - {filename}")
            self.csv_path = file_path

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load risk assessment file: {str(e)}")

    def merge_mitigation_rows(self, df):
        """Merge mitigation rows into their matching risk rows as extra columns.

        Looks for a Type column with Risk/Mitigation values. Mitigation rows are
        matched to risks by a shared key column (e.g. Error_Code) if one exists,
        otherwise positionally (mitigation must immediately follow its risk).

        Sets a '_mitigated' boolean column: True on risk rows that had a mitigation
        merged into them. The column is hidden from display by the model.
        """
        RISK_VALUES = {'risk', 'hazard', 'error'}
        MIT_VALUES = {'mitigation', 'control', 'measure', 'control measure'}

        # Find a Type column
        type_col = None
        for col in df.columns:
            if col.lower().replace('_', ' ').strip() in (
                    'type', 'row type', 'entry type', 'category', 'item type'):
                type_col = col
                break

        if type_col is None:
            df = df.copy()
            df['_mitigated'] = False
            return df

        values = df[type_col].astype(str).str.lower().str.strip()
        has_risks = values.isin(RISK_VALUES).any()
        has_mitigations = values.isin(MIT_VALUES).any()

        if not has_risks or not has_mitigations:
            df = df.copy()
            df['_mitigated'] = False
            return df

        other_cols = [c for c in df.columns if c != type_col]

        # Try to find a key column for matching (e.g. Error_Code, ID, Code)
        key_col = None
        for col in df.columns:
            norm = col.lower().replace('_', ' ').strip()
            if norm in ('error code', 'id', 'code', 'risk id', 'hazard id',
                        'ref', 'reference', 'number', 'no'):
                key_col = col
                break

        risk_mask = values.isin(RISK_VALUES)
        mit_mask = values.isin(MIT_VALUES)

        merged_rows = []

        if key_col:
            # Build mitigation lookup keyed by the shared key column
            mit_lookup = {}
            for _, mit_row in df[mit_mask].iterrows():
                k = str(mit_row[key_col]).strip() if not pd.isna(mit_row[key_col]) else None
                if k:
                    mit_lookup[k] = mit_row

            matched_keys = set()
            for _, risk_row in df[risk_mask].iterrows():
                row_data = {col: risk_row[col] for col in other_cols}
                k = str(risk_row[key_col]).strip() if not pd.isna(risk_row[key_col]) else None
                if k and k in mit_lookup:
                    mit_row = mit_lookup[k]
                    for col in other_cols:
                        if col == key_col:
                            continue
                        val = mit_row[col]
                        if not pd.isna(val) and str(val).strip():
                            row_data[f"Mitigation {col}"] = val
                    row_data['_mitigated'] = True
                    matched_keys.add(k)
                else:
                    row_data['_mitigated'] = False
                merged_rows.append(row_data)

            # Unmatched mitigation rows that had no corresponding risk
            for _, mit_row in df[mit_mask].iterrows():
                k = str(mit_row[key_col]).strip() if not pd.isna(mit_row[key_col]) else None
                if not k or k not in matched_keys:
                    row_data = {col: mit_row[col] for col in other_cols}
                    row_data['_mitigated'] = True
                    merged_rows.append(row_data)

            # Rows that are neither risk nor mitigation
            for i, row in df[~risk_mask & ~mit_mask].iterrows():
                row_data = {col: row[col] for col in other_cols}
                row_data['_mitigated'] = False
                merged_rows.append(row_data)

        else:
            # Positional: mitigation must immediately follow its risk row
            i = 0
            while i < len(df):
                row_type = str(df.iloc[i][type_col]).lower().strip()
                if row_type in RISK_VALUES:
                    row_data = {col: df.iloc[i][col] for col in other_cols}
                    if i + 1 < len(df):
                        next_type = str(df.iloc[i + 1][type_col]).lower().strip()
                        if next_type in MIT_VALUES:
                            for col in other_cols:
                                val = df.iloc[i + 1][col]
                                if not pd.isna(val) and str(val).strip():
                                    row_data[f"Mitigation {col}"] = val
                            row_data['_mitigated'] = True
                            merged_rows.append(row_data)
                            i += 2
                            continue
                    row_data['_mitigated'] = False
                    merged_rows.append(row_data)
                elif row_type in MIT_VALUES:
                    # Unmatched standalone mitigation row
                    row_data = {col: df.iloc[i][col] for col in other_cols}
                    row_data['_mitigated'] = True
                    merged_rows.append(row_data)
                else:
                    row_data = {col: df.iloc[i][col] for col in other_cols}
                    row_data['_mitigated'] = False
                    merged_rows.append(row_data)
                i += 1

        return pd.DataFrame(merged_rows) if merged_rows else df
