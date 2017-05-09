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
		self.webServer = WebServer(self.sendWebKey,self.getMidiNotes)
		self.movements = Movement()
		self.isRunning = True

		while self.isRunning:
			time.sleep(0.1)
 
 	def getMidiNotes(i):
 		print self
 		return "LKJLKSJDF"

	def sendWebKey(self,key, val):
		#try:
		key = key.lower()
		print key
		self.movements.executeMovement( key, int(val) )
		#except:
		#	pass

animatronic = Pasqually()
animatronic.webServer.shutdown()
quit()
