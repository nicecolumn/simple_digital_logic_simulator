from OpenGL.GL import *
from OpenGL.GLU import *
import pygame
import numpy as np
import math
from constants import *
import ctypes

# Shader source code
vertex_shader_source = """
#version 330 core
layout(location = 0) in vec2 position;
layout(location = 1) in vec4 color;
uniform mat4 projection;
out vec4 vertexColor;
void main()
{
    gl_Position = projection * vec4(position, 0.0, 1.0);
    vertexColor = color;
}
"""

fragment_shader_source = """
#version 330 core
in vec4 vertexColor;
out vec4 FragColor;
void main()
{
    FragColor = vertexColor;
}
"""

# Shader source code for textures
texture_vertex_shader_source = """
#version 330 core
layout(location = 0) in vec2 position;
layout(location = 1) in vec2 texCoord;
uniform mat4 projection;
out vec2 TexCoord;
void main()
{
    gl_Position = projection * vec4(position, 0.0, 1.0);
    TexCoord = texCoord;
}
"""

texture_fragment_shader_source = """
#version 330 core
in vec2 TexCoord;
out vec4 FragColor;
uniform sampler2D textTexture;
void main()
{
    FragColor = texture(textTexture, TexCoord);
}
"""

def check_gl_errors():
    """Check for OpenGL errors and print them."""
    error = glGetError()
    while error != GL_NO_ERROR:
        error_message = {
            GL_INVALID_ENUM: "GL_INVALID_ENUM",
            GL_INVALID_VALUE: "GL_INVALID_VALUE",
            GL_INVALID_OPERATION: "GL_INVALID_OPERATION",
            GL_STACK_OVERFLOW: "GL_STACK_OVERFLOW",
            GL_STACK_UNDERFLOW: "GL_STACK_UNDERFLOW",
            GL_OUT_OF_MEMORY: "GL_OUT_OF_MEMORY"
        }.get(error, f"Unknown error code: {error}")
        print(f"OpenGL Error: {error_message}")
        error = glGetError()

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
    if glGetShaderiv(shader, GL_COMPILE_STATUS) != GL_TRUE:
        error = glGetShaderInfoLog(shader).decode()
        shader_type_name = "Vertex" if shader_type == GL_VERTEX_SHADER else "Fragment"
        raise RuntimeError(f"{shader_type_name} shader compilation error: {error}")
    return shader

def create_shader_program():
    """
    Creates and links the shader program.

    Returns:
    - int: The linked shader program ID.

    Raises:
    - RuntimeError: If shader linking fails.
    """
    vertex_shader = compile_shader(vertex_shader_source, GL_VERTEX_SHADER)
    fragment_shader = compile_shader(fragment_shader_source, GL_FRAGMENT_SHADER)
    shader_program = glCreateProgram()
    glAttachShader(shader_program, vertex_shader)
    glAttachShader(shader_program, fragment_shader)
    glBindAttribLocation(shader_program, 0, 'position')
    glBindAttribLocation(shader_program, 1, 'color')
    glLinkProgram(shader_program)
    # Check for linking errors
    if glGetProgramiv(shader_program, GL_LINK_STATUS) != GL_TRUE:
        error = glGetProgramInfoLog(shader_program).decode()
        raise RuntimeError(f"Shader program linking error: {error}")
    # Cleanup shaders as they're no longer needed after linking
    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)
    return shader_program

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
    glEnable(GL_POINT_SMOOTH)
    glEnable(GL_LINE_SMOOTH)
    check_gl_errors()

def gl_color(color, alpha=1.0):
    """
    Converts Pygame color (0-255) to OpenGL color (0.0-1.0).

    Parameters:
    - color (tuple): RGB color tuple.
    - alpha (float): Alpha value.

    Returns:
    - tuple: RGBA color tuple with normalized values.
    """
    return (color[0]/255.0, color[1]/255.0, color[2]/255.0, alpha)

def cleanup_textures(renderer):
    """
    Deletes all textures stored in the text texture cache.

    Parameters:
    - renderer (Renderer): The renderer instance.

    Returns:
    - None
    """
    global text_texture_cache
    if renderer.text_texture_cache:
        texture_ids = [item[0] for item in renderer.text_texture_cache.values()]
        glDeleteTextures(texture_ids)
        renderer.text_texture_cache.clear()

