import pygame
import sys
import math
import copy
import json
import os
from collections import defaultdict, deque

pygame.init()

# Constants
WIDTH, HEIGHT = 1440, 896
GRID_SPACING = 100
MAX_GRID_POINTS = 20000
FPS = 60

# Frequency for Clock objects
CLOCK_FREQUENCY = 60

# Colors
BLACK = (32, 32, 32)
GREY = (122, 122, 122)
DARK_GREY = (90, 90, 90)
YELLOW = (156, 225, 0)
WHITE = (245, 245, 245)
LIGHTER_GREY = (180, 180, 180)
LIGHTER_YELLOW = (200, 255, 50)
LIGHTER_WHITE = (255, 255, 255)
RED = (235, 0, 0)
LIGHTER_RED = (255, 20, 20)

P_OFF = (120, 120, 60)
P_ON = (200, 200, 100)
N_OFF = (120, 60, 60)
N_ON = (200, 100, 100)

W_OFF = (120, 120, 120)
W_ON = (220, 220, 220)

CLOCK_COLOR = LIGHTER_GREY  # White cube

# Sizes
WIRE_SIZE = 16
CONNECTION_SIZE = 16
POINT_SIZE = 4
IO_POINT_SIZE = 32
HOVER_RADIUS = 30

# Modes
MODE_NONE = 'none'
MODE_WIRE = 'wire'
MODE_INPUT = 'input'
MODE_OUTPUT = 'output'
MODE_TRANSISTOR = 'transistor'
MODE_P_TRANSISTOR = 'p_transistor'
MODE_CLOCK = 'clock'  # New mode for Clock

# Initialize screen
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Circuit Simulator")
clock = pygame.time.Clock()

# Ensure the saves directory exists
SAVE_DIR = "saves"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# Font
FONT = pygame.font.SysFont(None, 24)
BIG_FONT = pygame.font.SysFont(None, 36)

# Function to draw a line with rounded corners
def draw_round_line(surface, color, start, end, width, radius):
    """
    Draws a rounded rectangle (like a thick line with rounded ends) between two points.

    Parameters:
    - surface (pygame.Surface): The surface to draw on.
    - color (tuple): The RGB color of the rectangle, e.g., (255, 0, 0) for red.
    - start (tuple): The starting point (x, y) of the rectangle.
    - end (tuple): The ending point (x, y) of the rectangle.
    - width (int): The thickness of the rectangle.
    - radius (float): The proportion of the width to use as radius.

    Returns:
    - None
    """
    # Calculate the difference in coordinates
    dx = end[0] - start[0]
    dy = end[1] - start[1]

    # Calculate the distance between start and end points
    distance = math.hypot(dx, dy)
    if distance == 0:
        # Avoid drawing if start and end points are the same
        return

    # Calculate the angle in degrees. Negative dy because Pygame's y-axis is inverted
    angle = math.degrees(math.atan2(-dy, dx))

    # Create a surface for the rectangle with per-pixel alpha
    rect_surface = pygame.Surface((distance, width), pygame.SRCALPHA)

    radius_px = min(int(width / 2), int(width * radius))

    # Draw the rounded rectangle on the temporary surface
    pygame.draw.rect(
        rect_surface,
        color,
        pygame.Rect(0, 0, distance, width),
        border_radius=radius_px
    )

    # Rotate the rectangle surface to align with the angle between start and end
    rotated_surface = pygame.transform.rotate(rect_surface, angle)

    # Get the rotated surface's rectangle and set its center to the midpoint between start and end
    rotated_rect = rotated_surface.get_rect()

    # Calculate midpoint
    mid_x = (start[0] + end[0]) / 2
    mid_y = (start[1] + end[1]) / 2

    # Calculate the top-left position to blit the rotated surface so that it's centered at the midpoint
    blit_position = (mid_x - rotated_rect.width / 2, mid_y - rotated_rect.height / 2)

    # Blit the rotated surface onto the target surface at the calculated position
    surface.blit(rotated_surface, blit_position)


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
            color = W_ON
        else:
            color = W_OFF

        if is_hovered:
            color = list(color)
            for i, v in enumerate(color):
                color[i] += 5
                color[i] = min(255, color[i])

        start_x, start_y = grid.world_to_screen(*self.start_point)
        end_x, end_y = grid.world_to_screen(*self.end_point)
        pygame.draw.line(screen, color, (start_x, start_y), (end_x, end_y), max(1, int(WIRE_SIZE * grid.scale)))

        pygame.draw.circle(screen, color, (int(start_x), int(start_y)), int(CONNECTION_SIZE * grid.scale))
        pygame.draw.circle(screen, color, (int(end_x), int(end_y)), int(CONNECTION_SIZE * grid.scale))

    def is_hovered(self, grid, mouse_pos):
        # Check if mouse is close to the wire
        start_x, start_y = grid.world_to_screen(*self.start_point)
        end_x, end_y = grid.world_to_screen(*self.end_point)
        mouse_x, mouse_y = mouse_pos

        # Calculate distance from mouse to the wire line
        if start_x == end_x and start_y == end_y:
            distance = math.hypot(mouse_x - start_x, mouse_y - start_y)
            return distance <= HOVER_RADIUS
        else:
            # Line equation parameters
            A = mouse_x - start_x
            B = mouse_y - start_y
            C = end_x - start_x
            D = end_y - start_y

            dot = A * C + B * D
            len_sq = C * C + D * D
            param = dot / len_sq if len_sq != 0 else -1

            if param < 0:
                xx, yy = start_x, start_y
            elif param > 1:
                xx, yy = end_x, end_y
            else:
                xx = start_x + param * C
                yy = start_y + param * D

            distance = math.hypot(mouse_x - xx, mouse_y - yy)
            return distance <= HOVER_RADIUS


