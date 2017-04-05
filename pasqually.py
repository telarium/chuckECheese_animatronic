import os
import sys
import time
import platform
from threading import Thread
from pasqually_movements import Movement
from pasqually_webIO import WebServer

class Pasqually():
	airCompressorOffHourStart = 1 # The hour of the day to switch off the air compressor. Change to None to disable.
	airCompressorOffHourEnd = 7 # The hour of the day to turn the air compressor back on after a restful evening. Change to None to disable.
	rebootHour = 2 # The hour of the day to reboot CHIP to reset everything. Change to None to disable.
	midiNotes = {}

	def __init__(self):
		self.isRunning = True
		self.movements = Movement()
		self.webServer = WebServer(self.sendWebKey,self.movements.getMidiNotes)

		while self.isRunning:
			time.sleep(0.1)
            
	def sendWebKey(self,key, val):
                key = key.lower()
                self.movements.executeMovement( key, int(val) )

animatronic = Pasqually()
animatronic.webServer.shutdown()
quit()
