import os
import sys
import time
from pydispatch import dispatcher
from web_io import WebServer
from system_info import SystemInfo
from gpio import GPIO
from animatronic_movements import Movement
from gamepad_input import USBGamepadReader

class Pasqually:
	def __init__(self):
		self.gpio = GPIO()
		self.movements = Movement(self.gpio)
		self.webServer = WebServer()
		self.systemInfo = SystemInfo(self.webServer)
		self.gamepad = USBGamepadReader()
		self.setDispatchEvents()
		self.isRunning = True

	def setDispatchEvents(self):
		dispatcher.connect(self.onKeyEvent, signal='keyEvent', sender=dispatcher.Any)
		dispatcher.connect(self.onGamepadKeyEvent, signal='gamepadKeyEvent', sender=dispatcher.Any)
		dispatcher.connect(self.onMirroredModeToggle, signal='mirrorModeToggle', sender=dispatcher.Any)
		dispatcher.connect(self.onConnectEvent, signal='connectEvent', sender=dispatcher.Any)

	def onSystemInfoEvent(self, cpu, ram):
		print(cpu)

	def onConnectEvent(self):
		self.webServer.broadcast('movementInfo', self.movements.getAllMovementInfo())

	def onKeyEvent(self, key, val):
		# Receieve key events from the HTML front end and execute any specified movement
		try:
			self.movements.executeMovement(str(key).lower(), val)
		except Exception as e:
			print(f"Invalid key: {e}")

	def onGamepadKeyEvent(self, key, val):
		# Tell the HTML front end that a gamepad event occured so that it can play the corresponding MIDI note
		try:
			if self.movements.executeMovement(str(key).lower(), val):
				self.webServer.broadcast('gamepadKeyEvent', [str(key).lower(), val])
		except Exception as e:
			print(f"Invalid key: {e}")

	def onMirroredModeToggle(self):
		# Toggle animation mirrored mode (swapping left and right movements)
		bNewMirrorMode = not self.movements.bMirrored
		self.movements.setMirrored(bNewMirrorMode)

	def run(self):
		try:
			while self.isRunning:
				time.sleep(0.01)
		except KeyboardInterrupt:
			self.shutdown()

	def shutdown(self):
		if self.webServer:
			self.webServer.shutdown()

if __name__ == "__main__":
	animatronic = Pasqually()
	animatronic.run()
