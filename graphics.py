# graphics.py

from OpenGL.GL import *
from OpenGL.GLU import *
import pygame
import numpy as np
import math
import ctypes
from constants import WHITE, BLACK, RED, GREEN, BLUE, GREY, DARK_GREY, LIGHTER_GREY  # Ensure constants.py is correctly set up

# ------------------------------------------
# Shader Source Codes for Colored Rendering
# ------------------------------------------

# Vertex Shader: Processes vertex positions and colors
vertex_shader_colored_source = """
#version 330 core
layout(location = 0) in vec2 position;  // Vertex position
layout(location = 1) in vec4 color;     // Vertex color
uniform mat4 projection;                // Orthographic projection matrix
out vec4 vertexColor;                    // Passed to fragment shader

void main()
{
    gl_Position = projection * vec4(position, 0.0, 1.0);
    vertexColor = color;
}
"""

# Fragment Shader: Outputs the interpolated color
fragment_shader_colored_source = """
#version 330 core
in vec4 vertexColor;    // Received from vertex shader
out vec4 FragColor;     // Final pixel color

void main()
{
    FragColor = vertexColor;
}
"""

# ------------------------------------------
# Shader Source Codes for Textured Rendering
# ------------------------------------------

# Vertex Shader: Processes vertex positions and texture coordinates
vertex_shader_textured_source = """
#version 330 core
layout(location = 0) in vec2 position;    // Vertex position
layout(location = 1) in vec2 texCoord;    // Texture coordinate
uniform mat4 projection;                  // Orthographic projection matrix
out vec2 v_texCoord;                      // Passed to fragment shader

void main()
{
    gl_Position = projection * vec4(position, 0.0, 1.0);
    v_texCoord = texCoord;
}
"""

# Fragment Shader: Samples the texture and outputs the color
fragment_shader_textured_source = """
#version 330 core
in vec2 v_texCoord;      // Received from vertex shader
out vec4 FragColor;      // Final pixel color
uniform sampler2D textTexture; // Texture sampler

void main()
{
    FragColor = texture(textTexture, v_texCoord);
}
"""

# ------------------------------------------
# Shader Compilation and Program Linking
# ------------------------------------------

def compile_shader(source, shader_type):
    """
    Compiles a shader of a given type.

    Parameters:
    - source (str): The GLSL source code for the shader.
    - shader_type (GLenum): The type of shader (e.g., GL_VERTEX_SHADER).

    Returns:
    - int: The compiled shader ID.

    Raises:
    - RuntimeError: If shader compilation fails.
    """
    shader = glCreateShader(shader_type)
    glShaderSource(shader, source)
    glCompileShader(shader)

    # Check for compilation errors
    compile_success = glGetShaderiv(shader, GL_COMPILE_STATUS)
    if not compile_success:
        error = glGetShaderInfoLog(shader).decode()
        shader_type_name = "Vertex" if shader_type == GL_VERTEX_SHADER else "Fragment"
        print(f"{shader_type_name} shader compilation error: {error}")
        raise RuntimeError(f"{shader_type_name} shader compilation error")

    return shader

def create_shader_program(vertex_source, fragment_source):
    """
    Creates and links a shader program.

    Parameters:
    - vertex_source (str): Vertex shader source code.
    - fragment_source (str): Fragment shader source code.

    Returns:
    - int: The linked shader program ID.

    Raises:
    - RuntimeError: If shader linking fails.
    """
    vertex_shader = compile_shader(vertex_source, GL_VERTEX_SHADER)
    fragment_shader = compile_shader(fragment_source, GL_FRAGMENT_SHADER)

    shader_program = glCreateProgram()
    glAttachShader(shader_program, vertex_shader)
    glAttachShader(shader_program, fragment_shader)
    glLinkProgram(shader_program)

    # Check for linking errors
    link_success = glGetProgramiv(shader_program, GL_LINK_STATUS)
    if not link_success:
        error = glGetProgramInfoLog(shader_program).decode()
        print(f"Shader program linking error: {error}")
        raise RuntimeError("Shader program linking error")

    # Shaders can be deleted after linking
    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)

    return shader_program

# ------------------------------------------
# OpenGL Initialization Function
# ------------------------------------------

def init_opengl(width, height):
    """
    Initializes OpenGL settings.

    Parameters:
    - width (int): Width of the display.
    - height (int): Height of the display.

    Returns:
    - None
    """
    glViewport(0, 0, width, height)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glPointSize(2.0)
    glLineWidth(1.0)
    glDisable(GL_DEPTH_TEST)

# ------------------------------------------
# Renderer Class for Handling OpenGL Rendering
# ------------------------------------------

