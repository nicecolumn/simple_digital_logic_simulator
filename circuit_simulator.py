
import pygame
import sys
import math
import copy

pygame.init()

# Constants
WIDTH, HEIGHT = 1440, 896
GRID_SPACING = 100
MAX_GRID_POINTS = 20000
FPS = 144

# Colors
BLACK = (32, 32, 32)
GREY = (122, 122, 122)
DARK_GREY = (90, 90, 90)
YELLOW = (156, 225, 0)
WHITE = (245, 245, 245)
LIGHTER_GREY = (180, 180, 180)
LIGHTER_YELLOW = (200, 255, 50)
LIGHTER_WHITE = (255, 255, 255)

# Sizes
WIRE_SIZE = 8
CONNECTION_SIZE = 16
POINT_SIZE = 4
IO_POINT_SIZE = 32

# Modes
MODE_NONE = 'none'
MODE_WIRE = 'wire'
MODE_INPUT = 'input'
MODE_OUTPUT = 'output'
MODE_TRANSISTOR = 'transistor'
MODE_P_TRANSISTOR = 'p_transistor'


# Initialize screen
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Circuit Simulator")
clock = pygame.time.Clock()

# Classes


class Grid:
    def __init__(self):
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.is_panning = False
        self.pan_start_pos = (0, 0)
        self.offset_start = (0, 0)

    def world_to_screen(self, x, y):
        screen_x = (x - self.offset_x) * self.scale
        screen_y = (y - self.offset_y) * self.scale
        return screen_x, screen_y

    def screen_to_world(self, x, y):
        world_x = x / self.scale + self.offset_x
        world_y = y / self.scale + self.offset_y
        return world_x, world_y

    def handle_zoom(self, event):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_mouse_x, world_mouse_y = self.screen_to_world(mouse_x, mouse_y)

        if event.y > 0:
            self.scale *= 1.033333333333
        elif event.y < 0:
            self.scale /= 1.033333333333

        self.scale = max(min(self.scale, 100), 0.01)

        self.offset_x = world_mouse_x - mouse_x / self.scale
        self.offset_y = world_mouse_y - mouse_y / self.scale

    def start_panning(self):
        self.is_panning = True
        self.pan_start_pos = pygame.mouse.get_pos()
        self.offset_start = (self.offset_x, self.offset_y)

    def pan(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        dx = (self.pan_start_pos[0] - mouse_x) / self.scale
        dy = (self.pan_start_pos[1] - mouse_y) / self.scale
        self.offset_x = self.offset_start[0] + dx
        self.offset_y = self.offset_start[1] + dy

    def stop_panning(self):
        self.is_panning = False

    def draw(self):
        # Compute the world coordinates of the screen edges
        world_left = self.offset_x
        world_right = (WIDTH / self.scale) + self.offset_x
        world_top = self.offset_y
        world_bottom = (HEIGHT / self.scale) + self.offset_y

        # Compute grid lines
        grid_x_start = int(math.floor(world_left / GRID_SPACING) * GRID_SPACING)
        grid_x_end = int(math.ceil(world_right / GRID_SPACING) * GRID_SPACING)
        grid_y_start = int(math.floor(world_top / GRID_SPACING) * GRID_SPACING)
        grid_y_end = int(math.ceil(world_bottom / GRID_SPACING) * GRID_SPACING)

        num_grid_x = int((grid_x_end - grid_x_start) / GRID_SPACING) + 1
        num_grid_y = int((grid_y_end - grid_y_start) / GRID_SPACING) + 1

        if num_grid_x * num_grid_y < MAX_GRID_POINTS:
            for x in range(grid_x_start, grid_x_end + GRID_SPACING, GRID_SPACING):
                for y in range(grid_y_start, grid_y_end + GRID_SPACING, GRID_SPACING):
                    screen_x, screen_y = self.world_to_screen(x, y)
                    if 0 <= screen_x < WIDTH and 0 <= screen_y < HEIGHT:
                        pygame.draw.circle(screen, GREY, (int(screen_x), int(screen_y)), max(1, int(POINT_SIZE * self.scale)))


class Wire:
    def __init__(self, start_point, end_point):
        self.start_point = start_point  # (x, y)
        self.end_point = end_point      # (x, y)
        self.state = False  # False = OFF, True = ON

    def draw(self, grid, is_hovered=False):
        if self.state:
            color = LIGHTER_YELLOW if is_hovered else YELLOW
        else:
            color = LIGHTER_GREY if is_hovered else GREY
        start_x, start_y = grid.world_to_screen(*self.start_point)
        end_x, end_y = grid.world_to_screen(*self.end_point)
        pygame.draw.line(screen, color, (start_x, start_y), (end_x, end_y), max(1, int(WIRE_SIZE * grid.scale)))

    def is_hovered(self, grid, mouse_pos):
        # Check if mouse is close to the wire
        start_x, start_y = grid.world_to_screen(*self.start_point)
        end_x, end_y = grid.world_to_screen(*self.end_point)
        mouse_x, mouse_y = mouse_pos

        # Check for horizontal wire
        if start_y == end_y:
            if min(start_x, end_x) - 5 <= mouse_x <= max(start_x, end_x) + 5 and abs(mouse_y - start_y) <= 5:
                return True
        # Check for vertical wire
        elif start_x == end_x:
            if min(start_y, end_y) - 5 <= mouse_y <= max(start_y, end_y) + 5 and abs(mouse_x - start_x) <= 5:
                return True
        return False


class Node:
    def __init__(self, position, node_type):
        self.position = position  # (x, y)
        self.node_type = node_type  # 'input' or 'output'
        self.state = False  # False = 0, True = 1

    def draw(self, grid, is_hovered=False):
        screen_x, screen_y = grid.world_to_screen(*self.position)

        color = YELLOW if self.state else WHITE
        if is_hovered:
            color = LIGHTER_YELLOW if self.state else LIGHTER_WHITE

        pygame.draw.circle(screen, color, (int(screen_x), int(screen_y)), int(IO_POINT_SIZE * grid.scale))
        font = pygame.font.SysFont(None, 24)
        text = font.render('1' if self.state else '0', True, BLACK)
        text_rect = text.get_rect(center=(int(screen_x), int(screen_y)))
        screen.blit(text, text_rect)

    def toggle(self):
        if self.node_type == 'input':
            self.state = not self.state

    def is_hovered(self, grid, mouse_pos):
        screen_x, screen_y = grid.world_to_screen(*self.position)
        mouse_x, mouse_y = mouse_pos
        distance = math.hypot(screen_x - mouse_x, screen_y - mouse_y)
        return distance < 10  # Threshold in pixels


class Transistor:
    def __init__(self, position, transistor_type='n-type'):
        self.position = position  # Middle point (x, y)
        self.state = False# if transistor_type == 'n-type' else True # False = OFF, True = ON
        self.transistor_type = transistor_type  # 'n-type' or 'p-type'

    def draw(self, grid, is_hovered=False):
        if self.transistor_type == 'n-type':
            base_color = WHITE if self.state else DARK_GREY
            hover_color = LIGHTER_WHITE if self.state else GREY
        else:  # p-type transistor
            base_color = (255, 192, 203) if self.state else (128, 0, 128)  # Pink colors
            hover_color = (255, 182, 193) if self.state else (147, 112, 219)

        color = base_color if not is_hovered else hover_color
        middle_x, middle_y = self.position
        left_x = middle_x - GRID_SPACING
        right_x = middle_x + GRID_SPACING

        # Draw legs
        leg_width = int(WIRE_SIZE * grid.scale)
        leg_height = GRID_SPACING // 3
        # Left leg
        left_leg_top = (left_x, middle_y - leg_height)
        left_leg_bottom = (left_x, middle_y)
        left_leg_top_screen = grid.world_to_screen(*left_leg_top)
        left_leg_bottom_screen = grid.world_to_screen(*left_leg_bottom)
        pygame.draw.line(screen, color, left_leg_top_screen,
                         left_leg_bottom_screen, int(leg_width*2))
        # Right leg
        right_leg_top = (right_x, middle_y - leg_height)
        right_leg_bottom = (right_x, middle_y)
        right_leg_top_screen = grid.world_to_screen(*right_leg_top)
        right_leg_bottom_screen = grid.world_to_screen(*right_leg_bottom)
        pygame.draw.line(screen, color, right_leg_top_screen,
                         right_leg_bottom_screen, int(leg_width*2))
        # Bridge
        bridge_height = middle_y - leg_height - 10  # Slightly raised above legs
        bridge_left = (left_x - 5, bridge_height)
        bridge_right = (right_x + 5, bridge_height)
        bridge_left_screen = grid.world_to_screen(*bridge_left)
        bridge_right_screen = grid.world_to_screen(*bridge_right)
        pygame.draw.line(screen, color, bridge_left_screen,
                         bridge_right_screen, leg_width)
        
        # Terminals
        pygame.draw.circle(screen, color, (int(left_leg_bottom_screen[0]), int(left_leg_bottom_screen[1])), int(CONNECTION_SIZE * grid.scale))
        pygame.draw.circle(screen, color, (int(right_leg_bottom_screen[0]), int(right_leg_bottom_screen[1])), int(CONNECTION_SIZE * grid.scale))

    def is_hovered(self, grid, mouse_pos):
        screen_x, screen_y = grid.world_to_screen(*self.position)
        mouse_x, mouse_y = mouse_pos
        distance = math.hypot(screen_x - mouse_x, screen_y - mouse_y)
        return distance < 15  # Threshold in pixels


class Circuit:
    def __init__(self):
        self.grid = Grid()
        self.mode = MODE_NONE
        self.nodes = []       # List of Node instances
        self.wires = []       # List of Wire instances
        self.transistors = []  # List of Transistor instances
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
        self.is_moving_selection = False
        self.selection_offset = None
        self.drawing_disabled = False  # Disable drawing when selection exists
        self.previous_mode = MODE_NONE

        # Clipboard for copy/paste
        self.copied_nodes = []
        self.copied_wires = []
        self.copied_transistors = []

        # Moving individual objects
        self.is_moving_object = False
        self.moving_object = None
        self.move_offset = None

    def handle_event(self, event):
        # Window resize
        if event.type == pygame.VIDEORESIZE:
            global WIDTH, HEIGHT, screen
            WIDTH, HEIGHT = event.w, event.h
            screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

        # Zooming
        elif event.type == pygame.MOUSEWHEEL:
            self.grid.handle_zoom(event)

        # Mouse button down
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 2:  # Middle mouse button for panning
                self.grid.start_panning()
            elif event.button == 1:  # Left mouse button
                ctrl_pressed = pygame.key.get_mods() & pygame.KMOD_CTRL
                shift_pressed = pygame.key.get_mods() & pygame.KMOD_SHIFT
                if ctrl_pressed:
                    # Start selection box
                    world_x, world_y = self.grid.screen_to_world(
                        *pygame.mouse.get_pos())
                    self.selection_start = (world_x, world_y)
                    self.selection_end = (world_x, world_y)
                    self.is_selecting = True
                    self.selected_nodes = []
                    self.selected_wires = []
                    self.selected_transistors = []
                    self.drawing_disabled = True
                elif shift_pressed:
                    # Start moving individual object
                    obj = self.get_hovered_object()
                    if obj:
                        self.is_moving_object = True
                        self.moving_object = obj
                        self.move_offset = pygame.mouse.get_pos()
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
                    if not self.drawing_disabled:
                        # Existing code for handling nodes, wires, etc.
                        world_x, world_y = self.grid.screen_to_world(
                            *pygame.mouse.get_pos())
                        grid_x = round(world_x / GRID_SPACING) * GRID_SPACING
                        grid_y = round(world_y / GRID_SPACING) * GRID_SPACING
                        position = (grid_x, grid_y)

                        node = self.node_at_position(position)
                        transistor = self.transistor_at_position(position)

                        # Toggle input node regardless of mode
                        if node and node.node_type == 'input':
                            node.toggle()
                            self.update_circuit_state()
                        else:
                            if self.mode == MODE_WIRE:
                                # Start drawing wire if not clicking on a node or transistor
                                if not node:
                                    self.is_drawing_wire = True
                                    self.wire_start_point = position
                            elif self.mode == MODE_INPUT:
                                # Place input node if position is empty
                                if not node and not transistor and not self.node_at_position(position):
                                    self.nodes.append(
                                        Node(position, 'input'))
                            elif self.mode == MODE_OUTPUT:
                                # Place output node if position is empty
                                if not node and not transistor and not self.node_at_position(position):
                                    self.nodes.append(
                                        Node(position, 'output'))
                            elif self.mode == MODE_TRANSISTOR:
                                # Place N-type transistor
                                if not node and not transistor and not self.transistor_at_position(position):
                                    self.transistors.append(Transistor(position, transistor_type='n-type'))
                            elif self.mode == MODE_P_TRANSISTOR:
                                # Place P-type transistor
                                if not node and not transistor and not self.transistor_at_position(position):
                                    self.transistors.append(Transistor(position, transistor_type='p-type'))


        # Mouse button up
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:  # Middle mouse button
                self.grid.stop_panning()
            elif event.button == 1:  # Left mouse button
                if self.is_selecting:
                    # Finish selection
                    self.is_selecting = False
                    # Create selection rectangle in world coordinates
                    x1, y1 = self.selection_start
                    x2, y2 = self.selection_end
                    left = min(x1, x2)
                    top = min(y1, y2)
                    width = abs(x2 - x1)
                    height = abs(y2 - y1)
                    self.selection_rect_world = pygame.Rect(
                        left, top, width, height)
                    # Find objects within the selection rectangle
                    self.selected_nodes = self.get_nodes_in_rect(
                        self.selection_rect_world)
                    self.selected_wires = self.get_wires_in_rect(
                        self.selection_rect_world)
                    self.selected_transistors = self.get_transistors_in_rect(
                        self.selection_rect_world)
                    # If no objects are selected, the selection box remains until a new selection is made
                    if not (self.selected_nodes or self.selected_wires or self.selected_transistors):
                        self.clear_selection()
                elif self.is_moving_selection:
                    # Finish moving selection
                    self.is_moving_selection = False
                    # Snap positions to grid
                    for node in self.selected_nodes:
                        grid_x = round(
                            node.position[0] / GRID_SPACING) * GRID_SPACING
                        grid_y = round(
                            node.position[1] / GRID_SPACING) * GRID_SPACING
                        node.position = (grid_x, grid_y)
                    for transistor in self.selected_transistors:
                        grid_x = round(
                            transistor.position[0] / GRID_SPACING) * GRID_SPACING
                        grid_y = round(
                            transistor.position[1] / GRID_SPACING) * GRID_SPACING
                        transistor.position = (grid_x, grid_y)
                    for wire in self.selected_wires:
                        start_x = round(
                            wire.start_point[0] / GRID_SPACING) * GRID_SPACING
                        start_y = round(
                            wire.start_point[1] / GRID_SPACING) * GRID_SPACING
                        end_x = round(
                            wire.end_point[0] / GRID_SPACING) * GRID_SPACING
                        end_y = round(
                            wire.end_point[1] / GRID_SPACING) * GRID_SPACING
                        wire.start_point = (start_x, start_y)
                        wire.end_point = (end_x, end_y)
                    # Update circuit state
                    self.update_circuit_state()
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
                    self.update_circuit_state()
                elif self.is_drawing_wire:
                    world_x, world_y = self.grid.screen_to_world(
                        *pygame.mouse.get_pos())
                    grid_x = round(world_x / GRID_SPACING) * GRID_SPACING
                    grid_y = round(world_y / GRID_SPACING) * GRID_SPACING

                    # Enforce horizontal or vertical wires
                    dx = abs(grid_x - self.wire_start_point[0])
                    dy = abs(grid_y - self.wire_start_point[1])
                    if dx > dy:
                        end_point = (grid_x, self.wire_start_point[1])
                    else:
                        end_point = (self.wire_start_point[0], grid_y)

                    # Create wire
                    self.wires.append(Wire(self.wire_start_point, end_point))
                    self.is_drawing_wire = False
                    self.update_circuit_state()

        # Mouse motion
        elif event.type == pygame.MOUSEMOTION:
            if self.grid.is_panning:
                self.grid.pan()
            elif self.is_selecting:
                # Update selection box
                world_x, world_y = self.grid.screen_to_world(
                    *pygame.mouse.get_pos())
                self.selection_end = (world_x, world_y)
            elif self.is_moving_selection:
                # Move selected objects
                mouse_x, mouse_y = pygame.mouse.get_pos()
                prev_mouse_x, prev_mouse_y = self.selection_offset
                dx_screen = mouse_x - prev_mouse_x
                dy_screen = mouse_y - prev_mouse_y
                self.selection_offset = (mouse_x, mouse_y)

                # Convert delta to world coordinates
                dx_world = dx_screen / self.grid.scale
                dy_world = dy_screen / self.grid.scale

                # Move selected nodes
                for node in self.selected_nodes:
                    node.position = (
                        node.position[0] + dx_world, node.position[1] + dy_world)

                # Move selected transistors
                for transistor in self.selected_transistors:
                    transistor.position = (
                        transistor.position[0] + dx_world, transistor.position[1] + dy_world)

                # Move selected wires
                for wire in self.selected_wires:
                    wire.start_point = (
                        wire.start_point[0] + dx_world, wire.start_point[1] + dy_world)
                    wire.end_point = (
                        wire.end_point[0] + dx_world, wire.end_point[1] + dy_world)

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

        # Key press
        elif event.type == pygame.KEYDOWN:
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

    def is_point_in_selection(self, x, y):
        world_x, world_y = self.grid.screen_to_world(x, y)
        return self.selection_rect_world.collidepoint(world_x, world_y)

    def is_mouse_over_selection(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        return self.is_point_in_selection(mouse_x, mouse_y)

    def clear_selection(self):
        self.selection_rect_world = None
        self.selected_nodes = []
        self.selected_wires = []
        self.selected_transistors = []
        self.drawing_disabled = False

    def copy_selection(self):
        # Deep copy selected objects
        self.copied_nodes = [copy.deepcopy(node) for node in self.selected_nodes]
        self.copied_wires = [copy.deepcopy(wire) for wire in self.selected_wires]
        self.copied_transistors = [copy.deepcopy(transistor)
                                   for transistor in self.selected_transistors]
        # Store the offset for pasting
        self.copy_offset = self.get_selection_center()

    def paste_copied_objects(self):
        if not (self.copied_nodes or self.copied_wires or self.copied_transistors):
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

        # Update circuit state
        self.update_circuit_state()

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
        self.update_circuit_state()

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

    def get_hovered_object(self):
        obj = self.get_hovered_node()
        if obj:
            return obj
        obj = self.get_hovered_transistor()
        if obj:
            return obj
        return None

    def delete_hovered_object(self):
        # Try to delete a node first
        node = self.get_hovered_node()
        if node:
            self.nodes.remove(node)
            self.update_circuit_state()
            return
        # Try to delete a transistor
        transistor = self.get_hovered_transistor()
        if transistor:
            self.transistors.remove(transistor)
            self.update_circuit_state()
            return
        # Try to delete a wire
        wire = self.get_hovered_wire()
        if wire:
            self.wires.remove(wire)
            self.update_circuit_state()

    def update_circuit_state(self):
        # First, reset states
        for wire in self.wires:
            wire.state = False
        for node in self.nodes:
            if node.node_type == 'output':
                node.state = False
        for transistor in self.transistors:
            transistor.state = False

        # Build the base graph (without transistor connections)
        def build_base_graph():
            graph = {}
            # Initialize the graph nodes
            all_points = set()
            for wire in self.wires:
                all_points.add(wire.start_point)
                all_points.add(wire.end_point)
            for transistor in self.transistors:
                left_point = (transistor.position[0] - GRID_SPACING, transistor.position[1])
                right_point = (transistor.position[0] + GRID_SPACING, transistor.position[1])
                all_points.add(left_point)
                all_points.add(right_point)
                all_points.add(transistor.position)
            for node in self.nodes:
                all_points.add(node.position)

            for point in all_points:
                graph[point] = []

            # Add edges from wires
            for wire in self.wires:
                graph[wire.start_point].append(wire.end_point)
                graph[wire.end_point].append(wire.start_point)

            return graph

        graph = build_base_graph()

        # Initialize 'on' points from 'on' input nodes
        on_points = set()
        for node in self.nodes:
            if node.node_type == 'input' and node.state:
                on_points.add(node.position)

        changed = True
        while changed:
            changed = False

            # Update transistor states
            transistor_states_changed = False
            for transistor in self.transistors:
                control_point = transistor.position
                if transistor.transistor_type == 'n-type':
                    new_state = control_point in on_points
                elif transistor.transistor_type == 'p-type':
                    new_state = control_point in on_points
                else:
                    new_state = False  # Default to OFF
                if transistor.state != new_state:
                    transistor.state = new_state
                    transistor_states_changed = True
                    changed = True

            # Rebuild the graph including 'on' transistors
            graph = build_base_graph()
            for transistor in self.transistors:
                left_point = (transistor.position[0] - GRID_SPACING, transistor.position[1])
                right_point = (transistor.position[0] + GRID_SPACING, transistor.position[1])
                if transistor.state and transistor.transistor_type == "n-type":
                    graph[left_point].append(right_point)
                    graph[right_point].append(left_point)
                if (not transistor.state) and transistor.transistor_type == "p-type":
                    graph[left_point].append(right_point)
                    graph[right_point].append(left_point)

            # BFS to find on_points
            new_on_points = set()
            visited = set()
            queue = list(on_points)
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                new_on_points.add(current)
                for neighbor in graph.get(current, []):
                    if neighbor not in visited:
                        queue.append(neighbor)

            if new_on_points != on_points:
                on_points = new_on_points
                changed = True

        # After convergence, update wire states
        for wire in self.wires:
            if wire.start_point in on_points or wire.end_point in on_points:
                wire.state = True
            else:
                wire.state = False

        # Update output node states
        for node in self.nodes:
            if node.node_type == 'output':
                if node.position in on_points:
                    node.state = True
                else:
                    node.state = False


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

    def draw(self):
        self.grid.draw()

        mouse_pos = pygame.mouse.get_pos()

        # Draw wires
        for wire in self.wires:
            is_hovered = wire.is_hovered(self.grid, mouse_pos)
            wire.draw(self.grid, is_hovered)

        # Draw nodes
        for node in self.nodes:
            is_hovered = node.is_hovered(self.grid, mouse_pos)
            node.draw(self.grid, is_hovered)

        # Draw transistors
        for transistor in self.transistors:
            is_hovered = transistor.is_hovered(self.grid, mouse_pos)
            transistor.draw(self.grid, is_hovered)

        # Draw larger points where wires join
        connection_points = self.get_connection_points()
        for point in connection_points:
            screen_x, screen_y = self.grid.world_to_screen(*point)
            pygame.draw.circle(screen, GREY, (int(screen_x), int(screen_y)), int(CONNECTION_SIZE * self.grid.scale))

        # Draw temporary wire if drawing
        if self.is_drawing_wire and self.wire_start_point:
            mouse_pos = pygame.mouse.get_pos()
            world_x, world_y = self.grid.screen_to_world(*mouse_pos)
            grid_x = round(world_x / GRID_SPACING) * GRID_SPACING
            grid_y = round(world_y / GRID_SPACING) * GRID_SPACING

            # Enforce horizontal or vertical wires
            dx = abs(grid_x - self.wire_start_point[0])
            dy = abs(grid_y - self.wire_start_point[1])
            if dx > dy:
                end_point = (grid_x, self.wire_start_point[1])
            else:
                end_point = (self.wire_start_point[0], grid_y)

            start_x, start_y = self.grid.world_to_screen(
                *self.wire_start_point)
            end_x, end_y = self.grid.world_to_screen(*end_point)
            pygame.draw.line(screen, WHITE, (start_x, start_y), (end_x, end_y), WIRE_SIZE)

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
            selection_rect = pygame.Rect(
                screen_left, screen_top, screen_width, screen_height)
            s = pygame.Surface(
                (screen_width, screen_height), pygame.SRCALPHA)
            s.fill((128, 128, 128, 100))  # Semi-transparent grey
            screen.blit(s, (screen_left, screen_top))
            # Also draw a border
            pygame.draw.rect(screen, GREY, selection_rect, 1)

    def get_connection_points(self):
        # Find points where wires connect
        points = []
        point_counts = {}
        for wire in self.wires:
            for point in [wire.start_point, wire.end_point]:
                if point in point_counts:
                    point_counts[point] += 1
                else:
                    point_counts[point] = 1
        for transistor in self.transistors:
            if transistor.state:
                left_point = (transistor.position[0] - GRID_SPACING,
                              transistor.position[1])
                right_point = (transistor.position[0] + GRID_SPACING,
                               transistor.position[1])
                for point in [left_point, right_point]:
                    if point in point_counts:
                        point_counts[point] += 1
                    else:
                        point_counts[point] = 1
        for point, count in point_counts.items():
            if count > 1:
                points.append(point)
        return points

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

            # Draw circuit
            self.draw()

            # Update display
            pygame.display.flip()

            # Cap the frame rate
            clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    circuit = Circuit()
    circuit.run()