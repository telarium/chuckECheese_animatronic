import os
import sys
import signal
import time
import threading
import pygame
from pydispatch import dispatcher
from web_io import WebServer
from system_info import SystemInfo
from gpio import GPIO
from animatronic_movements import Movement
from gamepad_input import USBGamepadReader
from show_player import ShowPlayer
from voice_input_processor import VoiceInputProcessor
from voice_event_handler import VoiceEventHandler
from wifi_management import WifiManagement

class Pasqually:
	def __init__(self):
		self.isRunning = True

		# Initialize pygame for managing audio playback
		pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
		pygame.display.init()
		pygame.display.set_mode((1, 1))

		self.voiceEvent = {
			'id': None,
			'value': None,
		}

		self.wifiAccessPoints = None
		

		# Initialize components
		self.gpio = GPIO()
		self.movements = Movement(self.gpio)
		self.webServer = WebServer()
		self.wifiManagement = WifiManagement()
		self.systemInfo = SystemInfo()
		self.gamepad = USBGamepadReader(self.movements, self.webServer)
		self.showPlayer = ShowPlayer(pygame)
		self.voiceInputProcessor = VoiceInputProcessor(pygame)
		self.voiceEventHandler = VoiceEventHandler(pygame, self.voiceInputProcessor)

		self.setDispatchEvents()

		# Handle SIGINT and SIGTERM for graceful shutdown
		signal.signal(signal.SIGINT, self.shutdown_signal_handler)
		signal.signal(signal.SIGTERM, self.shutdown_signal_handler)

		self.movements.setDefaultAnimation(True)

	def setDispatchEvents(self):
		dispatcher.connect(self.onKeyEvent, signal='keyEvent', sender=dispatcher.Any)
		dispatcher.connect(self.onSystemInfoUpdate, signal='systemInfoUpdate', sender=dispatcher.Any)
		dispatcher.connect(self.onVoiceInputEvent, signal='voiceInputEvent', sender=dispatcher.Any)
		dispatcher.connect(self.onMirroredModeToggle, signal='mirrorModeToggle', sender=dispatcher.Any)
		dispatcher.connect(self.onConnectEvent, signal='connectEvent', sender=dispatcher.Any)
		dispatcher.connect(self.onShowListLoad, signal='showListLoad', sender=dispatcher.Any)
		dispatcher.connect(self.onShowPlay, signal='showPlay', sender=dispatcher.Any)
		dispatcher.connect(self.onShowPause, signal='showPause', sender=dispatcher.Any)
		dispatcher.connect(self.onShowStop, signal='showStop', sender=dispatcher.Any)
		dispatcher.connect(self.onShowEnd, signal='showEnd', sender=dispatcher.Any)
		dispatcher.connect(self.onMirroredMode, signal='onMirroredMode', sender=dispatcher.Any)
		dispatcher.connect(self.onRetroMode, signal='onRetroMode', sender=dispatcher.Any)
		dispatcher.connect(self.onHeadNodInverted, signal='onHeadNodInverted', sender=dispatcher.Any)
		dispatcher.connect(self.onShowPlaybackMidiEvent, signal='showPlaybackMidiEvent', sender=dispatcher.Any)
		dispatcher.connect(self.onActivateWifiHotspot, signal='activateWifiHotspot', sender=dispatcher.Any)
		dispatcher.connect(self.onConnectToWifiNetwork, signal='connectToWifi', sender=dispatcher.Any)
		dispatcher.connect(self.onWebTTSEvent, signal='webTTSEvent', sender=dispatcher.Any)

	def run(self):
		try:
			while self.isRunning:
				if self.voiceEvent['id'] is not None:
					self.webServer.broadcast('voiceCommandUpdate', self.voiceEvent)
					self.voiceEvent['id'] = None
					self.voiceEvent['value'] = None

				# Broadcast a new wifi scan result if it has changed.
				if self.wifiManagement.get_wifi_access_points() != self.wifiAccessPoints:
					self.wifiAccessPoints = self.wifiManagement.get_wifi_access_points()
					self.webServer.broadcast('wifiScan', self.wifiAccessPoints)

				time.sleep(0.005)  # Regular sleep
		except Exception as e:
			print(f"Error in main loop: {e}")
		finally:
			self.shutdown()

	def shutdown_signal_handler(self, *args):
		"""Handle SIGINT or SIGTERM signals."""
		self.isRunning = False
		# Call shutdown asynchronously in a new thread
		threading.Thread(target=self.shutdown, daemon=True).start()

	def shutdown(self):
		try:
			# Shutdown child components
			if self.voiceInputProcessor:
				self.voiceInputProcessor.shutdown()
			if self.webServer:
				self.webServer.shutdown()
			if self.showPlayer:
				self.showPlayer.stopShow()

			sys.exit(0)
		except Exception as e:
			print(f"Error during shutdown: {e}")
			sys.exit(1)

	def onSystemInfoUpdate(self):
		self.webServer.broadcast('systemInfo', self.systemInfo.get())

	# Event handling methods
	def onVoiceInputEvent(self, id, value=None):
		self.voiceEvent['id'] = id
		self.voiceEvent['value'] = value

		# Play various animations to show Pasqually is listening and processing voice commands.
		if id == "idle" or id == "ttsComplete":
			# Don't do any animations while he's not doing any voice processing.
			self.movements.stopAllAnimationThreads()
		elif id == "wakeWord":
			# Twirls his mustache a bit to demonstrate wakeword acknowledgement.
			self.movements.playWakewordAcknowledgement()
			self.showPlayer.stopShow()  # Stop any playing shows
		elif id == "transcribing":
			# Start random blinking animation.
			self.movements.playBlinkAnimation()
		elif id == "command" or id == "ttsSubmitted":
			# Add some eye left/right movement animation.
			self.movements.playEyeLeftRightAnimation()
			self.movements.playBlinkAnimation()

		self.voiceEventHandler.triggerEvent(id, value)

	def onShowListLoad(self, showList):
		self.webServer.broadcast('showListLoaded', showList)

	def onShowPlay(self, showName):
		self.showPlayer.loadShow(showName)
		self.movements.setDefaultAnimation(False)

	def onShowStop(self):
		self.showPlayer.stopShow()
		self.movements.setDefaultAnimation(True)

	def onShowEnd(self):
		self.movements.setDefaultAnimation(True)

	def onShowPause(self):
		self.showPlayer.togglePause()

	def onShowPlaybackMidiEvent(self, midiNote, value):
		self.movements.executeMidiNote(midiNote, value)

	def onConnectEvent(self, client_ip):
		print(f"Web client connected from IP: {client_ip}")

		# Tell the web frontend what the current voice command status is.
		command = self.voiceInputProcessor.getLastVoiceCommand()
		self.voiceEvent['id'] = command['id']
		self.voiceEvent['value'] = command['value']

		self.onSystemInfoUpdate()
		self.showPlayer.getShowList()
		self.webServer.broadcast('movementInfo', self.movements.getAllMovementInfo())
		self.webServer.broadcast('wifiScan', self.wifiAccessPoints)
		self.wifiManagement.scan_wifi_access_points()

	def onKeyEvent(self, key, val):
		print(str(key).lower())
		# Receive key events from the HTML front end and execute any specified movement
		try:
			self.movements.executeMovement(str(key).lower(), val)
		except Exception as e:
			print(f"Invalid key: {e}")

	def onRetroMode(self, val):
		self.movements.setRetroMode(val)

	def onHeadNodInverted(self, val):
		self.gamepad.headNodInverted = val

	def onMirroredMode(self, val):
		self.movements.setMirrored(val)

	def onMirroredModeToggle(self):
		# Toggle animation mirrored mode (swapping left and right movements)
		bNewMirrorMode = not self.movements.bMirrored
		self.movements.setMirrored(bNewMirrorMode)

	def onActivateWifiHotspot(self, bActivate):
		if bActivate:
			self.wifiManagement.activate_hotspot()
		elif bActivate == False and self.wifiManagement.is_hotspot_active():
			self.wifiManagement.deactivate_hotspot_and_reconnect()

	def onConnectToWifiNetwork(self, ssid, password=None):
		self.wifiManagement.connect_to_wifi(ssid, password)

	def onWebTTSEvent(self, val):
		print(val)
		self.voiceInputProcessor.generate_and_play_tts(val)

if __name__ == "__main__":
	animatronic = Pasqually()
	animatronic.run()
