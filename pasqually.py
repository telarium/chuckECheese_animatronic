import os
import sys
import time
import platform
from threading import Thread
from pasqually_setup import Setup
from pasqually_movements import Movement
from pasqually_webIO import WebServer

try:
    import pygame
except:
    os.system( "sudo apt-get -y install python-pygame" )
    import pygame

import pygame.locals as pgl
from pygame.locals import *

try:
    from libsoc import GPIO
except:
    path = os.path.dirname(os.path.realpath(sys.argv[0]))
    os.system( "sudo apt-get -y install libsoc2" )
    os.system( "sudo dpkg -i sudo dpkg -i " + path + "/libsoc2_0.6.5-python-1_armhf.deb " + path + "/python-libsoc2_0.6.5-python-1_armhf.deb" )

from libsoc import DIRECTION_OUTPUT

Setup()

airCompressorOffHourStart = 1 # The hour of the day to switch off the air compressor. Change to None to disable.
airCompressorOffHourEnd = 7 # The hour of the day to turn the air compressor back on after a restful evening. Change to None to disable.
rebootHour = 2 # The hour of the day to reboot CHIP to reset everything. Change to None to disable.
midiNotes = {}

def sendWebKey( key, val ):
	key = key.lower()
	movements.executeMovement( key, int(val) )

pygame.init()
isRunning = True
clock = pygame.time.Clock()
movements = Movement(GPIO,DIRECTION_OUTPUT)
webServer = WebServer(sendWebKey,movements.getMidiNotes)
pygame.display.init()
size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
pygame.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
pygame.mixer.quit()
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
            
webServer.shutdown()
pygame.quit()
quit()
