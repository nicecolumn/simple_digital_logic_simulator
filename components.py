import math
import pygame
from constants import *
from OpenGL.GL import *
from OpenGL.GLU import *

# Initialize OpenGL settings
def init_opengl(width, height):
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    # Set up orthographic projection to match Pygame's coordinate system
    gluOrtho2D(0, width, height, 0)  # Inverted Y-axis to match Pygame
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glLineWidth(1.0)

# Helper function to convert Pygame color (0-255) to OpenGL color (0.0-1.0)
def gl_color(color):
    return (color[0]/255.0, color[1]/255.0, color[2]/255.0, 1.0)

# Helper function to draw a filled circle using triangle fan
def draw_circle(x, y, radius, color, segments=20):
    glColor4f(*gl_color(color))
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(x, y)
    for i in range(segments + 1):
        angle = 2 * math.pi * i / segments
        glVertex2f(x + math.cos(angle) * radius, y + math.sin(angle) * radius)
    glEnd()

# Helper function to draw a thick line with rounded ends
def draw_round_line(x1, y1, x2, y2, width, color):
    glColor4f(*gl_color(color))
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return
    angle = math.atan2(dy, dx)

    # Calculate perpendicular vector
    px = -dy / length
    py = dx / length

    # Calculate the four corners of the thick line
    half_width = width / 2
    x1a = x1 + px * half_width
    y1a = y1 + py * half_width
    x1b = x1 - px * half_width
    y1b = y1 - py * half_width
    x2a = x2 + px * half_width
    y2a = y2 + py * half_width
    x2b = x2 - px * half_width
    y2b = y2 - py * half_width

    # Draw the rectangle part of the thick line
    glBegin(GL_QUADS)
    glVertex2f(x1a, y1a)
    glVertex2f(x1b, y1b)
    glVertex2f(x2b, y2b)
    glVertex2f(x2a, y2a)
    glEnd()

    # Draw circles at both ends for rounded caps
    draw_circle(x1, y1, half_width, color)
    draw_circle(x2, y2, half_width, color)

# Classes
class Grid:
    def __init__(self, screen, width, height):
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.is_panning = False
        self.pan_start_pos = (0, 0)
        self.offset_start = (0, 0)
        self.screen = screen
        self.width = width
        self.height = height
        init_opengl(width, height)

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
        world_right = (self.width / self.scale) + self.offset_x
        world_top = self.offset_y
        world_bottom = (self.height / self.scale) + self.offset_y

        # Compute grid lines
        grid_x_start = int(math.floor(world_left / GRID_SPACING) * GRID_SPACING)
        grid_x_end = int(math.ceil(world_right / GRID_SPACING) * GRID_SPACING)
        grid_y_start = int(math.floor(world_top / GRID_SPACING) * GRID_SPACING)
        grid_y_end = int(math.ceil(world_bottom / GRID_SPACING) * GRID_SPACING)

        num_grid_x = int((grid_x_end - grid_x_start) / GRID_SPACING) + 1
        num_grid_y = int((grid_y_end - grid_y_start) / GRID_SPACING) + 1

        if num_grid_x * num_grid_y < MAX_GRID_POINTS:
            glColor4f(*gl_color(GREY))
            glBegin(GL_POINTS)
            for x in range(grid_x_start, grid_x_end + GRID_SPACING, GRID_SPACING):
                for y in range(grid_y_start, grid_y_end + GRID_SPACING, GRID_SPACING):
                    screen_x, screen_y = self.world_to_screen(x, y)
                    if 0 <= screen_x < self.width and 0 <= screen_y < self.height:
                        glVertex2f(screen_x, screen_y)
            glEnd()

class Wire:
    def __init__(self, start_point, end_point):
        self.start_point = start_point  # (x, y)
        self.end_point = end_point      # (x, y)
        self.state = False  # False = OFF, True = ON

    def draw(self, grid, is_hovered=False):
        color = W_ON if self.state else W_OFF

        if is_hovered:
            color = tuple(min(255, c + 50) for c in color)

        start_x, start_y = grid.world_to_screen(*self.start_point)
        end_x, end_y = grid.world_to_screen(*self.end_point)
        wire_width = max(1, int(WIRE_SIZE * grid.scale))

        draw_round_line(start_x, start_y, end_x, end_y, wire_width, color)

    def is_hovered(self, grid, mouse_pos):
        # Check if mouse is close to the wire
        start_x, start_y = grid.world_to_screen(*self.start_point)
        end_x, end_y = grid.world_to_screen(*self.end_point)
        mouse_x, mouse_y = mouse_pos

        # Calculate distance from mouse to the wire line
        if start_x == end_x and start_y == end_y:
            distance = math.hypot(mouse_x - start_x, mouse_y - start_y)
            return distance <= HOVER_RADIUS * grid.scale
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
            return distance <= HOVER_RADIUS * grid.scale

