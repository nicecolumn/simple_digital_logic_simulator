# constants.py

# Screen dimensions
WIDTH, HEIGHT = 1440, 896

# Grid settings
GRID_SPACING = 100
MAX_GRID_POINTS = 20000

# Frame rate
FPS = 60

# Frequency for Clock objects
CLOCK_FREQUENCY = 16

# Colors (RGBA)
BACKGROUND_COLOR = (120, 120, 120, 255)

BLACK = (32, 32, 32, 255)
GREY = (122, 122, 122, 255)
DARK_GREY = (90, 90, 90, 255)
YELLOW = (156, 225, 0, 255)
WHITE = (245, 245, 245, 255)
LIGHTER_GREY = (180, 180, 180, 255)
LIGHTER_YELLOW = (200, 255, 50, 255)
LIGHTER_WHITE = (255, 255, 255, 255)
RED = (235, 0, 0, 255)
LIGHTER_RED = (255, 20, 20, 255)
GREEN = (60, 120, 60)
BLUE = (60, 60, 120)

# Transistor States (RGBA)
P_OFF = (120, 120, 60, 255)
P_ON = (200, 200, 100, 255)
N_OFF = (120, 60, 60, 255)
N_ON = (200, 100, 100, 255)

# Wire States (RGBA)
W_OFF = (120, 120, 120, 255)
W_ON = (220, 220, 220, 255)

# Clock Color (RGBA)
CLOCK_COLOR = LIGHTER_GREY  # (180, 180, 180, 255)

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
MODE_CLOCK = 'clock'

# Simulation Settings
SIMULATION_SPEED = 1  # number of frames between updates
