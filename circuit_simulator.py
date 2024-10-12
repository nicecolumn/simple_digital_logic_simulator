import pygame
import sys
import math
import copy
import json
import os
from collections import defaultdict, deque
from components import Wire, Grid, Transistor, Clock, Node
from constants import *
from OpenGL.GL import *
from OpenGL.GLU import *
import graphics
import numpy as np


pygame.init()

# Initialize global screen and clock
#screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)

pygame.display.set_caption("Circuit Simulator")
clock = pygame.time.Clock()

# Ensure save directory exists
SAVE_DIR = "saves"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# Initialize fonts
FONT = pygame.font.SysFont(None, 24)
BIG_FONT = pygame.font.SysFont(None, 36)

class Circuit:
    """Manages circuit components such as nodes, wires, transistors, and clocks."""
    def __init__(self):
        self.nodes = []          # List of Node instances
        self.wires = []          # List of Wire instances
        self.transistors = []    # List of Transistor instances
        self.clocks = []         # List of Clock instances

    def add_node(self, node):
        self.nodes.append(node)

    def add_wire(self, wire):
        self.wires.append(wire)

    def add_transistor(self, transistor):
        self.transistors.append(transistor)

    def add_clock(self, clock):
        self.clocks.append(clock)

    def remove_node(self, node):
        if node in self.nodes:
            self.nodes.remove(node)

    def remove_wire(self, wire):
        if wire in self.wires:
            self.wires.remove(wire)

    def remove_transistor(self, transistor):
        if transistor in self.transistors:
            self.transistors.remove(transistor)

    def remove_clock(self, clock):
        if clock in self.clocks:
            self.clocks.remove(clock)

    def get_hovered_object(self, grid, mouse_pos):
        """Returns the object (Node, Transistor, Clock, Wire) hovered by the mouse."""
        # Check nodes
        for node in self.nodes:
            if node.is_hovered(grid, mouse_pos):
                return node
        # Check transistors
        for transistor in self.transistors:
            if transistor.is_hovered(grid, mouse_pos):
                return transistor
        # Check clocks
        for clock in self.clocks:
            if clock.is_hovered(grid, mouse_pos):
                return clock
        # Check wires
        for wire in self.wires:
            if wire.is_hovered(grid, mouse_pos):
                return wire
        return None

    def get_wire_endpoint_at_pos(self, grid, pos):
        """Checks if the given screen position is on any wire's start or end point."""
        mouse_x, mouse_y = pos
        for wire in self.wires:
            start_screen = grid.world_to_screen(*wire.start_point)
            end_screen = grid.world_to_screen(*wire.end_point)
            distance_start = math.hypot(mouse_x - start_screen[0], mouse_y - start_screen[1])
            distance_end = math.hypot(mouse_x - end_screen[0], mouse_y - end_screen[1])
            threshold = CONNECTION_SIZE * grid.scale + 5  # Add a small buffer
            if distance_start <= threshold:
                return wire, 'start'
            if distance_end <= threshold:
                return wire, 'end'
        return None, None

    def get_nodes_in_rect(self, rect):
        return [node for node in self.nodes if rect.collidepoint(node.position)]

    def get_transistors_in_rect(self, rect):
        return [transistor for transistor in self.transistors if rect.collidepoint(transistor.position)]

    def get_wires_in_rect(self, rect):
        return [wire for wire in self.wires if rect.collidepoint(wire.start_point) and rect.collidepoint(wire.end_point)]

    def get_clocks_in_rect(self, rect):
        return [clock for clock in self.clocks if rect.collidepoint(clock.position)]

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

