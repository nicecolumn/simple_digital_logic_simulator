import pygame
import math

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