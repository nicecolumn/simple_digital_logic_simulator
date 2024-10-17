import pygame
import math
import numpy as np

# # Function to draw a line with rounded corners
# def draw_round_line(surface, color, start, end, width, radius):
#     """
#     Draws a rounded rectangle (like a thick line with rounded ends) between two points.

#     Parameters:
#     - surface (pygame.Surface): The surface to draw on.
#     - color (tuple): The RGB color of the rectangle, e.g., (255, 0, 0) for red.
#     - start (tuple): The starting point (x, y) of the rectangle.
#     - end (tuple): The ending point (x, y) of the rectangle.
#     - width (int): The thickness of the rectangle.
#     - radius (float): The proportion of the width to use as radius.

#     Returns:
#     - None
#     """
#     # Calculate the difference in coordinates
#     dx = end[0] - start[0]
#     dy = end[1] - start[1]

#     # Calculate the distance between start and end points
#     distance = math.hypot(dx, dy)
#     if distance == 0:
#         # Avoid drawing if start and end points are the same
#         return

#     # Calculate the angle in degrees. Negative dy because Pygame's y-axis is inverted
#     angle = math.degrees(math.atan2(-dy, dx))

#     # Create a surface for the rectangle with per-pixel alpha
#     rect_surface = pygame.Surface((distance, width), pygame.SRCALPHA)

#     radius_px = min(int(width / 2), int(width * radius))

#     # Draw the rounded rectangle on the temporary surface
#     pygame.draw.rect(
#         rect_surface,
#         color,
#         pygame.Rect(0, 0, distance, width),
#         border_radius=radius_px
#     )

#     # Rotate the rectangle surface to align with the angle between start and end
#     rotated_surface = pygame.transform.rotate(rect_surface, angle)

#     # Get the rotated surface's rectangle and set its center to the midpoint between start and end
#     rotated_rect = rotated_surface.get_rect()

#     # Calculate midpoint
#     mid_x = (start[0] + end[0]) / 2
#     mid_y = (start[1] + end[1]) / 2

#     # Calculate the top-left position to blit the rotated surface so that it's centered at the midpoint
#     blit_position = (mid_x - rotated_rect.width / 2, mid_y - rotated_rect.height / 2)

#     # Blit the rotated surface onto the target surface at the calculated position
#     surface.blit(rotated_surface, blit_position)


def draw_rounded_rect(renderer, point1, point2, color, width, radius):
    x1, y1 = point1
    x2, y2 = point2

    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return  # Avoid division by zero

    px = -dy / length
    py = dx / length

    half_width = width / 2
    # Define the four corners of the thick line as two triangles
    vertices = [
        [x2 + px * half_width, y2 + py * half_width],
        [x2 - px * half_width, y2 - py * half_width],
        [x1 - px * half_width, y1 - py * half_width],
        [x1 + px * half_width, y1 + py * half_width]
    ]

    edges = [
        [vertices[0], vertices[1]],
        [vertices[1], vertices[2]],
        [vertices[2], vertices[3]],
        [vertices[3], vertices[0]]
    ]

    for edge in edges:
        draw_rounded_line(renderer, edge[0], edge[1], color, radius)


    draw_line(renderer, point1, point2, color, width)


def draw_rounded_line(renderer, point1, point2, color, width):
    radius = width /2

    point1 = list(point1)
    point2 = list(point2)

    # if point2[1] > point1[1]:
    #     point2[1] -= radius
    #     point1[1] += radius
    # else:
    #     point2[1] += radius
    #     point1[1] -= radius

    draw_line(renderer, point1, point2, color, width)
    draw_circle(renderer, point1[0], point1[1], color, radius)
    draw_circle(renderer, point2[0], point2[1], color, radius)


def draw_line(renderer, point1, point2, color, width):
    x1, y1 = point1
    x2, y2 = point2

    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return  # Avoid division by zero

    px = -dy / length
    py = dx / length

    half_width = width / 2
    # Define the four corners of the thick line as two triangles
    vertices = [
        [x1 + px * half_width, y1 + py * half_width],
        [x2 + px * half_width, y2 + py * half_width],
        [x2 - px * half_width, y2 - py * half_width],

        [x2 - px * half_width, y2 - py * half_width],
        [x1 - px * half_width, y1 - py * half_width],
        [x1 + px * half_width, y1 + py * half_width],
    ]

    # Define colors for each vertex
    color_rgba = [c / 255.0 for c in color[:3]] + [1.0]
    colors_rgba = [color_rgba] * 6
    colors_array = np.array(colors_rgba, dtype=np.float32)

    positions = np.array(vertices, dtype=np.float32)

    renderer.add_vertices(positions, colors_array)

def draw_circle(renderer, screen_x, screen_y, color, radius):
    # Define a circle using triangles (triangle fan)
    #segments = max(6, int(radius))  # Adjust number of segments based on radius
    segments = 6
    angle_increment = 2 * math.pi / segments
    vertices = []
    colors_rgba = []

    # Center vertex
    vertices.append([screen_x, screen_y])
    colors_rgba.append([c / 255.0 for c in color[:3]] + [1.0])

    for i in range(segments + 1):
        angle = i * angle_increment
        x = screen_x + math.cos(angle) * radius
        y = screen_y + math.sin(angle) * radius
        vertices.append([x, y])
        colors_rgba.append([c / 255.0 for c in color[:3]] + [1.0])

    # Create triangles (triangle fan)
    triangles = []
    for i in range(1, len(vertices) - 1):
        triangles.extend([vertices[0], vertices[i], vertices[i + 1]])

    positions = np.array(triangles, dtype=np.float32)
    # Assign the same color to each vertex
    colors_array = np.array([colors_rgba[0]] * len(triangles), dtype=np.float32)

    renderer.add_vertices(positions, colors_array)