class Simulation:
    """Handles the simulation logic of the circuit."""
    def __init__(self, circuit):
        self.circuit = circuit
        self.on_points = set()
        self.off_points = set()

    def get_state_at_point(self, point):
        if point in self.on_points:
            return True
        else:
            return False

    def build_connectivity_graph(self):
        graph = defaultdict(list)

        # Add wires to the graph
        for wire in self.circuit.wires:
            graph[wire.start_point].append(wire.end_point)
            graph[wire.end_point].append(wire.start_point)

        # Add nodes (inputs and outputs) to the graph
        for node in self.circuit.nodes:
            graph[node.position]  # Ensure the node is in the graph

        # Add Clocks as sources
        for clock in self.circuit.clocks:
            graph[clock.position]  # Ensure the clock is in the graph

        # Add transistors as conditional edges
        for transistor in self.circuit.transistors:
            if transistor.orientation == 'horizontal':
                source = (transistor.position[0] - GRID_SPACING, transistor.position[1])
                drain = (transistor.position[0] + GRID_SPACING, transistor.position[1])
            else:  # vertical
                source = (transistor.position[0], transistor.position[1] - GRID_SPACING)
                drain = (transistor.position[0], transistor.position[1] + GRID_SPACING)

            # Determine if the transistor is conducting
            gate_state = self.get_state_at_point(transistor.position)
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

    def update_circuit_state(self):
        # Update Clock states
        for clock in self.circuit.clocks:
            clock.update()

        previous_states = None
        previous_previous_states = None
        iteration = 0
        max_iterations = 100

        while True:
            if iteration > max_iterations:
                print("SOLVING CIRCUIT TOOK TOO LONG")
                break
            iteration += 1

            graph = self.build_connectivity_graph()
            input_nodes = [node.position for node in self.circuit.nodes if node.node_type == 'input' and node.state]
            # Include Clock states as input nodes
            clock_on_points = [clock.position for clock in self.circuit.clocks if clock.state]
            all_input_points = input_nodes + clock_on_points
            self.on_points = self.propagate_signals(graph, all_input_points)

            current_states = (frozenset(self.on_points), tuple(transistor.state for transistor in self.circuit.transistors))
            if current_states == previous_states or current_states == previous_previous_states:
                if current_states == previous_previous_states:
                    print("CIRCUIT OSCILLATION DETECTED!")
                break
            previous_previous_states = previous_states
            previous_states = current_states

            # Update states
            for wire in self.circuit.wires:
                wire.state = wire.start_point in self.on_points or wire.end_point in self.on_points

            for node in self.circuit.nodes:
                if node.node_type == 'output':
                    node.state = node.position in self.on_points

            for transistor in self.circuit.transistors:
                gate_state = self.get_state_at_point(transistor.position)
                transistor.state = (transistor.transistor_type == "n-type" and gate_state) or \
                                    (transistor.transistor_type == "p-type" and not gate_state)

        # Update colors based on state
        for wire in self.circuit.wires:
            wire.state = wire.start_point in self.on_points or wire.end_point in self.on_points

        for node in self.circuit.nodes:
            if node.node_type == 'output':
                node.state = node.position in self.on_points