class DialogManager:
    def __init__(self, font, big_font, screen_width, screen_height, renderer):
        self.font = font  # Pygame font for regular text
        self.big_font = big_font  # Pygame font for larger text
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.renderer = renderer

    def draw_save_dialog(self, grid, save_filename):
        """
        Draws the Save Circuit dialog using OpenGL.

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

        # Prepare rectangles and colors
        rects = []
        colors = []

        # Dialog background
        rects.append((dialog_x, dialog_y, dialog_width, dialog_height))
        colors.append(DARK_GREY)

        # Save button
        button_width = 70
        button_height = 30
        button_x = dialog_x + 220
        button_y = dialog_y + 50

        rects.append((button_x, button_y, button_width, button_height))
        colors.append(GREY)

        # Draw filled rectangles
        self.renderer.add_rectangles(rects, colors)

        # Draw borders
        self.renderer.draw_outlined_rect(dialog_x, dialog_y, dialog_width, dialog_height, WHITE, line_width=2)
        self.renderer.draw_outlined_rect(dialog_x + 10, dialog_y + 50, 200, 30, WHITE, line_width=2)
        self.renderer.draw_outlined_rect(button_x, button_y, button_width, button_height, WHITE, line_width=2)

        # Draw texts
        # Label text
        label_text = "Save Circuit"
        texture_id, text_width, text_height = self.renderer.load_text_texture(label_text, self.big_font, WHITE)
        self.renderer.draw_textured_quad(dialog_x + 10, dialog_y + 10, text_width, text_height, texture_id)

        # Input text
        input_text = save_filename
        texture_id, text_width, text_height = self.renderer.load_text_texture(input_text, self.font, WHITE)
        self.renderer.draw_textured_quad(dialog_x + 15, dialog_y + 55, text_width, text_height, texture_id)

        # Button text
        button_text = "Save"
        texture_id, text_width, text_height = self.renderer.load_text_texture(button_text, self.font, BLACK)
        text_x = button_x + (button_width - text_width) / 2
        text_y = button_y + (button_height - text_height) / 2
        self.renderer.draw_textured_quad(text_x, text_y, text_width, text_height, texture_id)

    def draw_load_dialog(self, grid, load_files, load_scroll_offset, load_selection_index):
        """
        Draws the Load Circuit dialog using OpenGL.

        Parameters:
        - grid (Grid): The Grid object for coordinate transformations.
        - load_files (list): List of filenames available for loading.
        - load_scroll_offset (int): Current scroll offset for the file list.
        - load_selection_index (int): Currently selected file index.

        Returns:
        - None
        """
        # Define dialog area
        dialog_width = self.screen_width - 40
        dialog_height = self.screen_height - 60
        dialog_x = 20
        dialog_y = 20

        # Prepare rectangles and colors
        rects = []
        colors = []

        # Dialog background
        rects.append((dialog_x, dialog_y, dialog_width, dialog_height))
        colors.append(DARK_GREY)

        # File list entries
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

            rects.append((file_rect_x, file_rect_y, file_rect_width, file_rect_height))
            colors.append(color)

            # File entry border
            self.renderer.draw_outlined_rect(file_rect_x, file_rect_y, file_rect_width, file_rect_height, WHITE, line_width=1)

            # File name text
            file_text = file
            texture_id, text_width, text_height = self.renderer.load_text_texture(file_text, self.font, WHITE)
            self.renderer.draw_textured_quad(file_rect_x + 5, file_rect_y + 5, text_width, text_height, texture_id)

        # Load button
        button_width = 100
        button_height = 40
        button_x = dialog_x + dialog_width - button_width - 20
        button_y = dialog_y + dialog_height - button_height - 20

        rects.append((button_x, button_y, button_width, button_height))
        colors.append(GREY)

        # Draw filled rectangles
        self.renderer.add_rectangles(rects, colors)

        # Draw borders
        self.renderer.draw_outlined_rect(dialog_x, dialog_y, dialog_width, dialog_height, WHITE, line_width=2)
        self.renderer.draw_outlined_rect(button_x, button_y, button_width, button_height, WHITE, line_width=2)

        # Draw label text
        label_text = "Load Circuit"
        texture_id, text_width, text_height = self.renderer.load_text_texture(label_text, self.big_font, WHITE)
        self.renderer.draw_textured_quad(dialog_x + 10, dialog_y + 10, text_width, text_height, texture_id)

        # Draw button text
        button_text = "Load"
        texture_id, text_width, text_height = self.renderer.load_text_texture(button_text, self.font, BLACK)
        text_x = button_x + (button_width - text_width) / 2
        text_y = button_y + (button_height - text_height) / 2
        self.renderer.draw_textured_quad(text_x, text_y, text_width, text_height, texture_id)

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

class Renderer:
    def __init__(self, screen_width, screen_height):
        # Initialize fonts
        pygame.font.init()
        self.font = pygame.font.SysFont(None, 24)  # Regular font
        self.big_font = pygame.font.SysFont(None, 36)  # Larger font

        # Initialize OpenGL
        init_opengl(screen_width, screen_height)
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Create shader program
        self.shader_program = create_shader_program()
        self.projection_loc = glGetUniformLocation(self.shader_program, 'projection')

        # Create texture shader program
        self.texture_shader_program = self.create_texture_shader_program()
        self.texture_projection_loc = glGetUniformLocation(self.texture_shader_program, 'projection')

        # Create projection matrix
        self.projection_matrix = self.create_orthographic_matrix(0, screen_width, screen_height, 0, -1, 1)

        # Prepare buffers for triangles
        self.max_vertices = 10000  # Adjust as needed
        self.triangle_vertex_data = np.zeros(self.max_vertices, dtype=[('position', np.float32, 2), ('color', np.float32, 4)])
        self.triangle_vertex_count = 0

        # Create VAO and VBO for triangles
        self.triangle_vao = glGenVertexArrays(1)
        self.triangle_vbo = glGenBuffers(1)

        # Initialize VAO and VBO for triangles
        glBindVertexArray(self.triangle_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.triangle_vbo)
        glBufferData(GL_ARRAY_BUFFER, self.triangle_vertex_data.nbytes, None, GL_DYNAMIC_DRAW)

        # Set up vertex attribute pointers
        stride = self.triangle_vertex_data.strides[0]
        offset = ctypes.c_void_p(0)

        # Position attribute
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, offset)

        # Color attribute
        offset = ctypes.c_void_p(self.triangle_vertex_data.dtype.fields['color'][1])
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, stride, offset)

        glBindVertexArray(0)

        # Prepare buffers for points
        self.max_points = 10000
        self.point_vertex_data = np.zeros(self.max_points, dtype=[('position', np.float32, 2), ('color', np.float32, 4)])
        self.point_vertex_count = 0

        # Create VAO and VBO for points
        self.point_vao = glGenVertexArrays(1)
        self.point_vbo = glGenBuffers(1)

        # Initialize VAO and VBO for points
        glBindVertexArray(self.point_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.point_vbo)
        glBufferData(GL_ARRAY_BUFFER, self.point_vertex_data.nbytes, None, GL_DYNAMIC_DRAW)

        # Set up vertex attribute pointers
        stride = self.point_vertex_data.strides[0]
        offset = ctypes.c_void_p(0)

        # Position attribute
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, offset)

        # Color attribute
        offset = ctypes.c_void_p(self.point_vertex_data.dtype.fields['color'][1])
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, stride, offset)

        glBindVertexArray(0)

        # Prepare buffers for lines
        self.line_vertex_data = np.zeros(self.max_vertices, dtype=[('position', np.float32, 2), ('color', np.float32, 4)])
        self.line_vertex_count = 0

        # Create VAO and VBO for lines
        self.line_vao = glGenVertexArrays(1)
        self.line_vbo = glGenBuffers(1)

        # Initialize VAO and VBO for lines
        glBindVertexArray(self.line_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.line_vbo)
        glBufferData(GL_ARRAY_BUFFER, self.line_vertex_data.nbytes, None, GL_DYNAMIC_DRAW)

        # Set up vertex attribute pointers
        stride = self.line_vertex_data.strides[0]
        offset = ctypes.c_void_p(0)

        # Position attribute
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, offset)

        # Color attribute
        offset = ctypes.c_void_p(self.line_vertex_data.dtype.fields['color'][1])
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, stride, offset)

        glBindVertexArray(0)

        # Initialize VAO and VBO for textured quads
        self.textured_quad_vao = glGenVertexArrays(1)
        self.textured_quad_vbo = glGenBuffers(1)

        glBindVertexArray(self.textured_quad_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.textured_quad_vbo)
        glBufferData(GL_ARRAY_BUFFER, 4 * 4 * ctypes.sizeof(ctypes.c_float), None, GL_DYNAMIC_DRAW)  # 4 vertices, each with position and texCoord

        # Set up vertex attribute pointers
        stride = 4 * ctypes.sizeof(ctypes.c_float)  # 2 position floats + 2 texCoord floats
        offset = ctypes.c_void_p(0)

        # Position attribute
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, offset)

        # TexCoord attribute
        offset = ctypes.c_void_p(2 * ctypes.sizeof(ctypes.c_float))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, offset)

        glBindVertexArray(0)

        # Initialize Dialog Manager
        self.dialog_manager = DialogManager(self.font, self.big_font, screen_width, screen_height, self)

        # Texture handling for text rendering
        self.text_texture_cache = {}

        # Default line width
        self.line_width = 1.0

        check_gl_errors()

    def create_texture_shader_program(self):
        vertex_shader = compile_shader(texture_vertex_shader_source, GL_VERTEX_SHADER)
        fragment_shader = compile_shader(texture_fragment_shader_source, GL_FRAGMENT_SHADER)
        shader_program = glCreateProgram()
        glAttachShader(shader_program, vertex_shader)
        glAttachShader(shader_program, fragment_shader)
        glBindAttribLocation(shader_program, 0, 'position')
        glBindAttribLocation(shader_program, 1, 'texCoord')
        glLinkProgram(shader_program)
        # Check for linking errors
        if glGetProgramiv(shader_program, GL_LINK_STATUS) != GL_TRUE:
            error = glGetProgramInfoLog(shader_program).decode()
            raise RuntimeError(f"Texture shader program linking error: {error}")
        # Cleanup shaders as they're no longer needed after linking
        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)
        return shader_program

    def create_orthographic_matrix(self, left, right, bottom, top, near, far):
        """
        Creates an orthographic projection matrix.
        """
        matrix = np.zeros((4, 4), dtype=np.float32)
        matrix[0][0] = 2 / (right - left)
        matrix[1][1] = 2 / (top - bottom)
        matrix[2][2] = -2 / (far - near)
        matrix[3][3] = 1
        matrix[3][0] = -(right + left) / (right - left)
        matrix[3][1] = -(top + bottom) / (top - bottom)
        matrix[3][2] = -(far + near) / (far - near)
        check_gl_errors()
        return matrix

    def begin(self):
        """
        Prepares for rendering by resetting the vertex counts.
        """
        self.triangle_vertex_count = 0
        self.point_vertex_count = 0
        self.line_vertex_count = 0

    def add_vertices(self, positions, colors):
        """
        Adds vertices to the triangle batch.

        Parameters:
        - positions (numpy.ndarray): Array of shape (N, 2) containing vertex positions.
        - colors (numpy.ndarray): Array of shape (N, 4) containing vertex colors.

        Returns:
        - None
        """
        num_vertices = len(positions)
        if self.triangle_vertex_count + num_vertices > self.max_vertices:
            self.end()
            self.begin()
            if num_vertices > self.max_vertices:
                raise ValueError("Too many vertices to batch.")

        # Ensure colors have exactly 4 components
        if colors.shape[1] != 4:
            raise ValueError(f"Colors array must have 4 components per vertex, got {colors.shape[1]}.")

        self.triangle_vertex_data['position'][self.triangle_vertex_count:self.triangle_vertex_count + num_vertices] = positions
        self.triangle_vertex_data['color'][self.triangle_vertex_count:self.triangle_vertex_count + num_vertices] = colors
        self.triangle_vertex_count += num_vertices
        check_gl_errors()

    def add_points(self, positions, colors):
        """
        Adds points to the point batch.

        Parameters:
        - positions (numpy.ndarray): Array of shape (N, 2) containing point positions.
        - colors (numpy.ndarray): Array of shape (N, 4) containing point colors.

        Returns:
        - None
        """
        num_points = len(positions)
        if self.point_vertex_count + num_points > self.max_points:
            self.end()
            self.begin()
            if num_points > self.max_points:
                raise ValueError("Too many points to batch.")

        # Ensure colors have exactly 4 components
        if colors.shape[1] != 4:
            raise ValueError(f"Colors array must have 4 components per point, got {colors.shape[1]}.")

        self.point_vertex_data['position'][self.point_vertex_count:self.point_vertex_count + num_points] = positions
        self.point_vertex_data['color'][self.point_vertex_count:self.point_vertex_count + num_points] = colors
        self.point_vertex_count += num_points
        check_gl_errors()

    def add_lines(self, positions, colors):
        """
        Adds lines to the line batch.

        Parameters:
        - positions (numpy.ndarray): Array of shape (N, 2) containing line vertex positions.
        - colors (numpy.ndarray): Array of shape (N, 4) containing vertex colors.

        Returns:
        - None
        """
        num_vertices = len(positions)
        if self.line_vertex_count + num_vertices > self.max_vertices:
            self.end()
            self.begin()
            if num_vertices > self.max_vertices:
                raise ValueError("Too many vertices to batch.")

        # Ensure colors have exactly 4 components
        if colors.shape[1] != 4:
            raise ValueError(f"Colors array must have 4 components per vertex, got {colors.shape[1]}.")

        self.line_vertex_data['position'][self.line_vertex_count:self.line_vertex_count + num_vertices] = positions
        self.line_vertex_data['color'][self.line_vertex_count:self.line_vertex_count + num_vertices] = colors
        self.line_vertex_count += num_vertices
        check_gl_errors()

    def add_rectangles(self, rects, colors):
        """
        Adds multiple filled rectangles to the triangle batch.

        Parameters:
        - rects (list): List of rectangles, each defined as (x, y, width, height).
        - colors (list): List of colors corresponding to each rectangle.

        Returns:
        - None
        """
        for rect, color in zip(rects, colors):
            x, y, width, height = rect
            vertices = [
                [x, y],
                [x + width, y],
                [x + width, y + height],

                [x + width, y + height],
                [x, y + height],
                [x, y],
            ]
            positions = np.array(vertices, dtype=np.float32)
            # Normalize color components
            color_rgba = [c / 255.0 for c in color[:3]] + [color[3] / 255.0 if len(color) > 3 else 1.0]
            colors_array = np.array([color_rgba] * 6, dtype=np.float32)

            self.add_vertices(positions, colors_array)
        check_gl_errors()

    def end(self):
        """
        Finalizes rendering by uploading vertex data and issuing the draw calls.
        """
        glUseProgram(self.shader_program)
        glUniformMatrix4fv(self.projection_loc, 1, GL_FALSE, self.projection_matrix)

        # Draw triangles
        if self.triangle_vertex_count > 0:
            glBindVertexArray(self.triangle_vao)
            glBindBuffer(GL_ARRAY_BUFFER, self.triangle_vbo)
            glBufferSubData(GL_ARRAY_BUFFER, 0, self.triangle_vertex_count * self.triangle_vertex_data.dtype.itemsize, self.triangle_vertex_data[:self.triangle_vertex_count])
            glDrawArrays(GL_TRIANGLES, 0, self.triangle_vertex_count)
            glBindVertexArray(0)

        # Draw points
        if self.point_vertex_count > 0:
            glBindVertexArray(self.point_vao)
            glBindBuffer(GL_ARRAY_BUFFER, self.point_vbo)
            glBufferSubData(GL_ARRAY_BUFFER, 0, self.point_vertex_count * self.point_vertex_data.dtype.itemsize, self.point_vertex_data[:self.point_vertex_count])
            glDrawArrays(GL_POINTS, 0, self.point_vertex_count)
            glBindVertexArray(0)

        # Draw lines
        if self.line_vertex_count > 0:
            glLineWidth(self.line_width)
            glBindVertexArray(self.line_vao)
            glBindBuffer(GL_ARRAY_BUFFER, self.line_vbo)
            glBufferSubData(GL_ARRAY_BUFFER, 0, self.line_vertex_count * self.line_vertex_data.dtype.itemsize, self.line_vertex_data[:self.line_vertex_count])
            glDrawArrays(GL_LINES, 0, self.line_vertex_count)
            glBindVertexArray(0)

        glUseProgram(0)
        check_gl_errors()

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
        # **Disable vertical flipping by setting flipped=False**
        text_data = pygame.image.tostring(text_surface, "RGBA", False)  # Changed from True to False
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

    def draw_textured_quad(self, x, y, width, height, texture_id):
        """
        Draws a textured quad at the specified position using modern OpenGL.

        Parameters:
        - x (float): Top-left X coordinate.
        - y (float): Top-left Y coordinate.
        - width (float): Width of the quad.
        - height (float): Height of the quad.
        - texture_id (int): OpenGL texture ID.

        Returns:
        - None
        """
        # Vertex data: position and texCoord
        vertices = [
            # Position       # TexCoord
            [x, y,            0.0, 0.0],
            [x + width, y,    1.0, 0.0],
            [x + width, y + height, 1.0, 1.0],
            [x, y + height,   0.0, 1.0],
        ]
        vertices = np.array(vertices, dtype=np.float32)

        # Bind the texture shader program
        glUseProgram(self.texture_shader_program)
        glUniformMatrix4fv(self.texture_projection_loc, 1, GL_FALSE, self.projection_matrix)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glUniform1i(glGetUniformLocation(self.texture_shader_program, 'textTexture'), 0)

        glBindVertexArray(self.textured_quad_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.textured_quad_vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, vertices.nbytes, vertices)

        glDrawArrays(GL_TRIANGLE_FAN, 0, 4)

        glBindVertexArray(0)
        glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)
        check_gl_errors()

    def draw_outlined_rect(self, x, y, width, height, color, line_width=2):
        """
        Draws an outlined rectangle using batched lines.

        Parameters:
        - x (float): Top-left X coordinate.
        - y (float): Top-left Y coordinate.
        - width (float): Width of the rectangle.
        - height (float): Height of the rectangle.
        - color (tuple): RGB or RGBA color tuple.
        - line_width (float): Width of the outline.

        Returns:
        - None
        """
        # Line vertices
        vertices = [
            [x, y],
            [x + width, y],

            [x + width, y],
            [x + width, y + height],

            [x + width, y + height],
            [x, y + height],

            [x, y + height],
            [x, y],
        ]
        positions = np.array(vertices, dtype=np.float32)
        # Normalize color components
        color_rgba = [c / 255.0 for c in color[:3]] + [color[3] / 255.0 if len(color) > 3 else 1.0]
        colors_array = np.array([color_rgba] * 8, dtype=np.float32)

        # Set line width
        self.line_width = line_width

        self.add_lines(positions, colors_array)

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

        self.begin()

        # Draw grid
        grid.draw(self)
        #self.end()

        #self.begin()

        # Draw Transistors
        for transistor in circuit.transistors:
            is_hovered = transistor.is_hovered(grid, mouse_pos)
            transistor.add_vertices_to_batch(self, grid, is_hovered)

        # Draw Clocks
        for clock in circuit.clocks:
            is_hovered = clock.is_hovered(grid, mouse_pos)
            clock.add_vertices_to_batch(self, grid, is_hovered)

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
            color = [0.5, 0.5, 0.5, 0.4]
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

            self.add_vertices(positions, colors_array)

            # Border
            self.draw_outlined_rect(left, top, width, height, GREY, line_width=1)

        self.end()

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
        check_gl_errors()

    def cleanup(self):
        """
        Cleans up all cached textures to free GPU memory.

        Parameters:
        - None

        Returns:
        - None
        """
        cleanup_textures(self)
        glDeleteProgram(self.shader_program)
        glDeleteProgram(self.texture_shader_program)
        glDeleteBuffers(1, [self.triangle_vbo])
        glDeleteVertexArrays(1, [self.triangle_vao])
        glDeleteBuffers(1, [self.point_vbo])
        glDeleteVertexArrays(1, [self.point_vao])
        glDeleteBuffers(1, [self.line_vbo])
        glDeleteVertexArrays(1, [self.line_vao])
        glDeleteBuffers(1, [self.textured_quad_vbo])
        glDeleteVertexArrays(1, [self.textured_quad_vao])