class Renderer:
    def __init__(self, screen_width, screen_height):
        """
        Initializes the Renderer by setting up shaders, buffers, and projection.

        Parameters:
        - screen_width (int): Width of the display window.
        - screen_height (int): Height of the display window.
        """
        # Initialize fonts
        pygame.font.init()
        self.font = pygame.font.SysFont(None, 24)      # Regular font
        self.big_font = pygame.font.SysFont(None, 36)  # Larger font

        # Initialize OpenGL
        init_opengl(screen_width, screen_height)
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Create shader programs
        self.colored_shader = create_shader_program(vertex_shader_colored_source, fragment_shader_colored_source)
        self.textured_shader = create_shader_program(vertex_shader_textured_source, fragment_shader_textured_source)

        # Get uniform locations
        self.colored_projection_loc = glGetUniformLocation(self.colored_shader, 'projection')
        self.textured_projection_loc = glGetUniformLocation(self.textured_shader, 'projection')
        self.textured_sampler_loc = glGetUniformLocation(self.textured_shader, 'textTexture')

        # Create projection matrix (orthographic)
        self.projection_matrix = self.create_orthographic_matrix(0, screen_width, screen_height, 0, -1, 1)

        # --------------------------
        # Setup for Colored Rendering
        # --------------------------

        # Prepare buffers for colored triangles (e.g., wires, nodes, transistors, clocks, filled rectangles)
        self.max_colored_vertices = 1000000  # Adjust as needed
        self.colored_vertex_data = np.zeros(self.max_colored_vertices, dtype=[('position', np.float32, 2), ('color', np.float32, 4)])
        self.colored_vertex_count = 0

        # Create VAO and VBO for colored rendering
        self.colored_vao = glGenVertexArrays(1)
        self.colored_vbo = glGenBuffers(1)

        glBindVertexArray(self.colored_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.colored_vbo)
        glBufferData(GL_ARRAY_BUFFER, self.colored_vertex_data.nbytes, None, GL_DYNAMIC_DRAW)

        # Set up vertex attribute pointers
        stride = self.colored_vertex_data.strides[0]
        offset = ctypes.c_void_p(0)

        # Position attribute
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(
            0, 2, GL_FLOAT, GL_FALSE,
            stride, offset
        )

        # Color attribute - Fixing the color offset
        color_offset = ctypes.c_void_p(self.colored_vertex_data.dtype.fields['color'][1])
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(
            1, 4, GL_FLOAT, GL_FALSE,
            stride, color_offset
        )

        glBindVertexArray(0)

        # ----------------------------
        # Setup for Points Rendering
        # ----------------------------

        # Prepare buffers for points (e.g., grid points)
        self.max_point_vertices = 1000000  # Adjust as needed
        self.point_vertex_data = np.zeros(self.max_point_vertices, dtype=[('position', np.float32, 2), ('color', np.float32, 4)])
        self.point_vertex_count = 0

        # Create VAO and VBO for points
        self.points_vao = glGenVertexArrays(1)
        self.points_vbo = glGenBuffers(1)

        glBindVertexArray(self.points_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.points_vbo)
        glBufferData(GL_ARRAY_BUFFER, self.point_vertex_data.nbytes, None, GL_DYNAMIC_DRAW)

        # Set up vertex attribute pointers
        stride = self.point_vertex_data.strides[0]
        offset = ctypes.c_void_p(0)

        # Position attribute
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(
            0, 2, GL_FLOAT, GL_FALSE,
            stride, offset
        )

        # Color attribute
        color_offset = ctypes.c_void_p(self.point_vertex_data.dtype.fields['color'][1])
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(
            1, 4, GL_FLOAT, GL_FALSE,
            stride, color_offset
        )

        glBindVertexArray(0)

        # ----------------------------
        # Setup for Textured Rendering
        # ----------------------------

        # Prepare buffers for textured quads (e.g., text in dialogs)
        self.max_textured_vertices = 1000000  # Adjust as needed
        self.textured_vertex_data = np.zeros(self.max_textured_vertices, dtype=[('position', np.float32, 2), ('texCoord', np.float32, 2)])
        self.textured_vertex_count = 0

        # Create VAO and VBO for textured rendering
        self.textured_vao = glGenVertexArrays(1)
        self.textured_vbo = glGenBuffers(1)

        glBindVertexArray(self.textured_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.textured_vbo)
        glBufferData(GL_ARRAY_BUFFER, self.textured_vertex_data.nbytes, None, GL_DYNAMIC_DRAW)

        # Set up vertex attribute pointers
        stride = self.textured_vertex_data.strides[0]
        offset = ctypes.c_void_p(0)

        # Position attribute
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(
            0, 2, GL_FLOAT, GL_FALSE,
            stride, offset
        )

        # TexCoord attribute
        tex_offset = ctypes.c_void_p(self.textured_vertex_data.dtype.fields['texCoord'][1])
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(
            1, 2, GL_FLOAT, GL_FALSE,
            stride, tex_offset
        )

        glBindVertexArray(0)

        # Initialize Dialog Manager
        self.dialog_manager = DialogManager(self.font, self.big_font, screen_width, screen_height, self)

        # Texture handling for text rendering
        self.text_texture_cache = {}

    def create_orthographic_matrix(self, left, right, bottom, top, near, far):
        """
        Creates an orthographic projection matrix.

        Parameters:
        - left, right, bottom, top, near, far (float): Boundaries of the orthographic projection.

        Returns:
        - numpy.ndarray: A 4x4 orthographic projection matrix.
        """
        matrix = np.zeros((4, 4), dtype=np.float32)
        matrix[0][0] = 2.0 / (right - left)
        matrix[1][1] = 2.0 / (top - bottom)
        matrix[2][2] = -2.0 / (far - near)
        matrix[3][3] = 1.0
        matrix[3][0] = -(right + left) / (right - left)
        matrix[3][1] = -(top + bottom) / (top - bottom)
        matrix[3][2] = -(far + near) / (far - near)
        return matrix

    # -------------------------
    # Colored Rendering Methods
    # -------------------------

    def begin_colored_batch(self):
        """
        Prepares the colored batch for rendering by resetting the vertex count.
        """
        self.colored_vertex_count = 0

    def add_colored_vertices(self, positions, colors):
        """
        Adds vertices to the colored triangle batch.

        Parameters:
        - positions (numpy.ndarray): Array of shape (N, 2) containing vertex positions.
        - colors (numpy.ndarray): Array of shape (N, 4) containing vertex colors in 0-255 range.

        Returns:
        - None
        """
        num_vertices = len(positions)
        if self.colored_vertex_count + num_vertices > self.max_colored_vertices:
            self.end_colored_batch()
            self.begin_colored_batch()
            if num_vertices > self.max_colored_vertices:
                raise ValueError("Too many colored vertices to batch.")

        # Debug: Print first few color values
        if self.colored_vertex_count == 0 and num_vertices > 0:
            print("Adding colored vertices with colors:")
            print(colors[:min(5, num_vertices)])

        # Normalize colors
        normalized_colors = colors / 255.0  # Assuming colors are in 0-255 range

        # Ensure colors have exactly 4 components
        if normalized_colors.shape[1] != 4:
            raise ValueError(f"Colors array must have 4 components per vertex, got {normalized_colors.shape[1]}.")

        # Add positions and colors to the buffer
        self.colored_vertex_data['position'][self.colored_vertex_count:self.colored_vertex_count + num_vertices] = positions
        self.colored_vertex_data['color'][self.colored_vertex_count:self.colored_vertex_count + num_vertices] = normalized_colors
        self.colored_vertex_count += num_vertices

    def end_colored_batch(self):
        """
        Finalizes the colored batch by uploading vertex data and issuing the draw call.
        """
        if self.colored_vertex_count == 0:
            return  # Nothing to draw

        glUseProgram(self.colored_shader)
        glUniformMatrix4fv(self.colored_projection_loc, 1, GL_FALSE, self.projection_matrix)

        glBindVertexArray(self.colored_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.colored_vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, self.colored_vertex_count * self.colored_vertex_data.dtype.itemsize,
                        self.colored_vertex_data[:self.colored_vertex_count])
        glDrawArrays(GL_TRIANGLES, 0, self.colored_vertex_count)
        glBindVertexArray(0)

        glUseProgram(0)

    # ------------------------
    # Points Rendering Methods
    # ------------------------

    def begin_points_batch(self):
        """
        Prepares the points batch for rendering by resetting the vertex count.
        """
        self.point_vertex_count = 0

    def add_points(self, positions, colors):
        """
        Adds points to the points batch.

        Parameters:
        - positions (numpy.ndarray): Array of shape (N, 2) containing point positions.
        - colors (numpy.ndarray): Array of shape (N, 4) containing point colors.

        Returns:
        - None
        """
        num_points = len(positions)
        if self.point_vertex_count + num_points > self.max_point_vertices:
            self.end_points_batch()
            self.begin_points_batch()
            if num_points > self.max_point_vertices:
                raise ValueError("Too many points to batch.")

        # Normalize colors
        normalized_colors = colors / 255.0  # Assuming colors are in 0-255 range

        # Ensure colors have exactly 4 components
        if normalized_colors.shape[1] != 4:
            raise ValueError(f"Colors array must have 4 components per point, got {normalized_colors.shape[1]}.")

        # Add positions and colors to the buffer
        self.point_vertex_data['position'][self.point_vertex_count:self.point_vertex_count + num_points] = positions
        self.point_vertex_data['color'][self.point_vertex_count:self.point_vertex_count + num_points] = normalized_colors
        self.point_vertex_count += num_points

    def end_points_batch(self):
        """
        Finalizes the points batch by uploading vertex data and issuing the draw call.
        """
        if self.point_vertex_count == 0:
            return  # Nothing to draw

        glUseProgram(self.colored_shader)
        glUniformMatrix4fv(self.colored_projection_loc, 1, GL_FALSE, self.projection_matrix)

        glBindVertexArray(self.points_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.points_vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, self.point_vertex_count * self.point_vertex_data.dtype.itemsize,
                        self.point_vertex_data[:self.point_vertex_count])
        glDrawArrays(GL_POINTS, 0, self.point_vertex_count)
        glBindVertexArray(0)

        glUseProgram(0)

    # --------------------------
    # Textured Rendering Methods
    # --------------------------

    def begin_textured_batch(self):
        """
        Prepares the textured batch for rendering by resetting the vertex count.
        """
        self.textured_vertex_count = 0

    def add_textured_quad(self, x, y, width, height, texture_id):
        """
        Adds a textured quad to the textured batch.

        Parameters:
        - x (float): Top-left X coordinate.
        - y (float): Top-left Y coordinate.
        - width (float): Width of the quad.
        - height (float): Height of the quad.
        - texture_id (int): OpenGL texture ID to bind.

        Returns:
        - None
        """
        # Define the quad as two triangles with texture coordinates
        vertices = [
            [x, y],
            [x + width, y],
            [x + width, y + height],
            [x + width, y + height],
            [x, y + height],
            [x, y],
        ]
        tex_coords = [
            [0.0, 0.0],
            [1.0, 0.0],
            [1.0, 1.0],
            [1.0, 1.0],
            [0.0, 1.0],
            [0.0, 0.0],
        ]

        positions = np.array(vertices, dtype=np.float32)
        tex_coords = np.array(tex_coords, dtype=np.float32)

        num_vertices = len(positions)
        if self.textured_vertex_count + num_vertices > self.max_textured_vertices:
            self.end_textured_batch()
            self.begin_textured_batch()
            if num_vertices > self.max_textured_vertices:
                raise ValueError("Too many textured vertices to batch.")

        # Add positions and texture coordinates to the buffer
        self.textured_vertex_data['position'][self.textured_vertex_count:self.textured_vertex_count + num_vertices] = positions
        self.textured_vertex_data['texCoord'][self.textured_vertex_count:self.textured_vertex_count + num_vertices] = tex_coords
        self.textured_vertex_count += num_vertices

        # Bind texture
        glBindTexture(GL_TEXTURE_2D, texture_id)

    def end_textured_batch(self):
        """
        Finalizes the textured batch by uploading vertex data and issuing the draw call.
        """
        if self.textured_vertex_count == 0:
            return  # Nothing to draw

        glUseProgram(self.textured_shader)
        glUniformMatrix4fv(self.textured_projection_loc, 1, GL_FALSE, self.projection_matrix)
        glUniform1i(self.textured_sampler_loc, 0)  # Texture unit 0

        glActiveTexture(GL_TEXTURE0)
        # Assuming that each textured quad binds its own texture before adding vertices
        # Hence, textures are already bound correctly

        glBindVertexArray(self.textured_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.textured_vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, self.textured_vertex_count * self.textured_vertex_data.dtype.itemsize,
                        self.textured_vertex_data[:self.textured_vertex_count])
        glDrawArrays(GL_TRIANGLES, 0, self.textured_vertex_count)
        glBindVertexArray(0)

        glUseProgram(0)

    # -------------------
    # Text Rendering Method
    # -------------------

    def load_text_texture(self, text, font, color):
        """
        Renders text to a texture using Pygame and returns the OpenGL texture ID along with its dimensions.

        Parameters:
        - text (str): Text to render.
        - font (pygame.font.Font): Pygame font object.
        - color (tuple): RGB or RGBA color tuple.

        Returns:
        - tuple: (texture_id (int), width (int), height (int))
        """
        cache_key = (text, id(font), font.get_height(), color)
        if cache_key in self.text_texture_cache:
            return self.text_texture_cache[cache_key]

        # Render the text to a Pygame surface
        text_surface = font.render(text, True, color[:3], color[3] if len(color) > 3 else None)
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        width, height = text_surface.get_size()

        # Generate a texture ID
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)

        # Set texture parameters
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

        # Upload the texture data
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        glBindTexture(GL_TEXTURE_2D, 0)  # Unbind the texture
        self.text_texture_cache[cache_key] = (texture_id, width, height)
        return self.text_texture_cache[cache_key]

    # -------------------
    # Main Draw Method
    # -------------------

    def draw(self, grid, circuit, mouse_pos,
             dragging_wire_endpoint=None, is_drawing_wire=False, wire_start_point=None,
             is_selecting=False, selection_start=None, selection_end=None,
             selection_rect_world=None, save_dialog_active=False,
             load_dialog_active=False, save_filename="",
             load_files=[], load_scroll_offset=0, load_selection_index=-1):
        """
        Main draw method to render all components and dialogs using OpenGL.

        Parameters:
        - grid (Grid): The Grid object for coordinate transformations.
        - circuit (object): The circuit containing wires, nodes, transistors, clocks.
        - mouse_pos (tuple): Current mouse position.
        - dragging_wire_endpoint (tuple): Information about the wire being dragged.
        - is_drawing_wire (bool): Whether a wire is being drawn.
        - wire_start_point (tuple): Starting point of the wire being drawn.
        - is_selecting (bool): Whether a selection box is active.
        - selection_start (tuple): Starting point of the selection.
        - selection_end (tuple): Ending point of the selection.
        - selection_rect_world (pygame.Rect): Selection rectangle in world coordinates.
        - save_dialog_active (bool): Whether the save dialog is active.
        - load_dialog_active (bool): Whether the load dialog is active.
        - save_filename (str): Current filename in the save input box.
        - load_files (list): List of filenames available for loading.
        - load_scroll_offset (int): Current scroll offset for the load file list.
        - load_selection_index (int): Currently selected file index.

        Returns:
        - None
        """
        # Clear screen
        glClearColor(0.0, 0.0, 0.0, 1.0)  # Black background
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # -----------------------
        # Render Colored Elements
        # -----------------------
        self.begin_colored_batch()

        # Draw grid
        grid.draw(self)

        # Draw Wires
        for wire in circuit.wires:
            is_hovered = wire.is_hovered(grid, mouse_pos)
            if dragging_wire_endpoint and wire == dragging_wire_endpoint[0]:
                is_hovered = True
            wire.add_vertices_to_batch(self, grid, is_hovered)

        # Draw Nodes
        for node in circuit.nodes:
            is_hovered = node.is_hovered(grid, mouse_pos)
            node.add_vertices_to_batch(self, grid, is_hovered)

        # Draw Transistors
        for transistor in circuit.transistors:
            is_hovered = transistor.is_hovered(grid, mouse_pos)
            transistor.add_vertices_to_batch(self, grid, is_hovered)

        # Draw Clocks
        for clock in circuit.clocks:
            is_hovered = clock.is_hovered(grid, mouse_pos)
            clock.add_vertices_to_batch(self, grid, is_hovered)

        # Draw temporary wire if drawing
        if is_drawing_wire and wire_start_point:
            # Calculate the end point snapped to grid
            mouse_x, mouse_y = mouse_pos
            world_x, world_y = grid.screen_to_world(mouse_x, mouse_y)
            grid_x = round(world_x / GRID_SPACING) * GRID_SPACING
            grid_y = round(world_y / GRID_SPACING) * GRID_SPACING
            end_point = (grid_x, grid_y)

            start_x, start_y = grid.world_to_screen(*wire_start_point)
            end_x, end_y = grid.world_to_screen(*end_point)

            if (start_x, start_y) != (end_x, end_y):
                # Define a temporary wire with white color
                color = WHITE
                wire_width = int(WIRE_SIZE * grid.scale)

                # Calculate the direction and perpendicular vectors
                dx = end_x - start_x
                dy = end_y - start_y
                length = math.hypot(dx, dy)
                if length != 0:
                    px = -dy / length
                    py = dx / length

                    half_width = wire_width / 2
                    vertices = [
                        [start_x + px * half_width, start_y + py * half_width],
                        [end_x + px * half_width, end_y + py * half_width],
                        [end_x - px * half_width, end_y - py * half_width],

                        [end_x - px * half_width, end_y - py * half_width],
                        [start_x - px * half_width, start_y - py * half_width],
                        [start_x + px * half_width, start_y + py * half_width],
                    ]

                    # Normalize color
                    color_rgba = [c / 255.0 for c in color[:3]] + [1.0]
                    colors_array = np.array([color_rgba] * 6, dtype=np.float32)

                    positions = np.array(vertices, dtype=np.float32)

                    self.add_colored_vertices(positions, colors_array)

        # Draw selection box if selecting
        if is_selecting and selection_start and selection_end:
            x1, y1 = selection_start
            x2, y2 = selection_end
            screen_x1, screen_y1 = grid.world_to_screen(x1, y1)
            screen_x2, screen_y2 = grid.world_to_screen(x2, y2)
            left = min(screen_x1, screen_x2)
            top = min(screen_y1, screen_y2)
            width = abs(screen_x2 - screen_x1)
            height = abs(screen_y2 - screen_y1)

            # Semi-transparent grey rectangle
            color = [128/255.0, 128/255.0, 128/255.0, 0.4]
            vertices = [
                [left, top],
                [left + width, top],
                [left + width, top + height],

                [left + width, top + height],
                [left, top + height],
                [left, top],
            ]
            positions = np.array(vertices, dtype=np.float32)
            colors_array = np.array([color] * 6, dtype=np.float32)

            self.add_colored_vertices(positions, colors_array)

            # Border using colored vertices (solid GREY)
            border_color = [GREY[0]/255.0, GREY[1]/255.0, GREY[2]/255.0, GREY[3]/255.0]
            border_vertices = [
                [left, top],
                [left + width, top],
                [left + width, top + height],
                [left + width, top + height],
                [left, top + height],
                [left, top],
            ]
            border_positions = np.array(border_vertices, dtype=np.float32)
            border_colors = np.array([border_color] * 6, dtype=np.float32)

            self.add_colored_vertices(border_positions, border_colors)

        # End and draw the colored batch
        self.end_colored_batch()

        # ------------------------
        # Render Points Elements
        # ------------------------
        self.begin_points_batch()

        # Note: If there are any point-based elements besides the grid, add them here.

        # End and draw the points batch
        self.end_points_batch()

        # --------------------------
        # Render Textured Elements
        # --------------------------
        self.begin_textured_batch()

        # Draw Save and Load Dialogs
        self.dialog_manager.draw_dialogs(
            grid,
            save_dialog_active,
            load_dialog_active,
            save_filename,
            load_files,
            load_scroll_offset,
            load_selection_index
        )

        # End and draw the textured batch
        self.end_textured_batch()

    def cleanup(self):
        """
        Cleans up all cached textures and OpenGL resources to free GPU memory.

        Parameters:
        - None

        Returns:
        - None
        """
        # Delete text textures
        if self.text_texture_cache:
            texture_ids = [item[0] for item in self.text_texture_cache.values()]
            glDeleteTextures(texture_ids)
            self.text_texture_cache.clear()

        # Delete shader programs
        glDeleteProgram(self.colored_shader)
        glDeleteProgram(self.textured_shader)

        # Delete buffers and VAOs for colored rendering
        glDeleteBuffers(1, [self.colored_vbo])
        glDeleteVertexArrays(1, [self.colored_vao])

        # Delete buffers and VAOs for points rendering
        glDeleteBuffers(1, [self.points_vbo])
        glDeleteVertexArrays(1, [self.points_vao])

        # Delete buffers and VAOs for textured rendering
        glDeleteBuffers(1, [self.textured_vbo])
        glDeleteVertexArrays(1, [self.textured_vao])

        print("Cleaned up OpenGL resources.")

