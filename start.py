import os
import sys
import signal
import eventlet
from pydispatch import dispatcher
from web_io import WebServer
from system_info import SystemInfo
from gpio import GPIO
from animatronic_movements import Movement
from gamepad_input import USBGamepadReader
from show_player import ShowPlayer
from voice_control import VoiceControl

class Pasqually:
	def __init__(self):
		self.isRunning = True

		# Initialize components
		self.setDispatchEvents()
		self.gpio = GPIO()
		self.movements = Movement(self.gpio)
		self.webServer = WebServer()
		self.systemInfo = SystemInfo(self.webServer)
		self.gamepad = USBGamepadReader()
		self.showPlayer = ShowPlayer()
		self.voiceControl = VoiceControl()

		# Handle SIGINT and SIGTERM for graceful shutdown
		signal.signal(signal.SIGINT, self.shutdown_signal_handler)
		signal.signal(signal.SIGTERM, self.shutdown_signal_handler)

	def setDispatchEvents(self):
		dispatcher.connect(self.onKeyEvent, signal='keyEvent', sender=dispatcher.Any)
		dispatcher.connect(self.onGamepadKeyEvent, signal='gamepadKeyEvent', sender=dispatcher.Any)
		dispatcher.connect(self.onMirroredModeToggle, signal='mirrorModeToggle', sender=dispatcher.Any)
		dispatcher.connect(self.onConnectEvent, signal='connectEvent', sender=dispatcher.Any)
		dispatcher.connect(self.onShowListLoad, signal='showListLoad', sender=dispatcher.Any)
		dispatcher.connect(self.onShowPlay, signal='showPlay', sender=dispatcher.Any)
		dispatcher.connect(self.onShowPause, signal='showPause', sender=dispatcher.Any)
		dispatcher.connect(self.onShowStop, signal='showStop', sender=dispatcher.Any)
		dispatcher.connect(self.onShowPlaybackMidiEvent, signal='showPlaybackMidiEvent', sender=dispatcher.Any)

	def run(self):
		try:
			while self.isRunning:
				eventlet.sleep(0.01)  # Eventlet-friendly sleep
		except Exception as e:
			print(f"Error in main loop: {e}")
		finally:
			self.shutdown()

	def shutdown_signal_handler(self, *args):
		"""Handle SIGINT or SIGTERM signals."""
		self.isRunning = False
		eventlet.spawn(self.shutdown)  # Run shutdown asynchronously

	def shutdown(self):
		"""Clean up resources and terminate components."""
		try:
			# Shutdown child components
			if self.voiceControl:
				self.voiceControl.cleanup()
			if self.webServer:
				self.webServer.shutdown()
			if self.showPlayer:
				self.showPlayer.stopShow()

			sys.exit(0)
		except Exception as e:
			print(f"Error during shutdown: {e}")
			sys.exit(1)

	# Event handling methods
	def onShowListLoad(self, showList):
		self.webServer.broadcast('showListLoaded', showList)

	def onShowPlay(self, showName):
		self.showPlayer.loadShow(showName)

	def onShowStop(self):
		self.showPlayer.stopShow()

	def onShowPause(self):
		self.showPlayer.togglePause()

	def onShowPlaybackMidiEvent(self, midiNote, value):
		self.movements.executeMidiNote(midiNote, value)

	def onConnectEvent(self, client_ip):
		print(f"Web client connected from IP: {client_ip}")
		self.showPlayer.getShowList()
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


if __name__ == "__main__":
	animatronic = Pasqually()
	animatronic.run()