class Node:
    def __init__(self, position, node_type):
        self.position = position  # (x, y)
        self.node_type = node_type  # 'input' or 'output'
        if self.node_type == 'input':
            self.state = False  # False = 0, True = 1
        else:
            self.state = False  # Outputs start as OFF

    def draw(self, grid, is_hovered=False):
        screen_x, screen_y = grid.world_to_screen(*self.position)

        if self.state:
            color = YELLOW
        else:
            color = WHITE

        if is_hovered:
            color = LIGHTER_YELLOW if self.state else LIGHTER_WHITE

        pygame.draw.circle(screen, color, (int(screen_x), int(screen_y)), int(IO_POINT_SIZE * grid.scale))
        font = pygame.font.SysFont(None, int(48 * grid.scale))
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
        return distance < (IO_POINT_SIZE * grid.scale)  # Threshold based on IO size


class Transistor:
    def __init__(self, position, transistor_type='n-type', orientation='horizontal'):
        self.position = position  # Middle point (x, y)
        self.state = False if transistor_type == 'n-type' else True  # False = OFF, True = ON
        self.transistor_type = transistor_type  # 'n-type' or 'p-type'
        self.orientation = orientation  # 'horizontal' or 'vertical'

    def rotate(self):
        if self.orientation == 'horizontal':
            self.orientation = 'vertical'
        else:
            self.orientation = 'horizontal'


    def draw(self, grid, is_hovered=False):
        if self.transistor_type == "n-type":
            if self.state:
                color_a = N_ON
                color_b = P_OFF
            else:
                color_a = N_OFF
                color_b = P_ON
        else:
            if self.state:
                color_a = P_OFF
                color_b = N_ON
            else:
                color_a = P_ON
                color_b = N_OFF

        if is_hovered:
            color_a = list(color_a)
            color_b = list(color_b)
            for i, v in enumerate(color_a):
                color_a[i] += 5
                color_b[i] += 5
                color_a[i] = min(255, color_a[i])
                color_b[i] = min(255, color_b[i])

        middle_x, middle_y = self.position

        if self.orientation == 'horizontal':
            left_x = middle_x - GRID_SPACING
            right_x = middle_x + GRID_SPACING

            # Legs
            leg_length = GRID_SPACING * 0.51
            # Left leg
            left_leg_top = (left_x, middle_y - leg_length)
            left_leg_bottom = (left_x, middle_y + leg_length)
            left_leg_top_screen = grid.world_to_screen(*left_leg_top)
            left_leg_bottom_screen = grid.world_to_screen(*left_leg_bottom)
            draw_round_line(screen, color_a, left_leg_top_screen,
                           left_leg_bottom_screen, int(GRID_SPACING * 0.4 * grid.scale), 0.15)
            # Right leg
            right_leg_top = (right_x, middle_y - leg_length)
            right_leg_bottom = (right_x, middle_y + leg_length)
            right_leg_top_screen = grid.world_to_screen(*right_leg_top)
            right_leg_bottom_screen = grid.world_to_screen(*right_leg_bottom)
            draw_round_line(screen, color_a, right_leg_top_screen,
                           right_leg_bottom_screen, int(GRID_SPACING * 0.4 * grid.scale), 0.15)
            # Bridge
            bridge_top = (middle_x, middle_y - GRID_SPACING * 0.51)
            bridge_bottom = (middle_x, middle_y + GRID_SPACING * 0.51)
        else:  # Vertical orientation
            top_y = middle_y - GRID_SPACING
            bottom_y = middle_y + GRID_SPACING

            # Legs
            leg_length = GRID_SPACING * 0.51
            # Top leg
            top_leg_left = (middle_x - leg_length, top_y)
            top_leg_right = (middle_x + leg_length, top_y)
            top_leg_left_screen = grid.world_to_screen(*top_leg_left)
            top_leg_right_screen = grid.world_to_screen(*top_leg_right)
            draw_round_line(screen, color_a, top_leg_left_screen,
                           top_leg_right_screen, int(GRID_SPACING * 0.4 * grid.scale), 0.15)
            # Bottom leg
            bottom_leg_left = (middle_x - leg_length, bottom_y)
            bottom_leg_right = (middle_x + leg_length, bottom_y)
            bottom_leg_left_screen = grid.world_to_screen(*bottom_leg_left)
            bottom_leg_right_screen = grid.world_to_screen(*bottom_leg_right)
            draw_round_line(screen, color_a, bottom_leg_left_screen,
                           bottom_leg_right_screen, int(GRID_SPACING * 0.4 * grid.scale), 0.15)
            # Bridge
            bridge_left = (middle_x - GRID_SPACING * 0.51, middle_y)
            bridge_right = (middle_x + GRID_SPACING * 0.51, middle_y)

        if self.orientation == 'horizontal':
            bridge_left_screen = grid.world_to_screen(*bridge_top)
            bridge_right_screen = grid.world_to_screen(*bridge_bottom)
            draw_round_line(screen, color_b, bridge_left_screen, bridge_right_screen,
                           int(GRID_SPACING * 0.8 * grid.scale), 0.15)
        else:
            bridge_left_screen = grid.world_to_screen(*bridge_left)
            bridge_right_screen = grid.world_to_screen(*bridge_right)
            draw_round_line(screen, color_b, bridge_left_screen, bridge_right_screen,
                           int(GRID_SPACING * 0.8 * grid.scale), 0.15)

    def is_hovered(self, grid, mouse_pos):
        screen_x, screen_y = grid.world_to_screen(*self.position)
        mouse_x, mouse_y = mouse_pos
        distance = math.hypot(screen_x - mouse_x, screen_y - mouse_y)
        return distance < (GRID_SPACING * 0.5 * grid.scale)  # Threshold based on transistor size


