import os
import sys
import time
import platform
from threading import Thread
from pasqually_setup import Setup
from pasqually_movements import Movement
from pasqually_GPIO import GPIO
from pasqually_webIO import WebServer

try:
    import pygame
except:
    os.system( "sudo apt-get -y install python-pygame" )
    import pygame

import pygame.locals as pgl
from pygame.locals import *

Setup()

airCompressorOffHourStart = 1 # The hour of the day to switch off the air compressor. Change to None to disable.
airCompressorOffHourEnd = 7 # The hour of the day to turn the air compressor back on after a restful evening. Change to None to disable.
rebootHour = 2 # The hour of the day to reboot CHIP to reset everything. Change to None to disable.

pygame.init()
isRunning = True
clock = pygame.time.Clock()
width, height = 480,320
gpio = GPIO()
movements = Movement(gpio)
webServer = WebServer()

def sendWebKey( key, val ):
    if len(key) == 1:
        movements.executeMovement( key, val )

os.putenv('SDL_VIDEODRIVER', 'directfb')
pygame.display.set_mode((width, height), 0, 8)
pygame.display.set_caption('Pasqually')
pygame.mixer.init(44100,-16,300, 1024) # Initialize audio mixer for Pygame

while isRunning:
    try:
        val = None
        clock.tick(60)
        pygame.display.update()
    except:
        isRunning = False

    for event in pygame.event.get():
        if event.type == QUIT:
            isRunning = False            
        if ( event.type == pygame.KEYDOWN or event.type == pygame.KEYUP ):
            val = 0
            if event.type == pygame.KEYDOWN:
                val = 1
                
            sendWebKey( pygame.key.name(event.key), val )
            
gpio.cleanup()
webServer.shutdown()
pygame.quit()
quit()
