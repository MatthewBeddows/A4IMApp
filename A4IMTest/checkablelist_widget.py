# checkable_list_widget.py

from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QWidget, QHBoxLayout, QCheckBox, QLabel

class CheckableListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def add_checkable_item(self, text):
        item = QListWidgetItem(self)
        self.addItem(item)
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        layout.setSpacing(0)
        checkbox = QCheckBox()
        label = QLabel(text)
        layout.addWidget(checkbox)
        layout.addWidget(label,1)
        item.setSizeHint(widget.sizeHint())
        self.setItemWidget(item, widget)
        return item
    

    def item_clicked(self, item):
        self.setCurrentItem(item)