class Clock:
    def __init__(self, position, frequency=CLOCK_FREQUENCY):
        self.position = position  # (x, y)
        self.state = False  # False = OFF, True = ON
        self.frequency = frequency  # Toggles per 144 frames
        self.frame_counter = 0  # Counter to track frames

    def draw(self, grid, is_hovered=False):
        screen_x, screen_y = grid.world_to_screen(*self.position)
        size = int(GRID_SPACING * 0.6 * grid.scale)
        side_distance = int(GRID_SPACING * 0.45 * grid.scale)
        length = int(GRID_SPACING * 0.4 * grid.scale)
        side_length = int(GRID_SPACING * 0.35 * grid.scale)
        
        color = CLOCK_COLOR if self.state else DARK_GREY
        color2 = DARK_GREY if self.state else CLOCK_COLOR
        if is_hovered:
            color = LIGHTER_WHITE
        
        # Draw a square (clock)
        draw_round_line(screen, color, (screen_x, screen_y-length), (screen_x, screen_y+length), size, 0.15)
        draw_round_line(screen, color2, (screen_x-side_distance, screen_y-side_length), (screen_x-side_distance, screen_y+side_length), size/4, 0.5)
        draw_round_line(screen, color2, (screen_x+side_distance, screen_y-side_length), (screen_x+side_distance, screen_y+side_length), size/4, 0.5)

    def update(self):
        self.frame_counter += 1
        toggle_interval = self.frequency#144 // self.frequency if self.frequency != 0 else 144
        if self.frame_counter >= toggle_interval:
            self.state = not self.state
            self.frame_counter = 0

    def is_hovered(self, grid, mouse_pos):
        screen_x, screen_y = grid.world_to_screen(*self.position)
        mouse_x, mouse_y = mouse_pos
        distance = math.hypot(screen_x - mouse_x, screen_y - mouse_y)
        return distance < (IO_POINT_SIZE * grid.scale)  # Threshold based on IO size


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
        iter = 0
        while True:
            if iter > 10000:
                print("SOLVING CIRCUIT TOOK TOO LONG")
                break
            iter += 1
            graph = self.build_connectivity_graph()
            input_nodes = [node.position for node in self.nodes if node.node_type == 'input' and node.state]
            # Include Clock states as input nodes
            clock_on_points = [clock.position for clock in self.clocks if clock.state]
            all_input_points = input_nodes + clock_on_points
            self.on_points = self.propagate_signals(graph, all_input_points)

            current_states = (self.on_points, tuple(transistor.state for transistor in self.transistors))
            if current_states == previous_states or current_states == previous_previous_states:
                if current_states == previous_previous_states:
                    print("CIRCUIT OSSCILATION DETECTED!")
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