class Game:
    """Manages the Pygame loop, event handling, drawing, and user interactions."""
    def __init__(self, screen):
        self.circuit = Circuit()
        self.simulation = Simulation(self.circuit)
        self.grid = Grid(screen, WIDTH, HEIGHT)
        self.mode = MODE_NONE
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
        self.copy_offset = (0, 0)

        # Moving individual objects
        self.is_moving_object = False
        self.moving_object = None
        self.move_offset = None

        # Save/Load Dialog Attributes
        self.save_dialog_active = False
        self.load_dialog_active = False
        self.save_filename = ""
        self.save_input_active = True  # To handle text input
        self.load_files = self.get_saved_files()
        self.load_scroll_offset = 0  # For scrolling through load files
        self.load_selection_index = 0

        # Variables to track dragging of wire endpoints
        self.dragging_wire_endpoint = None  # Tuple: (Wire instance, 'start' or 'end')

        self.simulation_running = False
        self.simulation_time = 0

        # Graphics
        self.renderer = graphics.Renderer(WIDTH, HEIGHT)

    def get_saved_files(self):
        files = [f for f in os.listdir(SAVE_DIR) if f.endswith('.txt')]
        return files

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.handle_resize(event)
        elif event.type == pygame.MOUSEWHEEL:
            self.handle_zoom(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.handle_mouse_button_down(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            self.handle_mouse_button_up(event)
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event)
        elif event.type == pygame.KEYDOWN:
            self.handle_key_down(event)

    def handle_resize(self, event):
        global screen, WIDTH, HEIGHT
        WIDTH, HEIGHT = event.w, event.h
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.grid.screen = screen
        self.grid.width = WIDTH
        self.grid.height = HEIGHT

    def handle_zoom(self, event):
        if not (self.save_dialog_active or self.load_dialog_active):
            self.grid.handle_zoom(event)

    def handle_mouse_button_down(self, event):
        if event.button == 2:  # Middle mouse button for panning
            if not (self.save_dialog_active or self.load_dialog_active):
                self.grid.start_panning()
        elif event.button == 1:  # Left mouse button
            shift_pressed = pygame.key.get_mods() & pygame.KMOD_SHIFT
            ctrl_pressed = pygame.key.get_mods() & pygame.KMOD_CTRL

            if shift_pressed:
                # Check if the click is on a wire endpoint
                wire, endpoint = self.circuit.get_wire_endpoint_at_pos(self.grid, event.pos)
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
                # Future enhancements: Handle clicking on the input box
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
                    obj = self.circuit.get_hovered_object(self.grid, event.pos)
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

                        # Toggle input node regardless of mode
                        node = self.circuit.node_at_position(position)
                        toggling_node = False
                        if node and node.node_type == 'input':
                            node.toggle()
                            toggling_node = True
                        else:
                            if self.mode == MODE_WIRE:
                                # Start drawing wire if not clicking on a node or transistor
                                if not toggling_node:
                                    wire = Wire(position, position)
                                    self.circuit.add_wire(wire)
                                    endpoint = position
                                    self.dragging_wire_endpoint = (wire, 'end')
                                    #self.is_drawing_wire = wire
                                    #self.wire_start_point = position
                            elif self.mode == MODE_INPUT:
                                # Place input node if position is empty
                                if not toggling_node:
                                    self.circuit.add_node(Node(position, 'input'))
                            elif self.mode == MODE_OUTPUT:
                                # Place output node if position is empty
                                if not toggling_node:
                                    self.circuit.add_node(Node(position, 'output'))
                            elif self.mode == MODE_TRANSISTOR:
                                # Place N-type transistor
                                if not toggling_node:
                                    self.circuit.add_transistor(Transistor(position, transistor_type='n-type'))
                            elif self.mode == MODE_P_TRANSISTOR:
                                # Place P-type transistor
                                if not toggling_node:
                                    self.circuit.add_transistor(Transistor(position, transistor_type='p-type'))
                            elif self.mode == MODE_CLOCK:
                                # Place Clock if position is empty
                                if not toggling_node:
                                    self.circuit.add_clock(Clock(position))

    def handle_mouse_button_up(self, event):
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
                    if (grid_x, grid_y) != wire.end_point:
                        wire.start_point = (grid_x, grid_y)
                    else:
                        self.circuit.remove_wire(wire)
                elif endpoint == 'end':
                    if (grid_x, grid_y) != wire.start_point:
                        wire.end_point = (grid_x, grid_y)
                    else:
                        self.circuit.remove_wire(wire)
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
                self.selected_nodes = self.circuit.get_nodes_in_rect(self.selection_rect_world)
                self.selected_wires = self.circuit.get_wires_in_rect(self.selection_rect_world)
                self.selected_transistors = self.circuit.get_transistors_in_rect(self.selection_rect_world)
                self.selected_clocks = self.circuit.get_clocks_in_rect(self.selection_rect_world)
                # If no objects are selected, clear selection
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
                # Finish moving individual object
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
                # Finish drawing wire
                world_x, world_y = self.grid.screen_to_world(*pygame.mouse.get_pos())
                grid_x = round(world_x / GRID_SPACING) * GRID_SPACING
                grid_y = round(world_y / GRID_SPACING) * GRID_SPACING
                end_point = (grid_x, grid_y)

                # Create wire
                if end_point == self.wire_start_point:
                    self.circuit.remove_wire(self.is_drawing_wire)
                    #self.circuit.add_wire(Wire(self.wire_start_point, end_point))

                self.is_drawing_wire = None
                self.wire_start_point = None

    def handle_mouse_motion(self, event):
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

    def handle_key_down(self, event):
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
                hovered_transistor = self.circuit.get_hovered_object(self.grid, pygame.mouse.get_pos())
                if isinstance(hovered_transistor, Transistor):
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
                if ctrl_pressed and self.selection_rect_world:
                    # Copy selected objects
                    self.copy_selection()
            elif event.key == pygame.K_v:
                if ctrl_pressed:
                    # Paste copied objects
                    self.paste_copied_objects()
            elif event.key == pygame.K_SPACE:
                self.simulation_running = not self.simulation_running

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
        return next((node for node in self.circuit.nodes if node.is_hovered(self.grid, pygame.mouse.get_pos())), None)

    def get_hovered_wire(self):
        return next((wire for wire in self.circuit.wires if wire.is_hovered(self.grid, pygame.mouse.get_pos())), None)

    def get_hovered_transistor(self):
        return next((transistor for transistor in self.circuit.transistors if transistor.is_hovered(self.grid, pygame.mouse.get_pos())), None)

    def get_hovered_clock(self):
        return next((clock for clock in self.circuit.clocks if clock.is_hovered(self.grid, pygame.mouse.get_pos())), None)

    def get_hovered_object(self):
        return self.circuit.get_hovered_object(self.grid, pygame.mouse.get_pos())

    def delete_hovered_object(self):
        obj = self.get_hovered_object()
        if isinstance(obj, Node):
            self.circuit.remove_node(obj)
        elif isinstance(obj, Transistor):
            self.circuit.remove_transistor(obj)
        elif isinstance(obj, Clock):
            self.circuit.remove_clock(obj)
        elif isinstance(obj, Wire):
            self.circuit.remove_wire(obj)

    def delete_selected_objects(self):
        for node in self.selected_nodes:
            self.circuit.remove_node(node)
        for transistor in self.selected_transistors:
            self.circuit.remove_transistor(transistor)
        for wire in self.selected_wires:
            self.circuit.remove_wire(wire)
        for clock in self.selected_clocks:
            self.circuit.remove_clock(clock)

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
        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_x, world_y = self.grid.screen_to_world(mouse_x, mouse_y)
        grid_x = round(world_x / GRID_SPACING) * GRID_SPACING
        grid_y = round(world_y / GRID_SPACING) * GRID_SPACING
        self.copy_offset = (grid_x, grid_y)

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
        for node in self.copied_nodes:
            new_node = copy.deepcopy(node)
            new_node.position = (node.position[0] + dx, node.position[1] + dy)
            self.circuit.add_node(new_node)

        # Paste transistors
        for transistor in self.copied_transistors:
            new_transistor = copy.deepcopy(transistor)
            new_transistor.position = (transistor.position[0] + dx, transistor.position[1] + dy)
            self.circuit.add_transistor(new_transistor)

        # Paste wires
        for wire in self.copied_wires:
            new_wire = copy.deepcopy(wire)
            new_wire.start_point = (wire.start_point[0] + dx, wire.start_point[1] + dy)
            new_wire.end_point = (wire.end_point[0] + dx, wire.end_point[1] + dy)
            self.circuit.add_wire(new_wire)

        # Paste Clocks
        for clock in self.copied_clocks:
            new_clock = copy.deepcopy(clock)
            new_clock.position = (clock.position[0] + dx, clock.position[1] + dy)
            self.circuit.add_clock(new_clock)

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

    def save_circuit(self, filename):
        data = {
            "nodes": [],
            "wires": [],
            "transistors": [],
            "clocks": []
        }
        for node in self.circuit.nodes:
            node_data = {
                "type": node.node_type,
                "position": node.position,
                "state": node.state
            }
            data["nodes"].append(node_data)
        for wire in self.circuit.wires:
            wire_data = {
                "start_point": wire.start_point,
                "end_point": wire.end_point,
                "state": wire.state
            }
            data["wires"].append(wire_data)
        for transistor in self.circuit.transistors:
            transistor_data = {
                "type": transistor.transistor_type,
                "position": transistor.position,
                "state": transistor.state,
                "orientation": transistor.orientation
            }
            data["transistors"].append(transistor_data)
        for clock in self.circuit.clocks:
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
        self.circuit.nodes.clear()
        self.circuit.wires.clear()
        self.circuit.transistors.clear()
        self.circuit.clocks.clear()

        # Load nodes
        for node_data in data.get("nodes", []):
            node = Node(tuple(node_data["position"]), node_data["type"])
            node.state = node_data["state"]
            self.circuit.add_node(node)

        # Load wires
        for wire_data in data.get("wires", []):
            wire = Wire(tuple(wire_data["start_point"]), tuple(wire_data["end_point"]))
            wire.state = wire_data["state"]
            self.circuit.add_wire(wire)

        # Load transistors
        for transistor_data in data.get("transistors", []):
            orientation = transistor_data.get("orientation", 'horizontal')  # Default to horizontal
            transistor = Transistor(tuple(transistor_data["position"]), transistor_data["type"], orientation=orientation)
            transistor.state = transistor_data["state"]
            self.circuit.add_transistor(transistor)

        # Load Clocks
        for clock_data in data.get("clocks", []):
            clock_obj = Clock(tuple(clock_data["position"]), frequency=clock_data.get("frequency", CLOCK_FREQUENCY))
            clock_obj.state = clock_data["state"]
            self.circuit.add_clock(clock_obj)

        print(f"Circuit loaded from {filepath}")

    def draw(self):
        mouse_pos = pygame.mouse.get_pos()
        self.renderer.draw(
            self.grid,
            self.circuit,
            mouse_pos,
            dragging_wire_endpoint=None,  # Replace with actual dragging logic
            is_drawing_wire=False,        # Replace with actual wire drawing logic
            wire_start_point=None,        # Replace with actual wire start point
            is_selecting=False,           # Replace with actual selection logic
            selection_start=None,         # Replace with actual selection start
            selection_end=None,           # Replace with actual selection end
            selection_rect_world=None,    # Replace with actual selection rectangle
            save_dialog_active=self.save_dialog_active,
            load_dialog_active=self.load_dialog_active,
            save_filename=self.save_filename,
            load_files=self.load_files,
            load_scroll_offset=self.load_scroll_offset,
            load_selection_index=self.load_selection_index
        )

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_event(event)

            # Clear screen
            glClearColor(0.0, 0.0, 0.0, 1.0)  # Black background
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glLoadIdentity()

            # main.py or your main application file

            # After initializing the renderer
            self.renderer.begin_colored_batch()

            # Draw a red rectangle
            red_color = [1.0, 1.0, 1.0, 1.0]  # Pure Red
            red_vertices = np.array([
                [100, 100],
                [200, 100],
                [200, 200],
                [200, 200],
                [100, 200],
                [100, 100],
            ], dtype=np.float32)
            red_colors = np.array([red_color] * 6, dtype=np.float32)
            self.renderer.add_colored_vertices(red_vertices, red_colors)

            # Draw a green rectangle
            green_color = [0.0, 1.0, 0.0, 1.0]  # Pure Green
            green_vertices = np.array([
                [250, 100],
                [350, 100],
                [350, 200],
                [350, 200],
                [250, 200],
                [250, 100],
            ], dtype=np.float32)
            green_colors = np.array([green_color] * 6, dtype=np.float32)
            self.renderer.add_colored_vertices(green_vertices, green_colors)

            # Draw a blue rectangle
            blue_color = [0.0, 0.0, 1.0, 1.0]  # Pure Blue
            blue_vertices = np.array([
                [400, 100],
                [500, 100],
                [500, 200],
                [500, 200],
                [400, 200],
                [400, 100],
            ], dtype=np.float32)
            blue_colors = np.array([blue_color] * 6, dtype=np.float32)
            self.renderer.add_colored_vertices(blue_vertices, blue_colors)

            # Finalize and draw the batch
            self.renderer.end_colored_batch()


            # Update simulation
            if self.simulation_running:
                if self.simulation_time >= SIMULATION_SPEED:
                    self.simulation.update_circuit_state()
                    self.simulation_time = 0

            self.simulation_time += 1

            # Draw circuit and dialogs
            self.draw()

            # Update display
            pygame.display.flip()

            # Cap the frame rate
            clock.tick(FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game(screen)
    game.run()
