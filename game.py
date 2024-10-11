import pygame
from constants import *

global screen


pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Circuit Simulator")
clock = pygame.time.Clock()