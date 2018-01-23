import os
import sys
import time
import platform
from threading import Thread
from pydispatch import dispatcher
from web_io import WebServer
from system_info import SystemInfo
from animatronic_movements import Movement

class Pasqually():
	airCompressorOffHourStart = 1 # The hour of the day to switch off the air compressor. Change to None to disable.
	airCompressorOffHourEnd = 7 # The hour of the day to turn the air compressor back on after a restful evening. Change to None to disable.
	rebootHour = 2 # The hour of the day to reboot CHIP to reset everything. Change to None to disable.
	midiNotes = {}

	def __init__(self):
		self.movements = Movement()
		self.webServer = WebServer()
		self.systemInfo = SystemInfo()
		self.setDispatchEvents()
		self.isRunning = True
		
		while self.isRunning:
			time.sleep(0.1)

	def setDispatchEvents(self):
		dispatcher.connect( self.onKeyEvent, signal="keyEvent", sender=dispatcher.Any )
		dispatcher.connect( self.onConnectEvent, signal="connectEvent", sender=dispatcher.Any )
		dispatcher.connect( self.onSystemInfoEvent, signal="systemInfoEvent", sender=dispatcher.Any )

	def onSystemInfoEvent(self,cpu,ram):
		print cpu

	def onConnectEvent(self):
		print "User connected!"

	def onKeyEvent(self,key,val):
		try:
			self.movements.executeMovement(str(key).lower(), val)
		except:
			print "Invalid key!"

animatronic = Pasqually()
animatronic.webServer.shutdown()
quit()
