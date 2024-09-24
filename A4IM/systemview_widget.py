from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QTextEdit, QPushButton, QLabel, QLineEdit, QCheckBox,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem,
    QGraphicsLineItem, QGraphicsItem, QGraphicsPixmapItem
)
from PyQt5.QtCore import Qt, QPointF, QRectF, QLineF
from PyQt5.QtGui import QFont, QColor, QPen, QBrush, QPainter, QPixmap
import math
import os

# NodeItem class for systems and modules
class NodeItem(QGraphicsRectItem):
    def __init__(self, name, data, system_view, node_type='module'):
        # Adjust size based on node type
        if node_type == 'project':
            width = 220
            height = 100
        elif node_type == 'system':
            width = 180
            height = 80
        else:
            width = 150
            height = 60

        super().__init__(-width/2, -height/2, width, height)  # Initialize rectangle centered
        self.name = name
        self.data = data
        self.system_view = system_view
        self.node_type = node_type  # 'project', 'system', or 'module'
        self.completed = False  # Completion status
        self.parent_node = None  # Parent node
        self.child_nodes = []  # List of child nodes
        self.connected_lines = []  # List to store lines connected to this node

        # Set colors based on node type
        if node_type == 'project':
            self.setBrush(QBrush(QColor("#2E4A62")))  # Darker blue color for project node
        elif node_type == 'system':
            self.setBrush(QBrush(QColor("#465775")))  # Blue color for systems
        else:
            self.setBrush(QBrush(QColor("#A9A9A9")))  # Grey color for modules

        self.setPen(QPen(Qt.NoPen))  # No border around node
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsFocusable)
        self.setAcceptHoverEvents(False)

        # Create text label for the node
        text = QGraphicsTextItem(self)
        text.setDefaultTextColor(Qt.white)
        # Adjust font based on node type
        if node_type == 'project':
            font = QFont('Arial', 14)  # Larger font size for project node
        elif node_type == 'system':
            font = QFont('Arial', 12)  # Increased font size for system nodes
        else:
            font = QFont('Arial', 10)
        font.setBold(True)  # Bold text
        text.setFont(font)
        text.setPlainText(name)
        text.setTextWidth(width - 10)

        # Center the text within the node
        text_rect = text.boundingRect()
        text_x = -text_rect.width() / 2
        text_y = -text_rect.height() / 2
        text.setPos(text_x, text_y)

        # Create status indicator at top right corner (not for project node)
        if node_type != 'project':
            indicator_size = 20
            indicator_x = width / 2 - indicator_size - 2
            indicator_y = -height / 2 + 2
            self.status_indicator = QGraphicsRectItem(0, 0, indicator_size, indicator_size, self)
            self.status_indicator.setBrush(QBrush(QColor("#D9534F")))
            self.status_indicator.setPen(QPen(Qt.black))
            self.status_indicator.setPos(indicator_x, indicator_y)

        # # Add logo to project node
        # if node_type == 'project':
        #     logo_path = os.path.join('docs','images','A4IMLogo_pink.png')  
        #     if os.path.exists(logo_path):
        #         pixmap = QPixmap(logo_path)
        #         scaled_pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        #         logo_item = QGraphicsPixmapItem(scaled_pixmap, self)
        #         logo_item.setPos(-scaled_pixmap.width()/2, -height/2 + 10)  # Position at the top center
        #     else:
        #         print("Logo image not found at:", logo_path)

    # Handle mouse press event
    def mousePressEvent(self, event):
        self.scene().clearSelection()
        self.setSelected(True)
        self.system_view.node_clicked(self)
        # Removed super().mousePressEvent(event) to prevent issues

    # Update the status indicator color
    def update_status_indicator(self):
        if self.node_type == 'module':
            if self.completed:
                self.status_indicator.setBrush(QBrush(QColor("#32CD32")))  # Lime green
            else:
                self.status_indicator.setBrush(QBrush(QColor("#D9534F")))  # Red
        elif self.node_type == 'system':
            if self.all_modules_completed():
                self.status_indicator.setBrush(QBrush(QColor("#32CD32")))  # Lime green
            elif self.has_completed_modules():
                self.status_indicator.setBrush(QBrush(QColor("#F0AD4E")))  # Yellow
            else:
                self.status_indicator.setBrush(QBrush(QColor("#D9534F")))  # Red

    # Update node color based on completion status
    def update_node_color(self):
        if self.node_type != 'project':
            self.update_status_indicator()

    # Check if any child modules are completed
    def has_completed_modules(self):
        for child in self.child_nodes:
            if child.node_type == 'module' and child.completed:
                return True
            elif child.node_type == 'system' and child.has_completed_modules():
                return True
        return False

    # Check if all child modules are completed
    def all_modules_completed(self):
        for child in self.child_nodes:
            if child.node_type == 'module' and not child.completed:
                return False
            elif child.node_type == 'system' and not child.all_modules_completed():
                return False
        return True

