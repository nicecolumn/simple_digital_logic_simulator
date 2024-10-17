import math
import numpy as np

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