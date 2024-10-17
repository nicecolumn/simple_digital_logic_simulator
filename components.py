
import math
import numpy as np
import pygame
from constants import *
from utils import *

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

    def draw(self, renderer):
        # Compute the world coordinates of the screen edges
        world_left = self.offset_x
        world_right = (self.width / self.scale) + self.offset_x
        world_top = self.offset_y
        world_bottom = (self.height / self.scale) + self.offset_y

        # Compute grid points
        grid_x_start = int(math.floor(world_left / GRID_SPACING) * GRID_SPACING)
        grid_x_end = int(math.ceil(world_right / GRID_SPACING) * GRID_SPACING)
        grid_y_start = int(math.floor(world_top / GRID_SPACING) * GRID_SPACING)
        grid_y_end = int(math.ceil(world_bottom / GRID_SPACING) * GRID_SPACING)

        num_grid_x = int((grid_x_end - grid_x_start) / GRID_SPACING) + 1
        num_grid_y = int((grid_y_end - grid_y_start) / GRID_SPACING) + 1


        # Background
        positions = np.array([[0.0, 0.0], [0.0, self.height], [self.width, self.height]])
        bg = [c / 255.0 for c in BACKGROUND_COLOR[:3]] + [1.0]
        bg = [bg for _ in range(len(positions))]
        bg = np.array(bg).astype(np.float32)
        renderer.add_vertices(positions, bg)
        
        positions = np.array([[0.0, 0.0], [self.width, 0.0], [self.width, self.height]])
        bg = [c / 255.0 for c in BACKGROUND_COLOR[:3]] + [1.0]
        bg = [bg for _ in range(len(positions))]
        bg = np.array(bg).astype(np.float32)
        renderer.add_vertices(positions, bg)


        if num_grid_x * num_grid_y < MAX_GRID_POINTS:
            positions = []
            colors = []
            color = [c / 255.0 for c in GRID_POINT_COLOR][:3] + [1.0]
            for x in range(grid_x_start, grid_x_end + GRID_SPACING, GRID_SPACING):
                for y in range(grid_y_start, grid_y_end + GRID_SPACING, GRID_SPACING):
                    screen_x, screen_y = self.world_to_screen(x, y)
                    if 0 <= screen_x < self.width and 0 <= screen_y < self.height:
                        positions.append([screen_x, screen_y])
                        colors.append(color)

            if positions:
                positions = np.array(positions, dtype=np.float32)
                colors = np.array(colors, dtype=np.float32)
                renderer.add_points(positions, colors)