# Custom GraphicsView class with zoom functionality
class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.zoom_factor = 1.15
        self.min_scale = 0.1
        self.max_scale = 10.0
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        #for mouse location zoom
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
        self.systems_data = {}  # Store systems data
        self.setup_ui()

    # Set up the user interface
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

        # Label for systems graph
        systems_label = QLabel("Systems Graph")
        systems_label.setFont(QFont('Arial', 16, QFont.Bold))
        systems_label.setStyleSheet("color: #465775;")
        graphics_layout.addWidget(systems_label)

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
        reset_view_button.setStyleSheet("""
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
        """)
        reset_view_button.clicked.connect(self.recenter_view)
        reset_view_button.setToolTip("Reset the view to the default position and zoom level")
        reset_view_button.setFixedSize(100, 30)
        button_layout.addWidget(reset_view_button)

        # Toggle All button
        self.toggle_button = QPushButton("Toggle All")
        self.toggle_button.setStyleSheet("""
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
        """)
        self.toggle_button.clicked.connect(self.toggle_modules)
        self.toggle_button.setToolTip("Toggle visibility of modules")
        self.toggle_button.setFixedSize(100, 30)
        button_layout.addWidget(self.toggle_button)

        graphics_layout.addLayout(button_layout)

        left_layout.addWidget(graphics_container)

        # Right layout for system details and buttons
        right_layout = QVBoxLayout()

        # Label for system details
        details_label = QLabel("System Details")
        details_label.setFont(QFont('Arial', 16, QFont.Bold))
        details_label.setStyleSheet("color: #465775;")
        right_layout.addWidget(details_label)

        # User/Team Assigned section
        assigned_layout = QHBoxLayout()
        assigned_label = QLabel("User/Team Assigned:")
        assigned_label.setStyleSheet("color: #465775; font-weight: bold;")
        self.assigned_value = QLabel("None")
        self.assigned_value.setStyleSheet("color: #808080;")
        self.assigned_value.mousePressEvent = self.start_editing
        self.assigned_edit = QLineEdit()
        self.assigned_edit.setStyleSheet("color: black;")
        self.assigned_edit.hide()
        self.assigned_edit.editingFinished.connect(self.finish_editing)
        assigned_layout.addWidget(assigned_label)
        assigned_layout.addWidget(self.assigned_value)
        assigned_layout.addWidget(self.assigned_edit)
        assigned_layout.addStretch()
        right_layout.addLayout(assigned_layout)

        # Checkbox for module completion
        self.completion_checkbox = QCheckBox("Mark as Completed")
        self.completion_checkbox.stateChanged.connect(self.completion_status_changed)
        self.completion_checkbox.hide()
        right_layout.addWidget(self.completion_checkbox)

        # Text edit for system details
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

        # Construct button (initially hidden)
        self.construct_button = self.create_button("Construct")
        self.construct_button.clicked.connect(self.construct_system)
        self.construct_button.hide()  # Initially hidden
        right_layout.addWidget(self.construct_button)

        # View System BOM / View Module BOM button
        self.view_bom_button = self.create_button("View System BOM")
        self.view_bom_button.clicked.connect(self.view_system_bom)
        right_layout.addWidget(self.view_bom_button)

        # Back button
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

    # Populate systems and modules in graphics scene
    def populate_systems(self, systems):
        self.systems_data = systems  # Store systems data for later use
        # Instead of clearing the scene, we'll manage node visibility
        if not hasattr(self, 'nodes_initialized'):
            self.graphics_scene.clear()
            self.node_items.clear()
            self.system_nodes = {}
            self.system_items = []
            self.all_nodes = []  # Keep track of all nodes
            self.initialize_nodes()
            self.nodes_initialized = True
        else:
            self.update_node_visibility()

       # Adjust scene rectangle with extra space
        items_rect = self.graphics_scene.itemsBoundingRect()
        extra_left = 200   # Adjust as needed
        extra_right = 500  # Adjust as needed
        extra_top = 200   # Adjust as needed
        extra_bottom = 200  # Adjust as needed
        items_rect.setLeft(items_rect.left() - extra_left)
        items_rect.setRight(items_rect.right() + extra_right)
        items_rect.setTop(items_rect.top() - extra_top)
        items_rect.setBottom(items_rect.bottom() + extra_bottom)
        self.graphics_scene.setSceneRect(items_rect)

    # Initialize all nodes without clearing them later
    def initialize_nodes(self):
        x = 0  # Starting x position for systems
        y = 0  # Starting y position

        self.system_positions = []  # To store system positions and heights

        # First pass: Calculate total height for each system
        for system_name, system_data in self.systems_data.items():
            modules = system_data.get('modules', {}) if isinstance(system_data, dict) else {}
            num_modules = len(modules)
            node_height = 80  # Height of a system node
            module_node_height = 60  # Height of a module node
            module_spacing = 100  # Spacing between modules
            system_spacing = 50  # Spacing between systems

            total_module_height = num_modules * (module_node_height + module_spacing) - module_spacing if num_modules > 0 else 0
            total_height = max(total_module_height, node_height)
            self.system_positions.append({
                'name': system_name,
                'data': system_data,
                'y': y,
                'total_height': total_height,
                'num_modules': num_modules,
                'modules': modules
            })
            y += total_height + system_spacing

        # Create the Project Node
        project_node_height = y
        project_position = QPointF(self.project_node_x, project_node_height / 2)
        self.project_node = self.add_node("A4IM Scanner", None, project_position, None, node_type='project')
        self.all_nodes.append(self.project_node)

        # Second pass: Position the systems and their modules
        for system_info in self.system_positions:
            system_name = system_info['name']
            system_data = system_info['data']
            system_y = system_info['y'] + system_info['total_height'] / 2
            position = QPointF(0, system_y)
            system_item = self.add_node(system_name, system_data, position, self.project_node, node_type='system')
            self.system_nodes[system_name] = system_item
            self.system_items.append(system_item)
            self.all_nodes.append(system_item)

            # Add modules
            modules = system_info['modules']
            num_modules = system_info['num_modules']
            if num_modules > 0:
                node_height = 60  # Height of a module node
                child_spacing = 100
                total_module_height = num_modules * (node_height + child_spacing) - module_spacing
                start_y = system_item.pos().y() - total_module_height / 2 + node_height / 2
                child_x = system_item.pos().x() + 200

                index = 0
                for module_name, module_data in modules.items():
                    child_y = start_y + index * (node_height + child_spacing)
                    child_position = QPointF(child_x, child_y)
                    module_item = self.add_node(module_name, module_data, child_position, system_item, node_type='module')
                    self.all_nodes.append(module_item)
                    index += 1


    # Update node visibility without clearing the scene
    def update_node_visibility(self):
        y = 0  # Starting y position
        for system_info, system_item in zip(self.system_positions, self.system_items):
            modules = system_info['modules']
            num_modules = len(modules)
            node_height = 80  # Height of a system node
            module_node_height = 60  # Height of a module node
            module_spacing = 100  # Spacing between modules
            system_spacing = 50  # Spacing between systems

            # Determine if modules should be shown
            show_modules = not self.toggle_mode or (self.selected_node and self.selected_node.name == system_info['name'])

            if show_modules:
                total_module_height = num_modules * (module_node_height + module_spacing) - module_spacing if num_modules > 0 else 0
            else:
                total_module_height = 0
                num_modules = 0

            total_height = max(total_module_height, node_height)
            system_info['y'] = y
            system_info['total_height'] = total_height

            # Update system node position
            system_y = system_info['y'] + system_info['total_height'] / 2
            system_item.setPos(QPointF(0, system_y))

            y += total_height + system_spacing  # Move y down after positioning the system node

            # Update module nodes
            index = 0
            for module_item in system_item.child_nodes:
                if show_modules:
                    node_height = 60
                    child_spacing = 100
                    total_module_height = num_modules * (node_height + child_spacing) - module_spacing
                    start_y = system_item.pos().y() - total_module_height / 2 + node_height / 2
                    child_x = system_item.pos().x() + 200
                    child_y = start_y + index * (node_height + child_spacing)
                    module_item.setPos(QPointF(child_x, child_y))
                    module_item.setVisible(True)
                    # Show lines connected to the module
                    for line in module_item.connected_lines:
                        line.setVisible(True)
                        # Update line positions
                        line.setLine(QLineF(system_item.pos(), module_item.pos()))
                    index += 1
                else:
                    module_item.setVisible(False)
                    # Hide lines connected to the module
                    for line in module_item.connected_lines:
                        line.setVisible(False)

        # Update project node position
        total_project_height = y
        project_node_x = self.project_node_x  # Use the same x-coordinate as in initialize_nodes()
        self.project_node.setPos(QPointF(project_node_x, total_project_height / 2))

        # Update lines connecting project node to systems
        for system_item in self.system_items:
            for line in system_item.connected_lines:
                if line in self.project_node.connected_lines:
                    line.setLine(QLineF(self.project_node.pos(), system_item.pos()))

        

        # Update lines connecting project node to systems
        for system_item in self.system_items:
            for line in system_item.connected_lines:
                if line in self.project_node.connected_lines:
                    line.setLine(QLineF(self.project_node.pos(), system_item.pos()))

        # Adjust scene rectangle with extra space
        items_rect = self.graphics_scene.itemsBoundingRect()
        extra_left = 200   # Adjust as needed
        extra_right = 500  # Adjust as needed
        extra_top = 200   # Adjust as needed
        extra_bottom = 200  # Adjust as needed
        items_rect.setLeft(items_rect.left() - extra_left)
        items_rect.setRight(items_rect.right() + extra_right)
        items_rect.setTop(items_rect.top() - extra_top)
        items_rect.setBottom(items_rect.bottom() + extra_bottom)
        self.graphics_scene.setSceneRect(items_rect)

    # Add a node (project, system, or module)
    def add_node(self, name, data, position, parent_node, node_type='module'):
        node = NodeItem(name, data, self, node_type=node_type)
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

    # Called when a node is clicked
    def node_clicked(self, node):
        self.selected_node = node
        name = node.name
        data = node.data
        if isinstance(data, dict):
            description = data.get('description', 'No details available.')
            assigned = data.get('assigned_to', 'None')
        else:
            description = str(data) if data else 'No details available.'
            assigned = 'None'

        self.system_details.setText(f"{name}\n\n{description}")
        self.assigned_value.setText(assigned)
        if assigned == 'None':
            self.assigned_value.setStyleSheet("color: #808080;")
        else:
            self.assigned_value.setStyleSheet("color: black;")

        # Show completion checkbox if it's a module
        if node.node_type == 'module':
            self.completion_checkbox.show()
            self.completion_checkbox.blockSignals(True)
            self.completion_checkbox.setChecked(node.completed)
            self.completion_checkbox.blockSignals(False)

            # Show the Construct button
            self.construct_button.show()

            # Change View BOM button text to "View Module BOM"
            self.view_bom_button.setText("View Module BOM")
            self.view_bom_button.clicked.disconnect()
            self.view_bom_button.clicked.connect(self.view_module_bom)

        else:
            self.completion_checkbox.hide()

            # Hide the Construct button
            self.construct_button.hide()

            # Change View BOM button text to "View System BOM" or hide if project node
            if node.node_type == 'system':
                self.view_bom_button.setText("View System BOM")
                self.view_bom_button.clicked.disconnect()
                self.view_bom_button.clicked.connect(self.view_system_bom)
            else:
                self.view_bom_button.setText("View Project Info")
                self.view_bom_button.clicked.disconnect()
                self.view_bom_button.clicked.connect(self.view_project_info)

        # If in toggle mode and a system node is clicked, update the display
        if self.toggle_mode and node.node_type == 'system':
            self.update_toggle_view()

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
            # Update parent system node status
            parent_node = self.selected_node.parent_node
            while parent_node:
                parent_node.update_node_color()
                parent_node = parent_node.parent_node

    # View system BOM
    def view_system_bom(self):
        if self.selected_node:
            name = self.selected_node.name
            if self.selected_node.node_type == 'system':
                # Open the system BOM URL
                url = "https://matthewbeddows.github.io/A4IM-ProjectArchitect/GitBuilding/index_BOM.html"
                self.parent.show_git_building(system=name, module=None, url=url)
            else:
                print("Please select a system to view its BOM.")
        else:
            print("No system selected")

    # View module BOM
    def view_module_bom(self):
        if self.selected_node:
            name = self.selected_node.name
            if self.selected_node.node_type == 'module':
                # Open the module BOM URL
                url = "https://matthewbeddows.github.io/A4IM-ProjectArchitect/GitBuilding/index_BOM.html"
                self.parent.show_git_building(system=None, module=name, url=url)
            else:
                print("Please select a module to view its BOM.")
        else:
            print("No module selected")

    # View project info
    def view_project_info(self):
        if self.selected_node:
            name = self.selected_node.name
            if self.selected_node.node_type == 'project':
                # Open the project info URL or display project information
                # For now, we'll just print a message
                print(f"Viewing project info for: {name}")
                # Implement logic to view project info if needed
            else:
                print("Please select the project node to view its info.")
        else:
            print("No project selected")

    # Construct system or module
    def construct_system(self):
        if self.selected_node:
            name = self.selected_node.name
            if self.selected_node.node_type == 'module':
                # Open the construct URL for the module
                url = "https://matthewbeddows.github.io/A4IM-ProjectArchitect/GitBuilding/testpage1.html"
                self.parent.show_git_building(system=None, module=name, url=url)
            else:
                print("Please select a module to construct.")
        else:
            print("Please select a node")

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
    def update_toggle_view(self):
        self.update_node_visibility()
