# main.py

import pygame
import numpy as np
from OpenGL.GL import *
import ctypes

# constants.py
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
RED = (255, 0, 0, 255)
GREEN = (0, 255, 0, 255)
BLUE = (0, 0, 255, 255)

# Shader source code for solid-colored rendering
vertex_shader_colored_source = """
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

fragment_shader_colored_source = """
#version 330 core
in vec4 vertexColor;
out vec4 FragColor;
void main()
{
    FragColor = vertexColor;
}
"""

def compile_shader(source, shader_type):
    shader = glCreateShader(shader_type)
    glShaderSource(shader, source)
    glCompileShader(shader)
    compile_success = glGetShaderiv(shader, GL_COMPILE_STATUS)
    if not compile_success:
        error = glGetShaderInfoLog(shader).decode()
        shader_type_name = "Vertex" if shader_type == GL_VERTEX_SHADER else "Fragment"
        print(f"{shader_type_name} shader compilation error: {error}")
        raise RuntimeError(f"{shader_type_name} shader compilation error")
    return shader

def create_shader_program(vertex_source, fragment_source):
    vertex_shader = compile_shader(vertex_source, GL_VERTEX_SHADER)
    fragment_shader = compile_shader(fragment_source, GL_FRAGMENT_SHADER)
    shader_program = glCreateProgram()
    glAttachShader(shader_program, vertex_shader)
    glAttachShader(shader_program, fragment_shader)
    glLinkProgram(shader_program)
    link_success = glGetProgramiv(shader_program, GL_LINK_STATUS)
    if not link_success:
        error = glGetProgramInfoLog(shader_program).decode()
        print(f"Shader program linking error: {error}")
        raise RuntimeError("Shader program linking error")
    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)
    return shader_program

class Renderer:
    def __init__(self, screen_width, screen_height):
        # Create shader program
        self.colored_shader = create_shader_program(vertex_shader_colored_source, fragment_shader_colored_source)
        
        # Get uniform locations
        self.projection_loc = glGetUniformLocation(self.colored_shader, 'projection')
        
        # Create projection matrix (orthographic)
        self.projection_matrix = self.create_orthographic_matrix(0, screen_width, screen_height, 0, -1, 1)
        
        # Prepare buffers for colored triangles
        self.max_vertices = 1000  # Adjust as needed
        self.vertex_data = np.zeros(self.max_vertices, dtype=[('position', np.float32, 2), ('color', np.float32, 4)])
        self.vertex_count = 0
        
        # Create VAO and VBO
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.vertex_data.nbytes, None, GL_DYNAMIC_DRAW)
        
        # Position attribute
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, self.vertex_data.strides[0], ctypes.c_void_p(0))
        
        # Color attribute - Fixing the color offset
        color_offset = ctypes.c_void_p(self.vertex_data.dtype.fields['color'][1])
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 4, GL_FLOAT, GL_FALSE, self.vertex_data.strides[0], color_offset)
        
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        
        print(f"Colored Shader Program ID: {self.colored_shader}")
    
    def create_orthographic_matrix(self, left, right, bottom, top, near, far):
        matrix = np.identity(4, dtype=np.float32)
        matrix[0][0] = 2.0 / (right - left)
        matrix[1][1] = 2.0 / (top - bottom)
        matrix[2][2] = -2.0 / (far - near)
        matrix[3][0] = -(right + left) / (right - left)
        matrix[3][1] = -(top + bottom) / (top - bottom)
        matrix[3][2] = -(far + near) / (far - near)
        return matrix
    
    def add_colored_vertices(self, positions, colors):
        num_vertices = len(positions)
        if self.vertex_count + num_vertices > self.max_vertices:
            self.flush()
            if num_vertices > self.max_vertices:
                raise ValueError("Too many vertices to batch.")
        
        # Normalize colors
        normalized_colors = colors / 255.0  # Assuming colors are in 0-255 range
        
        # Add to buffer
        self.vertex_data['position'][self.vertex_count:self.vertex_count + num_vertices] = positions
        self.vertex_data['color'][self.vertex_count:self.vertex_count + num_vertices] = normalized_colors
        self.vertex_count += num_vertices
    
    def flush(self):
        if self.vertex_count == 0:
            return  # Nothing to draw
        
        glUseProgram(self.colored_shader)
        glUniformMatrix4fv(self.projection_loc, 1, GL_FALSE, self.projection_matrix)
        
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, self.vertex_count * self.vertex_data.dtype.itemsize, self.vertex_data[:self.vertex_count])
        
        glDrawArrays(GL_TRIANGLES, 0, self.vertex_count)
        
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        glUseProgram(0)
        
        self.vertex_count = 0
    
    def cleanup(self):
        glDeleteBuffers(1, [self.vbo])
        glDeleteVertexArrays(1, [self.vao])
        glDeleteProgram(self.colored_shader)

def main():
    pygame.init()
    
    # Request OpenGL 3.3 Core Profile
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
    
    # Create the display window with OpenGL context
    screen_width, screen_height = 800, 600
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.OPENGL | pygame.DOUBLEBUF)
    pygame.display.set_caption("OpenGL Color Test")
    
    # Create Renderer
    renderer = Renderer(screen_width, screen_height)
    
    # Define color arrays for each rectangle's vertices
    red_color = np.array([
        [255, 0, 0, 255],
        [255, 0, 0, 255],
        [255, 0, 0, 255],
        [255, 0, 0, 255],
        [255, 0, 0, 255],
        [255, 0, 0, 255],
    ], dtype=np.float32)

    green_color = np.array([
        [0, 255, 0, 255],
        [0, 255, 0, 255],
        [0, 255, 0, 255],
        [0, 255, 0, 255],
        [0, 255, 0, 255],
        [0, 255, 0, 255],
    ], dtype=np.float32)

    blue_color = np.array([
        [0, 0, 255, 255],
        [0, 0, 255, 255],
        [0, 0, 255, 255],
        [0, 0, 255, 255],
        [0, 0, 255, 255],
        [0, 0, 255, 255],
    ], dtype=np.float32)
    
    # Define rectangle vertices (two triangles)
    red_vertices = np.array([
        [100, 100],
        [300, 100],
        [300, 300],
        [300, 300],
        [100, 300],
        [100, 100],
    ], dtype=np.float32)
    
    green_vertices = np.array([
        [400, 100],
        [600, 100],
        [600, 300],
        [600, 300],
        [400, 300],
        [400, 100],
    ], dtype=np.float32)
    
    blue_vertices = np.array([
        [700, 100],
        [900, 100],
        [900, 300],
        [900, 300],
        [700, 300],
        [700, 100],
    ], dtype=np.float32)
    
    # Run the main loop
    running = True
    clock = pygame.time.Clock()
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Begin colored batch
        renderer.add_colored_vertices(red_vertices, red_color)
        renderer.add_colored_vertices(green_vertices, green_color)
        renderer.add_colored_vertices(blue_vertices, blue_color)
        
        # Flush and draw
        renderer.flush()
        
        # Swap buffers
        pygame.display.flip()
        clock.tick(60)  # Limit to 60 FPS
    
    # Cleanup
    renderer.cleanup()
    pygame.quit()

if __name__ == "__main__":
    main()