class Wire:
    def __init__(self, start_point, end_point):
        self.start_point = start_point  # (x, y)
        self.end_point = end_point      # (x, y)
        self.state = False  # False = OFF, True = ON
        self.is_selected = False

    def add_vertices_to_batch(self, renderer, grid, is_hovered=False):
        color = W_ON if self.state else W_OFF

        if is_hovered or self.is_selected:
            color = tuple(min(255, c + 5) for c in color)

        start_x, start_y = grid.world_to_screen(*self.start_point)
        end_x, end_y = grid.world_to_screen(*self.end_point)
        wire_width = max(1, int(WIRE_SIZE * grid.scale))

        #draw_rounded_line(renderer, (start_x, start_y), (end_x, end_y), color, wire_width)
        draw_line(renderer, (start_x, start_y), (end_x, end_y), color, wire_width)

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
        self.is_selected = False

    def add_vertices_to_batch(self, renderer, grid, is_hovered=False):
        screen_x, screen_y = grid.world_to_screen(*self.position)
        radius = max(1, int(IO_POINT_SIZE * grid.scale))
        #radius = grid.scale * IO_POINT_SIZE
        color = YELLOW if self.state else WHITE
        if is_hovered or self.is_selected:
            color = tuple(min(255, c + 50) for c in color)

        draw_circle(renderer, screen_x, screen_y, color, radius)

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
        self.state = False if transistor_type == 'n-type' else False  # False = OFF, True = ON
        self.transistor_type = transistor_type  # 'n-type' or 'p-type'
        self.orientation = orientation  # 'horizontal' or 'vertical'
        self.is_selected = False

    def rotate(self):
        if self.orientation == 'horizontal':
            self.orientation = 'vertical'
        else:
            self.orientation = 'horizontal'

    def add_vertices_to_batch(self, renderer, grid, is_hovered=False):
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

        if is_hovered or self.is_selected:
            color_a = tuple(min(255, c + 5) for c in color_a)
            color_b = tuple(min(255, c + 5) for c in color_b)

        middle_x, middle_y = self.position
        grid_spacing_scaled = GRID_SPACING * grid.scale
        leg_length = GRID_SPACING * 0.51

        if self.orientation == 'horizontal':
            left_x = middle_x - GRID_SPACING
            right_x = middle_x + GRID_SPACING

            # Left leg
            left_leg_top = (left_x, middle_y - leg_length)
            left_leg_bottom = (left_x, middle_y + leg_length)
            left_leg_top_screen = grid.world_to_screen(*left_leg_top)
            left_leg_bottom_screen = grid.world_to_screen(*left_leg_bottom)
            self.add_rectangle(renderer, left_leg_top_screen, left_leg_bottom_screen, color_a, grid)

            # Right leg
            right_leg_top = (right_x, middle_y - leg_length)
            right_leg_bottom = (right_x, middle_y + leg_length)
            right_leg_top_screen = grid.world_to_screen(*right_leg_top)
            right_leg_bottom_screen = grid.world_to_screen(*right_leg_bottom)
            self.add_rectangle(renderer, right_leg_top_screen, right_leg_bottom_screen, color_a, grid)

            # Bridge
            bridge_top = (middle_x, middle_y - GRID_SPACING * 0.51)
            bridge_bottom = (middle_x, middle_y + GRID_SPACING * 0.51)
            bridge_top_screen = grid.world_to_screen(*bridge_top)
            bridge_bottom_screen = grid.world_to_screen(*bridge_bottom)
            self.add_rectangle(renderer, bridge_top_screen, bridge_bottom_screen, color_b, grid, wide=True)
        else:  # Vertical orientation
            top_y = middle_y - GRID_SPACING
            bottom_y = middle_y + GRID_SPACING

            # Top leg
            top_leg_left = (middle_x - leg_length, top_y)
            top_leg_right = (middle_x + leg_length, top_y)
            top_leg_left_screen = grid.world_to_screen(*top_leg_left)
            top_leg_right_screen = grid.world_to_screen(*top_leg_right)
            self.add_rectangle(renderer, top_leg_left_screen, top_leg_right_screen, color_a, grid)

            # Bottom leg
            bottom_leg_left = (middle_x - leg_length, bottom_y)
            bottom_leg_right = (middle_x + leg_length, bottom_y)
            bottom_leg_left_screen = grid.world_to_screen(*bottom_leg_left)
            bottom_leg_right_screen = grid.world_to_screen(*bottom_leg_right)
            self.add_rectangle(renderer, bottom_leg_left_screen, bottom_leg_right_screen, color_a, grid)

            # Bridge
            bridge_left = (middle_x - GRID_SPACING * 0.51, middle_y)
            bridge_right = (middle_x + GRID_SPACING * 0.51, middle_y)
            bridge_left_screen = grid.world_to_screen(*bridge_left)
            bridge_right_screen = grid.world_to_screen(*bridge_right)
            self.add_rectangle(renderer, bridge_left_screen, bridge_right_screen, color_b, grid, wide=True)

    def add_rectangle(self, renderer, point1, point2, color, grid, wide=False):
        if wide:
            width = GRID_SPACING * 0.8 * grid.scale
        else:
            width = GRID_SPACING * 0.4 * grid.scale
        #draw_rounded_rect(renderer, point1, point2, color, width, 10*grid.scale)
        draw_line(renderer, point1, point2, color, width)

    def is_hovered(self, grid, mouse_pos):
        screen_x, screen_y = grid.world_to_screen(*self.position)
        mouse_x, mouse_y = mouse_pos
        distance = math.hypot(screen_x - mouse_x, screen_y - mouse_y)
        return distance < (GRID_SPACING * 0.5 * grid.scale)  # Threshold based on transistor size

class Clock:
    def __init__(self, position, frequency=CLOCK_FREQUENCY):
        self.position = position  # (x, y)
        self.state = False  # False = OFF, True = ON
        self.frequency = frequency
        self.frame_counter = 0  # Counter to track frames
        self.is_selected = False

    def add_vertices_to_batch(self, renderer, grid, is_hovered=False):
        screen_x, screen_y = grid.world_to_screen(*self.position)
        size = max(1, int(GRID_SPACING * 0.5 * grid.scale))
        side_distance = max(1, int(GRID_SPACING * 0.45 * grid.scale))
        length = max(1, int(GRID_SPACING * 0.4 * grid.scale))
        side_length = max(1, int(GRID_SPACING * 0.35 * grid.scale))

        color = CLOCK_COLOR
        color2 = DARK_GREY
        if is_hovered or self.is_selected:
            color = tuple(min(255, c + 20) for c in color)
            color2 = tuple(min(255, c + 20) for c in color2)

        # Main vertical line
        self.add_rectangle(renderer, (screen_x, screen_y - length), (screen_x, screen_y + length), color, grid, width=size)

        # Left side line
        self.add_rectangle(renderer, (screen_x - side_distance, screen_y - side_length),
                           (screen_x - side_distance, screen_y + side_length), color2, grid, width=size / 4)

        # Right side line
        self.add_rectangle(renderer, (screen_x + side_distance, screen_y - side_length),
                           (screen_x + side_distance, screen_y + side_length), color2, grid, width=size / 4)

    def add_rectangle(self, renderer, point1, point2, color, grid, width):
        draw_rounded_rect(renderer, point1, point2, color, width, 10*grid.scale)

    def update(self):
        self.frame_counter += 1
        toggle_interval = self.frequency
        if self.frame_counter >= toggle_interval:
            self.state = not self.state
            self.frame_counter = 0

    def is_hovered(self, grid, mouse_pos):
        screen_x, screen_y = grid.world_to_screen(*self.position)
        mouse_x, mouse_y = mouse_pos
        distance = math.hypot(screen_x - mouse_x, screen_y - mouse_y)
        return distance < (IO_POINT_SIZE * grid.scale)  # Threshold based on clock size