import os
import sys
import time
import platform
import pygame
import pygame.locals as pgl
from pygame.locals import *
from threading import Thread
from pasqually_movements import Movement
from pasqually_webIO import WebServer

class Pasqually():
	airCompressorOffHourStart = 1 # The hour of the day to switch off the air compressor. Change to None to disable.
	airCompressorOffHourEnd = 7 # The hour of the day to turn the air compressor back on after a restful evening. Change to None to disable.
	rebootHour = 2 # The hour of the day to reboot CHIP to reset everything. Change to None to disable.
	midiNotes = {}

	def __init__(self):
		pygame.init()
		self.isRunning = True
		self.clock = pygame.time.Clock()
		self.movements = Movement()
		self.webServer = WebServer(self.sendWebKey,self.movements.getMidiNotes)
		pygame.display.init()
		size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
		pygame.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
		pygame.mixer.quit()
		pygame.mixer.init(44100,-16,300, 1024)
		self.pygame = pygame

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
