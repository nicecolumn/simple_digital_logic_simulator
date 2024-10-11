import pygame
import sys
import math
import copy
import json
import os
from collections import defaultdict, deque
from utils import draw_round_line
from components import Wire, Grid, Transistor, Clock, Node
from constants import *
from game import *

SAVE_DIR = "saves"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

FONT = pygame.font.SysFont(None, 24)
BIG_FONT = pygame.font.SysFont(None, 36)

class Circuit:
    def __init__(self):
        self.grid = Grid()
        self.mode = MODE_NONE
        self.nodes = []       # List of Node instances
        self.wires = []       # List of Wire instances
        self.transistors = []  # List of Transistor instances
        self.clocks = []      # List of Clock instances
        self.is_drawing_wire = False
        self.wire_start_point = None

        # Selection attributes
        self.is_selecting = False
        self.selection_start = None
        self.selection_end = None
        self.selection_rect_world = None
        self.selected_nodes = []
        self.selected_wires = []
        self.selected_transistors = []
        self.selected_clocks = []
        self.is_moving_selection = False
        self.selection_offset = None
        self.drawing_disabled = False  # Disable drawing when selection exists
        self.previous_mode = MODE_NONE

        # Clipboard for copy/paste
        self.copied_nodes = []
        self.copied_wires = []
        self.copied_transistors = []
        self.copied_clocks = []

        # Moving individual objects
        self.is_moving_object = False
        self.moving_object = None
        self.move_offset = None

        # Circuit Logic
        self.on_points = []
        self.off_points = []

        # Save/Load Dialog Attributes
        self.save_dialog_active = False
        self.load_dialog_active = False
        self.save_filename = ""
        self.save_input_active = True  # To handle text input
        self.load_selected = None
        self.load_files = self.get_saved_files()
        self.load_scroll_offset = 0  # For scrolling through load files
        self.load_selection_index = 0

        # Variables to track dragging of wire endpoints
        self.dragging_wire_endpoint = None  # Tuple: (Wire instance, 'start' or 'end')

    def get_saved_files(self):
        files = [f for f in os.listdir(SAVE_DIR) if f.endswith('.txt')]
        return files

    def handle_event(self, event):
        # Window resize
        if event.type == pygame.VIDEORESIZE:
            global WIDTH, HEIGHT, screen
            WIDTH, HEIGHT = event.w, event.h
            screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

        # Zooming
        elif event.type == pygame.MOUSEWHEEL:
            if not (self.save_dialog_active or self.load_dialog_active):
                self.grid.handle_zoom(event)

        # Mouse button down
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 2:  # Middle mouse button for panning
                if not (self.save_dialog_active or self.load_dialog_active):
                    self.grid.start_panning()
            elif event.button == 1:  # Left mouse button
                shift_pressed = pygame.key.get_mods() & pygame.KMOD_SHIFT
                ctrl_pressed = pygame.key.get_mods() & pygame.KMOD_CTRL

                if shift_pressed:
                    # Check if the click is on a wire endpoint
                    wire, endpoint = self.get_wire_endpoint_at_pos(event.pos)
                    if wire and endpoint:
                        self.dragging_wire_endpoint = (wire, endpoint)
                        return  # Early return to prevent other actions

                if self.save_dialog_active:
                    # Check if Save button is clicked
                    if self.is_click_on_save_button(event.pos):
                        if self.save_filename.strip() != "":
                            self.save_circuit(self.save_filename.strip())
                            self.save_dialog_active = False
                            self.save_filename = ""
                    # Check if clicking on the input box (optional for future enhancements)
                elif self.load_dialog_active:
                    # Check if a file is clicked
                    clicked_index = self.get_clicked_load_file(event.pos)
                    if clicked_index is not None:
                        self.load_selection_index = clicked_index
                    # Check if Load button is clicked
                    elif self.is_click_on_load_button(event.pos):
                        if self.load_files:
                            selected_file = self.load_files[self.load_selection_index]
                            self.load_circuit(selected_file)
                            self.load_dialog_active = False
                    # Optional: Handle scrolling or other interactions
                elif self.selection_rect_world:
                    # Check if clicking inside the selection box to move it
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    if self.is_point_in_selection(mouse_x, mouse_y):
                        self.is_moving_selection = True
                        self.selection_offset = pygame.mouse.get_pos()
                    else:
                        # Clicked outside the selection box, clear selection
                        self.clear_selection()
                else:
                    if ctrl_pressed:
                        # Start selection box
                        world_x, world_y = self.grid.screen_to_world(*pygame.mouse.get_pos())
                        self.selection_start = (world_x, world_y)
                        self.selection_end = (world_x, world_y)
                        self.is_selecting = True
                        self.selected_nodes = []
                        self.selected_wires = []
                        self.selected_transistors = []
                        self.selected_clocks = []
                        self.drawing_disabled = True
                    elif shift_pressed:
                        # Start moving individual object
                        obj = self.get_hovered_object()
                        if obj:
                            self.is_moving_object = True
                            self.moving_object = obj
                            self.move_offset = pygame.mouse.get_pos()
                    else:
                        if not self.drawing_disabled:
                            # Existing code for handling nodes, wires, etc.
                            world_x, world_y = self.grid.screen_to_world(*pygame.mouse.get_pos())
                            grid_x = round(world_x / GRID_SPACING) * GRID_SPACING
                            grid_y = round(world_y / GRID_SPACING) * GRID_SPACING
                            position = (grid_x, grid_y)

                            node = self.node_at_position(position)
                            transistor = self.transistor_at_position(position)
                            clock_obj = self.clock_at_position(position)

                            # Toggle input node regardless of mode
                            toggling_node = False
                            if node and node.node_type == 'input':
                                node.toggle()
                                toggling_node = True
                            
                            else:
                                if self.mode == MODE_WIRE:
                                    # Start drawing wire if not clicking on a node or transistor
                                    if not toggling_node:
                                        self.is_drawing_wire = True
                                        self.wire_start_point = position
                                elif self.mode == MODE_INPUT:
                                    # Place input node if position is empty
                                    if not toggling_node:
                                        self.nodes.append(Node(position, 'input'))
                                elif self.mode == MODE_OUTPUT:
                                    # Place output node if position is empty
                                    if not toggling_node:
                                        self.nodes.append(Node(position, 'output'))
                                elif self.mode == MODE_TRANSISTOR:
                                    # Place N-type transistor
                                    if not toggling_node:
                                        self.transistors.append(Transistor(position, transistor_type='n-type'))
                                elif self.mode == MODE_P_TRANSISTOR:
                                    # Place P-type transistor
                                    if not toggling_node:
                                        self.transistors.append(Transistor(position, transistor_type='p-type'))
                                elif self.mode == MODE_CLOCK:
                                    # Place Clock if position is empty
                                    if not toggling_node:
                                        self.clocks.append(Clock(position))

        # Mouse button up
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:  # Middle mouse button
                if not (self.save_dialog_active or self.load_dialog_active):
                    self.grid.stop_panning()
            elif event.button == 1:  # Left mouse button
                if self.dragging_wire_endpoint:
                    # Snap the dragged endpoint to the nearest grid point
                    mouse_pos = pygame.mouse.get_pos()
                    world_x, world_y = self.grid.screen_to_world(*mouse_pos)
                    grid_x = round(world_x / GRID_SPACING) * GRID_SPACING
                    grid_y = round(world_y / GRID_SPACING) * GRID_SPACING
                    wire, endpoint = self.dragging_wire_endpoint
                    if endpoint == 'start':
                        wire.start_point = (grid_x, grid_y)
                    elif endpoint == 'end':
                        wire.end_point = (grid_x, grid_y)
                    self.dragging_wire_endpoint = None
                    return  # Early return to prevent other actions

                if self.save_dialog_active:
                    pass  # Handled in MOUSEBUTTONDOWN
                elif self.load_dialog_active:
                    pass  # Handled in MOUSEBUTTONDOWN
                elif self.is_selecting:
                    # Finish selection
                    self.is_selecting = False
                    # Create selection rectangle in world coordinates
                    x1, y1 = self.selection_start
                    x2, y2 = self.selection_end
                    left = min(x1, x2)
                    top = min(y1, y2)
                    width = abs(x2 - x1)
                    height = abs(y2 - y1)
                    self.selection_rect_world = pygame.Rect(left, top, width, height)
                    # Find objects within the selection rectangle
                    self.selected_nodes = self.get_nodes_in_rect(self.selection_rect_world)
                    self.selected_wires = self.get_wires_in_rect(self.selection_rect_world)
                    self.selected_transistors = self.get_transistors_in_rect(self.selection_rect_world)
                    self.selected_clocks = self.get_clocks_in_rect(self.selection_rect_world)
                    # If no objects are selected, the selection box remains until a new selection is made
                    if not (self.selected_nodes or self.selected_wires or self.selected_transistors or self.selected_clocks):
                        self.clear_selection()
                elif self.is_moving_selection:
                    # Finish moving selection
                    self.is_moving_selection = False
                    # Snap positions to grid
                    for node in self.selected_nodes:
                        grid_x = round(node.position[0] / GRID_SPACING) * GRID_SPACING
                        grid_y = round(node.position[1] / GRID_SPACING) * GRID_SPACING
                        node.position = (grid_x, grid_y)
                    for transistor in self.selected_transistors:
                        grid_x = round(transistor.position[0] / GRID_SPACING) * GRID_SPACING
                        grid_y = round(transistor.position[1] / GRID_SPACING) * GRID_SPACING
                        transistor.position = (grid_x, grid_y)
                    for wire in self.selected_wires:
                        start_x = round(wire.start_point[0] / GRID_SPACING) * GRID_SPACING
                        start_y = round(wire.start_point[1] / GRID_SPACING) * GRID_SPACING
                        end_x = round(wire.end_point[0] / GRID_SPACING) * GRID_SPACING
                        end_y = round(wire.end_point[1] / GRID_SPACING) * GRID_SPACING
                        wire.start_point = (start_x, start_y)
                        wire.end_point = (end_x, end_y)
                    for clock in self.selected_clocks:
                        grid_x = round(clock.position[0] / GRID_SPACING) * GRID_SPACING
                        grid_y = round(clock.position[1] / GRID_SPACING) * GRID_SPACING
                        clock.position = (grid_x, grid_y)
                
                elif self.is_moving_object:
                    self.is_moving_object = False
                    obj = self.moving_object
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    world_x, world_y = self.grid.screen_to_world(mouse_x, mouse_y)
                    grid_x = round(world_x / GRID_SPACING) * GRID_SPACING
                    grid_y = round(world_y / GRID_SPACING) * GRID_SPACING
                    if isinstance(obj, Node):
                        obj.position = (grid_x, grid_y)
                    elif isinstance(obj, Transistor):
                        obj.position = (grid_x, grid_y)
                    elif isinstance(obj, Clock):
                        obj.position = (grid_x, grid_y)
                
                elif self.is_drawing_wire:
                    world_x, world_y = self.grid.screen_to_world(*pygame.mouse.get_pos())
                    grid_x = round(world_x / GRID_SPACING) * GRID_SPACING
                    grid_y = round(world_y / GRID_SPACING) * GRID_SPACING
                    end_point = (grid_x, grid_y)

                    # Create wire
                    if not (end_point == self.wire_start_point):
                        self.wires.append(Wire(self.wire_start_point, end_point))
                    
                    self.is_drawing_wire = False

        # Mouse motion
        elif event.type == pygame.MOUSEMOTION:
            if self.grid.is_panning:
                if not (self.save_dialog_active or self.load_dialog_active):
                    self.grid.pan()
            elif self.is_selecting:
                # Update selection box
                world_x, world_y = self.grid.screen_to_world(*pygame.mouse.get_pos())
                self.selection_end = (world_x, world_y)
            elif self.is_moving_selection:
                # Move selected objects
                mouse_x, mouse_y = pygame.mouse.get_pos()
                prev_mouse_x, prev_mouse_y = self.selection_offset
                dx_screen = mouse_x - prev_mouse_x
                dy_screen = mouse_y - prev_mouse_y
                self.selection_offset = pygame.mouse.get_pos()

                # Convert delta to world coordinates
                dx_world = dx_screen / self.grid.scale
                dy_world = dy_screen / self.grid.scale

                # Move selected nodes
                for node in self.selected_nodes:
                    node.position = (node.position[0] + dx_world, node.position[1] + dy_world)

                # Move selected transistors
                for transistor in self.selected_transistors:
                    transistor.position = (transistor.position[0] + dx_world, transistor.position[1] + dy_world)

                # Move selected wires
                for wire in self.selected_wires:
                    wire.start_point = (wire.start_point[0] + dx_world, wire.start_point[1] + dy_world)
                    wire.end_point = (wire.end_point[0] + dx_world, wire.end_point[1] + dy_world)

                # Move selected Clocks
                for clock in self.selected_clocks:
                    clock.position = (clock.position[0] + dx_world, clock.position[1] + dy_world)

                # Move selection rectangle
                x, y = self.selection_rect_world.topleft
                self.selection_rect_world.topleft = (x + dx_world, y + dy_world)
            elif self.is_moving_object:
                # Move individual object
                mouse_x, mouse_y = pygame.mouse.get_pos()
                world_x, world_y = self.grid.screen_to_world(mouse_x, mouse_y)
                if isinstance(self.moving_object, Node):
                    self.moving_object.position = (world_x, world_y)
                elif isinstance(self.moving_object, Transistor):
                    self.moving_object.position = (world_x, world_y)
                elif isinstance(self.moving_object, Clock):
                    self.moving_object.position = (world_x, world_y)
            elif self.dragging_wire_endpoint:
                # Update the position of the wire endpoint as the mouse moves
                mouse_pos = pygame.mouse.get_pos()
                world_x, world_y = self.grid.screen_to_world(*mouse_pos)
                grid_x = round(world_x / GRID_SPACING) * GRID_SPACING
                grid_y = round(world_y / GRID_SPACING) * GRID_SPACING
                wire, endpoint = self.dragging_wire_endpoint
                if endpoint == 'start':
                    wire.start_point = (grid_x, grid_y)
                elif endpoint == 'end':
                    wire.end_point = (grid_x, grid_y)

        # Key press
        elif event.type == pygame.KEYDOWN:
            # Check for Ctrl+S and Ctrl+L
            ctrl_pressed = pygame.key.get_mods() & pygame.KMOD_CTRL
            if ctrl_pressed and event.key == pygame.K_s and not (self.save_dialog_active or self.load_dialog_active):
                self.save_dialog_active = True
                self.save_filename = ""
                self.save_input_active = True
            elif ctrl_pressed and event.key == pygame.K_l and not (self.save_dialog_active or self.load_dialog_active):
                self.load_dialog_active = True
                self.load_files = self.get_saved_files()
                self.load_selection_index = 0

            # Handle Save Dialog text input
            if self.save_dialog_active:
                if event.key == pygame.K_RETURN:
                    if self.save_filename.strip() != "":
                        self.save_circuit(self.save_filename.strip())
                        self.save_dialog_active = False
                        self.save_filename = ""
                elif event.key == pygame.K_BACKSPACE:
                    self.save_filename = self.save_filename[:-1]
                else:
                    if len(self.save_filename) < 20 and event.unicode.isalnum():
                        self.save_filename += event.unicode
            elif self.load_dialog_active:
                if event.key == pygame.K_UP:
                    if self.load_selection_index > 0:
                        self.load_selection_index -= 1
                elif event.key == pygame.K_DOWN:
                    if self.load_selection_index < len(self.load_files) - 1:
                        self.load_selection_index += 1
                elif event.key == pygame.K_RETURN:
                    if self.load_files:
                        selected_file = self.load_files[self.load_selection_index]
                        self.load_circuit(selected_file)
                        self.load_dialog_active = False
                elif event.key == pygame.K_ESCAPE:
                    self.load_dialog_active = False
            else:
                # Existing key handling
                if event.key == pygame.K_w and not self.drawing_disabled:
                    self.mode = MODE_WIRE
                elif event.key == pygame.K_i and not self.drawing_disabled:
                    self.mode = MODE_INPUT
                elif event.key == pygame.K_o and not self.drawing_disabled:
                    self.mode = MODE_OUTPUT
                elif event.key == pygame.K_t and not self.drawing_disabled:
                    self.mode = MODE_TRANSISTOR  # N-type transistor
                elif event.key == pygame.K_n and not self.drawing_disabled:
                    self.mode = MODE_P_TRANSISTOR  # P-type transistor
                elif event.key == pygame.K_c and not self.drawing_disabled:
                    self.mode = MODE_CLOCK  # Clock mode
                elif event.key == pygame.K_r and not (self.save_dialog_active or self.load_dialog_active):
                    # Rotate hovered transistor
                    hovered_transistor = self.get_hovered_transistor()
                    if hovered_transistor:
                        hovered_transistor.rotate()
                    
                elif event.key == pygame.K_ESCAPE:
                    self.mode = MODE_NONE
                elif event.key == pygame.K_BACKSPACE:
                    if self.selection_rect_world and self.is_mouse_over_selection():
                        # Delete selected objects
                        self.delete_selected_objects()
                        self.clear_selection()
                    else:
                        self.delete_hovered_object()
                elif event.key == pygame.K_c:
                    ctrl_pressed = pygame.key.get_mods() & pygame.KMOD_CTRL
                    if ctrl_pressed and self.selection_rect_world:
                        # Copy selected objects
                        self.copy_selection()
                elif event.key == pygame.K_v:
                    ctrl_pressed = pygame.key.get_mods() & pygame.KMOD_CTRL
                    if ctrl_pressed:
                        # Paste copied objects
                        self.paste_copied_objects()


    def is_click_on_save_button(self, pos):
        # Define Save button rectangle
        button_width = 100
        button_height = 40
        button_x = 20
        button_y = HEIGHT - button_height - 20
        button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        return button_rect.collidepoint(pos)

    def is_click_on_load_button(self, pos):
        # Define Load button rectangle
        button_width = 100
        button_height = 40
        button_x = WIDTH - button_width - 20
        button_y = HEIGHT - button_height - 20
        button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        return button_rect.collidepoint(pos)

    def get_clicked_load_file(self, pos):
        # Define area for load file list
        list_x = 20
        list_y = 20
        item_height = 30
        for index, file in enumerate(self.load_files):
            file_rect = pygame.Rect(list_x, list_y + index * item_height, WIDTH - 40, item_height)
            if file_rect.collidepoint(pos):
                return index
        return None

    def is_mouse_over_selection(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_x, world_y = self.grid.screen_to_world(mouse_x, mouse_y)
        return self.selection_rect_world.collidepoint(world_x, world_y)

    def get_hovered_node(self):
        mouse_pos = pygame.mouse.get_pos()
        for node in self.nodes:
            if node.is_hovered(self.grid, mouse_pos):
                return node
        return None

    def get_hovered_wire(self):
        mouse_pos = pygame.mouse.get_pos()
        for wire in self.wires:
            if wire.is_hovered(self.grid, mouse_pos):
                return wire
        return None

    def get_hovered_transistor(self):
        mouse_pos = pygame.mouse.get_pos()
        for transistor in self.transistors:
            if transistor.is_hovered(self.grid, mouse_pos):
                return transistor
        return None

    def get_hovered_clock(self):
        mouse_pos = pygame.mouse.get_pos()
        for clock in self.clocks:
            if clock.is_hovered(self.grid, mouse_pos):
                return clock
        return None

    def get_hovered_object(self):
        obj = self.get_hovered_node()
        if obj:
            return obj
        obj = self.get_hovered_transistor()
        if obj:
            return obj
        obj = self.get_hovered_clock()
        if obj:
            return obj
        return None

    def delete_hovered_object(self):
        # Try to delete a node first
        node = self.get_hovered_node()
        if node:
            self.nodes.remove(node)
        
            return
        # Try to delete a transistor
        transistor = self.get_hovered_transistor()
        if transistor:
            self.transistors.remove(transistor)
        
            return
        # Try to delete a Clock
        clock = self.get_hovered_clock()
        if clock:
            self.clocks.remove(clock)
        
            return
        # Try to delete a wire
        wire = self.get_hovered_wire()
        if wire:
            self.wires.remove(wire)
        

    def get_state_at_point(self, point):
        if point in self.on_points:
            return True
        else:
            return False

    def build_connectivity_graph(self):
        graph = defaultdict(list)

        # Add wires to the graph
        for wire in self.wires:
            graph[wire.start_point].append(wire.end_point)
            graph[wire.end_point].append(wire.start_point)

        # Add nodes (inputs and outputs) to the graph
        for node in self.nodes:
            graph[node.position]  # Ensure the node is in the graph

        # Add Clocks as sources
        for clock in self.clocks:
            graph[clock.position]  # Ensure the clock is in the graph

        # Add transistors as conditional edges
        for transistor in self.transistors:
            if transistor.orientation == 'horizontal':
                source = (transistor.position[0] - GRID_SPACING, transistor.position[1])
                drain = (transistor.position[0] + GRID_SPACING, transistor.position[1])
            else:  # vertical
                source = (transistor.position[0], transistor.position[1] - GRID_SPACING)
                drain = (transistor.position[0], transistor.position[1] + GRID_SPACING)

            # Determine if the transistor is conducting
            gate_state = self.get_state_at_point(transistor.position)  # Function to determine the state at a given point
            conducting = False
            if transistor.transistor_type == "n-type" and gate_state:
                conducting = True
            elif transistor.transistor_type == "p-type" and not gate_state:
                conducting = True

            if conducting:
                # Connect source and drain
                graph[source].append(drain)
                graph[drain].append(source)

        return graph

    def update_circuit_state(self):
        # Update Clock states
        for clock in self.clocks:
            clock.update()

        previous_states = None
        previous_previous_states = None
        iteration = 0
        max_iterations = 10000

        while True:
            if iteration > max_iterations:
                print("SOLVING CIRCUIT TOOK TOO LONG")
                break
            iteration += 1

            graph = self.build_connectivity_graph()
            input_nodes = [node.position for node in self.nodes if node.node_type == 'input' and node.state]
            # Include Clock states as input nodes
            clock_on_points = [clock.position for clock in self.clocks if clock.state]
            all_input_points = input_nodes + clock_on_points
            self.on_points = self.propagate_signals(graph, all_input_points)

            current_states = (frozenset(self.on_points), tuple(transistor.state for transistor in self.transistors))
            if current_states == previous_states or current_states == previous_previous_states:
                if current_states == previous_previous_states:
                    print("CIRCUIT OSCILLATION DETECTED!")
                break
            previous_previous_states = previous_states
            previous_states = current_states

            # Update states
            for wire in self.wires:
                wire.state = wire.start_point in self.on_points or wire.end_point in self.on_points

            for node in self.nodes:
                if node.node_type == 'output':
                    node.state = node.position in self.on_points

            for transistor in self.transistors:
                gate_state = self.get_state_at_point(transistor.position)
                transistor.state = (transistor.transistor_type == "n-type" and gate_state) or \
                                    (transistor.transistor_type == "p-type" and not gate_state)

        # Update colors based on state
        for wire in self.wires:
            wire.state = wire.start_point in self.on_points or wire.end_point in self.on_points

        for node in self.nodes:
            if node.node_type == 'output':
                node.state = node.position in self.on_points

    def propagate_signals(self, graph, input_nodes):
        queue = deque(input_nodes)
        visited = set(input_nodes)

        while queue:
            current = queue.popleft()
            for neighbor in graph[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited

    def get_nodes_in_rect(self, rect):
        nodes_in_rect = []
        for node in self.nodes:
            if rect.collidepoint(node.position):
                nodes_in_rect.append(node)
        return nodes_in_rect

    def get_transistors_in_rect(self, rect):
        transistors_in_rect = []
        for transistor in self.transistors:
            if rect.collidepoint(transistor.position):
                transistors_in_rect.append(transistor)
        return transistors_in_rect

    def get_wires_in_rect(self, rect):
        wires_in_rect = []
        for wire in self.wires:
            if rect.collidepoint(wire.start_point) and rect.collidepoint(wire.end_point):
                wires_in_rect.append(wire)
        return wires_in_rect

    def get_clocks_in_rect(self, rect):
        clocks_in_rect = []
        for clock in self.clocks:
            if rect.collidepoint(clock.position):
                clocks_in_rect.append(clock)
        return clocks_in_rect

    def draw_save_dialog(self):
        # Define dialog area
        dialog_width = 300
        dialog_height = 100
        dialog_x = 20
        dialog_y = HEIGHT - dialog_height - 20
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(screen, DARK_GREY, dialog_rect)
        pygame.draw.rect(screen, WHITE, dialog_rect, 2)

        # Label
        label_text = BIG_FONT.render("Save Circuit", True, WHITE)
        screen.blit(label_text, (dialog_x + 10, dialog_y + 10))

        # Input box
        input_box_rect = pygame.Rect(dialog_x + 10, dialog_y + 50, 200, 30)
        pygame.draw.rect(screen, WHITE, input_box_rect, 2)
        input_text = FONT.render(self.save_filename, True, WHITE)
        screen.blit(input_text, (input_box_rect.x + 5, input_box_rect.y + 5))

        # Save button
        button_rect = pygame.Rect(dialog_x + 220, dialog_y + 50, 70, 30)
        pygame.draw.rect(screen, GREY, button_rect)
        pygame.draw.rect(screen, WHITE, button_rect, 2)
        button_text = FONT.render("Save", True, BLACK)
        text_rect = button_text.get_rect(center=button_rect.center)
        screen.blit(button_text, text_rect)

    def draw_load_dialog(self):
        # Define dialog area
        dialog_width = WIDTH - 40
        dialog_height = HEIGHT - 60
        dialog_x = 20
        dialog_y = 20
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(screen, DARK_GREY, dialog_rect)
        pygame.draw.rect(screen, WHITE, dialog_rect, 2)

        # Label
        label_text = BIG_FONT.render("Load Circuit", True, WHITE)
        screen.blit(label_text, (dialog_x + 10, dialog_y + 10))

        # List of files
        list_x = dialog_x + 10
        list_y = dialog_y + 50
        item_height = 30
        max_visible = (dialog_height - 70) // item_height
        visible_files = self.load_files[self.load_scroll_offset:self.load_scroll_offset + max_visible]
        for index, file in enumerate(visible_files):
            file_rect = pygame.Rect(list_x, list_y + index * item_height, dialog_width - 20, item_height - 5)
            actual_index = index + self.load_scroll_offset
            if actual_index == self.load_selection_index:
                color = LIGHTER_GREY
            else:
                color = DARK_GREY
            pygame.draw.rect(screen, color, file_rect)
            pygame.draw.rect(screen, WHITE, file_rect, 1)
            file_text = FONT.render(file, True, WHITE)
            screen.blit(file_text, (file_rect.x + 5, file_rect.y + 5))

        # Load button
        button_width = 100
        button_height = 40
        button_x = dialog_x + dialog_width - button_width - 20
        button_y = dialog_y + dialog_height - button_height - 20
        button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        pygame.draw.rect(screen, GREY, button_rect)
        pygame.draw.rect(screen, WHITE, button_rect, 2)
        button_text = FONT.render("Load", True, BLACK)
        text_rect = button_text.get_rect(center=button_rect.center)
        screen.blit(button_text, text_rect)

    def get_wire_endpoint_at_pos(self, pos):
        """
        Checks if the given screen position is on any wire's start or end point.
        Returns a tuple of (Wire instance, 'start' or 'end') if found, else (None, None).
        """
        mouse_x, mouse_y = pos
        for wire in self.wires:
            start_screen = self.grid.world_to_screen(*wire.start_point)
            end_screen = self.grid.world_to_screen(*wire.end_point)
            distance_start = math.hypot(mouse_x - start_screen[0], mouse_y - start_screen[1])
            distance_end = math.hypot(mouse_x - end_screen[0], mouse_y - end_screen[1])
            threshold = CONNECTION_SIZE * self.grid.scale + 5  # Add a small buffer
            if distance_start <= threshold:
                return wire, 'start'
            if distance_end <= threshold:
                return wire, 'end'
        return None, None

    def draw(self):
        self.grid.draw()

        mouse_pos = pygame.mouse.get_pos()

        # Draw Clocks
        for clock in self.clocks:
            is_hovered = clock.is_hovered(self.grid, mouse_pos)
            clock.draw(self.grid, is_hovered)

        # Draw transistors
        for transistor in self.transistors:
            is_hovered = transistor.is_hovered(self.grid, mouse_pos)
            transistor.draw(self.grid, is_hovered)

        # Draw wires
        for wire in self.wires:
            is_hovered = wire.is_hovered(self.grid, mouse_pos)
            # Highlight wire if it's being dragged
            if self.dragging_wire_endpoint and wire == self.dragging_wire_endpoint[0]:
                wire.draw(self.grid, is_hovered=True)  # Force hover effect
            else:
                wire.draw(self.grid, is_hovered=is_hovered)

        # Draw nodes
        for node in self.nodes:
            is_hovered = node.is_hovered(self.grid, mouse_pos)
            node.draw(self.grid, is_hovered=is_hovered)

        # Draw temporary wire if drawing
        if self.is_drawing_wire and self.wire_start_point:
            mouse_pos = pygame.mouse.get_pos()
            world_x, world_y = self.grid.screen_to_world(*mouse_pos)
            grid_x = round(world_x / GRID_SPACING) * GRID_SPACING
            grid_y = round(world_y / GRID_SPACING) * GRID_SPACING
            end_point = (grid_x, grid_y)

            start_x, start_y = self.grid.world_to_screen(*self.wire_start_point)
            end_x, end_y = self.grid.world_to_screen(*end_point)

            if (start_x, start_y) != (end_x, end_y):
                pygame.draw.line(screen, WHITE, (start_x, start_y), (end_x, end_y), int(WIRE_SIZE * self.grid.scale))
                pygame.draw.circle(screen, WHITE, (start_x, start_y), int(CONNECTION_SIZE * self.grid.scale))
                pygame.draw.circle(screen, WHITE, (end_x, end_y), int(CONNECTION_SIZE * self.grid.scale))

        # Draw selection box if selecting
        if self.is_selecting:
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end
            screen_x1, screen_y1 = self.grid.world_to_screen(x1, y1)
            screen_x2, screen_y2 = self.grid.world_to_screen(x2, y2)
            left = min(screen_x1, screen_x2)
            top = min(screen_y1, screen_y2)
            width = abs(screen_x2 - screen_x1)
            height = abs(screen_y2 - screen_y1)
            selection_rect = pygame.Rect(left, top, width, height)
            s = pygame.Surface((width, height), pygame.SRCALPHA)
            s.fill((128, 128, 128, 100))  # Semi-transparent grey
            screen.blit(s, (left, top))
            pygame.draw.rect(screen, GREY, selection_rect, 1)

        # Draw selection rectangle if exists
        elif self.selection_rect_world:
            left, top = self.selection_rect_world.topleft
            width = self.selection_rect_world.width
            height = self.selection_rect_world.height
            screen_left, screen_top = self.grid.world_to_screen(left, top)
            screen_width = width * self.grid.scale
            screen_height = height * self.grid.scale
            selection_rect = pygame.Rect(screen_left, screen_top, screen_width, screen_height)
            s = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            s.fill((128, 128, 128, 100))  # Semi-transparent grey
            screen.blit(s, (screen_left, screen_top))
            # Also draw a border
            pygame.draw.rect(screen, GREY, selection_rect, 1)

        # Draw Save Dialog
        if self.save_dialog_active:
            self.draw_save_dialog()

        # Draw Load Dialog
        if self.load_dialog_active:
            self.draw_load_dialog()
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_event(event)

            # Clear screen
            screen.fill(BLACK)

            # Update clocks
            self.update_circuit_state()

            # Draw circuit and dialogs
            self.draw()

            # Update display
            pygame.display.flip()

            # Cap the frame rate
            clock.tick(FPS)

        pygame.quit()
        sys.exit()

    def run_text_input(self, event):
        # Not used since text input is handled directly in handle_event
        pass

    def run_button_click(self, event):
        # Not used since button clicks are handled directly in handle_event
        pass

    def is_point_in_selection(self, x, y):
        world_x, world_y = self.grid.screen_to_world(x, y)
        return self.selection_rect_world.collidepoint(world_x, world_y)

    def clear_selection(self):
        self.selection_rect_world = None
        self.selected_nodes = []
        self.selected_wires = []
        self.selected_transistors = []
        self.selected_clocks = []
        self.drawing_disabled = False

    def copy_selection(self):
        # Deep copy selected objects
        self.copied_nodes = [copy.deepcopy(node) for node in self.selected_nodes]
        self.copied_wires = [copy.deepcopy(wire) for wire in self.selected_wires]
        self.copied_transistors = [copy.deepcopy(transistor) for transistor in self.selected_transistors]
        self.copied_clocks = [copy.deepcopy(clock) for clock in self.selected_clocks]
        # Store the offset for pasting
        self.copy_offset = self.get_selection_center()

    def paste_copied_objects(self):
        if not (self.copied_nodes or self.copied_wires or self.copied_transistors or self.copied_clocks):
            return

        # Get the mouse position in world coordinates
        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_x, world_y = self.grid.screen_to_world(mouse_x, mouse_y)
        grid_x = round(world_x / GRID_SPACING) * GRID_SPACING
        grid_y = round(world_y / GRID_SPACING) * GRID_SPACING
        paste_position = (grid_x, grid_y)

        # Calculate offset
        dx = paste_position[0] - self.copy_offset[0]
        dy = paste_position[1] - self.copy_offset[1]

        # Paste nodes
        new_nodes = []
        for node in self.copied_nodes:
            new_node = copy.deepcopy(node)
            new_node.position = (
                node.position[0] + dx, node.position[1] + dy)
            new_nodes.append(new_node)
        self.nodes.extend(new_nodes)

        # Paste transistors
        new_transistors = []
        for transistor in self.copied_transistors:
            new_transistor = copy.deepcopy(transistor)
            new_transistor.position = (
                transistor.position[0] + dx, transistor.position[1] + dy)
            new_transistors.append(new_transistor)
        self.transistors.extend(new_transistors)

        # Paste wires
        new_wires = []
        for wire in self.copied_wires:
            new_wire = copy.deepcopy(wire)
            new_wire.start_point = (
                wire.start_point[0] + dx, wire.start_point[1] + dy)
            new_wire.end_point = (
                wire.end_point[0] + dx, wire.end_point[1] + dy)
            new_wires.append(new_wire)
        self.wires.extend(new_wires)

        # Paste Clocks
        new_clocks = []
        for clock in self.copied_clocks:
            new_clock = copy.deepcopy(clock)
            new_clock.position = (
                clock.position[0] + dx, clock.position[1] + dy)
            new_clocks.append(new_clock)
        self.clocks.extend(new_clocks)

    
    

    def get_selection_center(self):
        # Calculate the center of the selection
        x_values = []
        y_values = []
        for node in self.selected_nodes:
            x_values.append(node.position[0])
            y_values.append(node.position[1])
        for transistor in self.selected_transistors:
            x_values.append(transistor.position[0])
            y_values.append(transistor.position[1])
        for wire in self.selected_wires:
            x_values.extend([wire.start_point[0], wire.end_point[0]])
            y_values.extend([wire.start_point[1], wire.end_point[1]])
        for clock in self.selected_clocks:
            x_values.append(clock.position[0])
            y_values.append(clock.position[1])

        if not x_values or not y_values:
            return (0, 0)

        center_x = sum(x_values) / len(x_values)
        center_y = sum(y_values) / len(y_values)
        return (center_x, center_y)

    def delete_selected_objects(self):
        for node in self.selected_nodes:
            if node in self.nodes:
                self.nodes.remove(node)
        for transistor in self.selected_transistors:
            if transistor in self.transistors:
                self.transistors.remove(transistor)
        for wire in self.selected_wires:
            if wire in self.wires:
                self.wires.remove(wire)
        for clock in self.selected_clocks:
            if clock in self.clocks:
                self.clocks.remove(clock)
    

    def node_at_position(self, position):
        for node in self.nodes:
            if node.position == position:
                return node
        return None

    def transistor_at_position(self, position):
        for transistor in self.transistors:
            if transistor.position == position:
                return transistor
        return None

    def clock_at_position(self, position):
        for clock in self.clocks:
            if clock.position == position:
                return clock
        return None

    def save_circuit(self, filename):
        data = {
            "nodes": [],
            "wires": [],
            "transistors": [],
            "clocks": []  # Add Clocks to the save data
        }
        for node in self.nodes:
            node_data = {
                "type": node.node_type,
                "position": node.position,
                "state": node.state
            }
            data["nodes"].append(node_data)
        for wire in self.wires:
            wire_data = {
                "start_point": wire.start_point,
                "end_point": wire.end_point,
                "state": wire.state
            }
            data["wires"].append(wire_data)
        for transistor in self.transistors:
            transistor_data = {
                "type": transistor.transistor_type,
                "position": transistor.position,
                "state": transistor.state,
                "orientation": transistor.orientation  # Save orientation
            }
            data["transistors"].append(transistor_data)
        for clock in self.clocks:
            clock_data = {
                "position": clock.position,
                "state": clock.state,
                "frequency": clock.frequency
            }
            data["clocks"].append(clock_data)
        filepath = os.path.join(SAVE_DIR, f"{filename}.txt")
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Circuit saved as {filepath}")

    def load_circuit(self, filename):
        filepath = os.path.join(SAVE_DIR, filename)
        if not os.path.exists(filepath):
            print(f"File {filepath} does not exist.")
            return
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Clear current circuit
        self.nodes.clear()
        self.wires.clear()
        self.transistors.clear()
        self.clocks.clear()  # Clear Clocks

        # Load nodes
        for node_data in data.get("nodes", []):
            node = Node(tuple(node_data["position"]), node_data["type"])
            node.state = node_data["state"]
            self.nodes.append(node)

        # Load wires
        for wire_data in data.get("wires", []):
            wire = Wire(tuple(wire_data["start_point"]), tuple(wire_data["end_point"]))
            wire.state = wire_data["state"]
            self.wires.append(wire)

        # Load transistors
        for transistor_data in data.get("transistors", []):
            orientation = transistor_data.get("orientation", 'horizontal')  # Default to horizontal
            transistor = Transistor(tuple(transistor_data["position"]), transistor_data["type"], orientation=orientation)
            transistor.state = transistor_data["state"]
            self.transistors.append(transistor)

        # Load Clocks
        for clock_data in data.get("clocks", []):
            clock_obj = Clock(tuple(clock_data["position"]), frequency=clock_data.get("frequency", CLOCK_FREQUENCY))
            clock_obj.state = clock_data["state"]
            self.clocks.append(clock_obj)

    
    
        print(f"Circuit loaded from {filepath}")

    def draw_save_dialog(self):
        # Define dialog area
        dialog_width = 300
        dialog_height = 100
        dialog_x = 20
        dialog_y = HEIGHT - dialog_height - 20
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(screen, DARK_GREY, dialog_rect)
        pygame.draw.rect(screen, WHITE, dialog_rect, 2)

        # Label
        label_text = BIG_FONT.render("Save Circuit", True, WHITE)
        screen.blit(label_text, (dialog_x + 10, dialog_y + 10))

        # Input box
        input_box_rect = pygame.Rect(dialog_x + 10, dialog_y + 50, 200, 30)
        pygame.draw.rect(screen, WHITE, input_box_rect, 2)
        input_text = FONT.render(self.save_filename, True, WHITE)
        screen.blit(input_text, (input_box_rect.x + 5, input_box_rect.y + 5))

        # Save button
        button_rect = pygame.Rect(dialog_x + 220, dialog_y + 50, 70, 30)
        pygame.draw.rect(screen, GREY, button_rect)
        pygame.draw.rect(screen, WHITE, button_rect, 2)
        button_text = FONT.render("Save", True, BLACK)
        text_rect = button_text.get_rect(center=button_rect.center)
        screen.blit(button_text, text_rect)

    def draw_load_dialog(self):
        # Define dialog area
        dialog_width = WIDTH - 40
        dialog_height = HEIGHT - 60
        dialog_x = 20
        dialog_y = 20
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(screen, DARK_GREY, dialog_rect)
        pygame.draw.rect(screen, WHITE, dialog_rect, 2)

        # Label
        label_text = BIG_FONT.render("Load Circuit", True, WHITE)
        screen.blit(label_text, (dialog_x + 10, dialog_y + 10))

        # List of files
        list_x = dialog_x + 10
        list_y = dialog_y + 50
        item_height = 30
        max_visible = (dialog_height - 70) // item_height
        visible_files = self.load_files[self.load_scroll_offset:self.load_scroll_offset + max_visible]
        for index, file in enumerate(visible_files):
            file_rect = pygame.Rect(list_x, list_y + index * item_height, dialog_width - 20, item_height)
            actual_index = index + self.load_scroll_offset
            if actual_index == self.load_selection_index:
                color = LIGHTER_GREY
            else:
                color = DARK_GREY
            pygame.draw.rect(screen, color, file_rect)
            pygame.draw.rect(screen, WHITE, file_rect, 1)
            file_text = FONT.render(file, True, WHITE)
            screen.blit(file_text, (file_rect.x + 5, file_rect.y + 5))

        # Load button
        button_width = 100
        button_height = 40
        button_x = dialog_x + dialog_width - button_width - 20
        button_y = dialog_y + dialog_height - button_height - 20
        button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        pygame.draw.rect(screen, GREY, button_rect)
        pygame.draw.rect(screen, WHITE, button_rect, 2)
        button_text = FONT.render("Load", True, BLACK)
        text_rect = button_text.get_rect(center=button_rect.center)
        screen.blit(button_text, text_rect)

    def is_point_in_selection(self, x, y):
        world_x, world_y = self.grid.screen_to_world(x, y)
        return self.selection_rect_world.collidepoint(world_x, world_y)

    def clear_selection(self):
        self.selection_rect_world = None
        self.selected_nodes = []
        self.selected_wires = []
        self.selected_transistors = []
        self.selected_clocks = []
        self.drawing_disabled = False

    def node_at_position(self, position):
        for node in self.nodes:
            if node.position == position:
                return node
        return None

    def transistor_at_position(self, position):
        for transistor in self.transistors:
            if transistor.position == position:
                return transistor
        return None

    def clock_at_position(self, position):
        for clock in self.clocks:
            if clock.position == position:
                return clock
        return None

    def run_text_input(self, event):
        # Not used since text input is handled directly in handle_event
        pass

    def run_button_click(self, event):
        # Not used since button clicks are handled directly in handle_event
        pass


if __name__ == "__main__":
    circuit = Circuit()
    circuit.run()