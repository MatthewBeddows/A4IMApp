from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDialogButtonBox, QWidget, QHBoxLayout, QVBoxLayout, QTextEdit, QPushButton, QLabel, QLineEdit, QCheckBox,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem,
    QGraphicsLineItem, QGraphicsItem, QGraphicsPixmapItem, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, QPointF, QRectF, QLineF
from PyQt5.QtGui import QFont, QColor, QPen, QBrush, QPainter, QPixmap
from PyQt5.QtCore import QUrl
import math
import os
import re  # For regex operations to strip text in square brackets
import pygit2
import subprocess
from collections import OrderedDict

#class for creating modules
class AddModuleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Module")
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout()
        
        # Module name input
        self.name_input = QLineEdit()
        layout.addRow("Module Name:", self.name_input)
        
        # Module description input
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        layout.addRow("Description:", self.description_input)
        
        # Repository address input
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("https://github.com/username/repository")
        layout.addRow("Repository URL:", self.repo_input)
        
        # Parent module selection
        self.parent_select = QComboBox()
        self.parent_select.addItem("Project Root")
        layout.addRow("Parent Module:", self.parent_select)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
        
        self.setLayout(layout)

    def populate_parent_modules(self, modules):
        self.parent_select.clear()
        self.parent_select.addItem("Project Root")
        for module_name in modules:
            self.parent_select.addItem(module_name)

    def get_module_data(self):
        return {
            'name': self.name_input.text().strip(),
            'description': self.description_input.toPlainText().strip(),
            'repository': {
                'address': self.repo_input.text().strip()
            }
        }
# NodeItem class for modules
class NodeItem(QGraphicsRectItem):
    def __init__(self, name, data, system_view, node_type='module'):
        # Adjust size based on node depth (more nested modules will be smaller)
        depth = data.get('depth', 0)
        width = max(150 - depth * 10, 80)  # Minimum width of 80
        height = max(80 - depth * 5, 50)   # Minimum height of 50

        # Initialize the rectangle centered at (0,0)
        super().__init__(-width/2, -height/2, width, height)
        self.name = name
        self.data = data
        self.system_view = system_view
        self.node_type = node_type  # 'project' or 'module'
        self.completed = False  # Completion status
        self.parent_node = None  # Parent node
        self.child_nodes = []  # List of child nodes
        self.connected_lines = []  # List to store lines connected to this node

        # Set colors based on node type
        if node_type == 'project':
            self.setBrush(QBrush(QColor("#2E4A62")))  # Darker blue color for project node
        else:
            self.setBrush(QBrush(QColor("#465775")))  # Blue color for modules

        self.setPen(QPen(Qt.NoPen))  # No border around node
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsFocusable)
        self.setAcceptHoverEvents(False)

        # Create text label for the node
        text = QGraphicsTextItem(self)
        text.setDefaultTextColor(Qt.white)
        # Adjust font based on node depth
        font_size = max(12 - depth, 8)  # Decrease font size with depth
        font = QFont('Arial', font_size)
        font.setBold(True)  # Bold text
        text.setFont(font)
        # Strip text in square brackets from name
        display_name = re.sub(r'\[.*?\]', '', name).strip()
        text.setPlainText(display_name)
        text.setTextWidth(width - 10)

        # Center the text within the node
        text_rect = text.boundingRect()
        text_x = -text_rect.width() / 2
        text_y = -text_rect.height() / 2
        text.setPos(text_x, text_y)

        # Create status indicator at top right corner (not for project node)
        if node_type != 'project':
            indicator_size = 15
            indicator_x = width / 2 - indicator_size - 2
            indicator_y = -height / 2 + 2
            self.status_indicator = QGraphicsRectItem(0, 0, indicator_size, indicator_size, self)
            self.status_indicator.setBrush(QBrush(QColor("#D9534F")))  # Red color for incomplete
            self.status_indicator.setPen(QPen(Qt.black))
            self.status_indicator.setPos(indicator_x, indicator_y)

    # Handle mouse press event
    def mousePressEvent(self, event):
        self.scene().clearSelection()
        self.setSelected(True)
        self.system_view.node_clicked(self)
        # Prevent default behavior

    # Update the status indicator color
    def update_status_indicator(self):
        if self.completed:
            self.status_indicator.setBrush(QBrush(QColor("#32CD32")))  # Lime green
        elif self.has_completed_children():
            self.status_indicator.setBrush(QBrush(QColor("#F0AD4E")))  # Yellow
        else:
            self.status_indicator.setBrush(QBrush(QColor("#D9534F")))  # Red

    # Update node color based on completion status
    def update_node_color(self):
        if self.node_type != 'project':
            self.update_status_indicator()

    # Check if any child modules are completed
    def has_completed_children(self):
        for child in self.child_nodes:
            if child.completed or child.has_completed_children():
                return True
        return False

    # Check if all child modules are completed
    def all_children_completed(self):
        if not self.child_nodes:
            return self.completed
        return all(child.all_children_completed() for child in self.child_nodes)