class Node:
    def __init__(self, position, node_type):
        self.position = position  # (x, y)
        self.node_type = node_type  # 'input' or 'output'
        self.state = False if self.node_type == 'input' else False  # Inputs can toggle

    def draw(self, grid, is_hovered=False):
        screen_x, screen_y = grid.world_to_screen(*self.position)
        radius = int(IO_POINT_SIZE * grid.scale)

        color = YELLOW if self.state else WHITE
        if is_hovered:
            color = LIGHTER_YELLOW if self.state else LIGHTER_WHITE

        # Draw the node as a filled circle
        draw_circle(screen_x, screen_y, radius, color)

        # Note: Text rendering is omitted. Implement text rendering using textures or other methods as needed.

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
            color_a = tuple(min(255, c + 5) for c in color_a)
            color_b = tuple(min(255, c + 5) for c in color_b)

        middle_x, middle_y = self.position
        grid_spacing_scaled = GRID_SPACING * grid.scale
        leg_length = GRID_SPACING * 0.51 * grid.scale

        if self.orientation == 'horizontal':
            left_x = middle_x - GRID_SPACING
            right_x = middle_x + GRID_SPACING

            # Left leg
            left_leg_top = (left_x, middle_y - leg_length)
            left_leg_bottom = (left_x, middle_y + leg_length)
            left_leg_top_screen = grid.world_to_screen(*left_leg_top)
            left_leg_bottom_screen = grid.world_to_screen(*left_leg_bottom)
            draw_round_line(left_leg_top_screen[0], left_leg_top_screen[1],
                           left_leg_bottom_screen[0], left_leg_bottom_screen[1],
                           int(GRID_SPACING * 0.4 * grid.scale), color_a)

            # Right leg
            right_leg_top = (right_x, middle_y - leg_length)
            right_leg_bottom = (right_x, middle_y + leg_length)
            right_leg_top_screen = grid.world_to_screen(*right_leg_top)
            right_leg_bottom_screen = grid.world_to_screen(*right_leg_bottom)
            draw_round_line(right_leg_top_screen[0], right_leg_top_screen[1],
                           right_leg_bottom_screen[0], right_leg_bottom_screen[1],
                           int(GRID_SPACING * 0.4 * grid.scale), color_a)

            # Bridge
            bridge_top = (middle_x, middle_y - GRID_SPACING * 0.51)
            bridge_bottom = (middle_x, middle_y + GRID_SPACING * 0.51)
            bridge_top_screen = grid.world_to_screen(*bridge_top)
            bridge_bottom_screen = grid.world_to_screen(*bridge_bottom)
            draw_round_line(bridge_top_screen[0], bridge_top_screen[1],
                           bridge_bottom_screen[0], bridge_bottom_screen[1],
                           int(GRID_SPACING * 0.8 * grid.scale), color_b)
        else:  # Vertical orientation
            top_y = middle_y - GRID_SPACING
            bottom_y = middle_y + GRID_SPACING

            # Top leg
            top_leg_left = (middle_x - leg_length, top_y)
            top_leg_right = (middle_x + leg_length, top_y)
            top_leg_left_screen = grid.world_to_screen(*top_leg_left)
            top_leg_right_screen = grid.world_to_screen(*top_leg_right)
            draw_round_line(top_leg_left_screen[0], top_leg_left_screen[1],
                           top_leg_right_screen[0], top_leg_right_screen[1],
                           int(GRID_SPACING * 0.4 * grid.scale), color_a)

            # Bottom leg
            bottom_leg_left = (middle_x - leg_length, bottom_y)
            bottom_leg_right = (middle_x + leg_length, bottom_y)
            bottom_leg_left_screen = grid.world_to_screen(*bottom_leg_left)
            bottom_leg_right_screen = grid.world_to_screen(*bottom_leg_right)
            draw_round_line(bottom_leg_left_screen[0], bottom_leg_left_screen[1],
                           bottom_leg_right_screen[0], bottom_leg_right_screen[1],
                           int(GRID_SPACING * 0.4 * grid.scale), color_a)

            # Bridge
            bridge_left = (middle_x - GRID_SPACING * 0.51, middle_y)
            bridge_right = (middle_x + GRID_SPACING * 0.51, middle_y)
            bridge_left_screen = grid.world_to_screen(*bridge_left)
            bridge_right_screen = grid.world_to_screen(*bridge_right)
            draw_round_line(bridge_left_screen[0], bridge_left_screen[1],
                           bridge_right_screen[0], bridge_right_screen[1],
                           int(GRID_SPACING * 0.8 * grid.scale), color_b)

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

        # Draw the main vertical line of the clock
        draw_round_line(screen_x, screen_y - length, screen_x, screen_y + length, size, color)

        # Draw the side lines of the clock
        half_side_width = int((size / 4) if (size / 4) > 0 else 1)
        draw_round_line(screen_x - side_distance, screen_y - side_length,
                       screen_x - side_distance, screen_y + side_length, half_side_width, color2)
        draw_round_line(screen_x + side_distance, screen_y - side_length,
                       screen_x + side_distance, screen_y + side_length, half_side_width, color2)

    def update(self):
        self.frame_counter += 1
        toggle_interval = self.frequency  # 144 // self.frequency if self.frequency != 0 else 144
        if self.frame_counter >= toggle_interval:
            self.state = not self.state
            self.frame_counter = 0

    def is_hovered(self, grid, mouse_pos):
        screen_x, screen_y = grid.world_to_screen(*self.position)
        mouse_x, mouse_y = mouse_pos
        distance = math.hypot(screen_x - mouse_x, screen_y - mouse_y)
        return distance < (IO_POINT_SIZE * grid.scale)  # Threshold based on IO size