# ------------------------------------------
# DialogManager Class for Handling Dialogs
# ------------------------------------------

class DialogManager:
    def __init__(self, font, big_font, screen_width, screen_height, renderer):
        self.font = font                      # Pygame font for regular text
        self.big_font = big_font              # Pygame font for larger text
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.renderer = renderer              # Renderer instance

    def draw_save_dialog(self, grid, save_filename):
        """
        Draws the Save Circuit dialog using the Renderer.

        Parameters:
        - grid (Grid): The Grid object for coordinate transformations.
        - save_filename (str): The current filename in the input box.

        Returns:
        - None
        """
        # Define dialog area
        dialog_width = 300
        dialog_height = 100
        dialog_x = 20
        dialog_y = self.screen_height - dialog_height - 20

        # Draw dialog background
        self.renderer.add_colored_vertices(
            positions=np.array([
                [dialog_x, dialog_y],
                [dialog_x + dialog_width, dialog_y],
                [dialog_x + dialog_width, dialog_y + dialog_height],
                [dialog_x + dialog_width, dialog_y + dialog_height],
                [dialog_x, dialog_y + dialog_height],
                [dialog_x, dialog_y],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in DARK_GREY[:3]] + [DARK_GREY[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Draw borders
        # Top Border
        self.renderer.add_colored_vertices(
            positions=np.array([
                [dialog_x, dialog_y],
                [dialog_x + dialog_width, dialog_y],
                [dialog_x + dialog_width, dialog_y + 2],
                [dialog_x + dialog_width, dialog_y + 2],
                [dialog_x, dialog_y + 2],
                [dialog_x, dialog_y],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in WHITE[:3]] + [WHITE[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Bottom Border
        self.renderer.add_colored_vertices(
            positions=np.array([
                [dialog_x, dialog_y + dialog_height - 2],
                [dialog_x + dialog_width, dialog_y + dialog_height - 2],
                [dialog_x + dialog_width, dialog_y + dialog_height],
                [dialog_x + dialog_width, dialog_y + dialog_height],
                [dialog_x, dialog_y + dialog_height],
                [dialog_x, dialog_y + dialog_height - 2],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in WHITE[:3]] + [WHITE[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Left Border
        self.renderer.add_colored_vertices(
            positions=np.array([
                [dialog_x, dialog_y],
                [dialog_x + 2, dialog_y],
                [dialog_x + 2, dialog_y + dialog_height],
                [dialog_x + 2, dialog_y + dialog_height],
                [dialog_x, dialog_y + dialog_height],
                [dialog_x, dialog_y],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in WHITE[:3]] + [WHITE[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Right Border
        self.renderer.add_colored_vertices(
            positions=np.array([
                [dialog_x + dialog_width - 2, dialog_y],
                [dialog_x + dialog_width, dialog_y],
                [dialog_x + dialog_width, dialog_y + dialog_height],
                [dialog_x + dialog_width, dialog_y + dialog_height],
                [dialog_x + dialog_width - 2, dialog_y + dialog_height],
                [dialog_x + dialog_width - 2, dialog_y],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in WHITE[:3]] + [WHITE[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Draw input box background
        input_box_x = dialog_x + 10
        input_box_y = dialog_y + 50
        input_box_width = 200
        input_box_height = 30

        self.renderer.add_colored_vertices(
            positions=np.array([
                [input_box_x, input_box_y],
                [input_box_x + input_box_width, input_box_y],
                [input_box_x + input_box_width, input_box_y + input_box_height],
                [input_box_x + input_box_width, input_box_y + input_box_height],
                [input_box_x, input_box_y + input_box_height],
                [input_box_x, input_box_y],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in BLACK[:3]] + [BLACK[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Draw input box border
        self.renderer.add_colored_vertices(
            positions=np.array([
                [input_box_x, input_box_y],
                [input_box_x + input_box_width, input_box_y],
                [input_box_x + input_box_width, input_box_y + input_box_height],
                [input_box_x + input_box_width, input_box_y + input_box_height],
                [input_box_x, input_box_y + input_box_height],
                [input_box_x, input_box_y],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in WHITE[:3]] + [WHITE[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Draw "Save" button background
        button_width = 70
        button_height = 30
        button_x = dialog_x + 220
        button_y = dialog_y + 50

        self.renderer.add_colored_vertices(
            positions=np.array([
                [button_x, button_y],
                [button_x + button_width, button_y],
                [button_x + button_width, button_y + button_height],
                [button_x + button_width, button_y + button_height],
                [button_x, button_y + button_height],
                [button_x, button_y],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in GREY[:3]] + [GREY[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Draw "Save" button border
        self.renderer.add_colored_vertices(
            positions=np.array([
                [button_x, button_y],
                [button_x + button_width, button_y],
                [button_x + button_width, button_y + button_height],
                [button_x + button_width, button_y + button_height],
                [button_x, button_y + button_height],
                [button_x, button_y],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in WHITE[:3]] + [WHITE[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Draw texts using Renderer (textured quads)
        # Label text
        label_text = "Save Circuit"
        texture_id, text_width, text_height = self.renderer.load_text_texture(label_text, self.big_font, WHITE)
        self.renderer.add_textured_quad(dialog_x + 10, dialog_y + 10, text_width, text_height, texture_id)

        # Input text
        input_text = save_filename if save_filename else "Enter filename..."
        texture_id, text_width, text_height = self.renderer.load_text_texture(input_text, self.font, WHITE)
        self.renderer.add_textured_quad(input_box_x + 5, input_box_y + 5, text_width, text_height, texture_id)

        # Button text
        button_text = "Save"
        texture_id, text_width, text_height = self.renderer.load_text_texture(button_text, self.font, BLACK)
        text_x = button_x + (button_width - text_width) / 2
        text_y = button_y + (button_height - text_height) / 2
        self.renderer.add_textured_quad(text_x, text_y, text_width, text_height, texture_id)

    def draw_load_dialog(self, grid, load_files, load_scroll_offset, load_selection_index):
        """
        Draws the Load Circuit dialog using the Renderer.

        Parameters:
        - grid (Grid): The Grid object for coordinate transformations.
        - load_files (list): List of filenames available for loading.
        - load_scroll_offset (int): Current scroll offset for the load file list.
        - load_selection_index (int): Currently selected file index.

        Returns:
        - None
        """
        # Define dialog area
        dialog_width = self.screen_width - 40
        dialog_height = self.screen_height - 60
        dialog_x = 20
        dialog_y = 20

        # Draw dialog background
        self.renderer.add_colored_vertices(
            positions=np.array([
                [dialog_x, dialog_y],
                [dialog_x + dialog_width, dialog_y],
                [dialog_x + dialog_width, dialog_y + dialog_height],
                [dialog_x + dialog_width, dialog_y + dialog_height],
                [dialog_x, dialog_y + dialog_height],
                [dialog_x, dialog_y],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in DARK_GREY[:3]] + [DARK_GREY[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Draw borders
        # Top Border
        self.renderer.add_colored_vertices(
            positions=np.array([
                [dialog_x, dialog_y],
                [dialog_x + dialog_width, dialog_y],
                [dialog_x + dialog_width, dialog_y + 2],
                [dialog_x + dialog_width, dialog_y + 2],
                [dialog_x, dialog_y + 2],
                [dialog_x, dialog_y],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in WHITE[:3]] + [WHITE[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Bottom Border
        self.renderer.add_colored_vertices(
            positions=np.array([
                [dialog_x, dialog_y + dialog_height - 2],
                [dialog_x + dialog_width, dialog_y + dialog_height - 2],
                [dialog_x + dialog_width, dialog_y + dialog_height],
                [dialog_x + dialog_width, dialog_y + dialog_height],
                [dialog_x, dialog_y + dialog_height],
                [dialog_x, dialog_y + dialog_height - 2],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in WHITE[:3]] + [WHITE[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Left Border
        self.renderer.add_colored_vertices(
            positions=np.array([
                [dialog_x, dialog_y],
                [dialog_x + 2, dialog_y],
                [dialog_x + 2, dialog_y + dialog_height],
                [dialog_x + 2, dialog_y + dialog_height],
                [dialog_x, dialog_y + dialog_height],
                [dialog_x, dialog_y],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in WHITE[:3]] + [WHITE[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Right Border
        self.renderer.add_colored_vertices(
            positions=np.array([
                [dialog_x + dialog_width - 2, dialog_y],
                [dialog_x + dialog_width, dialog_y],
                [dialog_x + dialog_width, dialog_y + dialog_height],
                [dialog_x + dialog_width, dialog_y + dialog_height],
                [dialog_x + dialog_width - 2, dialog_y + dialog_height],
                [dialog_x + dialog_width - 2, dialog_y],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in WHITE[:3]] + [WHITE[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Draw file list entries
        list_x = dialog_x + 10
        list_y = dialog_y + 50
        item_height = 30
        max_visible = int((dialog_height - 70) / item_height)
        visible_files = load_files[load_scroll_offset:load_scroll_offset + max_visible]

        for index, file in enumerate(visible_files):
            actual_index = index + load_scroll_offset
            file_rect_x = list_x
            file_rect_y = list_y + index * item_height
            file_rect_width = dialog_width - 20
            file_rect_height = item_height

            if actual_index == load_selection_index:
                color = LIGHTER_GREY
            else:
                color = DARK_GREY

            # Draw file entry background
            self.renderer.add_colored_vertices(
                positions=np.array([
                    [file_rect_x, file_rect_y],
                    [file_rect_x + file_rect_width, file_rect_y],
                    [file_rect_x + file_rect_width, file_rect_y + file_rect_height],
                    [file_rect_x + file_rect_width, file_rect_y + file_rect_height],
                    [file_rect_x, file_rect_y + file_rect_height],
                    [file_rect_x, file_rect_y],
                ], dtype=np.float32),
                colors=np.array([
                    [c / 255.0 for c in color[:3]] + [color[3] / 255.0] for _ in range(6)
                ], dtype=np.float32)
            )

            # Draw file entry border
            self.renderer.add_colored_vertices(
                positions=np.array([
                    [file_rect_x, file_rect_y],
                    [file_rect_x + file_rect_width, file_rect_y],
                    [file_rect_x + file_rect_width, file_rect_y + file_rect_height],
                    [file_rect_x + file_rect_width, file_rect_y + file_rect_height],
                    [file_rect_x, file_rect_y + file_rect_height],
                    [file_rect_x, file_rect_y],
                ], dtype=np.float32),
                colors=np.array([
                    [c / 255.0 for c in WHITE[:3]] + [WHITE[3] / 255.0] for _ in range(6)
                ], dtype=np.float32)
            )

            # Draw file name text
            file_text = file
            texture_id, text_width, text_height = self.renderer.load_text_texture(file_text, self.font, WHITE)
            self.renderer.add_textured_quad(file_rect_x + 5, file_rect_y + 5, text_width, text_height, texture_id)

        # Draw "Load" button background
        button_width = 100
        button_height = 40
        button_x = dialog_x + dialog_width - button_width - 20
        button_y = dialog_y + dialog_height - button_height - 20

        self.renderer.add_colored_vertices(
            positions=np.array([
                [button_x, button_y],
                [button_x + button_width, button_y],
                [button_x + button_width, button_y + button_height],
                [button_x + button_width, button_y + button_height],
                [button_x, button_y + button_height],
                [button_x, button_y],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in GREY[:3]] + [GREY[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Draw "Load" button border
        self.renderer.add_colored_vertices(
            positions=np.array([
                [button_x, button_y],
                [button_x + button_width, button_y],
                [button_x + button_width, button_y + button_height],
                [button_x + button_width, button_y + button_height],
                [button_x, button_y + button_height],
                [button_x, button_y],
            ], dtype=np.float32),
            colors=np.array([
                [c / 255.0 for c in WHITE[:3]] + [WHITE[3] / 255.0] for _ in range(6)
            ], dtype=np.float32)
        )

        # Draw label text
        label_text = "Load Circuit"
        texture_id, text_width, text_height = self.renderer.load_text_texture(label_text, self.big_font, WHITE)
        self.renderer.add_textured_quad(dialog_x + 10, dialog_y + 10, text_width, text_height, texture_id)

        # Draw "Load" button text
        button_text = "Load"
        texture_id, text_width, text_height = self.renderer.load_text_texture(button_text, self.font, BLACK)
        text_x = button_x + (button_width - text_width) / 2
        text_y = button_y + (button_height - text_height) / 2
        self.renderer.add_textured_quad(text_x, text_y, text_width, text_height, texture_id)

    def draw_dialogs(self, grid, save_dialog_active, load_dialog_active,
                     save_filename="", load_files=[], load_scroll_offset=0, load_selection_index=-1):
        """
        Draws active dialogs based on the current state.

        Parameters:
        - grid (Grid): The Grid object for coordinate transformations.
        - save_dialog_active (bool): Whether the save dialog is active.
        - load_dialog_active (bool): Whether the load dialog is active.
        - save_filename (str): Current filename in the save input box.
        - load_files (list): List of filenames available for loading.
        - load_scroll_offset (int): Current scroll offset for the load file list.
        - load_selection_index (int): Currently selected file index.

        Returns:
        - None
        """
        if save_dialog_active:
            self.draw_save_dialog(grid, save_filename)
        if load_dialog_active:
            self.draw_load_dialog(grid, load_files, load_scroll_offset, load_selection_index)

# ------------------------------------------
# Utility Functions (if any)
# ------------------------------------------

def draw_textured_quad(renderer, x, y, width, height, texture_id):
    """
    Draws a textured quad at the specified position using the Renderer.

    Parameters:
    - renderer (Renderer): The renderer instance.
    - x (float): Top-left X coordinate.
    - y (float): Top-left Y coordinate.
    - width (float): Width of the quad.
    - height (float): Height of the quad.
    - texture_id (int): OpenGL texture ID.

    Returns:
    - None
    """
    renderer.add_textured_quad(x, y, width, height, texture_id)

def draw_outlined_rect(renderer, x, y, width, height, color, line_width=2):
    """
    Draws an outlined rectangle using the Renderer.

    Parameters:
    - renderer (Renderer): The renderer instance.
    - x (float): Top-left X coordinate.
    - y (float): Top-left Y coordinate.
    - width (float): Width of the rectangle.
    - height (float): Height of the rectangle.
    - color (tuple): RGB or RGBA color tuple.
    - line_width (float): Width of the outline.

    Returns:
    - None
    """
    # Define the rectangle as two triangles
    vertices = [
        [x, y],
        [x + width, y],
        [x + width, y + height],

        [x + width, y + height],
        [x, y + height],
        [x, y],
    ]
    positions = np.array(vertices, dtype=np.float32)

    # Normalize color
    color_rgba = [c / 255.0 for c in color[:3]] + ([color[3] / 255.0] if len(color) > 3 else [1.0])
    colors_array = np.array([color_rgba] * 6, dtype=np.float32)

    # Add to renderer as colored vertices
    renderer.add_colored_vertices(positions, colors_array)
