import os

# Supress annoying Pygame messages
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
if 'XDG_RUNTIME_DIR' not in os.environ:
	os.environ['XDG_RUNTIME_DIR'] = "/tmp"

import sys
import signal
import time
import threading
import pygame
import ctypes
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
		signal.signal(signal.SIGINT, self.shutdown)
		signal.signal(signal.SIGTERM, self.shutdown)

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
				# Broadcast a new wifi scan result if it has changed.
				if self.wifiManagement.get_wifi_access_points() != self.wifiAccessPoints:
					self.wifiAccessPoints = self.wifiManagement.get_wifi_access_points()
					self.webServer.broadcast('wifiScan', self.wifiAccessPoints)

				time.sleep(0.005)

		except Exception as e:
			print(f"Error in main loop: {e}")
		finally:
			print("Main loop exiting, calling shutdown...")
			self.shutdown()

	def shutdown(self, *args):
		try:
			self.isRunning = False  # Signal all loops to stop

			# Stop all dependent components
			if self.voiceInputProcessor:
				self.voiceInputProcessor.shutdown()

			if self.webServer:
				self.webServer.shutdown()

			if self.showPlayer:
				self.showPlayer.stopShow()

			# Ensure all non-main threads exit before quitting pygame
			for thread in threading.enumerate():
				if thread is not threading.main_thread():
					# If thread is still alive, force kill it
					if thread.is_alive():
						try:
							ctypes.pythonapi.PyThreadState_SetAsyncExc(
								ctypes.c_long(thread.ident), ctypes.py_object(SystemExit)
							)
						except Exception as e:
							print(f"Error stopping thread {thread.name}: {e}")

			pygame.mixer.quit()
			pygame.display.quit()
			pygame.quit()

			print("Shutdown complete. Exiting.")
			sys.exit(0)

		except Exception as e:
			print(f"Error during shutdown: {e}")
			sys.exit(1)


	def onSystemInfoUpdate(self):
		self.webServer.broadcast('systemInfo', self.systemInfo.get())

	# Event handling methods
	def onVoiceInputEvent(self, id, value=None):
		self.webServer.broadcast('voiceCommandUpdate',  {"id": id, "value": value})

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
		elif id == "llmSend":
			self.movements.playBlinkAnimation()
			self.movements.playEyeLeftRightAnimation()
		elif id == "speaking":
			self.movements.playNeckAnimation()
			self.movements.playEyeLeftRightAnimation()
			self.movements.playNeckAnimation()
		elif id == "command" or id == "ttsSubmitted":
			# Add some eye left/right movement animation.
			self.movements.playEyeLeftRightAnimation()
			self.movements.playBlinkAnimation()
			self.movements.playNeckAnimation()

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
		self.webServer.broadcast('voiceCommandUpdate', command)

		self.onSystemInfoUpdate()
		self.showPlayer.getShowList()
		self.webServer.broadcast('movementInfo', self.movements.getAllMovementInfo())
		self.webServer.broadcast('wifiScan', self.wifiAccessPoints)
		self.wifiManagement.scan_wifi_access_points()

	def onKeyEvent(self, key, val):
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
		dispatcher.send(signal="voiceInputEvent", id="ttsSubmitted")
		self.voiceInputProcessor.generate_and_play_tts(val)

if __name__ == "__main__":
	animatronic = Pasqually()
	animatronic.run()
