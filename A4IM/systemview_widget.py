from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDialogButtonBox, QWidget, QHBoxLayout, QVBoxLayout, QTextEdit, QPushButton, QLabel, QLineEdit, QCheckBox,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem,
    QGraphicsLineItem, QGraphicsItem, QGraphicsPixmapItem, QMessageBox, QApplication, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt, QPointF, QRectF, QLineF
from PyQt5.QtGui import QFont, QColor, QPen, QBrush, QPainter, QPixmap
from PyQt5.QtCore import QUrl, QThread, pyqtSignal
import math
import os
import tempfile
import re 
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
        self.node_type = node_type  # 'module'
        self.completed = False  # Completion status
        self.completion_status = 'not_started'  # 'not_started', 'in_progress', 'completed'
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
        text.setTextWidth(width - 30)  # Leave more space for indicators

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
        
        # Track download state
        self.is_downloaded = data.get('is_downloaded', False)
        
        # Add download indicator at BOTTOM LEFT corner
        if node_type != 'project':
            self.download_indicator = QGraphicsTextItem(self)
            self.download_indicator.setDefaultTextColor(QColor("#FFD700"))  # Gold color
            download_font = QFont('Arial', 14, QFont.Bold)
            self.download_indicator.setFont(download_font)
            self.download_indicator.setPlainText("☁")  # Cloud icon
            
            # Position at bottom right
            indicator_width = self.download_indicator.boundingRect().width()
            indicator_height = self.download_indicator.boundingRect().height()
            self.download_indicator.setPos(
                width/2 - indicator_width - 3,  # Right edge with small padding
                height/2 - indicator_height - 3  # Bottom edge with small padding
            )

    # Handle mouse press event
    def mousePressEvent(self, event):
        self.scene().clearSelection()
        self.setSelected(True)
        self.system_view.node_clicked(self)
        

    # Update the status indicator color based on completion status
    def update_status_indicator(self):
        print(f"Updating status indicator for {self.name}: completion_status = {self.completion_status}")
        if self.completion_status == 'completed':
            self.status_indicator.setBrush(QBrush(QColor("#32CD32")))  # Lime green
            print(f"  -> Set to GREEN (completed)")
        elif self.completion_status == 'in_progress':
            self.status_indicator.setBrush(QBrush(QColor("#F0AD4E")))  # Yellow
            print(f"  -> Set to YELLOW (in_progress)")
        elif self.has_completed_children():
            self.status_indicator.setBrush(QBrush(QColor("#F0AD4E")))  # Yellow
            print(f"  -> Set to YELLOW (has completed children)")
        else:
            self.status_indicator.setBrush(QBrush(QColor("#D9534F")))  # Red
            print(f"  -> Set to RED (not_started)")

    # Update node color based on completion status
    def update_node_color(self):
        if self.node_type != 'project':
            # For loading: if we already have a specific completion_status from file, respect it
            if hasattr(self, 'data') and self.data and 'completion_status' in self.data:
                self.completion_status = self.data['completion_status']
                print(f"update_node_color for {self.name}: using loaded status = {self.completion_status}")
            else:
                # Determine the current status dynamically (for runtime changes)
                if self.completed:
                    self.completion_status = 'completed'
                elif self.has_completed_children():
                    # Only set to in_progress if not explicitly completed and not already set
                    if self.completion_status not in ['completed', 'in_progress']:
                        self.completion_status = 'in_progress'
                        # Save the in_progress status to file
                        if hasattr(self, 'data') and self.data:
                            self.data['completion_status'] = 'in_progress'
                            self.system_view.save_module_data_to_file(self.data)
                else:
                    if self.completion_status != 'completed':
                        self.completion_status = 'not_started'
                
                print(f"update_node_color for {self.name}: determined status = {self.completion_status}")
            
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
        self.project_name = None  # Store the project name dynamically
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

        self.risk_button = self.create_button("Risk Assessment")
        self.risk_button.clicked.connect(self.open_risk_assessment)
        self.risk_button.hide()  # Initially hide the button
        right_layout.addWidget(self.risk_button)


        self.view_bom_button = self.create_button("View Module BOM")
        self.view_bom_button.clicked.connect(self.view_module_bom)
        right_layout.addWidget(self.view_bom_button)

        # Add these new CSV buttons
        self.inventory_button = self.create_button("View Inventory")
        self.inventory_button.clicked.connect(self.view_inventory_csv)
        self.inventory_button.hide()
        right_layout.addWidget(self.inventory_button)

        self.parts_button = self.create_button("View Parts")
        self.parts_button.clicked.connect(self.view_parts_csv)
        self.parts_button.hide()
        right_layout.addWidget(self.parts_button)

        self.materials_button = self.create_button("View Materials")
        self.materials_button.clicked.connect(self.view_materials_csv)
        self.materials_button.hide()
        right_layout.addWidget(self.materials_button)

        # Replace both download buttons with a single one
        self.download_module_button = self.create_button("Download Module")
        self.download_module_button.clicked.connect(self.show_download_dialog)
        self.download_module_button.hide()
        right_layout.addWidget(self.download_module_button)


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
    def populate_modules(self, modules, project_name=None):
        self.modules_data = modules  # Store modules data for later use
        
        # Set the project name - try multiple sources
        if project_name:
            self.project_name = project_name
        elif hasattr(self.parent, 'project_name') and self.parent.project_name:
            self.project_name = self.parent.project_name
        elif hasattr(self.parent, 'architect_folder') and self.parent.architect_folder:
            # Use the architect folder name as project name
            self.project_name = self.parent.architect_folder
        else:
            # Fallback to first module name or default
            if modules:
                self.project_name = list(modules.keys())[0] + " Project"
            else:
                self.project_name = "Project"
        
        self.graphics_scene.clear()
        self.node_items.clear()
        self.all_nodes = []  # Keep track of all nodes
        self.initialize_nodes()

        # Update all node colors after all nodes are created
        # This ensures proper status indication based on loaded data
        for node in self.all_nodes:
            if node.node_type == 'module':
                print(f"Updating color for {node.name}: completion_status = {node.completion_status}")
                node.update_node_color()

        # Adjust scene rectangle with extra space
        items_rect = self.graphics_scene.itemsBoundingRect()
        extra_space = 500
        items_rect.adjust(-extra_space, -extra_space, extra_space, extra_space)
        self.graphics_scene.setSceneRect(items_rect)


    # Initialize nodes recursively
    def initialize_nodes(self):
        # Start directly with the modules - no separate project node needed
        # The first architect module becomes the root
        self.layout_modules(self.modules_data, parent_node=None, depth=0, x=0, y=0)

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
            
            # Load additional data from ModuleInfo.txt
            self.load_module_data_from_file(module_data)
            
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
        
        # Set completion status from loaded data
        if data:
            if 'completed' in data:
                node.completed = data['completed']
            
            # Set the completion status for proper color handling
            if 'completion_status' in data:
                node.completion_status = data['completion_status']
                print(f"Node {name}: loaded completion_status = {node.completion_status}")
            else:
                # Determine status based on completed flag for backward compatibility
                node.completion_status = 'completed' if data.get('completed', False) else 'not_started'
                print(f"Node {name}: determined completion_status = {node.completion_status}")
        else:
            node.completion_status = 'not_started'
        
        # Check if repository is actually downloaded on disk
        if data and 'repository' in data:
            repo_info = data.get('repository', {})
            if repo_info and repo_info.get('name'):
                repo_dir = os.path.join("Downloaded Repositories", self.parent.repo_folder)
                repo_path = os.path.join(repo_dir, repo_info.get('name'))
                
                # Check if directory exists and has content (not just metadata)
                if os.path.exists(repo_path) and os.path.isdir(repo_path):
                    # Check if it has actual repo content (not just in .metadata folder)
                    has_content = False
                    try:
                        # Look for common repo files/folders besides just ModuleInfo.txt
                        contents = os.listdir(repo_path)
                        # Filter out just metadata files
                        real_contents = [f for f in contents if f.lower() not in ['moduleinfo.txt', 'moduleinfor.txt']]
                        if real_contents:
                            has_content = True
                    except:
                        pass
                    
                    if has_content:
                        node.is_downloaded = True
                        if hasattr(node, 'download_indicator'):
                            node.download_indicator.setPlainText("✓")
                            node.download_indicator.setDefaultTextColor(QColor("#32CD32"))  # Green
                        print(f"Node {name}: Repository found on disk - marked as downloaded")
                    else:
                        node.is_downloaded = False
                        print(f"Node {name}: Repository folder exists but is empty")
                else:
                    node.is_downloaded = False
                    print(f"Node {name}: Repository not found on disk")
            else:
                node.is_downloaded = False
        else:
            node.is_downloaded = False
        
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

    def load_module_data_from_file(self, module_data):
        """Load assigned_to and completed status from ModuleInfo.txt"""
        if not module_data or not isinstance(module_data, dict):
            return
            
        repository_info = module_data.get('repository', {})
        if not repository_info or not repository_info.get('name'):
            return
            
        # Get the repository folder
        repo_dir = os.path.join("Downloaded Repositories", self.parent.repo_folder)
        module_dir = os.path.join(repo_dir, repository_info.get('name'))
        
        if not os.path.exists(module_dir):
            return
        
        # Find ModuleInfo.txt file
        module_info_path = self.find_module_info_file(module_dir)
        
        if not module_info_path:
            return
            
        try:
            with open(module_info_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse for assigned_to
            assigned_match = re.search(r'\[Team/Assigned\]\s*(.+)', content, re.IGNORECASE)
            if assigned_match:
                assigned_value = assigned_match.group(1).strip()
                module_data['assigned_to'] = assigned_value if assigned_value else 'None'
            else:
                module_data['assigned_to'] = 'None'
            
            # Parse for completed status
            completed_match = re.search(r'\[Completed\]\s*(.+)', content, re.IGNORECASE)
            if completed_match:
                completed_value = completed_match.group(1).strip().lower()
                if completed_value in ['yes', 'true', '1']:
                    module_data['completed'] = True
                    module_data['completion_status'] = 'completed'
                elif completed_value == 'in progress':
                    module_data['completed'] = False
                    module_data['completion_status'] = 'in_progress'
                else:
                    module_data['completed'] = False
                    module_data['completion_status'] = 'not_started'
            else:
                module_data['completed'] = False
                module_data['completion_status'] = 'not_started'
                
        except Exception as e:
            print(f"Error loading module data from {module_info_path}: {str(e)}")
            module_data['assigned_to'] = 'None'
            module_data['completed'] = False
            module_data['completion_status'] = 'not_started'

    def save_module_data_to_file(self, module_data):
        """Save assigned_to and completed status to ModuleInfo.txt"""
        if not module_data or not isinstance(module_data, dict):
            return False
            
        repository_info = module_data.get('repository', {})
        if not repository_info or not repository_info.get('name'):
            return False
            
        # Get the repository folder
        repo_dir = os.path.join("Downloaded Repositories", self.parent.repo_folder)
        module_dir = os.path.join(repo_dir, repository_info.get('name'))
        
        if not os.path.exists(module_dir):
            return False
        
        # Find ModuleInfo.txt file
        module_info_path = self.find_module_info_file(module_dir)
        
        if not module_info_path:
            return False
            
        try:
            # Read current content
            with open(module_info_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assigned_to = module_data.get('assigned_to', 'None')
            
            # Determine completion status text
            completion_status = module_data.get('completion_status', 'not_started')
            if completion_status == 'completed':
                completed_text = 'Yes'
            elif completion_status == 'in_progress':
                completed_text = 'In progress'
            else:
                completed_text = 'No'
            
            # Update or add [Team/Assigned] line
            if re.search(r'\[Team/Assigned\]', content, re.IGNORECASE):
                content = re.sub(r'\[Team/Assigned\].*', f"[Team/Assigned] {assigned_to}", content, flags=re.IGNORECASE)
            else:
                content += f"\n[Team/Assigned] {assigned_to}"
            
            # Update or add [Completed] line
            if re.search(r'\[Completed\]', content, re.IGNORECASE):
                content = re.sub(r'\[Completed\].*', f"[Completed] {completed_text}", content, flags=re.IGNORECASE)
            else:
                content += f"\n[Completed] {completed_text}"
            
            # Write back to file
            with open(module_info_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return True
            
        except Exception as e:
            print(f"Error saving module data to {module_info_path}: {str(e)}")
            return False

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
        parent_select.addItem("Project Root")  # No user data needed for root
        
        # Collect all module names including nested submodules
        def collect_modules(modules, depth=0):
            for module_name, module_data in modules.items():
                # Create indented display name for visual hierarchy
                display_name = "  " * depth + module_name
                # Add to dropdown with actual module name as user data
                parent_select.addItem(display_name, module_name)
                
                # Process submodules if any
                if 'submodules' in module_data and module_data['submodules']:
                    collect_modules(module_data['submodules'], depth + 1)
        
        # Collect all modules from the hierarchy
        collect_modules(self.modules_data)
        
        # If a module is currently selected, set it as the default parent
        if self.selected_node and self.selected_node.node_type == 'module':
            selected_name = self.selected_node.name
            for i in range(parent_select.count()):
                # Use itemData to get the actual module name without indentation
                item_data = parent_select.itemData(i)
                if item_data == selected_name:
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
                
                # Get the actual module name from the dropdown's user data
                parent_index = parent_select.currentIndex()
                if parent_index == 0:  # "Project Root" is selected
                    parent_name = "Project Root"
                else:
                    # Get the actual module name from itemData (without indentation)
                    parent_name = parent_select.itemData(parent_index)
                
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
                        parent_repo_dir = os.path.join(repo_dir, parent_repo)
                        
                        # Use the new function to find the module info file
                        parent_info_path = self.find_module_info_file(parent_repo_dir)
                        
                        if parent_info_path:
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
                            else:
                                # If [Requirements] section not found, add it
                                lines.append("[Requirements]\n")
                                lines.append(f"[Module Address] {repo_url}\n")
                                
                                with open(parent_info_path, 'w', encoding='utf-8') as f:
                                    f.writelines(lines)
                        else:
                            # Create new module info file if not found
                            parent_info_path = os.path.join(parent_repo_dir, "ModuleInfo.txt")
                            with open(parent_info_path, 'w', encoding='utf-8') as f:
                                f.write(f"[Module Name] {parent_name}\n")
                                f.write(f"[Module Info] Parent module for {module_name}\n")
                                f.write("[Requirements]\n")
                                f.write(f"[Module Address] {repo_url}\n")
                    else:
                        raise Exception(f"Could not find parent module: {parent_name}")
                
                # Update data structure
                new_module = {
                    'name': module_name,
                    'description': description,
                    'submodules': OrderedDict(),
                    'submodule_addresses': [],
                    'repository': {
                        'name': repo_name,
                        'address': repo_url,
                        'docs_path': None
                    },
                    'assigned_to': 'None',
                    'completed': False,
                    'completion_status': 'not_started'
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
            doc_file_path = self.check_module_documentation(data)
            if doc_file_path:
                self.construct_button.show()
            else:
                self.construct_button.hide()

            # Check if risk assessment exists (current + children)
            if self.has_csv_in_children(node, self.check_risk_assessment_file):
                self.risk_button.show()
            else:
                self.risk_button.hide()

            # Check for BOM files (current + children)
            if self.has_csv_in_children(node, self.check_for_bom_file):
                self.view_bom_button.show()
            else:
                self.view_bom_button.hide()

            # Check for inventory files (current + children)
            if self.has_csv_in_children(node, self.check_for_inventory_csv):
                self.inventory_button.show()
            else:
                self.inventory_button.hide()

            # Check for parts files (current + children)
            if self.has_csv_in_children(node, self.check_for_parts_csv):
                self.parts_button.show()
            else:
                self.parts_button.hide()

            # Check for materials files (current + children)
            if self.has_csv_in_children(node, self.check_for_materials_csv):
                self.materials_button.show()
            else:
                self.materials_button.hide()

        else:
            # For project node
            self.completion_checkbox.hide()
            self.construct_button.hide()
            
            # Check if risk assessment exists in children for project node
            if self.has_csv_in_children(node, self.check_risk_assessment_file):
                self.risk_button.show()
            else:
                self.risk_button.hide()

            # Check for BOM files in children for project node
            if self.has_csv_in_children(node, self.check_for_bom_file):
                self.view_bom_button.setText("View Module BOM")
                self.view_bom_button.clicked.disconnect()
                self.view_bom_button.clicked.connect(self.view_module_bom)
                self.view_bom_button.show()
            else:
                # Update View BOM button for project node when no BOM files
                self.view_bom_button.setText("View Project Info")
                self.view_bom_button.clicked.disconnect()
                self.view_bom_button.clicked.connect(self.view_project_info)
                self.view_bom_button.show()

            # Check for CSV files in children for project node
            if self.has_csv_in_children(node, self.check_for_inventory_csv):
                self.inventory_button.show()
            else:
                self.inventory_button.hide()

            if self.has_csv_in_children(node, self.check_for_parts_csv):
                self.parts_button.show()
            else:
                self.parts_button.hide()

            if self.has_csv_in_children(node, self.check_for_materials_csv):
                self.materials_button.show()
            else:
                self.materials_button.hide()

            # Show download button if not downloaded (works for ALL nodes including root)
            if not node.is_downloaded:
                self.download_module_button.show()
            else:
                self.download_module_button.hide()

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
        new_text = self.assigned_edit.text().strip()
        if not new_text:
            new_text = "None"
            
        self.assigned_value.setText(new_text)
        if new_text == "None":
            self.assigned_value.setStyleSheet("color: #808080;")
        else:
            self.assigned_value.setStyleSheet("color: black;")
            
        self.assigned_edit.hide()
        self.assigned_value.show()
        
        # Update data structure with new assigned value
        if self.selected_node and isinstance(self.selected_node.data, dict):
            self.selected_node.data['assigned_to'] = new_text
            # Save to ModuleInfo.txt
            if self.save_module_data_to_file(self.selected_node.data):
                print(f"Saved assigned_to: {new_text} to ModuleInfo.txt")
            else:
                print("Failed to save assigned_to to ModuleInfo.txt")

    # Handle completion checkbox state change
    def completion_status_changed(self, state):
        if self.selected_node:
            self.selected_node.completed = bool(state)
            
            # Update completion status
            if bool(state):
                self.selected_node.completion_status = 'completed'
                self.selected_node.data['completion_status'] = 'completed'
            else:
                # When unchecked, determine if it should be in_progress or not_started
                if self.selected_node.has_completed_children():
                    self.selected_node.completion_status = 'in_progress'
                    self.selected_node.data['completion_status'] = 'in_progress'
                else:
                    self.selected_node.completion_status = 'not_started'
                    self.selected_node.data['completion_status'] = 'not_started'
            
            self.selected_node.data['completed'] = bool(state)
            
            # Save to ModuleInfo.txt
            if self.save_module_data_to_file(self.selected_node.data):
                print(f"Saved completed: {self.selected_node.completion_status} to ModuleInfo.txt")
            else:
                print("Failed to save completed status to ModuleInfo.txt")
            
            self.selected_node.update_node_color()
            # Update parent module node status
            parent_node = self.selected_node.parent_node
            while parent_node:
                parent_node.update_node_color()
                parent_node = parent_node.parent_node

    def view_module_bom(self):
        """View the Bill of Materials (BOM) for the selected module"""
        if not self.selected_node:
            QMessageBox.warning(self, "Error", "No module selected.")
            return
        
        # First check if current node has its own BOM
        current_node_bom = self.check_for_bom_file(self.selected_node.data)
        
        # Find all BOM files in current node and children
        bom_files = self.find_csv_in_children(self.selected_node, self.check_for_bom_file)
        
        if not bom_files:
            QMessageBox.information(self, "BOM File Not Found", 
                                "No BOM.csv file was found in this module or its sub-modules.")
            return
        
        # Check if current node has its own BOM
        if current_node_bom:
            # Current node has its own BOM
            if len(bom_files) == 1:
                # Only current node has BOM
                self.open_csv_in_viewer(bom_files[0]['path'])
            else:
                # Current node + children have BOMs - show choice dialog
                self.show_csv_aggregation_dialog(bom_files, "BOM")
        else:
            # Current node doesn't have its own BOM, but children do
            reply = QMessageBox.question(
                self, "BOM", 
                f"This module does not have its own BOM file.\n\n"
                f"However, {len(bom_files)} BOM file(s) were found in sub-modules.\n\n"
                f"Would you like to view the aggregated BOM from sub-modules?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                if len(bom_files) == 1:
                    # Only one child has BOM - open it directly
                    self.open_csv_in_viewer(bom_files[0]['path'])
                else:
                    # Multiple children have BOMs - create aggregated view directly
                    self.create_and_open_aggregated_csv(bom_files, "BOM")

    def open_csv_in_viewer(self, csv_path):
        """Open a CSV file in the CSV viewer"""
        try:
            # Import the CSV viewer class
            from CSVViewer_widget import CSVViewerWidget
            
            # Create the CSV viewer
            csv_viewer = CSVViewerWidget(self.parent, csv_path)
            
            # Add to parent's central widget if it exists
            if hasattr(self.parent, 'central_widget'):
                # First, check if the CSV viewer is already in the central widget
                for i in range(self.parent.central_widget.count()):
                    if isinstance(self.parent.central_widget.widget(i), CSVViewerWidget):
                        # Remove the existing CSV viewer
                        existing_viewer = self.parent.central_widget.widget(i)
                        self.parent.central_widget.removeWidget(existing_viewer)
                        existing_viewer.deleteLater()
                        
                # Add the new CSV viewer
                self.parent.central_widget.addWidget(csv_viewer)
                self.parent.central_widget.setCurrentWidget(csv_viewer)
            else:
                # If no central widget, just show it as a separate window
                csv_viewer.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open CSV viewer: {str(e)}")

    def check_for_bom_file(self, module_data):
        """Check if a module has a BOM.csv file in the lib folder"""
        if not module_data or not isinstance(module_data, dict):
            return None  # Changed from False to None
                
        repository_info = module_data.get('repository', {})
        if not repository_info or not repository_info.get('name'):
            return None  # Changed from False to None
                
        # Get the repository folder
        repo_dir = os.path.join("Downloaded Repositories", self.parent.repo_folder)
        module_dir = os.path.join(repo_dir, repository_info.get('name'))
        
        if not os.path.exists(module_dir):
            return None  # Changed from False to None
        
        # Check specifically for BOM.csv in the lib folder
        lib_folder = os.path.join(module_dir, "lib")
        
        # First check if lib folder exists
        if not os.path.exists(lib_folder) or not os.path.isdir(lib_folder):
            return None  # Changed from False to None
            
        # Then check for BOM.csv file
        bom_file = os.path.join(lib_folder, "BOM.csv")
        return bom_file if os.path.exists(bom_file) else None  # Return the path, not True/False


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
        """Open the module documentation in the web browser"""

        if not self.selected_node.is_downloaded:
            QMessageBox.warning(self, "Not Downloaded", 
                            "Please download this module first to view documentation.")
            return

        if not self.selected_node:
            QMessageBox.warning(self, "Error", "No module selected.")
            return
        
        # Check for documentation file
        doc_path = self.check_module_documentation(self.selected_node.data)
        
        if not doc_path:
            QMessageBox.information(self, "Documentation Not Found", 
                                "Documentation not found for this module.")
            return
        
        # Create file URL
        file_url = QUrl.fromLocalFile(os.path.abspath(doc_path))
        
        # Show the Git Building window and pass the file URL
        self.parent.show_git_building(
            self.selected_node.name,
            None,
            file_url.toString()
        )

    def check_module_documentation(self, module_data):
        """Check if a module has documentation file"""
        if not module_data or not isinstance(module_data, dict):
            return None
            
        repository_info = module_data.get('repository', {})
        if not repository_info or not repository_info.get('name'):
            return None
            
        # Get the repository folder
        repo_dir = os.path.join("Downloaded Repositories", self.parent.repo_folder)
        module_dir = os.path.join(repo_dir, repository_info.get('name'))
        
        if not os.path.exists(module_dir):
            return None
        
        # Check for documentation file
        doc_path = os.path.join(module_dir, "src", "doc", "_site", "missing.html")
        
        # Also check with src in different capitalizations
        alt_paths = [
            os.path.join(module_dir, "Src", "doc", "_site", "missing.html"),
            os.path.join(module_dir, "SRC", "doc", "_site", "missing.html"),
            # Check with Doc variations
            os.path.join(module_dir, "src", "Doc", "_site", "missing.html"),
            os.path.join(module_dir, "src", "DOC", "_site", "missing.html"),
            # Check with _site variations
            os.path.join(module_dir, "src", "doc", "_Site", "missing.html"),
            os.path.join(module_dir, "src", "doc", "_SITE", "missing.html"),
            # Check with missing.html variations
            os.path.join(module_dir, "src", "doc", "_site", "Missing.html"),
            os.path.join(module_dir, "src", "doc", "_site", "MISSING.html"),
            # Common alternative capitalization combinations
            os.path.join(module_dir, "Src", "Doc", "_Site", "Missing.html"),
            os.path.join(module_dir, "SRC", "DOC", "_SITE", "MISSING.html"),
        ]
        
        # Check main path first
        if os.path.exists(doc_path):
            return doc_path
        
        # Then check alternative paths
        for path in alt_paths:
            if os.path.exists(path):
                return path
                
        return None
                
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

    def find_module_info_file(self, module_dir):
        """Find the module info file with case-insensitive search and variation handling"""
        possible_filenames = [
            "ModuleInfo.txt",
            "moduleInfo.txt",
            "moduleinfo.txt",
            "MODULEINFO.txt",
            "ModuleInfor.txt",
            "moduleInfor.txt",
            "moduleinfor.txt",
            "Module_Info.txt",
            "module_info.txt"
        ]
        
        for filename in possible_filenames:
            file_path = os.path.join(module_dir, filename)
            if os.path.exists(file_path):
                return file_path
        
        # If no exact match is found, try a case-insensitive search
        if os.path.exists(module_dir):
            existing_files = os.listdir(module_dir)
            for existing_file in existing_files:
                lower_file = existing_file.lower()
                if "moduleinfo" in lower_file or "moduleinfor" in lower_file:
                    return os.path.join(module_dir, existing_file)
        
        return None  # No matching file found

    # Update node visibility (used when toggling)
    def update_node_visibility(self):
        for node in self.all_nodes:
            node.setVisible(True)
            for line in node.connected_lines:
                line.setVisible(True)


    def check_risk_assessment_file(self, module_data):
        """Check if a risk assessment CSV file exists for the module"""
        if not module_data or not isinstance(module_data, dict):
            return None
            
        repository_info = module_data.get('repository', {})
        if not repository_info or not repository_info.get('name'):
            return None
            
        # Get the repository folder
        repo_dir = os.path.join("Downloaded Repositories", self.parent.repo_folder)
        module_dir = os.path.join(repo_dir, repository_info.get('name'))
        
        if not os.path.exists(module_dir):
            return None
        
        # Check for risk assessment CSV file with different capitalizations
        possible_filenames = [
            "RiskAssessment.csv", 
            "riskassessment.csv", 
            "RISKASSESSMENT.csv", 
            "Risk_Assessment.csv", 
            "risk_assessment.csv",
            "risk-assessment.csv",
            "Risk-Assessment.csv"
        ]
        
        for filename in possible_filenames:
            file_path = os.path.join(module_dir, filename)
            if os.path.exists(file_path):
                return file_path
                
        return None

    def open_risk_assessment(self):
        """Open the risk assessment file for the selected module"""
        if not self.selected_node:
            QMessageBox.warning(self, "Error", "No module selected.")
            return
        
        # First check if current node has its own risk assessment
        current_node_risk = self.check_risk_assessment_file(self.selected_node.data)
        
        # Then find all risk assessment files in current node and children
        risk_files = self.find_csv_in_children(self.selected_node, self.check_risk_assessment_file)
        
        if not risk_files:
            QMessageBox.information(self, "Risk Assessment", 
                                "No risk assessment file found for this module or its sub-modules.")
            return
        
        # Check if current node has its own file
        if current_node_risk:
            # Current node has its own risk assessment
            if len(risk_files) == 1:
                # Only current node has risk assessment
                self.open_csv_in_viewer(risk_files[0]['path'])
            else:
                # Current node + children have risk assessments - show choice dialog
                self.show_csv_aggregation_dialog(risk_files, "Risk Assessment")
        else:
            # Current node doesn't have its own risk assessment, but children do
            # Show informational dialog first
            reply = QMessageBox.question(
                self, "Risk Assessment", 
                f"This module does not have its own risk assessment file.\n\n"
                f"However, {len(risk_files)} risk assessment file(s) were found in sub-modules.\n\n"
                f"Would you like to view the aggregated risk assessments from sub-modules?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                if len(risk_files) == 1:
                    # Only one child has risk assessment - open it directly
                    self.open_csv_in_viewer(risk_files[0]['path'])
                else:
                    # Multiple children have risk assessments - create aggregated view directly
                    self.create_and_open_aggregated_csv(risk_files, "Risk Assessment")


    def find_csv_in_children(self, node, csv_checker_method):
        """Recursively find CSV files in child nodes using the specified checker method"""
        csv_files = []
        
        # Check current node
        csv_path = csv_checker_method(node.data)
        if csv_path:
            csv_files.append({
                'node_name': node.name,
                'path': csv_path,
                'node': node
            })
        
        # Recursively check all child nodes
        for child_node in node.child_nodes:
            child_csvs = self.find_csv_in_children(child_node, csv_checker_method)
            csv_files.extend(child_csvs)
        
        return csv_files

    def has_csv_in_children(self, node, csv_checker_method):
        """Check if any child nodes have the specified CSV type"""
        csv_files = self.find_csv_in_children(node, csv_checker_method)
        return len(csv_files) > 0

    def show_csv_aggregation_dialog(self, csv_files, csv_type):
        """Show dialog to choose between single or aggregated CSV"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Load {csv_type}")
        dialog.setMinimumSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(f"Multiple {csv_type} files found. Choose an option:")
        instructions.setFont(QFont('Arial', 12))
        layout.addWidget(instructions)
        
        # Radio buttons for options
        self.csv_choice_group = QButtonGroup()
        
        # Option 1: Current node only
        current_radio = QRadioButton(f"View {csv_type} for current module only")
        current_radio.setChecked(True)
        self.csv_choice_group.addButton(current_radio, 0)
        layout.addWidget(current_radio)
        
        # Option 2: Aggregated
        aggregated_radio = QRadioButton(f"View aggregated {csv_type} from all sub-modules")
        self.csv_choice_group.addButton(aggregated_radio, 1)
        layout.addWidget(aggregated_radio)
        
        # List of files found
        files_label = QLabel(f"\n{csv_type} files found in:")
        files_label.setFont(QFont('Arial', 10, QFont.Bold))
        layout.addWidget(files_label)
        
        files_list = QTextEdit()
        files_list.setMaximumHeight(120)
        files_list.setReadOnly(True)
        
        file_text = ""
        for csv_file in csv_files:
            # Strip text in square brackets from node name
            display_name = re.sub(r'\[.*?\]', '', csv_file['node_name']).strip()
            file_text += f"• {display_name}\n"
        
        files_list.setPlainText(file_text)
        layout.addWidget(files_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        open_button = QPushButton("Open")
        open_button.setStyleSheet(self.get_button_style())
        open_button.clicked.connect(dialog.accept)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet(self.get_button_style())
        cancel_button.clicked.connect(dialog.reject)
        
        button_layout.addWidget(open_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            choice = self.csv_choice_group.checkedId()
            if choice == 0:
                # Open current node only
                current_node_csv = next((f for f in csv_files if f['node'] == self.selected_node), None)
                if current_node_csv:
                    self.open_csv_in_viewer(current_node_csv['path'])
            elif choice == 1:
                # Create aggregated CSV
                self.create_and_open_aggregated_csv(csv_files, csv_type)

    def create_and_open_aggregated_csv(self, csv_files, csv_type):
        """Create an aggregated CSV from multiple CSV files"""
        try:
            import pandas as pd
            
            all_dataframes = []
            
            for csv_file in csv_files:
                try:
                    # Read each CSV
                    df = pd.read_csv(csv_file['path'])
                    
                    # Add a column to identify source module
                    display_name = re.sub(r'\[.*?\]', '', csv_file['node_name']).strip()
                    df['Source_Module'] = display_name
                    
                    all_dataframes.append(df)
                    
                except Exception as e:
                    print(f"Error reading CSV from {csv_file['node_name']}: {str(e)}")
                    continue
            
            if not all_dataframes:
                QMessageBox.warning(self, "Error", "Could not read any CSV files for aggregation.")
                return
            
            # Combine all dataframes
            combined_df = pd.concat(all_dataframes, ignore_index=True, sort=False)
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=f'_aggregated_{csv_type.lower()}.csv', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            # Save combined data
            combined_df.to_csv(temp_path, index=False)
            
            # Open in CSV viewer
            self.open_csv_in_viewer(temp_path)
            
            # Store temp file path for cleanup later
            if not hasattr(self, 'temp_csv_files'):
                self.temp_csv_files = []
            self.temp_csv_files.append(temp_path)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create aggregated CSV: {str(e)}")

    def cleanup_temp_files(self):
        """Clean up temporary aggregated CSV files"""
        if hasattr(self, 'temp_csv_files'):
            for temp_file in self.temp_csv_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
            self.temp_csv_files = []

    def view_inventory_csv(self):
        """Open inventory CSV"""
        if not self.selected_node:
            return
        
        inventory_files = self.find_csv_in_children(self.selected_node, self.check_for_inventory_csv)
        
        if not inventory_files:
            return
        
        if len(inventory_files) == 1:
            self.open_csv_in_viewer(inventory_files[0]['path'])
        else:
            self.show_csv_aggregation_dialog(inventory_files, "Inventory")

    def view_parts_csv(self):
        """Open parts CSV"""
        if not self.selected_node:
            return
        
        parts_files = self.find_csv_in_children(self.selected_node, self.check_for_parts_csv)
        
        if not parts_files:
            return
        
        if len(parts_files) == 1:
            self.open_csv_in_viewer(parts_files[0]['path'])
        else:
            self.show_csv_aggregation_dialog(parts_files, "Parts")

    def check_for_specific_csv(self, module_data, csv_name, folder_path=""):
        """Check if a specific named CSV exists in a module"""
        if not module_data or not isinstance(module_data, dict):
            return None
            
        repository_info = module_data.get('repository', {})
        if not repository_info or not repository_info.get('name'):
            return None
            
        # Get the repository folder
        repo_dir = os.path.join("Downloaded Repositories", self.parent.repo_folder)
        module_dir = os.path.join(repo_dir, repository_info.get('name'))
        
        if not os.path.exists(module_dir):
            return None
        
        # Build the full path to the CSV
        if folder_path:
            csv_path = os.path.join(module_dir, folder_path, csv_name)
        else:
            csv_path = os.path.join(module_dir, csv_name)
        
        return csv_path if os.path.exists(csv_path) else None

    def check_for_inventory_csv(self, module_data):
        """Check for inventory.csv in various locations"""
        possible_files = [
            ("inventory.csv", ""),
            ("Inventory.csv", ""),
            ("INVENTORY.csv", ""),
            ("inventory.csv", "lib"),
            ("Inventory.csv", "lib"),
            ("inventory.csv", "data"),
            ("Inventory.csv", "data"),
        ]
        
        for csv_name, folder in possible_files:
            path = self.check_for_specific_csv(module_data, csv_name, folder)
            if path:
                return path
        return None

    def check_for_parts_csv(self, module_data):
        """Check for parts.csv in various locations"""
        possible_files = [
            ("parts.csv", ""),
            ("Parts.csv", ""),
            ("PARTS.csv", ""),
            ("parts.csv", "lib"),
            ("Parts.csv", "lib"),
            ("parts.csv", "data"),
            ("Parts.csv", "data"),
            ("partslist.csv", ""),
            ("PartsList.csv", ""),
            ("parts_list.csv", ""),
        ]
        
        for csv_name, folder in possible_files:
            path = self.check_for_specific_csv(module_data, csv_name, folder)
            if path:
                return path
        return None

    def check_for_materials_csv(self, module_data):
        """Check for materials.csv in various locations"""
        possible_files = [
            ("materials.csv", ""),
            ("Materials.csv", ""),
            ("MATERIALS.csv", ""),
            ("materials.csv", "lib"),
            ("Materials.csv", "lib"),
            ("materials.csv", "data"),
            ("Materials.csv", "data"),
        ]
        
        for csv_name, folder in possible_files:
            path = self.check_for_specific_csv(module_data, csv_name, folder)
            if path:
                return path
        return None

    def view_materials_csv(self):
        """Open materials CSV"""
        if not self.selected_node:
            return
        
        materials_files = self.find_csv_in_children(self.selected_node, self.check_for_materials_csv)
        
        if not materials_files:
            return
        
        if len(materials_files) == 1:
            self.open_csv_in_viewer(materials_files[0]['path'])
        else:
            self.show_csv_aggregation_dialog(materials_files, "Materials")

    def download_selected_module(self):
        """Download only the selected module"""
        if not self.selected_node:
            return
        
        reply = QMessageBox.question(
            self, "Download Module",
            f"Download full repository for '{self.selected_node.name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.download_single_module(self.selected_node)

    def download_module_with_children(self):
        """Download selected module and all its children"""
        if not self.selected_node:
            return
        
        # Count total modules
        def count_modules(node):
            count = 1
            for child in node.child_nodes:
                count += count_modules(child)
            return count
        
        total = count_modules(self.selected_node)
        
        reply = QMessageBox.question(
            self, "Download Modules",
            f"Download {total} module(s) (this module and all children)?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.download_node_tree(self.selected_node)

    def download_single_module(self, node):
        """Actually clone the repository for a single module"""
        repo_info = node.data.get('repository', {})
        if not repo_info or not repo_info.get('address'):
            return
        
        repo_url = repo_info['address']
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        repo_dir = os.path.join("Downloaded Repositories", self.parent.repo_folder)
        local_path = os.path.join(repo_dir, repo_name)
        
        # Create and start download worker
        self.download_worker = DownloadWorker(repo_url, local_path)
        self.download_worker.progress.connect(lambda msg: print(msg))
        self.download_worker.finished.connect(lambda success, msg: self.on_download_finished(node, repo_name, success, msg))
        
        # Disable button during download
        self.download_module_button.setEnabled(False)
        self.download_module_button.setText("Downloading...")
        
        self.download_worker.start()

    def on_download_finished(self, node, repo_name, success, message):
        """Handle download completion"""
        # Re-enable button
        self.download_module_button.setEnabled(True)
        self.download_module_button.setText("Download Module")
        
        if success:
            # Update node state
            node.is_downloaded = True
            node.download_indicator.setPlainText("✓")
            node.download_indicator.setDefaultTextColor(QColor("#32CD32"))
            
            # Hide download button
            self.download_module_button.hide()
            
            QMessageBox.information(self, "Success", f"Downloaded {repo_name}")
        else:
            QMessageBox.critical(self, "Error", f"Failed to download: {message}")

    def show_download_dialog(self):
        """Show dialog to choose download scope"""
        if not self.selected_node:
            return
        
        # Count children
        def count_modules(node):
            count = 1
            for child in node.child_nodes:
                count += count_modules(child)
            return count
        
        total_with_children = count_modules(self.selected_node)
        
        # If no children, just download directly without dialog
        if total_with_children == 1:
            self.download_single_module(self.selected_node)
            return
        
        # Otherwise show dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Download Module")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel(f"Download: {self.selected_node.name}")
        title.setFont(QFont('Arial', 14, QFont.Bold))
        layout.addWidget(title)
        
        # Spacing
        layout.addSpacing(10)
        
        # Radio buttons
        radio_group = QButtonGroup(dialog)
        
        # Option 1: Module + children (default)
        with_children_radio = QRadioButton(
            f"Download this module and its required children ({total_with_children} modules)"
        )
        with_children_radio.setChecked(True)  # Default option
        radio_group.addButton(with_children_radio, 1)
        layout.addWidget(with_children_radio)
        
        layout.addSpacing(10)
        
        # Option 2: This module only
        single_radio = QRadioButton("Download only this module (1 module)")
        radio_group.addButton(single_radio, 0)
        layout.addWidget(single_radio)
        
        layout.addSpacing(20)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        download_button = QPushButton("Download")
        download_button.setStyleSheet(self.get_button_style())
        download_button.clicked.connect(dialog.accept)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet(self.get_button_style())
        cancel_button.clicked.connect(dialog.reject)
        
        button_layout.addWidget(download_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            choice = radio_group.checkedId()
            if choice == 1:
                # Download with children
                self.download_node_tree(self.selected_node)
            else:
                # Download single module
                self.download_single_module(self.selected_node)

    def download_node_tree(self, node):
        """Recursively download node and all children"""
        # Create list of all nodes to download
        nodes_to_download = []
        
        def collect_nodes(n):
            nodes_to_download.append(n)
            for child in n.child_nodes:
                collect_nodes(child)
        
        collect_nodes(node)
        
        # Start downloading
        self.download_queue = nodes_to_download
        self.current_download_index = 0
        self.download_next_in_queue()

    def download_next_in_queue(self):
        """Download the next module in the queue"""
        if self.current_download_index >= len(self.download_queue):
            # All downloads complete
            QMessageBox.information(self, "Complete", "All modules downloaded successfully!")
            return
        
        current_node = self.download_queue[self.current_download_index]
        
        # Skip if already downloaded
        if current_node.is_downloaded:
            self.current_download_index += 1
            self.download_next_in_queue()
            return
        
        repo_info = current_node.data.get('repository', {})
        if not repo_info or not repo_info.get('address'):
            self.current_download_index += 1
            self.download_next_in_queue()
            return
        
        repo_url = repo_info['address']
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        repo_dir = os.path.join("Downloaded Repositories", self.parent.repo_folder)
        local_path = os.path.join(repo_dir, repo_name)
        
        # Create and start download worker
        self.download_worker = DownloadWorker(repo_url, local_path)
        self.download_worker.progress.connect(lambda msg: print(msg))
        self.download_worker.finished.connect(
            lambda success, msg: self.on_queue_download_finished(current_node, repo_name, success, msg)
        )
        
        # Update button to show progress
        self.download_module_button.setEnabled(False)
        self.download_module_button.setText(f"Downloading {self.current_download_index + 1}/{len(self.download_queue)}...")
        
        self.download_worker.start()

    def on_queue_download_finished(self, node, repo_name, success, message):
        """Handle completion of a queued download"""
        if success:
            # Update node state
            node.is_downloaded = True
            node.download_indicator.setPlainText("✓")
            node.download_indicator.setDefaultTextColor(QColor("#32CD32"))
            print(f"Downloaded {repo_name}")
        else:
            print(f"Failed to download {repo_name}: {message}")
        
        # Move to next download
        self.current_download_index += 1
        self.download_next_in_queue()



class DownloadWorker(QThread):
    """Background thread for downloading repositories"""
    progress = pyqtSignal(str)  # Emits status messages
    finished = pyqtSignal(bool, str)  # Emits (success, message)
    
    def __init__(self, repo_url, local_path):
        super().__init__()
        self.repo_url = repo_url
        self.local_path = local_path
    
    def run(self):
        try:
            import pygit2
            self.progress.emit(f"Cloning repository...")
            pygit2.clone_repository(self.repo_url, self.local_path)
            self.finished.emit(True, "Download complete")
        except Exception as e:
            self.finished.emit(False, str(e))