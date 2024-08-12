# system_view.py

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QTextEdit, 
                             QPushButton, QLabel, QCheckBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPalette
from checkablelist_widget import CheckableListWidget

class SystemView(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Set flat white background
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor('white'))
        self.setPalette(palette)

        # Left side (System List)
        left_layout = QVBoxLayout()
        
        systems_label = QLabel("Systems")
        systems_label.setFont(QFont('Arial', 16, QFont.Bold))
        systems_label.setStyleSheet("color: #465775;")
        left_layout.addWidget(systems_label)

        self.system_list = CheckableListWidget()
        self.system_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #d9d9d9;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
            }
            QListWidget::item {
                padding: 0px;
                border-bottom: 1px solid #d9d9d9;
            }
            QCheckBox {
                margin-right: 5px;
            }
            QLabel {
                color: #465775;
            }
        """)
        self.system_list.itemClicked.connect(self.show_system_details)
        left_layout.addWidget(self.system_list)

        # Right side (System Details and Buttons)
        right_layout = QVBoxLayout()

        details_label = QLabel("System Details")
        details_label.setFont(QFont('Arial', 16, QFont.Bold))
        details_label.setStyleSheet("color: #465775;")
        right_layout.addWidget(details_label)

        self.system_details = QTextEdit()
        self.system_details.setReadOnly(True)
        self.system_details.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d9d9d9;
                border-radius: 5px;
                padding: 10px;
                background-color: white;
                color: #465775;
                font-size: 14px;
            }
        """)
        right_layout.addWidget(self.system_details)

        construct_button = self.create_button("Construct")
        construct_button.clicked.connect(self.construct_system)
        right_layout.addWidget(construct_button)

        back_button = self.create_button("Back")
        back_button.clicked.connect(self.parent.show_main_menu)
        right_layout.addWidget(back_button)

        # Add layouts to main layout
        layout.addLayout(left_layout, 1)
        layout.addLayout(right_layout, 2)

        self.setLayout(layout)

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
        """)
        return button

    def populate_systems(self, systems):
        self.system_list.clear()
        for system_name in systems:
            item = self.system_list.add_checkable_item(system_name)
            widget = self.system_list.itemWidget(item)
            checkbox = widget.findChild(QCheckBox)
            label = widget.findChild(QLabel)
            checkbox.setStyleSheet("QCheckBox { color: #465775; }")
            label.setStyleSheet("QLabel { color: #465775; font-size: 14px; }")
            # Make the label expand to fill available space
            widget.layout().setStretchFactor(label, 1)

    def show_system_details(self, item):
        widget = self.system_list.itemWidget(item)
        system_name = widget.findChild(QLabel).text()
        system_info = self.parent.systems.get(system_name, {})
        self.system_details.setText(system_info.get('description', ''))

    def construct_system(self):
        current_item = self.system_list.currentItem()
        if current_item:
            widget = self.system_list.itemWidget(current_item)
            system_name = widget.findChild(QLabel).text()
            self.parent.show_module_view(system_name)
        else:
            print("Please select a system")