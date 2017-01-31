import os
import sys
import time
import platform
from threading import Thread
from pasqually_setup import Setup
from pasqually_movements import Movement
from pasqually_webIO import WebServer

import pygame
import pygame.locals as pgl
from pygame.locals import *

try:
	import CHIP_IO.GPIO as GPIO
except:
	path = os.path.dirname(os.path.realpath(sys.argv[0]))
	os.system('sudo apt-get install git build-essential python-dev python-pip flex bison chip-dt-overlays -y')
	os.system('git clone https://github.com/NextThingCo/dtc ' + path + '/dtc')
	os.system('cd ' + path + '/dtc && sudo make && sudo make install PREFIX=/usr')
	os.system('git clone git://github.com/xtacocorex/CHIP_IO.git ' + path + '/CHIP_IO')
	os.system('cd ' + path + '/CHIP_IO && sudo python setup.py install')
	os.system('cd ' + path + ' && sudo rm -rf ' + path + '/CHIP_IO')

class Pasqually():
	Setup()

	airCompressorOffHourStart = 1 # The hour of the day to switch off the air compressor. Change to None to disable.
	airCompressorOffHourEnd = 7 # The hour of the day to turn the air compressor back on after a restful evening. Change to None to disable.
	rebootHour = 2 # The hour of the day to reboot CHIP to reset everything. Change to None to disable.
	midiNotes = {}

	def __init__(self):
		pygame.init()
		self.isRunning = True
		self.clock = pygame.time.Clock()
		self.movements = Movement()

<<<<<<< HEAD
pygame.init()
isRunning = True
clock = pygame.time.Clock()
movements = Movement()
webServer = WebServer(sendWebKey,movements.getMidiNotes)
pygame.display.init()
size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
pygame.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
pygame.mixer.quit()
pygame.mixer.init(44100,-16,300, 1024)
=======
		self.webServer = WebServer(self.sendWebKey,self.movements.getMidiNotes)
		pygame.display.init()
		size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
		pygame.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
		pygame.mixer.quit()
		pygame.mixer.init(44100,-16,300, 1024)
		self.pygame = pygame
>>>>>>> 49a498642c8fcad72efea45be543ee23a0fdb28f

		while self.isRunning:
    			try:
       				val = None
				self.clock.tick(60)
        			pygame.display.update()
			except:
        			self.isRunning = False
		
			for event in pygame.event.get():
        			if event.type == QUIT:
            				self.isRunning = False            
        			if ( event.type == pygame.KEYDOWN or event.type == pygame.KEYUP ):
            				val = 0
            			if event.type == pygame.KEYDOWN:
                			val = 1
                
            			self.sendWebKey( pygame.key.name(event.key), val )
            
	def sendWebKey(self,key, val):
                key = key.lower()
                self.movements.executeMovement( key, int(val) )

animatronic = Pasqually()
animatronic.webServer.shutdown()
animatronic.pygame.quit()
quit()
