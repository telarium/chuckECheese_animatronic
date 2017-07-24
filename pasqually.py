import os
import sys
import time
import platform
from threading import Thread
from pydispatch import dispatcher
from pasqually_movements import Movement
from pasqually_webIO import WebServer
from pasqually_networkManager import NetworkManagement
from pasqually_systemInfo import SystemInfo

class Pasqually():
	airCompressorOffHourStart = 1 # The hour of the day to switch off the air compressor. Change to None to disable.
	airCompressorOffHourEnd = 7 # The hour of the day to turn the air compressor back on after a restful evening. Change to None to disable.
	rebootHour = 2 # The hour of the day to reboot CHIP to reset everything. Change to None to disable.
	midiNotes = {}

	def __init__(self):
		os.system("i2cset -f -y 0 0x34 0x30 0x03") # Turn off AXP current limiting
		dispatcher.connect( self.onKeyEvent, signal="keyEvent", sender=dispatcher.Any )
		dispatcher.connect( self.onGamepadEvent, signal="gamepadEvent", sender=dispatcher.Any )
		dispatcher.connect( self.onConnectEvent, signal="connectEvent", sender=dispatcher.Any )
		self.webServer = WebServer()
		self.movements = Movement(self.webServer.socket)
		self.systemInfo = SystemInfo(self.webServer.socket)
		self.isRunning = True
		
		while self.isRunning:
			time.sleep(0.1)

	def onConnectEvent(self):
		print "User connected!"
		NetworkManagement().scanWifi()

	def onKeyEvent(self,key,val):
		try:
			self.movements.executeMovement(str(key).lower(), val)
		except:
			print "Invalid key!"

	def onGamepadEvent(self,buttonNum,val):
		self.movements.executeGamepad(int(buttonNum),int(val))

animatronic = Pasqually()
animatronic.webServer.shutdown()
quit()
