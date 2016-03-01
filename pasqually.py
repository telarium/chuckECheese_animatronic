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
def sendWebKey( key, val ):
	key = key.lower()
        movements.executeMovement( key, val )

pygame.init()
isRunning = True
clock = pygame.time.Clock()
gpio = GPIO()
movements = Movement(gpio)
webServer = WebServer(sendWebKey)

pygame.display.init()
size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
pygame.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
pygame.mixer.init(44100,-16,300, 1024)

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