# Custom GraphicsView class with zoom functionality
class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.zoom_factor = 1.15
        self.min_scale = 0.1
        self.max_scale = 10.0
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        # For mouse location zoom
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    # Override wheel event to implement zooming
    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        if angle > 0:
            zoom = self.zoom_factor
        else:
            zoom = 1 / self.zoom_factor

        current_scale = self.transform().m11()
        new_scale = current_scale * zoom

        if self.min_scale <= new_scale <= self.max_scale:
            mouse_pos = self.mapToScene(event.pos())
            self.scale(zoom, zoom)
            new_mouse_pos = self.mapToScene(event.pos())
            delta = new_mouse_pos - mouse_pos
            self.translate(delta.x(), delta.y())
        else:
            super().wheelEvent(event)

    # Ensure dragging is always possible
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().mouseReleaseEvent(event)

# Main SystemView class
class SystemView(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.project_node_x = -400  # Adjust this value as needed
        self.node_items = {}
        self.selected_node = None
        self.toggle_mode = False  # Toggle mode flag
        self.modules_data = {}  # Store modules data
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Set background color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor('white'))
        self.setPalette(palette)

        # Left layout for graphics view
        left_layout = QVBoxLayout()

        # Container for graphics view and buttons
        graphics_container = QWidget()
        graphics_layout = QVBoxLayout()
        graphics_layout.setContentsMargins(0, 0, 0, 0)
        graphics_container.setLayout(graphics_layout)

        # Label for modules graph
        modules_label = QLabel("Modules Graph")
        modules_label.setFont(QFont('Arial', 16, QFont.Bold))
        modules_label.setStyleSheet("color: #465775;")
        graphics_layout.addWidget(modules_label)

        # Create custom graphics view with zoom functionality
        self.graphics_view = ZoomableGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        self.graphics_view.setRenderHint(QPainter.Antialiasing)
        self.graphics_view.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #d9d9d9;
                border-radius: 5px;
                background-color: white;
            }
        """)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        graphics_layout.addWidget(self.graphics_view)

        # Buttons layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Reset View button
        reset_view_button = QPushButton("Reset View")
        reset_view_button.setStyleSheet(self.get_button_style())
        reset_view_button.clicked.connect(self.recenter_view)
        reset_view_button.setToolTip("Reset the view to the default position and zoom level")
        reset_view_button.setFixedSize(100, 30)
        button_layout.addWidget(reset_view_button)

        # Add Open Folder button
        open_folder_button = QPushButton("Open Folder")
        open_folder_button.setStyleSheet(self.get_button_style())
        open_folder_button.clicked.connect(self.open_project_folder)
        open_folder_button.setToolTip("Open the project folder in file explorer")
        open_folder_button.setFixedSize(100, 30)
        button_layout.addWidget(open_folder_button)

        # Toggle All button
        self.toggle_button = QPushButton("Toggle All")
        self.toggle_button.setStyleSheet(self.get_button_style())
        self.toggle_button.clicked.connect(self.toggle_modules)
        self.toggle_button.setToolTip("Toggle visibility of child modules")
        self.toggle_button.setFixedSize(100, 30)
        #button_layout.addWidget(self.toggle_button) re-add at a later date

        # Add "Add Module" button next to Toggle All button in button_layout
        self.add_module_button = QPushButton("Add Module")
        self.add_module_button.setStyleSheet(self.get_button_style())
        self.add_module_button.clicked.connect(self.show_add_module_dialog)
        self.add_module_button.setToolTip("Add a new module to the system")
        self.add_module_button.setFixedSize(100, 30)
        button_layout.addWidget(self.add_module_button)

        graphics_layout.addLayout(button_layout)
        left_layout.addWidget(graphics_container)

        # Right layout for module details and buttons
        right_layout = QVBoxLayout()

        # Module Title (initially hidden)
        self.module_title = QLabel()
        self.module_title.setFont(QFont('Arial', 16, QFont.Bold))
        self.module_title.setStyleSheet("color: #465775; margin-bottom: 10px;")
        self.module_title.setWordWrap(True)
        self.module_title.hide()
        right_layout.addWidget(self.module_title)

        # Container for repo link and assigned user
        header_container = QHBoxLayout()
        header_container.setSpacing(20)  # Space between elements



        # Repository Link Label (initially hidden)
        self.repo_link = QLabel()
        self.repo_link.setStyleSheet("""
            QLabel {
                color: #0066cc;
                font-size: 14px;
                font-weight: bold;
            }
            QLabel:hover {
                color: #003399;
                cursor: pointer;
            }
        """)
        self.repo_link.setCursor(Qt.PointingHandCursor)
        self.repo_link.mousePressEvent = self.open_repo_link
        self.repo_link.hide()
        header_container.addWidget(self.repo_link)

        # Add stretch to push assigned section to the right
        header_container.addStretch()

        # User/Team Assigned section
        assigned_container = QHBoxLayout()
        assigned_container.setSpacing(5)  # Space between label and value
        
        assigned_label = QLabel("User/Team Assigned:")
        assigned_label.setStyleSheet("color: #465775; font-weight: bold;")
        assigned_container.addWidget(assigned_label)
        
        self.assigned_value = QLabel("None")
        self.assigned_value.setStyleSheet("color: #808080;")
        self.assigned_value.mousePressEvent = self.start_editing
        assigned_container.addWidget(self.assigned_value)
        
        self.assigned_edit = QLineEdit()
        self.assigned_edit.setStyleSheet("color: black;")
        self.assigned_edit.hide()
        self.assigned_edit.editingFinished.connect(self.finish_editing)
        assigned_container.addWidget(self.assigned_edit)

        # Add the assigned container to the header
        header_container.addLayout(assigned_container)

        # Add the header container to the main layout
        right_layout.addLayout(header_container)

        # Add some vertical spacing after the header
        spacer = QWidget()
        spacer.setFixedHeight(10)
        right_layout.addWidget(spacer)

        # Checkbox for module completion
        self.completion_checkbox = QCheckBox("Mark as Completed")
        self.completion_checkbox.stateChanged.connect(self.completion_status_changed)
        self.completion_checkbox.hide()
        right_layout.addWidget(self.completion_checkbox)

        # Text edit for module details
        self.module_details = QTextEdit()
        self.module_details.setReadOnly(True)
        self.module_details.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d9d9d9;
                border-radius: 5px;
                padding: 10px;
                background-color: white;
                color: #465775;
                font-size: 14px;
            }
        """)
        right_layout.addWidget(self.module_details)

        # Buttons at the bottom
        self.construct_button = self.create_button("Construct")
        self.construct_button.clicked.connect(self.construct_module)
        self.construct_button.hide()
        right_layout.addWidget(self.construct_button)

        self.risk_button = self.create_button("Risk Assesment")
        #self.risk_button.clicked.connect(self.construct_module)
        right_layout.addWidget(self.risk_button)


        self.view_bom_button = self.create_button("View Module BOM")
        self.view_bom_button.clicked.connect(self.view_module_bom)
        right_layout.addWidget(self.view_bom_button)

        back_button = self.create_button("Back")
        back_button.clicked.connect(self.parent.show_main_menu)
        right_layout.addWidget(back_button)

        # Add left and right layouts to main layout
        layout.addLayout(left_layout, 2)
        layout.addLayout(right_layout, 1)

        self.setLayout(layout)

    # Helper method to create buttons
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

    # Populate modules in graphics scene
    def populate_modules(self, modules):
        self.modules_data = modules  # Store modules data for later use
        self.graphics_scene.clear()
        self.node_items.clear()
        self.all_nodes = []  # Keep track of all nodes
        self.initialize_nodes()

        # Adjust scene rectangle with extra space
        items_rect = self.graphics_scene.itemsBoundingRect()
        extra_space = 500
        items_rect.adjust(-extra_space, -extra_space, extra_space, extra_space)
        self.graphics_scene.setSceneRect(items_rect)

    # Initialize nodes recursively
    def initialize_nodes(self):
        # Create the Project Node
        self.project_node = self.add_node("A4IM Scanner", None, position=QPointF(0, 0), parent_node=None, depth=0)
        self.layout_modules(self.modules_data, parent_node=self.project_node, depth=1, x=0, y=0)

    # Layout modules recursively
    def layout_modules(self, modules, parent_node, depth, x, y):
        spacing_x = 200
        spacing_y = 150
        total_height = 0
        positions = []
        # First, calculate the total height needed
        for module_name in modules:
            child_modules = modules[module_name].get('submodules', {})
            num_children = len(child_modules)
            height = max((num_children * spacing_y), spacing_y)
            total_height += height
            positions.append((module_name, height))

        # Start positioning child modules
        current_y = y - total_height / 2
        for module_name, height in positions:
            module_data = modules[module_name]
            module_data['depth'] = depth  # Store depth for styling purposes
            position = QPointF(x + spacing_x, current_y + height / 2)
            module_node = self.add_node(module_name, module_data, position, parent_node, depth)
            self.all_nodes.append(module_node)
            # Recurse into child modules
            child_modules = module_data.get('submodules', {})
            if child_modules:
                self.layout_modules(child_modules, module_node, depth + 1, x + spacing_x, position.y())
            current_y += height

    # Add a node (project or module)
    def add_node(self, name, data, position, parent_node, depth):
        node = NodeItem(name, data if data else {}, self, node_type='module' if parent_node else 'project')
        node.setPos(position)
        node.setZValue(1)
        self.graphics_scene.addItem(node)

        node.parent_node = parent_node
        if parent_node:
            parent_node.child_nodes.append(node)
            # Draw a line connecting to parent
            line = QGraphicsLineItem(QLineF(parent_node.pos(), node.pos()))
            line.setPen(QPen(QColor("#808080"), 2))
            line.setZValue(0)
            self.graphics_scene.addItem(line)
            # Store the line in both nodes
            node.connected_lines.append(line)
            parent_node.connected_lines.append(line)

        self.node_items[node] = {'name': name, 'data': data}

        return node


    def update_parent_module_info(self, parent_name, new_module_address):
        """Update the parent module's moduleInfo.txt with the new module address"""
        architect_dir = os.path.join("Downloaded Repositories", self.parent.architect_folder)
        
        # Find parent module's folder
        parent_info = self.find_module_by_name(self.modules_data, parent_name)
        if parent_info and 'repository' in parent_info:
            parent_repo = parent_info['repository']['name']
            parent_info_path = os.path.join(architect_dir, parent_repo, "moduleInfo.txt")
            
            if os.path.exists(parent_info_path):
                # Read existing content
                with open(parent_info_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Find Requirements section and add new module
                requirements_index = -1
                for i, line in enumerate(lines):
                    if line.strip() == "[Requirements]":
                        requirements_index = i
                        break
                
                if requirements_index != -1:
                    # Add new module address after Requirements section
                    lines.insert(requirements_index + 1, f"[Module Address] {new_module_address}\n")
                    
                    # Write back to file
                    with open(parent_info_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)


    def show_add_module_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Module")
        
        layout = QFormLayout()
        
        # Module name input
        name_input = QLineEdit()
        layout.addRow("Module Name:", name_input)
        
        # Module description input
        description_input = QTextEdit()
        description_input.setMaximumHeight(100)
        layout.addRow("Description:", description_input)
        
        # Repository address input
        repo_input = QLineEdit()
        repo_input.setPlaceholderText("https://github.com/username/repository")
        layout.addRow("Repository URL:", repo_input)
        
        # Parent module selection - include all modules at all levels
        parent_select = QComboBox()
        parent_select.addItem("Project Root")
        
        # Add all top-level modules to the dropdown
        for module_name in self.modules_data:
            parent_select.addItem(module_name)
        
        # If a module is currently selected, set it as the default parent
        if self.selected_node and self.selected_node.node_type == 'module':
            selected_name = self.selected_node.name
            for i in range(parent_select.count()):
                if parent_select.itemText(i) == selected_name:
                    parent_select.setCurrentIndex(i)
                    break
        
        layout.addRow("Parent Module:", parent_select)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            try:
                module_name = name_input.text().strip()
                description = description_input.toPlainText().strip()
                repo_url = repo_input.text().strip()
                parent_name = parent_select.currentText()
                
                # Create module directory
                repo_dir = os.path.join("Downloaded Repositories", self.parent.repo_folder)
                repo_name = repo_url.split('/')[-1]
                module_dir = os.path.join(repo_dir, repo_name)
                os.makedirs(module_dir, exist_ok=True)
                
                # Create ModuleInfo.txt
                module_info_path = os.path.join(module_dir, "ModuleInfo.txt")
                with open(module_info_path, 'w', encoding='utf-8') as f:
                    f.write(f"[Module Name] {module_name}\n")
                    f.write(f"[Module Info] {description}\n")
                    f.write("[Requirements]\n")
                
                # Update parent's ModuleInfo.txt if this is a submodule
                if parent_name != "Project Root":
                    parent_info = self.find_module_by_name(self.modules_data, parent_name)
                    if parent_info and 'repository' in parent_info:
                        parent_repo = parent_info['repository']['name']
                        parent_info_path = os.path.join(repo_dir, parent_repo, "ModuleInfo.txt")
                        
                        if os.path.exists(parent_info_path):
                            with open(parent_info_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                            
                            requirements_index = -1
                            for i, line in enumerate(lines):
                                if line.strip() == "[Requirements]":
                                    requirements_index = i
                                    break
                            
                            if requirements_index != -1:
                                lines.insert(requirements_index + 1, f"[Module Address] {repo_url}\n")
                                
                                with open(parent_info_path, 'w', encoding='utf-8') as f:
                                    f.writelines(lines)
                
                # Update data structure
                new_module = {
                    'name': module_name,  # Add the name key to the module data
                    'description': description,
                    'submodules': OrderedDict(),
                    'submodule_addresses': [],
                    'repository': {
                        'name': repo_name,
                        'address': repo_url,
                        'docs_path': None
                    }
                }
                
                if parent_name == "Project Root":
                    self.modules_data[module_name] = new_module
                else:
                    # Add to parent module's submodules
                    parent_module = self.find_module_by_name(self.modules_data, parent_name)
                    if parent_module:
                        if 'submodules' not in parent_module:
                            parent_module['submodules'] = OrderedDict()
                        parent_module['submodules'][module_name] = new_module
                        
                        # Also add to parent's submodule_addresses
                        if 'submodule_addresses' not in parent_module:
                            parent_module['submodule_addresses'] = []
                        parent_module['submodule_addresses'].append(repo_url)
                    else:
                        raise Exception(f"Could not find parent module: {parent_name}")
                
                # Refresh the view
                self.populate_modules(self.modules_data)
                
                QMessageBox.information(self, "Success", f"Module '{module_name}' created successfully!")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create module: {str(e)}")

    def find_and_add_to_parent(self, modules, parent_name, new_module):
        for name, module in modules.items():
            if name == parent_name:
                if 'submodules' not in module:
                    module['submodules'] = OrderedDict()
                module['submodules'][new_module['name']] = new_module
                
                # Also add to parent's submodule_addresses
                if 'submodule_addresses' not in module:
                    module['submodule_addresses'] = []
                module['submodule_addresses'].append(new_module['repository']['address'])
                
                return True
            if 'submodules' in module:
                if self.find_and_add_to_parent(module['submodules'], parent_name, new_module):
                    return True
        return False


    # Called when a node is clicked
    def node_clicked(self, node):
        self.selected_node = node
        name = node.name
        data = node.data

        # Strip text in square brackets from name and description
        display_name = re.sub(r'\[.*?\]', '', name).strip()
        description = data.get('description', 'No details available.')
        description = re.sub(r'\[.*?\]', '', description).strip()

        # Update and show the title
        self.module_title.setText(display_name)
        self.module_title.show()

        # Show/hide repo link based on whether we have repository info
        repository_info = data.get('repository', {})
        if repository_info and repository_info.get('address'):
            self.repo_link.setText("Link to Repo")
            self.repo_link.show()
        else:
            self.repo_link.hide()

        assigned = data.get('assigned_to', 'None')

        # Display just the description in the details pane
        self.module_details.setText(description)
        self.assigned_value.setText(assigned)
        if assigned == 'None':
            self.assigned_value.setStyleSheet("color: #808080;")
        else:
            self.assigned_value.setStyleSheet("color: black;")

        # Show completion checkbox for modules (not for project node)
        if node.node_type == 'module':
            self.completion_checkbox.show()
            self.completion_checkbox.blockSignals(True)
            self.completion_checkbox.setChecked(node.completed)
            self.completion_checkbox.blockSignals(False)

            # Check if module has docs
            repository_info = data.get('repository', {})
            if repository_info and repository_info.get('docs_path'):
                self.construct_button.show()
            else:
                self.construct_button.hide()

            # Update View BOM button
            self.view_bom_button.setText("View Module BOM")
            self.view_bom_button.clicked.disconnect()
            self.view_bom_button.clicked.connect(self.view_module_bom)

        else:
            self.completion_checkbox.hide()
            self.construct_button.hide()

            # Update View BOM button
            self.view_bom_button.setText("View Project Info")
            self.view_bom_button.clicked.disconnect()
            self.view_bom_button.clicked.connect(self.view_project_info)

        # If in toggle mode and a module node is clicked, update the display
        if self.toggle_mode:
            self.update_toggle_view(node)


    def get_button_style(self):
        return """
            QPushButton {
                background-color: #465775;
                color: white;
                font-size: 12px;
                border: none;
                padding: 5px 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #566985;
            }
            QPushButton:pressed {
                background-color: #364765;
            }
        """

    def get_repo_name_from_node(self, node):
        """Extract repository name from module data"""
        if node.data and 'submodule_addresses' in node.data:
            # Get the first address (assuming it's the main module address)
            addresses = node.data.get('submodule_addresses', [])
            if addresses:
                # Extract repo name from the GitHub URL
                return addresses[0].split('/')[-1]
        return None

    # Start editing assigned value
    def start_editing(self, event):
        self.assigned_value.hide()
        self.assigned_edit.setText(self.assigned_value.text())
        self.assigned_edit.show()
        self.assigned_edit.setFocus()

    # Finish editing assigned value
    def finish_editing(self):
        new_text = self.assigned_edit.text()
        if new_text:
            self.assigned_value.setText(new_text)
            self.assigned_value.setStyleSheet("color: black;")
        else:
            self.assigned_value.setText("None")
            self.assigned_value.setStyleSheet("color: #808080;")
        self.assigned_edit.hide()
        self.assigned_value.show()
        # Update data structure with new assigned value
        if self.selected_node and isinstance(self.selected_node.data, dict):
            self.selected_node.data['assigned_to'] = new_text

    # Handle completion checkbox state change
    def completion_status_changed(self, state):
        if self.selected_node:
            self.selected_node.completed = bool(state)
            self.selected_node.update_node_color()
            # Update parent module node status
            parent_node = self.selected_node.parent_node
            while parent_node:
                parent_node.update_node_color()
                parent_node = parent_node.parent_node

    # View module BOM
    def view_module_bom(self):
        if self.selected_node:
            name = self.selected_node.name
            # Implement logic to open the module BOM URL
            # For now, we'll just print a message
            print(f"Viewing BOM for module: {name}")
            # You can use self.parent.show_git_building(...) if needed
        else:
            print("No module selected")

    # View project info
    def view_project_info(self):
        if self.selected_node:
            name = self.selected_node.name
            if self.selected_node.node_type == 'project':
                # Open the project info URL or display project information
                print(f"Viewing project info for: {name}")
            else:
                print("Please select the project node to view its info.")
        else:
            print("No project selected")

    def construct_module(self):
        if self.selected_node:
            repository_info = self.selected_node.data.get('repository', {})

            if repository_info and repository_info.get('docs_path'):
                file_url = QUrl.fromLocalFile(os.path.abspath(repository_info['docs_path']))
                
                self.parent.show_git_building(
                    self.selected_node.name,
                    None,
                    file_url.toString()
                )
            else:
                print("No documentation available for this module")
                
    # Recenter the graphics view
    def recenter_view(self):
        self.graphics_view.resetTransform()
        self.graphics_view.centerOn(0, 0)

    # Toggle modules visibility
    def toggle_modules(self):
        self.toggle_mode = not self.toggle_mode
        if self.toggle_mode:
            self.toggle_button.setText("Show All")
        else:
            self.toggle_button.setText("Toggle All")
        # Update the view without repopulating
        self.update_node_visibility()

    # Update the view when toggled
    def update_toggle_view(self, node):
        # Hide all child nodes except for the selected one
        for n in self.all_nodes:
            if n != node and n.parent_node == node:
                n.setVisible(not n.isVisible())
                for line in n.connected_lines:
                    line.setVisible(n.isVisible())

    def open_project_folder(self):
        """Open the project folder in the system file explorer - WSL compatible"""
        try:
            repo_dir = os.path.join(os.getcwd(), "Downloaded Repositories", self.parent.repo_folder)
            
            if not os.path.exists(repo_dir):
                QMessageBox.warning(self, "Folder Not Found", "Project folder does not exist.")
                return
            
            # Check for WSL
            is_wsl = False
            try:
                with open('/proc/version', 'r') as f:
                    if 'microsoft' in f.read().lower():
                        is_wsl = True
            except:
                pass
                
            if is_wsl:
                # For WSL, convert path to Windows format and use explorer.exe
                try:
                    # Get Windows path using wslpath
                    process = subprocess.run(['wslpath', '-w', repo_dir], 
                                            capture_output=True, text=True, check=True)
                    windows_path = process.stdout.strip()
                    
                    # Use Windows explorer to open the folder
                    subprocess.run(['explorer.exe', windows_path])
                except Exception as e:
                    # Try powershell.exe as a fallback
                    try:
                        subprocess.run(['powershell.exe', 'start', repo_dir])
                    except:
                        QMessageBox.information(self, "Folder Path", 
                                            f"Your project folder is located at:\n{repo_dir}")
            else:
                # Standard Linux/Unix/Mac handling
                import platform
                if platform.system() == "Windows":
                    subprocess.run(['explorer', repo_dir])
                else:
                    # Show dialog with path - simplest solution
                    QMessageBox.information(self, "Folder Path", 
                                        f"Your project folder is located at:\n{repo_dir}")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open folder: {str(e)}")


    def open_repo_link(self, event):
        if self.selected_node:
            repository_info = self.selected_node.data.get('repository', {})
            if repository_info and repository_info.get('address'):
                url = repository_info['address']
                # Ensure URL starts with http:// or https://
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url

                try:
                    # Use powershell.exe through WSL to open the URL in Windows' default browser
                    
                    subprocess.run(['powershell.exe', 'start', url])
                except Exception as e:
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Information)
                    msg.setWindowTitle("Repository Link")
                    msg.setText("Unable to open browser automatically.\nPlease copy this URL:")
                    msg.setInformativeText(url)
                    msg.setStandardButtons(QMessageBox.Ok)
                    
                    # Add copy button
                    copy_button = msg.addButton("Copy URL", QMessageBox.ActionRole)
                    copy_button.clicked.connect(lambda: self.copy_to_clipboard(url))
                    
                    msg.exec_()

    def copy_to_clipboard(self, text):
        """Helper method to copy text to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)


    def create_module_files(self, module_data, parent_name=None):
        """Create the module folder and moduleInfo.txt file"""
        architect_dir = os.path.join("Downloaded Repositories", self.parent.architect_folder)
        
        # Create repository name from the last part of the URL
        repo_name = module_data['repository']['address'].split('/')[-1]
        module_dir = os.path.join(architect_dir, repo_name)
        
        # Create module directory
        os.makedirs(module_dir, exist_ok=True)
        
        # Create moduleInfo.txt
        module_info_path = os.path.join(module_dir, "moduleInfo.txt")
        with open(module_info_path, 'w', encoding='utf-8') as f:
            f.write(f"[Module Name] {module_data['name']}\n")
            f.write(f"[Module Info] {module_data['description']}\n")
            f.write("[Requirements]\n")  # Start with empty requirements
        
        # Update parent's moduleInfo.txt if this is a submodule
        if parent_name and parent_name != "Project Root":
            self.update_parent_module_info(parent_name, module_data['repository']['address'])
        
        return module_dir

    

    def find_module_by_name(self, modules, target_name):
        """Recursively find a module by name in the module hierarchy"""
        for name, module in modules.items():
            if name == target_name:
                return module
            if 'submodules' in module:
                result = self.find_module_by_name(module['submodules'], target_name)
                if result:
                    return result
        return None



    # Update node visibility (used when toggling)
    def update_node_visibility(self):
        for node in self.all_nodes:
            node.setVisible(True)
            for line in node.connected_lines:
                line.setVisible(True)


    
